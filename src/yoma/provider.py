"""Vendor-neutral AI provider contract and explicit no-provider default."""

from dataclasses import dataclass
import json
from typing import Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlparse

from .context import AssembledContext


@dataclass(frozen=True)
class GenerationResult:
    generation_status: str
    provider: str
    answer: str | None
    citations: tuple[dict, ...]
    reason: str | None = None


class AIProvider(Protocol):
    name: str
    requires_external_egress: bool

    def generate_answer(self, query: str, context: AssembledContext, policy: "GenerationPolicy") -> GenerationResult:
        ...


@dataclass(frozen=True)
class GenerationPolicy:
    external_egress_enabled: bool = False


class ProviderPolicyError(ValueError):
    pass


class NoProvider:
    name = "none"
    requires_external_egress = False

    def generate_answer(self, query: str, context: AssembledContext, policy: GenerationPolicy) -> GenerationResult:
        return GenerationResult(
            generation_status="unavailable",
            provider=self.name,
            answer=None,
            citations=(),
            reason="no AI provider is configured",
        )


class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat-completions client with no SDK dependency."""

    name = "openai-compatible"
    requires_external_egress = True

    def __init__(self, base_url: str | None, model: str | None, api_key: str | None, timeout_seconds: float):
        self._base_url = base_url.rstrip("/") if base_url else None
        self._model = model
        self._api_key = api_key
        self._timeout_seconds = max(0.1, min(timeout_seconds, 120.0))

    def _configuration_ready(self) -> bool:
        if not (self._base_url and self._model and self._api_key):
            return False
        parsed = urlparse(self._base_url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def generate_answer(self, query: str, context: AssembledContext, policy: GenerationPolicy) -> GenerationResult:
        if not self._configuration_ready():
            return GenerationResult("configuration_error", self.name, None, (), "provider configuration is incomplete")
        if not policy.external_egress_enabled:
            raise ProviderPolicyError("external AI egress is disabled")

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": context.system_instructions},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_query": context.query,
                            "conversation_history": list(context.conversation_messages),
                            "user_memory_data": [
                                {
                                    "memory_id": block.source.memory_id,
                                    "category": block.source.category,
                                    "source": block.source.source,
                                    "importance": block.source.importance,
                                    "content": block.content,
                                }
                                for block in context.memory_blocks
                            ],
                            "retrieved_document_data": [
                                {
                                    "document_id": block.source.document_id,
                                    "filename": block.source.filename,
                                    "relative_path": block.source.relative_path,
                                    "workspace_root_id": block.source.workspace_root_id,
                                    "source_locations": list(block.source.source_locations),
                                    "content": block.content,
                                }
                                for block in context.blocks
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = urllib_request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_body = response.read(2 * 1024 * 1024)
            parsed = json.loads(response_body.decode("utf-8"))
            answer = parsed["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("empty answer")
            return GenerationResult("generated", self.name, answer, ())
        except urllib_error.HTTPError as exc:
            if exc.code in {401, 403}:
                reason = "provider authentication failed"
            elif exc.code == 408:
                reason = "provider request timed out"
            elif exc.code == 429:
                reason = "provider rate limit reached"
            elif exc.code >= 500:
                reason = "provider unavailable"
            else:
                reason = "provider request failed"
            return GenerationResult("failed", self.name, None, (), reason)
        except (urllib_error.URLError, TimeoutError):
            return GenerationResult("failed", self.name, None, (), "provider unavailable or timed out")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, UnicodeDecodeError, ValueError):
            return GenerationResult("failed", self.name, None, (), "provider returned an invalid response")
        except Exception:
            return GenerationResult("failed", self.name, None, (), "provider request failed")


def provider_from_settings(settings) -> AIProvider:
    if settings.ai_provider in {"", "none"}:
        return NoProvider()
    if settings.ai_provider == "yoma-native":
        return YOMAProvider()
    if settings.ai_provider == "openai-compatible":
        return OpenAICompatibleProvider(settings.ai_base_url, settings.ai_model, settings.ai_api_key, settings.ai_timeout_seconds)
    return NoProvider()


def enforce_provider_policy(provider: AIProvider, policy: GenerationPolicy) -> None:
    if provider.requires_external_egress and not policy.external_egress_enabled:
        raise ProviderPolicyError("external AI egress is disabled")

class YOMAProvider:
    """Deterministic, fully local YOMA-native AI provider."""

    name = "yoma-native"
    requires_external_egress = False

    def generate_answer(
        self,
        query: str,
        context: AssembledContext,
        policy: GenerationPolicy,
    ) -> GenerationResult:
        normalized = query.strip().lower()

        if normalized in {"hello", "hi"}:
            answer = "Hello. YOMA is ready."
        elif normalized == "status":
            answer = "YOMA is ready."
        elif normalized == "who are you":
            answer = "I am YOMA, a local AI engine."
        elif normalized == "help":
            answer = "YOMA is ready. Native AI capabilities are being developed."
        else:
            answer = "YOMA native engine cannot answer that request yet."

        return GenerationResult(
            generation_status="generated",
            provider=self.name,
            answer=answer,
            citations=(),
            reason=None,
        )
