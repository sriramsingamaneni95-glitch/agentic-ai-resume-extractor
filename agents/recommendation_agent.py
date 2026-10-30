
import json
from llm_client import get_client
from schema import ResumeData, MatchResult
from utils.retry import clean_json_text, retry_on_failure
from utils.logging_config import log_call, log_token_usage

MATCH_PROMPT = """
You are an expert resume-to-job-description matching agent.

Compare the candidate's resume with the job description.
Evaluate how well the candidate's skills, experience, and education match the role.
Do not invent qualifications or experience.

Resume JSON:
{resume_json}

Job description:
{jd_text}

Return ONLY a valid JSON object with these fields:
{
"fit_score": 0,
"reasoning": "Explain the match using evidence from the resume and job description.",
"matching_skills": [],
"missing_skills": []
}

The fit_score must be between 0 and 100.
Return no Markdown or additional text.
"""

@log_call
@retry_on_failure(max_attempts=3)
def match_resume_to_jd(resume: ResumeData, jd_text: str) -> MatchResult:
    client = get_client()
    prompt = MATCH_PROMPT.format(resume_json=resume.model_dump_json(), jd_text=jd_text)
    response = client.responses.create(
        model="gpt-4.1",
        input=prompt,
        text={"format": {"type": "json_object"}},
    )
    log_token_usage(response, label="matching")
    data = json.loads(clean_json_text(response.output_text))
    return MatchResult(**data)
