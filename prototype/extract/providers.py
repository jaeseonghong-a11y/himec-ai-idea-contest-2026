"""One output shape for three providers, plus a stored-fixture replay.

Only the request/response plumbing lives here. Whatever comes back is still
validated by `core.normalize_items`, so a provider cannot widen the contract.

Live calls are unverified: no key was available while this module was written,
so every adapter below has been exercised against its request builder only.
Record the provider, model and call date in the PR when a live run happens.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .core import ExtractionError, PROVIDERS

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-5",
    "gemini": "gemini-2.0-flash",
}

ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

PROMPT = """회의 대본에서 도면 변경 지시만 뽑아 JSON으로만 답하세요.

규칙:
- `quote`는 대본에 그대로 있는 문자열이어야 합니다. 바꿔 쓰지 마세요.
- 지시가 아닌 잡담은 제외합니다.
- 대상 도면이나 객체가 분명하지 않으면 `sheet`와 `target.tag`를 null로 두세요. 추측하지 마세요.
- 이동량은 mm 정수로 `params.dx_mm`, `params.dy_mm`에 넣습니다. 이동이 아니면 `action`을 "review"로 두고 `params`는 {}로 둡니다.

출력 형식:
{"items": [{"id": "CR-001", "source": {"quote": "...", "speaker": "...", "time": "hh:mm:ss"},
  "sheet": "A-101", "target": {"tag": "C1"}, "action": "move",
  "params": {"dx_mm": 0, "dy_mm": 500}, "impacts": ["A-301", "E-201"]}]}

대본:
"""


def resolve_api_key(provider: str) -> str | None:
    """Read the key from the local environment only. Never log or store it."""
    return os.environ.get(ENV_KEYS[provider]) or None


def _extract_items(text: str) -> list:
    """Pull the items array out of a model reply that may wrap it in prose."""
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ExtractionError(f"provider reply was not JSON: {error}") from error
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise ExtractionError("provider reply has no items array")


def build_request(provider: str, transcript: str, api_key: str, model: str) -> tuple[str, dict, dict]:
    """Return (url, headers, body) so the wire format stays testable offline."""
    if provider not in PROVIDERS:
        raise ExtractionError(f"provider must be one of {PROVIDERS}")
    prompt = PROMPT + transcript
    if provider == "openai":
        return (
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
    if provider == "anthropic":
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            {
                "model": model,
                "max_tokens": 2048,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": api_key, "Content-Type": "application/json"},
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        },
    )


def read_reply(provider: str, payload: dict) -> list:
    """Normalize the three response envelopes down to the items array."""
    try:
        if provider == "openai":
            text = payload["choices"][0]["message"]["content"]
        elif provider == "anthropic":
            text = "".join(block.get("text", "") for block in payload["content"])
        else:
            text = "".join(
                part.get("text", "") for part in payload["candidates"][0]["content"]["parts"]
            )
    except (KeyError, IndexError, TypeError) as error:
        raise ExtractionError(f"unexpected {provider} response shape: {error}") from error
    return _extract_items(text)


def call_provider(provider: str, transcript: str, api_key: str, model: str | None = None, timeout: int = 60) -> list:
    """Make one live call. Raises `ExtractionError` so the CLI can fall back."""
    import requests  # imported lazily: fixture replay must work without it

    url, headers, body = build_request(provider, transcript, api_key, model or DEFAULT_MODELS[provider])
    try:
        response = requests.post(url, headers=headers, json=body, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as error:  # network, auth, quota, malformed JSON
        # The key itself is never included in the message.
        raise ExtractionError(f"{provider} call failed: {type(error).__name__}") from error
    return read_reply(provider, payload)


def replay_fixture(path: Path) -> list:
    """Replay a stored example. This is not a live model result."""
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise ExtractionError(f"fixture has no items array: {path}")
