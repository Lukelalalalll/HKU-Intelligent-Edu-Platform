from __future__ import annotations

from typing import Any, TypedDict


class PptGraphState(TypedDict, total=False):
    project_id: str
    page_id: str | None
    action_type: str
    decision: dict[str, Any]
    events: list[dict[str, Any]]


class PptWorkflowGraph:
    """Small, durable-by-contract LangGraph wrapper for action routing.

    The business service owns persistence; this graph owns the explicit decision
    boundary so every chat/action has a structured, inspectable plan.
    """

    def __init__(self):
        self._graph = None
        try:
            from langgraph.graph import END, StateGraph
            graph = StateGraph(PptGraphState)
            graph.add_node("route", self._route)
            graph.set_entry_point("route")
            graph.add_edge("route", END)
            self._graph = graph.compile()
        except ImportError:
            self._graph = None

    @staticmethod
    def _route(state: PptGraphState) -> PptGraphState:
        action = state.get("action_type", "")
        allowed = {
            "page_generate_search_queries", "page_search_run", "page_search_refresh",
            "page_summary_generate", "page_draft_generate", "page_design_generate",
            "project_batch_search", "project_batch_summary", "project_batch_draft", "project_batch_design",
        }
        decision = {"action_type": action, "should_execute": action in allowed, "scope_type": "page" if state.get("page_id") else "project", "target_page_id": state.get("page_id"), "missing_data": [] if action in allowed else ["supported action_type"], "execution_plan": [{"step_code": action, "step_name": action, "reason": "explicit user action"}]}
        return {**state, "decision": decision, "events": [{"event_type": "router.decision", "payload": decision}]}

    def invoke(self, state: PptGraphState) -> PptGraphState:
        if self._graph is not None:
            return self._graph.invoke(state)
        return self._route(state)
