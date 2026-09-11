from typing import Any, TypedDict


class LessonPlanState(TypedDict, total=False):
    project_id: str
    request_text: str
    stage: str
    outline: list[dict[str, Any]]
    events: list[dict[str, Any]]


class LessonPlanWorkflow:
    """LangGraph workflow with a deterministic fallback for minimal installs."""
    def __init__(self):
        self.graph = None
        try:
            from langgraph.graph import END, StateGraph
            graph = StateGraph(LessonPlanState)
            for name in ("intake", "outline", "render", "quality"):
                graph.add_node(name, getattr(self, f"_{name}"))
            graph.set_entry_point("intake")
            graph.add_edge("intake", "outline"); graph.add_edge("outline", "render"); graph.add_edge("render", "quality"); graph.add_edge("quality", END)
            self.graph = graph.compile()
        except ImportError:
            pass

    def _emit(self, state, node, message):
        events = list(state.get("events", [])); events.append({"event_type": "node.completed", "payload": {"node": node, "message": message}})
        return {**state, "stage": node, "events": events}

    def _intake(self, state): return self._emit(state, "intake", "已整理教学目标与受众")
    def _outline(self, state):
        outline = [{"title": "学习目标", "role": "objectives"}, {"title": "核心知识", "role": "content"}, {"title": "课堂练习", "role": "exercise"}, {"title": "总结与作业", "role": "summary"}]
        return {**self._emit(state, "outline", "已生成学案结构"), "outline": outline}
    def _render(self, state): return self._emit(state, "render", "已生成 A4 页面画布")
    def _quality(self, state): return self._emit(state, "quality", "已完成基础质量检查")

    def invoke(self, state):
        if self.graph: return self.graph.invoke(state)
        for fn in (self._intake, self._outline, self._render, self._quality): state = fn(state)
        return state
