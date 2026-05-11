"""Deduplication and persistence for seen articles and saved analysis runs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.analyzer import AnalysisResult, ThoughtStep
from app.fetcher import Article
from app.knowledge import ANALYSIS_RUNS_PATH, SEEN_DB_PATH

MAX_SAVED_RUNS = 25


def load_seen() -> dict:
    p = Path(SEEN_DB_PATH)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def save_seen(db: dict):
    p = Path(SEEN_DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(db, indent=2))


def filter_unseen(articles: list, db: dict) -> list:
    return [a for a in articles if a.uid not in db]


def mark_seen(articles: list, db: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    for a in articles:
        db[a.uid] = {"title": a.title[:100], "url": a.url, "seen": now}
    # prune
    if len(db) > 5000:
        keys = sorted(db, key=lambda k: db[k].get("seen", ""))
        for k in keys[:len(db) - 5000]:
            del db[k]
    return db


# ─── Analysis run history (survives Streamlit restarts) ─────────────


def _article_to_dict(a: Article) -> dict[str, Any]:
    pub = a.published
    return {
        "title": a.title,
        "url": a.url,
        "source": a.source,
        "published": pub.isoformat() if pub else None,
        "summary": a.summary,
        "content": a.content,
        "uid": a.uid,
        "matched_keywords": list(a.matched_keywords),
        "geo_tags": list(a.geo_tags),
    }


def _dict_to_article(d: dict[str, Any]) -> Article:
    pub_raw = d.get("published")
    published = None
    if pub_raw:
        try:
            published = datetime.fromisoformat(
                pub_raw.replace("Z", "+00:00") if isinstance(pub_raw, str) else str(pub_raw)
            )
        except (ValueError, TypeError):
            published = None
    return Article(
        title=d.get("title", ""),
        url=d.get("url", ""),
        source=d.get("source", ""),
        published=published,
        summary=d.get("summary", ""),
        content=d.get("content", ""),
        uid=d.get("uid", ""),
        matched_keywords=list(d.get("matched_keywords") or []),
        geo_tags=list(d.get("geo_tags") or []),
    )


def thought_step_to_dict(s: ThoughtStep) -> dict[str, Any]:
    return {
        "phase": s.phase,
        "article_title": s.article_title,
        "payer_name": s.payer_name,
        "message": s.message,
        "raw_response": s.raw_response,
        "timestamp": s.timestamp,
    }


def dict_to_thought_step(d: dict[str, Any]) -> ThoughtStep:
    return ThoughtStep(
        phase=d.get("phase", ""),
        article_title=d.get("article_title", ""),
        payer_name=d.get("payer_name", ""),
        message=d.get("message", ""),
        raw_response=d.get("raw_response", ""),
        timestamp=d.get("timestamp", ""),
    )


def analysis_result_to_dict(r: AnalysisResult) -> dict[str, Any]:
    return {
        "article": _article_to_dict(r.article),
        "relevance_score": r.relevance_score,
        "summary": r.summary,
        "parties": list(r.parties),
        "negotiation_type": r.negotiation_type,
        "states_affected": list(r.states_affected),
        "key_insight": r.key_insight,
        "action_signals": list(r.action_signals),
        "chain_of_thought": r.chain_of_thought,
        "payer_perspectives": dict(r.payer_perspectives),
        "error": r.error,
    }


def dict_to_analysis_result(d: dict[str, Any]) -> AnalysisResult:
    return AnalysisResult(
        article=_dict_to_article(d.get("article") or {}),
        relevance_score=int(d.get("relevance_score", 0)),
        summary=d.get("summary", ""),
        parties=list(d.get("parties") or []),
        negotiation_type=d.get("negotiation_type", "other"),
        states_affected=list(d.get("states_affected") or []),
        key_insight=d.get("key_insight", ""),
        action_signals=list(d.get("action_signals") or []),
        chain_of_thought=d.get("chain_of_thought", ""),
        payer_perspectives=dict(d.get("payer_perspectives") or {}),
        error=d.get("error"),
    )


def load_analysis_runs() -> list[dict[str, Any]]:
    p = Path(ANALYSIS_RUNS_PATH)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        runs = data.get("runs")
        if not isinstance(runs, list):
            return []
        return [r for r in runs if isinstance(r, dict) and r.get("ts")]
    except Exception:
        return []


def save_analysis_runs(runs: list[dict[str, Any]]) -> None:
    p = Path(ANALYSIS_RUNS_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    trimmed = runs[:MAX_SAVED_RUNS]
    p.write_text(
        json.dumps({"runs": trimmed}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def append_analysis_run(
    thoughts: list[ThoughtStep],
    results: list[AnalysisResult],
) -> dict[str, Any]:
    """Build one run record (callers merge into session + save)."""
    now = datetime.now(timezone.utc)
    return {
        "ts": now.isoformat(),
        "label": now.strftime("%Y-%m-%d %H:%M UTC"),
        "thoughts": [thought_step_to_dict(t) for t in thoughts],
        "results": [analysis_result_to_dict(r) for r in results],
    }


def materialize_run(record: dict[str, Any]) -> tuple[list[ThoughtStep], list[AnalysisResult]]:
    """Deserialize a stored run for UI display."""
    thoughts = [
        dict_to_thought_step(t)
        for t in record.get("thoughts") or []
        if isinstance(t, dict)
    ]
    results = [
        dict_to_analysis_result(r)
        for r in record.get("results") or []
        if isinstance(r, dict)
    ]
    return thoughts, results
