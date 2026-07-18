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
        tools: Optional[object] = None,
    ):
        """Initialize the reasoning agent.

        Args:
            model: Model name (defaults to settings.reasoning_model)
            api_key: OpenRouter API key (defaults to settings.openrouter_api_key)
            base_url: OpenRouter base URL (defaults to settings.openrouter_base_url)
            max_tool_calls: Maximum tool calls per query
            max_file_reads: Maximum file reads per query
            tools: ToolRegistry with search/read tools wired to the real corpus.
                Without it the agent still runs but tool steps are skipped.
        """
        raw_client = OpenAI(
            api_key=api_key or settings.openrouter_api_key,
            base_url=base_url or settings.openrouter_base_url,
        )
        self.client = _wrap_openai(raw_client)
        self.model = model or settings.reasoning_model
        self.max_tool_calls = max_tool_calls
        self.max_file_reads = max_file_reads
        self.tools = tools

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

        The default plan is search-then-read: one lexical search over the
        variant's corpus, followed by reading the top documents (bounded by
        the file-read budget).

        Args:
            state: Current agent state

        Returns:
            Updated state dict with tool plan
        """
        logger.info(f"Planning tools for query: {state.query}")

        plan = [{"tool": "lexical_search", "args": {"query": state.query, "variant": state.variant, "limit": 8}}]
        if "compare" in state.query.lower() or "difference between" in state.query.lower():
            plan.append({"tool": "compare_variants", "args": {"topic": state.query}})

        return {"tool_calls": state.tool_calls, "search_results": plan}

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
        """Execute the planned tools via the ToolRegistry, respecting budgets.

        Runs the planned calls (search/compare), then follows up by reading
        the top search hits with read_html — up to the file-read budget.

        Args:
            state: Current agent state

        Returns:
            Updated state dict
        """
        logger.info(f"Executing tools (calls used: {state.tool_calls_used})")

        calls = list(state.tool_calls)
        tool_calls_used = state.tool_calls_used
        file_reads_used = state.file_reads_used

        if self.tools is None:
            logger.warning("No ToolRegistry injected — skipping tool execution")
            return {
                "tool_calls": calls,
                "tool_calls_used": tool_calls_used,
                "current_tool_output": "No tools available",
            }

        plan = state.search_results if isinstance(state.search_results, list) else []
        search_hits: list[dict] = []

        for step in plan:
            if tool_calls_used >= self.max_tool_calls:
                break
            result = self.tools.execute_tool(step["tool"], **step["args"])
            tool_calls_used += 1
            calls.append(
                AgentToolCall(
                    tool_name=step["tool"],
                    input=step["args"],
                    output=result.data if result.success else {"error": result.error},
                )
            )
            if step["tool"] == "lexical_search" and result.success:
                search_hits = result.data.get("results", [])

        # Read the top hits for full context (budget-bounded)
        for hit in search_hits[:3]:
            if tool_calls_used >= self.max_tool_calls or file_reads_used >= self.max_file_reads:
                break
            result = self.tools.execute_tool(
                "read_html", file_path=hit["path"], variant=state.variant
            )
            tool_calls_used += 1
            file_reads_used += 1
            calls.append(
                AgentToolCall(
                    tool_name="read_html",
                    input={"file_path": hit["path"], "variant": state.variant},
                    output=result.data if result.success else {"error": result.error},
                )
            )

        return {
            "tool_calls": calls,
            "tool_calls_used": tool_calls_used,
            "file_reads_used": file_reads_used,
            "current_tool_output": f"Executed {tool_calls_used} tool calls",
        }

    def _generate_answer(self, state: AgentState) -> dict:
        """Generate the final answer from tool outputs (structured, cited).

        Args:
            state: Current agent state

        Returns:
            Updated state dict
        """
        logger.info("Generating answer")

        # Collect sources: full documents read via read_html, else search previews
        hits: list[dict] = []
        previews: dict[str, dict] = {}
        for call in state.tool_calls:
            if not isinstance(call.output, dict) or "error" in call.output:
                continue
            if call.tool_name == "lexical_search":
                for r in call.output.get("results", []):
                    if not isinstance(r, dict) or "path" not in r:
                        continue
                    previews[r["path"]] = {
                        "title": r.get("title", r["path"]),
                        "path": r["path"],
                        "passage": r.get("preview", ""),
                    }
            elif call.tool_name == "read_html":
                path = call.input.get("file_path", "")
                hits.append(
                    {
                        "title": call.output.get("title", path),
                        "path": path,
                        "passage": call.output.get("content", "")[:1500],
                    }
                )
        read_paths = {h["path"] for h in hits}
        hits.extend(p for path, p in previews.items() if path not in read_paths)
        hits = hits[:6]

        from compass.retrieval.answer import generate_answer

        answer, _ = generate_answer(state.query, state.variant, hits, model=self.model)
        citations = [
            {
                "doc_id": h["path"],
                "title": h["title"],
                "path": h["path"],
                "content": h["passage"][:500],
            }
            for h in hits
        ]
        return {"final_answer": answer, "citations": citations}

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

    def query(self, question: str, variant: str = "CloudNative", identity: str = "anonymous") -> dict:
        """Process a question and return the answer.

        Args:
            question: User question
            variant: Documentation variant ("CloudNative" or "ServerBased")
            identity: Caller identity for rate limiting

        Returns:
            Dict with answer, citations, and metadata
        """
        # Input guardrail — refuse injection/harmful/malformed before any tool runs
        from compass.guardrails import GuardrailPipeline

        guardrails = getattr(self, "guardrails", None) or GuardrailPipeline()
        self.guardrails = guardrails
        pre = guardrails.check_request(question, identity=identity)
        if pre.blocked:
            return {
                "answer": pre.message,
                "variant": variant,
                "tool_calls": 0,
                "citations": [],
                "guardrail": pre.to_audit(),
            }
        question = pre.sanitized_text or question

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
