"""Thin LLM interface (OpenRouter)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("NDIS_LLM_MODEL", "anthropic/claude-haiku-4.5")


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        env = Path(__file__).resolve().parent.parent / ".env"
        if env.exists():
            m = re.search(r"^OPENROUTER_API_KEY=(.+)$", env.read_text(), re.M)
            if m:
                key = m.group(1).strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set (env or .env)")
    return key


def complete(system: str, user: str, *, json_object: bool = False,
             model: str = DEFAULT_MODEL, max_tokens: int = 8000,
             temperature: float = 0.0) -> str | dict | list:
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    if json_object:
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(API_URL, json=body, timeout=300,
                   headers={"Authorization": f"Bearer {_api_key()}"})
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    if not json_object:
        return content
    content = re.sub(r"^```(json)?\s*|\s*```$", "", content.strip())
    return json.loads(content)
