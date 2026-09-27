
from agent_graph import AgentGraph, AgentState
from orchestrator import _build_routers, AblationConfig


def _routers(**overrides):
    return _build_routers(AblationConfig(**overrides))


def test_router_plan_routes_to_clean_text_when_messy():
    routers = _routers()
    state = AgentState(resume_text="x")
    state.plan = {"is_scanned_or_messy": True}
    assert routers["plan"](state) == "clean_text"


def test_router_plan_routes_to_extract_when_clean():
    routers = _routers()
    state = AgentState(resume_text="x")
    state.plan = {"is_scanned_or_messy": False}
    assert routers["plan"](state) == "extract"


def test_router_plan_uses_fixed_path_when_dynamic_routing_disabled():
    routers = _routers(enable_dynamic_routing=False)
    state = AgentState(resume_text="x")
    state.plan = {"is_scanned_or_messy": False}
    assert routers["plan"](state) == "clean_text"  


def test_router_extract_retries_on_error():
    routers = _routers()
    state = AgentState(resume_text="x")
    state.raw_extraction_error = "bad json"
    state.extraction_attempts = 1
    assert routers["extract"](state) == "extract"


def test_router_extract_gives_up_after_3_attempts():
    routers = _routers()
    state = AgentState(resume_text="x")
    state.raw_extraction_error = "bad json"
    state.extraction_attempts = 3
    assert routers["extract"](state) == "END"


def test_router_extract_skips_reflect_when_ablated():
    routers = _routers(enable_reflection=False)
    state = AgentState(resume_text="x")
    state.raw_extraction_error = None
    assert routers["extract"](state) == "validate"


def test_router_validate_routes_to_verification_when_low_confidence():
    routers = _routers()
    state = AgentState(resume_text="x")
    state.low_confidence_fields = ["email"]
    assert routers["validate"](state) == "targeted_verification"


def test_router_validate_routes_to_score_when_confident():
    routers = _routers()
    state = AgentState(resume_text="x")
    state.low_confidence_fields = []
    assert routers["validate"](state) == "score"


def test_router_validate_skips_verification_when_ablated():
    routers = _routers(enable_verification=False)
    state = AgentState(resume_text="x")
    state.low_confidence_fields = ["email"]  
    assert routers["validate"](state) == "score"


def test_router_score_skips_memory_when_ablated():
    routers = _routers(enable_memory=False)
    state = AgentState(resume_text="x")
    assert routers["score"](state) == "END"


def test_graph_executes_simple_path():
    graph = AgentGraph()
    graph.add_node("a", lambda s: s)
    graph.add_node("b", lambda s: s)
    graph.add_router("a", lambda s: "b")
    graph.add_router("b", lambda s: "END")
    graph.set_entry("a")

    state = AgentState(resume_text="x")
    state = graph.run(state)
    assert state.log == ["a", "b"]
