"""
Orchestrator — a real stateful agent graph with dynamic routing, PLUS
an AblationConfig so the evaluation harness (eval/) can independently
switch off reflection / verification / memory / dynamic routing to
measure whether each one actually earns its keep.

Dynamic routing decisions made here (when ablation is off):
  - plan -> clean_text -> extract   IF plan flags the resume as messy/scanned
  - plan -> extract                 otherwise
  - extract -> extract (retry)      IF the model's JSON was malformed, up to 3x
  - validate -> targeted_verification  IF any field confidence is low
  - validate -> score               otherwise
  - score node runs intelligence / ATS / JD-match IN PARALLEL (ThreadPoolExecutor)

Run `result["agent_trace"]` after any pipeline run to see which path was
actually taken for that specific resume - it's not always the same path.
"""
import re
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from agent_graph import AgentGraph, AgentState
from agents.planning_agent import plan_extraction
from agents.extraction_agent import extract_resume_json
from agents.reflection_agent import self_reflect
from agents.validation_agent import validate_resume, needs_human_review
from agents.verification_agent import verify_low_confidence_fields
from agents.scoring_agent import compute_resume_intelligence, compute_ats_score
from agents.recommendation_agent import match_resume_to_jd
from memory import save_version
from semantic_memory import store_memory, retrieve_similar
from utils.logging_config import logger


@dataclass
class AblationConfig:
    """Toggle individual agentic components off, for the ablation study in eval/.
    All True = full agentic pipeline (the default / production behavior)."""
    enable_reflection: bool = True
    enable_verification: bool = True
    enable_memory: bool = True
    enable_dynamic_routing: bool = True  # if False: always extract (skip clean_text),
                                          # never branch to targeted_verification


# ---------- Nodes ----------

def node_plan(state: AgentState) -> AgentState:
    state.plan = plan_extraction(state.resume_text)
    logger.info(f"Plan: {state.plan}")
    return state


def node_clean_text(state: AgentState) -> AgentState:
    """Only reached when the planning agent flags the text as messy/OCR-like."""
    state.resume_text = re.sub(r"[^\x20-\x7E\n]+", " ", state.resume_text)
    logger.info("Cleaned messy/OCR-like text before extraction.")
    return state


def node_extract(state: AgentState) -> AgentState:
    state.extraction_attempts += 1
    try:
        state.data = extract_resume_json(state.resume_text, state.plan)
        state.raw_extraction_error = None
    except Exception as e:
        state.raw_extraction_error = str(e)
        logger.warning(f"Extraction attempt {state.extraction_attempts} failed: {e}")
    return state


def node_reflect(state: AgentState) -> AgentState:
    before = state.data.model_dump()
    state.data = self_reflect(state.data, state.resume_text)
    after = state.data.model_dump()
    state.reflection_changed_fields = [k for k in before if before.get(k) != after.get(k)]
    return state


def node_validate(state: AgentState) -> AgentState:
    state.data = validate_resume(state.data)
    state.low_confidence_fields = needs_human_review(state.data)
    return state


def node_targeted_verification(state: AgentState) -> AgentState:
    before = state.data.model_dump()
    state.data = verify_low_confidence_fields(state.data, state.resume_text, state.low_confidence_fields)
    after = state.data.model_dump()
    state.verification_changed_fields = [k for k in before if before.get(k) != after.get(k)]
    state.low_confidence_fields = needs_human_review(state.data)  # recheck after verification
    return state


def node_score(state: AgentState) -> AgentState:
    """Runs independent scoring tasks in PARALLEL instead of sequentially."""
    with ThreadPoolExecutor(max_workers=3) as ex:
        intel_future = ex.submit(compute_resume_intelligence, state.data)
        ats_future = ex.submit(compute_ats_score, state.resume_text, state.jd_text) if state.jd_text else None
        match_future = ex.submit(match_resume_to_jd, state.data, state.jd_text) if state.jd_text else None

        state.data.intelligence = intel_future.result()
        state.ats_result = ats_future.result() if ats_future else None
        state.match_result = match_future.result() if match_future else None
    return state


def node_memory(state: AgentState) -> AgentState:
    state.diff = save_version(state.resume_name, state.data.model_dump())

    try:
        summary_text = state.data.summary or " ".join(state.data.skills) or state.data.name
        state.similar_resumes = retrieve_similar(summary_text, top_k=3)
        store_memory(
            state.resume_name,
            summary_text,
            {"name": state.data.name, "seniority": getattr(state.data.intelligence, "seniority_level", None)},
        )
    except Exception as e:
        logger.warning(f"Semantic memory step skipped (non-critical): {e}")

    return state


def node_noop(state: AgentState) -> AgentState:
    """Used when a node is ablated away - passes state through unchanged."""
    return state


# ---------- Router factory (closures capture the AblationConfig) ----------

def _build_routers(config: AblationConfig) -> dict:

    def router_plan(state: AgentState) -> str:
        if not config.enable_dynamic_routing:
            # Fixed control path for the routing ablation: all optional stages
            # remain enabled, but no state-dependent branch is allowed.
            return "clean_text"
        return "clean_text" if state.plan.get("is_scanned_or_messy") else "extract"

    def router_clean_text(state: AgentState) -> str:
        return "extract"

    def router_extract(state: AgentState) -> str:
        if state.raw_extraction_error:
            if config.enable_dynamic_routing and state.extraction_attempts < 3:
                return "extract"
            return "END"
        return "reflect" if config.enable_reflection else "validate"

    def router_reflect(state: AgentState) -> str:
        return "validate"

    def router_validate(state: AgentState) -> str:
        if not config.enable_verification:
            return "score"
        if not config.enable_dynamic_routing:
            # Fixed control path: verification is always run so the ablation
            # isolates routing decisions rather than removing verification.
            return "targeted_verification"
        return "targeted_verification" if state.low_confidence_fields else "score"

    def router_targeted_verification(state: AgentState) -> str:
        return "score"

    def router_score(state: AgentState) -> str:
        return "memory" if config.enable_memory else "END"

    def router_memory(state: AgentState) -> str:
        return "END"

    return {
        "plan": router_plan, "clean_text": router_clean_text, "extract": router_extract,
        "reflect": router_reflect, "validate": router_validate,
        "targeted_verification": router_targeted_verification,
        "score": router_score, "memory": router_memory,
    }


def build_graph(config: AblationConfig | None = None) -> AgentGraph:
    config = config or AblationConfig()
    graph = AgentGraph()

    reflect_node = node_reflect if config.enable_reflection else node_noop
    memory_node = node_memory if config.enable_memory else node_noop

    for name, fn in [
        ("plan", node_plan),
        ("clean_text", node_clean_text),
        ("extract", node_extract),
        ("reflect", reflect_node),
        ("validate", node_validate),
        ("targeted_verification", node_targeted_verification),
        ("score", node_score),
        ("memory", memory_node),
    ]:
        graph.add_node(name, fn)

    for name, router in _build_routers(config).items():
        graph.add_router(name, router)

    graph.set_entry("plan")
    return graph


def run_pipeline(resume_text: str, resume_name: str = "sample_resume.txt",
                  jd_text: str | None = None,
                  ablation_config: AblationConfig | None = None) -> dict:
    config = ablation_config or AblationConfig()
    logger.info(f"=== Agent graph run start (ablation={config}) ===")
    state = AgentState(resume_text=resume_text, resume_name=resume_name, jd_text=jd_text)
    graph = build_graph(config)
    state = graph.run(state)

    if state.raw_extraction_error:
        raise RuntimeError(
            f"Extraction failed after {state.extraction_attempts} attempts: {state.raw_extraction_error}"
        )

    logger.info(f"Agent path taken: {' -> '.join(state.log)}")

    return {
        "data": state.data.model_dump(),
        "low_confidence_fields": state.low_confidence_fields,
        "ats_result": state.ats_result.model_dump() if state.ats_result else None,
        "match_result": state.match_result.model_dump() if state.match_result else None,
        "changes_since_last_version": state.diff,
        "similar_past_resumes": state.similar_resumes,
        "agent_trace": state.log,
        "reflection_changed_fields": state.reflection_changed_fields,
        "verification_changed_fields": state.verification_changed_fields,
    }
