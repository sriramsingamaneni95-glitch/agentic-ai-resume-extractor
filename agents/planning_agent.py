import json
from llm_client import get_client
from utils.logging_config import logger, log_call
PLANNING_PROMPT = """
Analyze the resume text and return a valid JSON object.
Use these four keys:
- is_scanned_or_messy: true or false
- has_multiple_pages: true or false
- language: string describing the resume's language, or "unknown"
- notes: string with a brief processing recommendation
Return only a JSON object. Do not include Markdown.
Resume:
{resume_text}
"""
@log_call
def plan_extraction(resume_text: str) -> dict:
    client = get_client()
    response = client.responses.create(
        model="gpt-4.1",
        input=PLANNING_PROMPT.format(resume_text=resume_text[:3000]),
        text={"format": {"type": "json_object"}},
    )
    try:
        return json.loads(response.output_text.strip())
    except (json.JSONDecodeError, AttributeError):
        logger.warning(
            "Planning agent returned invalid JSON, using default plan."
        )
        return {
            "is_scanned_or_messy": False,
            "has_multiple_pages": False,
            "language": "unknown",
            "notes": "",
        }