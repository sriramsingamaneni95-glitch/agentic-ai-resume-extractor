"""
Prompt regression tests: guard against someone silently editing a prompt
template in a way that breaks its contract with the rest of the system
(e.g. removing a schema field, dropping the "JSON only" instruction, or
changing a tool name the code depends on). These don't call the API -
they check the prompt TEMPLATES themselves stay structurally intact.
"""
from agents.extraction_agent import SYSTEM_PROMPT, TOOLS
from agents.planning_agent import PLANNING_PROMPT
from agents.reflection_agent import REFLECTION_PROMPT
from agents.verification_agent import VERIFY_PROMPT
from agents.recommendation_agent import MATCH_PROMPT

REQUIRED_SCHEMA_FIELDS = [
    "name", "email", "phone", "summary", "skills",
    "experience", "education", "confidence_scores",
]


def test_extraction_prompt_mentions_every_schema_field():
    for field in REQUIRED_SCHEMA_FIELDS:
        assert field in SYSTEM_PROMPT, f"Extraction prompt regression: missing '{field}'"


def test_extraction_prompt_still_instructs_json_only_output():
    assert "ONLY the final JSON" in SYSTEM_PROMPT


def test_extraction_tools_schema_names_are_stable():
    tool_names = {t["function"]["name"] for t in TOOLS}
    assert tool_names == {"validate_email", "parse_date", "normalize_skill"}, (
        "A tool was renamed/added/removed - extraction_agent._run_tool() "
        "must be updated to match, or tool calls will silently fail."
    )


def test_planning_prompt_asks_for_required_plan_fields():
    for key in ["is_scanned_or_messy", "has_multiple_pages", "language", "notes"]:
        assert key in PLANNING_PROMPT, f"Planning prompt regression: missing '{key}'"


def test_reflection_prompt_still_receives_original_resume_text():
    assert "{resume_text}" in REFLECTION_PROMPT


def test_reflection_prompt_still_receives_prior_extraction():
    assert "{extracted_json}" in REFLECTION_PROMPT


def test_verification_prompt_takes_a_field_list_and_resume_text():
    assert "{fields}" in VERIFY_PROMPT
    assert "{resume_text}" in VERIFY_PROMPT


def test_match_prompt_asks_for_fit_score_shape():
    for key in ["fit_score", "reasoning", "matching_skills", "missing_skills"]:
        assert key in MATCH_PROMPT, f"Match prompt regression: missing '{key}'"
