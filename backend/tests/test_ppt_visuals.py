import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ppt_agent import PptAgentService, ProviderGateway
from app.services.ppt_graph import PptWorkflowGraph
from app.services.ppt_theme import get_theme
from app.services.visual_search import extract_keywords, rank_candidates


def test_theme_pack_exposes_tokens_and_accessibility():
    theme = get_theme("light-academic")
    assert theme["tokens"]["font_family"]
    assert "layout_recipes" not in theme or isinstance(theme["layout_recipes"], dict)
    assert theme["accessibility"]["passes"] is True


def test_visual_batch_action_is_supported_by_workflow_router():
    state = PptWorkflowGraph._route({
        "project_id": "project-1",
        "page_id": None,
        "action_type": "project_batch_visual",
    })
    assert state["decision"]["should_execute"] is True
    assert state["decision"]["missing_data"] == []


def test_deepseek_responses_web_search_json_uses_native_web_search_tool():
    calls = []

    class FakeResponse:
        output_text = '{"results":[{"title":"Coral reef","image_url":"https://example.test/coral.jpg"}]}'

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    gateway = ProviderGateway.__new__(ProviderGateway)
    gateway.config = SimpleNamespace(model="deepseek-v4-flash")
    gateway._client = lambda: FakeClient()
    result = gateway.web_search_json("coral reef ecology", image_focus=True)
    assert result["results"][0]["image_url"].endswith("coral.jpg")
    assert calls[0]["tools"] == [{"type": "web_search"}]
    assert calls[0]["tool_choice"] == {"type": "web_search"}


def test_visual_plan_turns_asset_candidate_into_image_slot_and_document_element():
    page = SimpleNamespace(
        id="page-1",
        title="珊瑚礁生态",
        section_title="案例",
        page_role="case",
        citations_json=[{"title": "Coral reef", "image_url": "data:image/png;base64,AAAA", "score": 0.9}],
        visual_plan_json={},
        statuses_json={},
    )
    service = PptAgentService.__new__(PptAgentService)
    service.db = SimpleNamespace(commit=lambda: None)
    project = SimpleNamespace(id="project-1")
    visual = service._visual_research(project, page)
    assert visual["asset_count"] == 1
    plan = service._visual_plan(project, page)
    assert plan["image_slots"][0]["placement_hint"] == "right"
    document = service._apply_visual_plan(page, {"elements": [{"type": "title", "x": 7, "y": 7, "w": 80, "h": 10, "text": page.title}]})
    image = next(item for item in document["elements"] if item["type"] == "image")
    assert image["src"].startswith("data:image/png")
    assert image["x"] >= 50


def test_visual_search_extracts_outline_terms_and_limits_ranked_candidates():
    words = extract_keywords("sustainable design", "campus ecology", ["data analytics"], "concept")
    assert "sustainable" in words and "ecology" in words
    results = rank_candidates([{"title": f"image {i} ecology", "image_url": f"https://example.test/{i}.jpg"} for i in range(10)], words, 6)
    assert len(results) == 6
