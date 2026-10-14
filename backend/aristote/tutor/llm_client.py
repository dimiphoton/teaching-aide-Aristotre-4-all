"""Client LLM unique, compatible avec l'API OpenAI « chat completions ».

Fonctionne avec :
- Mistral (`https://api.mistral.ai/v1`, hébergement UE) ;
- Ollama sur le hub de classe (`http://hub.local:11434/v1`, 100 % local) ;
- tout autre serveur compatible (vLLM, llama.cpp server…).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Callable, Protocol

import httpx

log = logging.getLogger(__name__)

Message = dict[str, Any]


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    async def chat(self, messages: list[Message], *, json_mode: bool = False,
                   temperature: float | None = None) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, base_url: str, model: str, api_key: str | None = None, *, temperature: float = 0.3,
                 timeout_s: float = 30.0, max_retries: int = 2, json_mode_supported: bool = True,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s,
                                         transport=transport)
        self.model = model
        self._temperature = temperature
        self._max_retries = max_retries
        self._json_mode_supported = json_mode_supported

    async def chat(self, messages: list[Message], *, json_mode: bool = False,
                   temperature: float | None = None) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self._temperature if temperature is None else temperature,
        }
        if json_mode and self._json_mode_supported:
            body["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post("/chat/completions", json=body)
                if response.status_code in (429, 500, 502, 503, 504):
                    raise LLMError(f"HTTP {response.status_code}")
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"] or ""
            except (httpx.HTTPError, LLMError, KeyError, ValueError) as exc:
                last_error = exc
                log.warning("appel LLM échoué (%s), tentative %d", exc, attempt + 1)
                await asyncio.sleep(0.5 * 2 ** attempt)
        raise LLMError(f"LLM indisponible : {last_error}")

    async def aclose(self) -> None:
        await self._client.aclose()


class ScriptedLLM:
    """LLM simulé pour les tests et le mode démonstration : une fonction décide de chaque réponse."""

    def __init__(self, responder: Callable[[list[Message], bool], str]) -> None:
        self._responder = responder
        self.calls: list[tuple[list[Message], bool]] = []

    async def chat(self, messages: list[Message], *, json_mode: bool = False,
                   temperature: float | None = None) -> str:
        self.calls.append((messages, json_mode))
        return self._responder(messages, json_mode)


def parse_json_reply(text: str) -> dict[str, Any]:
    """Extrait l'objet JSON d'une réponse (tolère un bloc ```json … ``` ou du texte autour)."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("aucun objet JSON dans la réponse")
        text = text[start:end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("la réponse JSON n'est pas un objet")
    return data


def client_from_config(cfg) -> LLMClient:
    """Construit le client à partir de la section [llm] de la configuration."""
    api_key = os.environ.get(cfg.api_key_env) if cfg.api_key_env else None
    return OpenAICompatibleClient(cfg.base_url, cfg.model, api_key, temperature=cfg.temperature,
                                  timeout_s=cfg.timeout_s, json_mode_supported=cfg.json_mode)
