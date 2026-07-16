"""Agent state management."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentToolCall:
    """Record of a tool call made by the agent."""

    tool_name: str
    input: dict
    output: Any
    timestamp: Optional[int] = None


@dataclass
class AgentState:
    """State for the reasoning agent.

    A plain dataclass (LangGraph supports dataclass state schemas natively).
    Deliberately does NOT extend MessagesState: that is a TypedDict in current
    LangGraph versions, which silently turns instances into dicts and breaks
    attribute access.
    """

    # Conversation context
    messages: list = field(default_factory=list)

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

    # Tool plan produced by _plan_tools (list of {tool, args} steps)
    search_results: list[dict] = field(default_factory=list)
