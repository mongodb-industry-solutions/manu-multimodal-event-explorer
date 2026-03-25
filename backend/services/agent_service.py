"""
Agent Service for Chatbot with Tool Use (Claude via Bedrock)
Implements a proper agentic loop with tool calling and execution trace.
Supports both batch (run) and real-time streaming (run_stream) modes.

Tool Discovery
--------------
Tools are registered via the @register_tool decorator and stored in TOOL_REGISTRY.
AgentService reads from TOOL_REGISTRY at call time, so adding a new tool requires
only a single decorated function — no manual synchronisation of separate handler/schema dicts.
"""
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Tuple, Generator

from bedrock.anthropic_chat_completions import BedrockAnthropicChatCompletions
from services.search_service import SearchService
from models.search import SearchRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool registry — central source of truth for all agent tools
# ---------------------------------------------------------------------------


@dataclass
class Tool:
    """A registered agent tool."""
    name: str
    description: str
    input_schema: dict
    handler: Callable
    requires_approval: bool = field(default=False)  # set True to enable HITL for this tool


# Global registry: tool_name → Tool
TOOL_REGISTRY: Dict[str, Tool] = {}

# ---------------------------------------------------------------------------
# Human-in-the-Loop state — one Event per pending tool call, keyed by
# "{request_id}:{tool_id}".  Each user's stream generates its own request_id,
# so concurrent users never share state.
# ---------------------------------------------------------------------------

APPROVAL_TIMEOUT_SECONDS = 60  # auto-reject if no response within this window

_pending_approvals: Dict[str, threading.Event] = {}  # approval_key → Event
_approval_decisions: Dict[str, bool] = {}            # approval_key → approved?


def resolve_approval(approval_key: str, approved: bool) -> bool:
    """Signal a waiting run_stream() call with the user's decision.

    Called by the POST /api/chat/approve route.

    Returns:
        True  — the approval key was found and the event was set.
        False — the key is unknown (already timed out, or invalid).
    """
    event = _pending_approvals.get(approval_key)
    if event is None:
        return False
    _approval_decisions[approval_key] = approved
    event.set()
    return True


def register_tool(name: str, description: str, input_schema: dict,
                  requires_approval: bool = False) -> Callable:
    """Decorator that registers a function as an agent tool.

    Usage::

        @register_tool(
            name="my_tool",
            description="Does something useful.",
            input_schema={"type": "object", "properties": {...}, "required": [...]},
        )
        def my_tool(param: str) -> dict:
            ...

    The decorated function is stored in TOOL_REGISTRY under *name* and is
    automatically available to AgentService without any further changes.
    """
    def decorator(fn: Callable) -> Callable:
        TOOL_REGISTRY[name] = Tool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=fn,
            requires_approval=requires_approval,
        )
        logger.debug(f"Registered tool: {name}")
        return fn
    return decorator

# ---------------------------------------------------------------------------
# Tool implementations — each decorated with @register_tool
# ---------------------------------------------------------------------------

search_service = SearchService()


@register_tool(
    name="search_events",
    description=(
        "Search for driving events in the MongoDB Atlas database using natural language. "
        "Use this for questions about specific conditions, rare events, weather, time of day, or seasons."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language search query, e.g. 'foggy night on highway'"},
            "limit": {"type": "integer", "description": "Max number of results (default 5, max 10)"},
            "domain": {"type": "string", "description": "Domain to search in (default 'adas')"},
        },
        "required": ["query"],
    },
)
def _search_events(query: str, limit: int = 5, domain: str = "adas") -> List[Dict[str, Any]]:
    """Search events by natural language query using hybrid search."""
    req = SearchRequest(
        query=query,
        limit=min(limit, 10),
        domain=domain,
        use_vector_search=True,
        use_text_search=True,
        use_reranker=False,
    )
    resp = search_service.search(req)
    return [
        {
            "event_id": r.event_id,
            "description": r.text_description,
            "season": r.season,
            "time_of_day": r.time_of_day,
            "weather": r.weather,
            "rarity_score": r.rarity_score,
            "score": round(r.scores.combined_score, 4),
        }
        for r in resp.results
    ]


@register_tool(
    name="get_stats",
    description="Get dataset statistics: distribution of seasons, times of day, weather, and rarity scores.",
    input_schema={"type": "object", "properties": {}, "required": []},
)
def _get_stats() -> Dict[str, Any]:
    """Get dataset statistics across ALL documents using a MongoDB $facet aggregation.

    This replaces the old search-based sampling (which only looked at 20 results)
    with a full collection scan so distributions are always accurate.
    """
    return search_service.get_dataset_distributions()


@register_tool(
    name="compare_scenarios",
    description="Compare two different driving scenarios side by side.",
    requires_approval=True,   # ← HITL demo: user must approve before this runs
    input_schema={
        "type": "object",
        "properties": {
            "query1": {"type": "string", "description": "First scenario query"},
            "query2": {"type": "string", "description": "Second scenario query"},
            "limit": {"type": "integer", "description": "Results per scenario (default 3)"},
            "domain": {"type": "string", "description": "Domain (default 'adas')"},
        },
        "required": ["query1", "query2"],
    },
)
def _compare_scenarios(query1: str, query2: str, limit: int = 3, domain: str = "adas") -> Dict[str, Any]:
    """Compare two driving scenarios."""
    return {
        "scenario_1": {"query": query1, "results": _search_events(query1, limit, domain)},
        "scenario_2": {"query": query2, "results": _search_events(query2, limit, domain)},
    }

SYSTEM_PROMPT = (
    "You are the MongoDB AI Agent for a multimodal autonomous driving event explorer. "
    "The database contains driving events with metadata: season, time_of_day, weather, and rarity_score. "
    "Always use the available tools to answer questions with real data from the database. "
    "For rare events, search for low-frequency conditions like night + rain, or use get_stats to see distributions. "
    "Be concise but informative. Explain what you found and why it matters."
)

# ---------------------------------------------------------------------------
# Agent Service
# ---------------------------------------------------------------------------


class AgentService:
    MAX_ITERATIONS = 6

    def __init__(self):
        self.llm = BedrockAnthropicChatCompletions()

    # ------------------------------------------------------------------
    # Tool discovery helpers
    # ------------------------------------------------------------------

    @staticmethod
    def list_tools() -> List[Dict[str, Any]]:
        """Return a summary of all registered tools for display or inspection.

        Each entry contains the tool's name, description, and parameter schema.
        Useful for building tool-info panels or letting the agent describe itself.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in TOOL_REGISTRY.values()
        ]

    @staticmethod
    def _tool_definitions() -> List[Dict[str, Any]]:
        """Build the Anthropic tool-schema list from the live registry."""
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in TOOL_REGISTRY.values()
        ]

    @staticmethod
    def _dispatch_tool(tool_name: str, tool_input: dict):
        """Look up and call a tool from the registry. Returns (result, is_error)."""
        tool = TOOL_REGISTRY.get(tool_name)
        if tool is None:
            return {"error": f"Unknown tool: {tool_name}"}, True
        try:
            return tool.handler(**tool_input), False
        except Exception as exc:
            return {"error": str(exc)}, True

    # ------------------------------------------------------------------
    # Agentic loop (batch)
    # ------------------------------------------------------------------

    def run(self, messages: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, Any]]]:
        """Run the agentic loop with tool use.

        Args:
            messages: Chat history as list of {role, content} dicts.

        Returns:
            Tuple of (response_text, trace) where trace is a list of tool
            call/result entries for display in the UI.
        """
        trace: List[Dict[str, Any]] = []

        anthropic_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] in ("user", "assistant")
        ]
        # Anthropic requires the first message to have the "user" role.
        while anthropic_messages and anthropic_messages[0]["role"] != "user":
            anthropic_messages.pop(0)

        for _ in range(self.MAX_ITERATIONS):
            request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "tools": self._tool_definitions(),
                "messages": anthropic_messages,
            }

            response_body = self.llm.invoke(request)
            stop_reason = response_body.get("stop_reason")
            content = response_body.get("content", [])

            if stop_reason == "end_turn":
                text = next((b["text"] for b in content if b.get("type") == "text"), "")
                return text, trace

            if stop_reason == "tool_use":
                tool_calls = [b for b in content if b.get("type") == "tool_use"]
                anthropic_messages.append({"role": "assistant", "content": content})

                tool_results = []
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_input = tc.get("input", {})
                    tool_id = tc["id"]

                    trace.append({"type": "tool_call", "name": tool_name, "input": tool_input})
                    logger.info(f"Agent calling tool '{tool_name}' with {tool_input}")

                    result, is_error = self._dispatch_tool(tool_name, tool_input)
                    trace.append({"type": "tool_result", "name": tool_name, "output": result})
                    entry = {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result),
                    }
                    if is_error:
                        entry["is_error"] = True
                    tool_results.append(entry)

                anthropic_messages.append({"role": "user", "content": tool_results})
            else:
                logger.warning(f"Unexpected stop_reason: {stop_reason}")
                break

        return "I was unable to complete the task after several steps.", trace

    # ------------------------------------------------------------------
    # Agentic loop (streaming)
    # ------------------------------------------------------------------

    def run_stream(self, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        """Streaming version of run(). Yields events as they happen.

        Yields dicts with shape:
          {"type": "trace",            "entry": {type, name, input|output}}
          {"type": "approval_required", "approval_key": str, "tool_name": str, "tool_input": dict}
          {"type": "response",         "content": str}
          {"type": "error",            "message": str}

        Human-in-the-Loop (HITL)
        ------------------------
        When Claude wants to call a tool marked requires_approval=True, run_stream()
        yields an "approval_required" event and then blocks (via threading.Event.wait)
        until the frontend POSTs to /api/chat/approve with the same approval_key.
        Each stream call has a unique request_id so concurrent users never share state.
        """
        # Unique ID for this stream call — scopes all HITL events for this user session
        request_id = str(uuid.uuid4())

        anthropic_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] in ("user", "assistant")
        ]
        while anthropic_messages and anthropic_messages[0]["role"] != "user":
            anthropic_messages.pop(0)

        for _ in range(self.MAX_ITERATIONS):
            request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "tools": self._tool_definitions(),
                "messages": anthropic_messages,
            }

            response_body = self.llm.invoke(request)
            stop_reason = response_body.get("stop_reason")
            content = response_body.get("content", [])

            if stop_reason == "end_turn":
                text = next((b["text"] for b in content if b.get("type") == "text"), "")
                yield {"type": "response", "content": text}
                return

            if stop_reason == "tool_use":
                tool_calls = [b for b in content if b.get("type") == "tool_use"]
                anthropic_messages.append({"role": "assistant", "content": content})

                tool_results = []
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_input = tc.get("input", {})
                    tool_id = tc["id"]

                    yield {"type": "trace", "entry": {"type": "tool_call", "name": tool_name, "input": tool_input}}
                    logger.info(f"Agent calling tool '{tool_name}' with {tool_input}")

                    # ── HITL gate ──────────────────────────────────────────────
                    tool_entry = TOOL_REGISTRY.get(tool_name)
                    if tool_entry and tool_entry.requires_approval:
                        approval_key = f"{request_id}:{tool_id}"
                        event = threading.Event()
                        _pending_approvals[approval_key] = event

                        # Tell the frontend to show an Approve / Reject card
                        yield {
                            "type": "approval_required",
                            "approval_key": approval_key,
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                        }

                        # Block this thread until the user responds or time runs out.
                        # Other users' requests run in separate threads — unaffected.
                        fired = event.wait(timeout=APPROVAL_TIMEOUT_SECONDS)
                        approved = _approval_decisions.pop(approval_key, False) if fired else False
                        _pending_approvals.pop(approval_key, None)

                        if not approved:
                            reason = (
                                "User declined to run this tool."
                                if fired else
                                f"No response within {APPROVAL_TIMEOUT_SECONDS}s — tool skipped."
                            )
                            skipped = {"status": "skipped", "reason": reason}
                            yield {"type": "trace", "entry": {"type": "tool_result", "name": tool_name, "output": skipped}}
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(skipped),
                            })
                            continue  # skip _dispatch_tool, move to next tool call
                    # ── end HITL gate ──────────────────────────────────────────

                    result, is_error = self._dispatch_tool(tool_name, tool_input)
                    yield {"type": "trace", "entry": {"type": "tool_result", "name": tool_name, "output": result}}
                    entry = {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result),
                    }
                    if is_error:
                        entry["is_error"] = True
                    tool_results.append(entry)

                anthropic_messages.append({"role": "user", "content": tool_results})
            else:
                logger.warning(f"Unexpected stop_reason: {stop_reason}")
                break

        yield {"type": "response", "content": "I was unable to complete the task after several steps."}


# Example usage
if __name__ == "__main__":
    agent = AgentService()
    response, trace = agent.run([{"role": "user", "content": "What are the rarest driving conditions?"}])
    print("Response:", response)
    print("Trace:", json.dumps(trace, indent=2))
