"""LangGraph-based reasoning agent for documentation Q&A."""

import logging
from typing import Optional

from openai import OpenAI
from langgraph.graph import StateGraph, START, END

try:
    from langsmith.wrappers import wrap_openai as _wrap_openai
except ImportError:
    def _wrap_openai(client):  # passthrough when langsmith not installed
        return client

from compass.agent.state import AgentState, AgentToolCall
from compass.config import settings

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """LangGraph-based reasoning agent using DeepSeek via OpenRouter."""

    # Budget constraints
    MAX_TOOL_CALLS_PER_QUERY = 20
    MAX_FILE_READS_PER_QUERY = 8

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tool_calls: int = MAX_TOOL_CALLS_PER_QUERY,
        max_file_reads: int = MAX_FILE_READS_PER_QUERY,
    ):
        """Initialize the reasoning agent.

        Args:
            model: Model name (defaults to settings.reasoning_model)
            api_key: OpenRouter API key (defaults to settings.openrouter_api_key)
            base_url: OpenRouter base URL (defaults to settings.openrouter_base_url)
            max_tool_calls: Maximum tool calls per query
            max_file_reads: Maximum file reads per query
        """
        raw_client = OpenAI(
            api_key=api_key or settings.openrouter_api_key,
            base_url=base_url or settings.openrouter_base_url,
        )
        self.client = _wrap_openai(raw_client)
        self.model = model or settings.reasoning_model
        self.max_tool_calls = max_tool_calls
        self.max_file_reads = max_file_reads

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("process_query", self._process_query)
        workflow.add_node("plan_tools", self._plan_tools)
        workflow.add_node("execute_tools", self._execute_tools)
        workflow.add_node("generate_answer", self._generate_answer)
        workflow.add_node("finalize", self._finalize)

        # Add edges
        workflow.add_edge(START, "process_query")
        workflow.add_edge("process_query", "plan_tools")
        workflow.add_conditional_edges(
            "plan_tools",
            self._should_execute_tools,
            {
                "execute": "execute_tools",
                "skip": "generate_answer",
            },
        )
        workflow.add_edge("execute_tools", "generate_answer")
        workflow.add_edge("generate_answer", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _process_query(self, state: AgentState) -> dict:
        """Process and validate the initial query.

        Args:
            state: Current agent state

        Returns:
            Updated state dict
        """
        logger.info(f"Processing query: {state.query}")
        logger.info(f"Variant selected: {state.variant}")

        # Validate variant
        if state.variant not in ["CloudNative", "ServerBased"]:
            logger.warning(f"Invalid variant: {state.variant}, defaulting to CloudNative")
            state.variant = "CloudNative"

        return {"query": state.query, "variant": state.variant}

    def _plan_tools(self, state: AgentState) -> dict:
        """Plan which tools to use based on the query.

        Args:
            state: Current agent state

        Returns:
            Updated state dict with tool plan
        """
        logger.info(f"Planning tools for query: {state.query}")

        # For now, just mark that tools should be executed
        # In production, this would be more sophisticated
        tool_plan = {
            "needs_search": True,
            "needs_document_read": True,
            "tools": ["lexical_search", "read_html"],
        }

        return {"tool_calls": state.tool_calls, "search_results": tool_plan}

    def _should_execute_tools(self, state: AgentState) -> str:
        """Determine if tools should be executed.

        Args:
            state: Current agent state

        Returns:
            "execute" or "skip"
        """
        if state.tool_calls_used >= self.max_tool_calls:
            logger.warning("Tool call budget exhausted")
            return "skip"

        # Check if we have tool calls to make
        if state.search_results:
            return "execute"

        return "skip"

    def _execute_tools(self, state: AgentState) -> dict:
        """Execute planned tools.

        Args:
            state: Current agent state

        Returns:
            Updated state dict
        """
        logger.info(f"Executing tools (calls used: {state.tool_calls_used})")

        # Placeholder: in production, actually execute tools
        # For now, just simulate tool execution
        tool_call = AgentToolCall(
            tool_name="lexical_search",
            input={"query": state.query, "variant": state.variant},
            output={"results": []},
        )

        updated_calls = state.tool_calls + [tool_call]
        updated_tool_calls_used = state.tool_calls_used + 1

        return {
            "tool_calls": updated_calls,
            "tool_calls_used": updated_tool_calls_used,
            "current_tool_output": "Tool executed",
        }

    def _generate_answer(self, state: AgentState) -> dict:
        """Generate final answer using Claude.

        Args:
            state: Current agent state

        Returns:
            Updated state dict
        """
        logger.info("Generating answer from Claude")

        # Build context from tool results
        context = "\n".join(
            [f"Tool: {call.tool_name}\nOutput: {call.output}" for call in state.tool_calls]
        )

        prompt = f"""Answer the user's question based on the documentation.

Query: {state.query}
Variant: {state.variant}
Documentation Context:
{context}

Provide a clear, concise answer with citations where applicable."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            answer = response.choices[0].message.content
            return {"final_answer": answer}

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return {"final_answer": "Unable to generate answer at this time."}

    def _finalize(self, state: AgentState) -> dict:
        """Finalize the response.

        Args:
            state: Current agent state

        Returns:
            Updated state dict
        """
        logger.info("Finalizing response")

        # Log statistics
        logger.info(
            f"Query completed - Tool calls: {state.tool_calls_used}/{self.max_tool_calls}, "
            f"File reads: {state.file_reads_used}/{self.max_file_reads}"
        )

        return {"final_answer": state.final_answer}

    def query(self, question: str, variant: str = "CloudNative") -> dict:
        """Process a question and return the answer.

        Args:
            question: User question
            variant: Documentation variant ("CloudNative" or "ServerBased")

        Returns:
            Dict with answer, citations, and metadata
        """
        # Create initial state
        initial_state = AgentState(
            messages=[],
            query=question,
            variant=variant,
            tool_calls=[],
            tool_calls_used=0,
            file_reads_used=0,
        )

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        return {
            "answer": final_state.get("final_answer"),
            "variant": final_state.get("variant"),
            "tool_calls": len(final_state.get("tool_calls", [])),
            "citations": final_state.get("citations", []),
        }
