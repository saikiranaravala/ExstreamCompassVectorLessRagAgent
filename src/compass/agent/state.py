"""Agent state management."""

from dataclasses import dataclass, field
from typing import Any, Optional

from langgraph.graph import MessagesState


@dataclass
class AgentToolCall:
    """Record of a tool call made by the agent."""

    tool_name: str
    input: dict
    output: Any
    timestamp: Optional[int] = None


@dataclass
class AgentState(MessagesState):
    """State for the reasoning agent.

    Extends LangGraph MessagesState with additional fields for
    query context, tool tracking, and budgets.
    """

    # Query context
    query: str = ""
    variant: str = ""  # "CloudNative" or "ServerBased"

    # Tool tracking
    tool_calls: list[AgentToolCall] = field(default_factory=list)
    current_tool_output: Optional[str] = None

    # Budget tracking
    tool_calls_used: int = 0
    file_reads_used: int = 0

    # Results
    final_answer: Optional[str] = None
    citations: list[dict] = field(default_factory=list)

    # Metadata
    search_results: list[dict] = field(default_factory=list)
