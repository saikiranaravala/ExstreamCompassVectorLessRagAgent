"""Tests for LangGraph reasoning agent."""

import pytest

from compass.agent.agent import ReasoningAgent
from compass.agent.state import AgentState, AgentToolCall


class TestAgentState:
    """Test AgentState dataclass."""

    def test_create_state(self):
        """Test creating agent state."""
        state = AgentState(
            messages=[],
            query="What is Python?",
            variant="CloudNative",
        )

        assert state.query == "What is Python?"
        assert state.variant == "CloudNative"
        assert state.tool_calls == []
        assert state.tool_calls_used == 0
        assert state.file_reads_used == 0

    def test_state_with_tool_calls(self):
        """Test state with tool call records."""
        tool_call = AgentToolCall(
            tool_name="lexical_search",
            input={"query": "Python"},
            output={"results": []},
        )

        state = AgentState(
            messages=[],
            query="What is Python?",
            variant="CloudNative",
            tool_calls=[tool_call],
            tool_calls_used=1,
        )

        assert len(state.tool_calls) == 1
        assert state.tool_calls[0].tool_name == "lexical_search"
        assert state.tool_calls_used == 1

    def test_tool_call_record(self):
        """Test AgentToolCall dataclass."""
        call = AgentToolCall(
            tool_name="read_html",
            input={"path": "docs/intro.html"},
            output={"content": "Document content"},
        )

        assert call.tool_name == "read_html"
        assert call.input["path"] == "docs/intro.html"
        assert call.output["content"] == "Document content"


class TestReasoningAgent:
    """Test ReasoningAgent class."""

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = ReasoningAgent()

        assert agent.model == "claude-opus-4-7"
        assert agent.max_tool_calls == ReasoningAgent.MAX_TOOL_CALLS_PER_QUERY
        assert agent.max_file_reads == ReasoningAgent.MAX_FILE_READS_PER_QUERY

    def test_agent_with_custom_model(self):
        """Test agent with custom model."""
        agent = ReasoningAgent(model="claude-sonnet-4-6")

        assert agent.model == "claude-sonnet-4-6"

    def test_agent_with_custom_budgets(self):
        """Test agent with custom budget limits."""
        agent = ReasoningAgent(max_tool_calls=10, max_file_reads=5)

        assert agent.max_tool_calls == 10
        assert agent.max_file_reads == 5

    def test_graph_is_compiled(self):
        """Test that the graph is compiled."""
        agent = ReasoningAgent()

        assert agent.graph is not None
        # Graph should be runnable
        assert hasattr(agent.graph, "invoke")

    def test_process_query_node(self):
        """Test query processing node."""
        agent = ReasoningAgent()

        state = AgentState(
            messages=[],
            query="What is machine learning?",
            variant="CloudNative",
        )

        result = agent._process_query(state)

        assert result["query"] == "What is machine learning?"
        assert result["variant"] == "CloudNative"

    def test_process_query_validates_variant(self):
        """Test that query processing validates variant."""
        agent = ReasoningAgent()

        state = AgentState(
            messages=[],
            query="Test query",
            variant="InvalidVariant",
        )

        result = agent._process_query(state)

        # Should default to CloudNative on invalid variant
        assert result["variant"] == "CloudNative"

    def test_plan_tools_node(self):
        """Test tool planning node."""
        agent = ReasoningAgent()

        state = AgentState(
            messages=[],
            query="Find documentation about X",
            variant="CloudNative",
            tool_calls=[],
        )

        result = agent._plan_tools(state)

        assert "search_results" in result
        assert result["search_results"]["needs_search"] is True

    def test_should_execute_tools_within_budget(self):
        """Test tool execution decision within budget."""
        agent = ReasoningAgent(max_tool_calls=20)

        state = AgentState(
            messages=[],
            query="Test",
            variant="CloudNative",
            tool_calls_used=5,
            search_results={"some": "plan"},
        )

        decision = agent._should_execute_tools(state)

        assert decision == "execute"

    def test_should_execute_tools_budget_exceeded(self):
        """Test tool execution decision when budget exceeded."""
        agent = ReasoningAgent(max_tool_calls=10)

        state = AgentState(
            messages=[],
            query="Test",
            variant="CloudNative",
            tool_calls_used=10,
            search_results={"some": "plan"},
        )

        decision = agent._should_execute_tools(state)

        assert decision == "skip"

    def test_execute_tools_node(self):
        """Test tool execution node."""
        agent = ReasoningAgent()

        state = AgentState(
            messages=[],
            query="Search for Python",
            variant="CloudNative",
            tool_calls=[],
            tool_calls_used=0,
            search_results={"plan": "search"},
        )

        result = agent._execute_tools(state)

        assert "tool_calls" in result
        assert "tool_calls_used" in result
        assert result["tool_calls_used"] == 1

    def test_generate_answer_node(self):
        """Test answer generation node."""
        agent = ReasoningAgent()

        state = AgentState(
            messages=[],
            query="What is Python?",
            variant="CloudNative",
            tool_calls=[
                AgentToolCall(
                    tool_name="search",
                    input={"query": "Python"},
                    output={"results": ["Python is a language"]},
                )
            ],
        )

        result = agent._generate_answer(state)

        assert "final_answer" in result
        # Answer should be a string (or placeholder if API fails)
        assert isinstance(result["final_answer"], str)

    def test_finalize_node(self):
        """Test finalization node."""
        agent = ReasoningAgent()

        state = AgentState(
            messages=[],
            query="Test",
            variant="CloudNative",
            final_answer="This is the answer",
            tool_calls_used=3,
            file_reads_used=2,
        )

        result = agent._finalize(state)

        assert "final_answer" in result
        assert result["final_answer"] == "This is the answer"

    def test_query_integration(self):
        """Test end-to-end query processing."""
        agent = ReasoningAgent()

        result = agent.query(
            "What is machine learning?",
            variant="CloudNative",
        )

        assert "answer" in result
        assert "variant" in result
        assert "tool_calls" in result
        assert result["variant"] == "CloudNative"
        assert isinstance(result["tool_calls"], int)

    def test_query_with_server_based_variant(self):
        """Test query with ServerBased variant."""
        agent = ReasoningAgent()

        result = agent.query(
            "How do I set up the server?",
            variant="ServerBased",
        )

        assert result["variant"] == "ServerBased"
        assert isinstance(result["answer"], str)

    def test_agent_budget_constants(self):
        """Test agent budget constants."""
        assert ReasoningAgent.MAX_TOOL_CALLS_PER_QUERY == 20
        assert ReasoningAgent.MAX_FILE_READS_PER_QUERY == 8
