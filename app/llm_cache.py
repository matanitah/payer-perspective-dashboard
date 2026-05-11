"""
Disk-backed cache for Ollama chat completions under data/llm_cache/.

Keys are SHA-256 hashes of a stable JSON encoding of the request payload
(model, messages, options, format) so identical prompts reuse prior outputs.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

from app.knowledge import LLM_CACHE_DIR

logger = logging.getLogger(__name__)


def _payload_fingerprint(payload: dict) -> dict:
    """Subset of the Ollama request used for cache identity."""
    fp: dict = {
        "model": payload.get("model"),
        "messages": payload.get("messages"),
        "stream": payload.get("stream"),
        "options": payload.get("options"),
    }
    if "format" in payload:
        fp["format"] = payload["format"]
    return fp


def cache_key(payload: dict) -> str:
    blob = json.dumps(_payload_fingerprint(payload), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_file(key: str) -> Path:
    return Path(LLM_CACHE_DIR) / f"{key}.txt"


def read_cached(key: str) -> str | None:
    path = _cache_file(key)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def write_cached(key: str, content: str) -> None:
    path = _cache_file(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def get_cached_or_run(payload: dict, run: Callable[[], str]) -> str:
    key = cache_key(payload)
    hit = read_cached(key)
    if hit is not None:
        logger.debug("LLM cache hit %s…", key[:16])
        return hit
    content = run()
    write_cached(key, content)
    return content
