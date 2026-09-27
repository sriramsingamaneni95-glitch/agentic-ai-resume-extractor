
import json


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeChatResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]
        self.usage = None


class FakeResponsesResponse:
    def __init__(self, output_text):
        self.output_text = output_text
        self.usage = None


class FakeEmbeddingData:
    def __init__(self, embedding):
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(self, embedding):
        self.data = [FakeEmbeddingData(embedding)]


class FakeCompletions:
    def __init__(self, extraction_json: str):
        self.extraction_json = extraction_json

    def create(self, **kwargs):
      
        return FakeChatResponse(FakeMessage(content=self.extraction_json, tool_calls=None))


class FakeChat:
    def __init__(self, completions: FakeCompletions):
        self.completions = completions


class FakeResponses:
    def __init__(self, responder):
        self.responder = responder  

    def create(self, **kwargs):
        return FakeResponsesResponse(self.responder(kwargs))


class FakeEmbeddings:
    def create(self, **kwargs):
        return FakeEmbeddingResponse([0.1, 0.2, 0.3, 0.4])


class FakeOpenAIClient:
    def __init__(self, extraction_json: str, responder):
        self.chat = FakeChat(FakeCompletions(extraction_json))
        self.responses = FakeResponses(responder)
        self.embeddings = FakeEmbeddings()


def make_responder(extraction_json: str):
    def responder(kwargs):
        text = str(kwargs.get("input", "")).lower()
        if "planning agent" in text:
            return json.dumps({
                "is_scanned_or_messy": False, "has_multiple_pages": False,
                "language": "en", "notes": "",
            })
        if "re-check it against" in text:
            return extraction_json  
        if "focus only on" in text:
            return "{}"  
        if "compare this candidate" in text:
            return json.dumps({
                "fit_score": 82, "reasoning": "Strong skills overlap.",
                "matching_skills": ["Python"], "missing_skills": ["Kubernetes"],
            })
        return "{}"
    return responder


SAMPLE_EXTRACTION = {
    "name": "Test User",
    "email": "test@example.com",
    "phone": "1234567890",
    "summary": "Experienced backend engineer",
    "skills": ["python", "sql"],
    "experience": [{
        "company": "Google", "title": "Software Engineer",
        "start_date": "2020-01", "end_date": "present",
        "description": "led a small team",
    }],
    "education": [{"institution": "IIT Bombay", "degree": "BTech", "year": "2019"}],
    "confidence_scores": {
        "name": 0.95, "email": 0.95, "phone": 0.9,
        "skills": 0.9, "experience": 0.9, "education": 0.9,
    },
}
