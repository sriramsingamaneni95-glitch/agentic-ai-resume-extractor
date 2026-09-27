
import json
from unittest.mock import patch

import pytest

import llm_client
import orchestrator
from tests.fakes import FakeOpenAIClient, make_responder, SAMPLE_EXTRACTION


@pytest.fixture(autouse=True)
def isolate_cwd_and_cache(tmp_path, monkeypatch):
   
    monkeypatch.chdir(tmp_path)
    llm_client.get_client.cache_clear()
    yield
    llm_client.get_client.cache_clear()


def _run_with_fake_client(resume_text, extraction_json, ablation_config=None):
    fake_client = FakeOpenAIClient(json.dumps(extraction_json), make_responder(json.dumps(extraction_json)))
    with patch("llm_client.OpenAI", return_value=fake_client):
        return orchestrator.run_pipeline(resume_text, resume_name="integration_test.txt",
                                          ablation_config=ablation_config)


def test_full_pipeline_happy_path():
    result = _run_with_fake_client("some resume text here", SAMPLE_EXTRACTION)

    assert result["data"]["name"] == "Test User"
    assert result["low_confidence_fields"] == [] 
    assert result["agent_trace"][0] == "plan"
    assert "extract" in result["agent_trace"]
    assert "reflect" in result["agent_trace"]
    assert "validate" in result["agent_trace"]
    assert "score" in result["agent_trace"]
    assert "memory" in result["agent_trace"]
   
    assert "targeted_verification" not in result["agent_trace"]


def test_low_confidence_triggers_targeted_verification():
    low_conf_extraction = dict(SAMPLE_EXTRACTION)
    low_conf_extraction["confidence_scores"] = dict(SAMPLE_EXTRACTION["confidence_scores"])
    low_conf_extraction["confidence_scores"]["email"] = 0.3 

    result = _run_with_fake_client("some resume text here", low_conf_extraction)

    assert "targeted_verification" in result["agent_trace"]


def test_ablation_no_reflection_skips_reflect_node():
    config = orchestrator.AblationConfig(enable_reflection=False)
    result = _run_with_fake_client("some resume text here", SAMPLE_EXTRACTION, ablation_config=config)

    assert result["data"]["name"] == "Test User"


def test_ablation_no_dynamic_routing_ignores_messy_flag():
    """Even if planning flags the resume as messy, disabling dynamic routing
    should skip straight to extraction rather than branching to clean_text."""
    config = orchestrator.AblationConfig(enable_dynamic_routing=False)

    messy_responder = make_responder(json.dumps(SAMPLE_EXTRACTION))

    def forced_messy_responder(kwargs):
        text = str(kwargs.get("input", "")).lower()
        if "planning agent" in text:
            return json.dumps({"is_scanned_or_messy": True, "has_multiple_pages": False,
                                "language": "en", "notes": ""})
        return messy_responder(kwargs)

    fake_client = FakeOpenAIClient(json.dumps(SAMPLE_EXTRACTION), forced_messy_responder)
    with patch("llm_client.OpenAI", return_value=fake_client):
        result = orchestrator.run_pipeline("messy text", resume_name="t.txt", ablation_config=config)

    assert "clean_text" in result["agent_trace"]
    assert "targeted_verification" in result["agent_trace"]


def test_ablation_no_memory_skips_memory_work():
    config = orchestrator.AblationConfig(enable_memory=False)
    result = _run_with_fake_client("some resume text here", SAMPLE_EXTRACTION, ablation_config=config)

    assert result["changes_since_last_version"] is None
    assert result["similar_past_resumes"] == []
