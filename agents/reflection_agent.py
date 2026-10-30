
import json
from llm_client import get_client
from schema import ResumeData
from utils.retry import clean_json_text, retry_on_failure
from utils.logging_config import log_call, log_token_usage
REFLECTION_PROMPT = """
You are a careful resume extraction reviewer.
Review the extracted resume JSON against the original resume text.
Correct missing, inaccurate, or unsupported information.
Do not invent details that are not present in the resume.
Preserve the required schema and data types.
Return only a valid JSON object with all required fields.
Original resume:
{resume_text}
Current extracted JSON:
{extracted_json}
"""
@log_call
@retry_on_failure(max_attempts=2)
def self_reflect(data: ResumeData, resume_text: str) -> ResumeData:
    client = get_client()
    prompt = REFLECTION_PROMPT.format(
        extracted_json=data.model_dump_json(),
        resume_text=resume_text,
    )
    response = client.responses.create(
        model="gpt-4.1",
        input=prompt,
        text={"format": {"type": "json_object"}},
    )
    log_token_usage(response, label="reflection")
    corrected = json.loads(clean_json_text(response.output_text))
    # Preserve original fields if the reflection response omits them.
    original = data.model_dump()
    for field in original:
        if field not in corrected:
            corrected[field] = original[field]
    # Reject an incomplete reflection result and preserve valid original data.
    try:
        return ResumeData(**corrected)
    except Exception as exc:
        logger.warning(
            "Reflection output was invalid; keeping original extraction: %s",
            exc,
        )
        return data
