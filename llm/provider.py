"""The provider behind an interface: one `complete()` method. The triage code never knows which provider it is,
so Ollama, OpenRouter, or a fake in the tests are interchangeable."""
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

from llm.config import Settings


@dataclass
class Completion:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    model: str


class Provider(Protocol):
    model: str

    def complete(self, messages: list[dict], temperature: float, response_format: dict | None = None) -> Completion: ...


class OpenAICompatible:
    """Any server that speaks the OpenAI chat-completions shape: Ollama, OpenRouter, OpenAI, vLLM..."""

    def __init__(self, s: Settings):
        self.model = s.model
        # timeout: the SDK default is 10 minutes, which is not a timeout. max_retries=0: the SDK would silently retry
        # twice on its own; our own policy in llm/retry.py decides instead, so one log line = one real call.
        self.client = OpenAI(base_url=s.base_url, api_key=s.api_key, timeout=s.timeout_s, max_retries=0)

    def complete(self, messages: list[dict], temperature: float, response_format: dict | None = None) -> Completion:
        kwargs = {"response_format": response_format} if response_format else {}
        res = self.client.chat.completions.create(model=self.model, messages=messages, temperature=temperature,
                                                  **kwargs)
        usage = res.usage
        return Completion(text=res.choices[0].message.content or "",
                          input_tokens=getattr(usage, "prompt_tokens", None),
                          output_tokens=getattr(usage, "completion_tokens", None),
                          model=getattr(res, "model", None) or self.model)
