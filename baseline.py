"""
Non-agentic baseline: ONE prompt, ONE OpenAI call, same model and same
output schema as the agentic pipeline. No planning, no reflection, no
validation, no retries, no tools. This is the fair comparison point the
review asked for - if the agentic pipeline can't beat this, the extra
complexity isn't justified.
"""
import json
import time

from llm_client import get_client
from schema import ResumeData
from utils.retry import clean_json_text

BASELINE_PROMPT = """Extract structured resume data as JSON matching this shape:
{{
  "name": str, "email": str, "phone": str, "summary": str,
  "skills": [str],
  "experience": [{{"company","title","start_date","end_date","description"}}],
  "education": [{{"institution","degree","year"}}]
}}
Return ONLY the JSON, nothing else.

Resume:
{resume_text}
"""


def run_baseline(resume_text: str) -> dict:
    """Returns a dict with the extracted data (or None on failure) plus
    the same cost/latency signals the agentic pipeline reports, so the
    two are directly comparable."""
    client = get_client()
    start = time.time()

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": BASELINE_PROMPT.format(resume_text=resume_text)}],
        )
        latency = time.time() - start
        raw = clean_json_text(response.choices[0].message.content)
        data = json.loads(raw)

        # Validate against the SAME schema (minus confidence_scores/intelligence,
        # which only the agentic pipeline produces) so field names are comparable.
        data.setdefault("confidence_scores", {})
        ResumeData(**data)  # raises if structurally invalid

        usage = getattr(response, "usage", None)
        return {
            "success": True,
            "data": data,
            "latency_seconds": round(latency, 3),
            "llm_calls": 1,
            "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
            "output_tokens": getattr(usage, "completion_tokens", None) if usage else None,
            "error": None,
        }
    except Exception as e:
        latency = time.time() - start
        return {
            "success": False,
            "data": None,
            "latency_seconds": round(latency, 3),
            "llm_calls": 1,
            "input_tokens": None,
            "output_tokens": None,
            "error": str(e),
        }
