"""Single lazy-loaded OpenAI client shared by all agents.

The wrapper also records per-run API telemetry when the evaluation harness
opens a telemetry context. Outside evaluation it behaves like the normal
OpenAI client and adds no required dependency or API-key work at import time.
"""
from functools import lru_cache
import time
from openai import OpenAI
from eval.telemetry import record_call


class _CallProxy:
    def __init__(self, target, api_name):
        self._target = target
        self._api_name = api_name

    def create(self, *args, **kwargs):
        started = time.time()
        model = kwargs.get("model", "unknown")
        try:
            response = self._target.create(*args, **kwargs)
            record_call(api=self._api_name, model=model, started=started, response=response)
            return response
        except Exception as exc:
            record_call(api=self._api_name, model=model, started=started, error=exc)
            raise


class _CompletionsProxy:
    def __init__(self, target):
        self._target = target
        self.completions = _CallProxy(target.completions, "chat.completions")


class InstrumentedOpenAI:
    def __init__(self, client):
        self._client = client
        self.responses = _CallProxy(client.responses, "responses")
        self.chat = _CompletionsProxy(client.chat)
        self.embeddings = _CallProxy(client.embeddings, "embeddings")


@lru_cache
def get_client() -> InstrumentedOpenAI:
    return InstrumentedOpenAI(OpenAI())
