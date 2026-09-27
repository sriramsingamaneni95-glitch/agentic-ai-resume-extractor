import json
import time

from llm_client import get_client
from schema import ResumeData
from utils.retry import clean_json_text


BASELINE_PROMPT = """Extract this resume into valid JSON matching the ResumeData schema.
Do not invent information. Return only JSON.

Resume:
{resume_text}
"""

def run_baseline(resume_text: str) -> dict:
    client = get_client()
    start = time.time()

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "user",
                    "content": BASELINE_PROMPT.format(
                        resume_text=resume_text
                    ),
                }
            ],
        )

        raw = clean_json_text(
            response.choices[0].message.content
        )

        data = json.loads(raw)
        data.setdefault("confidence_scores", {})

        ResumeData(**data)

        usage = getattr(response, "usage", None)

        return {
            "success": True,
            "data": data,
            "latency_seconds": round(time.time() - start, 3),
            "llm_calls": 1,
            "input_tokens": (
                getattr(usage, "prompt_tokens", None)
                if usage
                else None
            ),
            "output_tokens": (
                getattr(usage, "completion_tokens", None)
                if usage
                else None
            ),
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "data": None,
            "latency_seconds": round(time.time() - start, 3),
            "llm_calls": 1,
            "input_tokens": None,
            "output_tokens": None,
            "error": str(exc),
        }
