"""
Sends articles to Ollama for:
  1. Structured relevance/insight analysis
  2. Payer-perspective inference (Cigna, United, Anthem chain-of-thought)

All chain-of-thought steps are captured and streamed to the UI.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Callable

import httpx

from app.fetcher import Article, fetch_article_content
from app.llm_cache import get_cached_or_run
from app.knowledge import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
    MIN_RELEVANCE_SCORE, PAYER_INFERENCE_PROMPTS,
)

logger = logging.getLogger(__name__)

# ─── System prompt for article analysis ──────────────────────────────

ANALYSIS_SYSTEM = """\
You are an expert healthcare policy analyst specializing in provider-payer \
contract negotiations in the NY/CT/NJ tri-state region. You analyze news \
for actionable intelligence about reimbursement dynamics, network changes, \
enrollment-period leverage, regulatory shifts, and market consolidation. \
You know the major providers (NYP, Mount Sinai, NYU Langone, Northwell, \
Montefiore, MSK in NY; Yale New Haven, Hartford HealthCare, Nuvance in CT; \
HMH, RWJBarnabas, Atlantic Health in NJ) and major payers (UHC, Anthem/Empire, \
Cigna, Aetna, Healthfirst, EmblemHealth, Fidelis, Horizon BCBS NJ).\
"""

ANALYSIS_PROMPT = """\
Analyze this article for provider-payer negotiation intelligence.

TITLE: {title}
SOURCE: {source}
KEYWORDS: {keywords}
GEO TAGS: {geo}

TEXT:
{text}

Respond in EXACTLY this JSON (no fences, no extra text):
{{
  "relevance_score": <1-10>,
  "summary": "<2-3 sentences on negotiation implications>",
  "parties": ["<specific payers and providers>"],
  "negotiation_type": "<contract_dispute|network_exit|rate_negotiation|regulatory_change|market_consolidation|enrollment_impact|policy_update|other>",
  "states_affected": ["<NY|CT|NJ or empty>"],
  "key_insight": "<one sentence: the most important takeaway>",
  "action_signals": ["<what a strategist should watch or do>"],
  "chain_of_thought": "<2-3 sentences explaining your reasoning for the score and classification>"
}}
"""

# ─── Payer inference prompt ──────────────────────────────────────────

PAYER_INFERENCE_USER = """\
NEWS ARTICLE:
Title: {title}
Source: {source}
Summary: {summary}

Based on this news, provide your analysis as {payer_name}'s contracting team. \
Structure your response as:

STRATEGIC ASSESSMENT: (2-3 sentences on what this means for {payer_name})
LEVERAGE IMPLICATIONS: (1-2 sentences on how this shifts negotiating power)
LIKELY MOVES: (2-3 bullet points on what {payer_name} would do in response)
RISK FACTORS: (1-2 sentences on what could go wrong for {payer_name})
"""


@dataclass
class AnalysisResult:
    article: Article
    relevance_score: int = 0
    summary: str = ""
    parties: list = field(default_factory=list)
    negotiation_type: str = "other"
    states_affected: list = field(default_factory=list)
    key_insight: str = ""
    action_signals: list = field(default_factory=list)
    chain_of_thought: str = ""
    payer_perspectives: dict = field(default_factory=dict)  # payer_name -> text
    error: Optional[str] = None


@dataclass
class ThoughtStep:
    """A single step in the chain of thought, for UI streaming."""
    phase: str  # "fetch", "analyze", "payer_inference"
    article_title: str = ""
    payer_name: str = ""
    message: str = ""
    raw_response: str = ""
    timestamp: str = ""


def _call_ollama(
    messages: list[dict],
    temperature: float = 0.2,
    *,
    json_mode: bool = False,
    num_predict: int = 1000,
) -> str:
    payload: dict = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    if json_mode:
        # Ollama emits valid JSON; avoids unescaped quotes/newlines from free-form output.
        payload["format"] = "json"

    def _post() -> str:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    return get_cached_or_run(payload, _post)


def _parse_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text).strip()
    start, end = text.find("{"), text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


def _parse_json_lenient(text: str) -> dict:
    """When JSON is still invalid (truncation, etc.), keep a minimal structured result."""
    score = 5
    if m := re.search(r'"relevance_score"\s*:\s*(\d+)', text):
        score = int(m.group(1))
    return {
        "relevance_score": score,
        "summary": text[:2000],
        "parties": [],
        "negotiation_type": "other",
        "states_affected": [],
        "key_insight": "",
        "action_signals": [],
        "chain_of_thought": text[:2000],
    }


def check_ollama() -> tuple[bool, str]:
    """Returns (available, message)."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            base = OLLAMA_MODEL.split(":")[0]
            if any(base in m for m in models):
                return True, f"Connected. Model '{OLLAMA_MODEL}' available."
            return False, f"Model '{OLLAMA_MODEL}' not found. Available: {models}"
    except Exception as e:
        return False, f"Cannot connect to Ollama at {OLLAMA_BASE_URL}: {e}"


def analyze_article(
    article: Article,
    on_thought: Optional[Callable[[ThoughtStep], None]] = None,
    run_payer_inference: bool = True,
) -> AnalysisResult:
    """Full analysis pipeline for a single article."""
    result = AnalysisResult(article=article)

    # --- Get full text ---
    text = article.content or article.summary
    if len(text) < 200:
        if on_thought:
            on_thought(ThoughtStep("fetch", article.title, message="Fetching full article text..."))
        full = fetch_article_content(article.url)
        if full:
            text = full
            article.content = full

    if not text:
        text = article.title

    # --- Article analysis ---
    if on_thought:
        on_thought(ThoughtStep("analyze", article.title, message="Analyzing with LLM..."))

    prompt = ANALYSIS_PROMPT.format(
        title=article.title,
        source=article.source,
        keywords=", ".join(article.matched_keywords[:10]),
        geo=", ".join(article.geo_tags) or "none",
        text=text[:4000],
    )

    try:
        raw = _call_ollama(
            [
                {"role": "system", "content": ANALYSIS_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
            num_predict=4096,
        )
        try:
            parsed = _parse_json(raw)
        except json.JSONDecodeError:
            parsed = _parse_json_lenient(raw)

        result.relevance_score = int(parsed.get("relevance_score", 0))
        result.summary = parsed.get("summary", "")
        result.parties = parsed.get("parties", [])
        result.negotiation_type = parsed.get("negotiation_type", "other")
        result.states_affected = parsed.get("states_affected", [])
        result.key_insight = parsed.get("key_insight", "")
        result.action_signals = parsed.get("action_signals", [])
        result.chain_of_thought = parsed.get("chain_of_thought", "")

        if on_thought:
            on_thought(ThoughtStep(
                "analyze", article.title,
                message=f"Score: {result.relevance_score}/10 — {result.key_insight[:100]}",
                raw_response=raw,
            ))

    except json.JSONDecodeError as e:
        result.error = f"JSON parse: {e}"
        result.relevance_score = 5
        if on_thought:
            on_thought(ThoughtStep("analyze", article.title, message=f"⚠ Parse error: {e}"))
    except Exception as e:
        result.error = str(e)
        if on_thought:
            on_thought(ThoughtStep("analyze", article.title, message=f"⚠ Error: {e}"))
        return result

    # --- Payer perspective inference ---
    if run_payer_inference and result.relevance_score >= MIN_RELEVANCE_SCORE:
        for payer_name, system_prompt in PAYER_INFERENCE_PROMPTS.items():
            if on_thought:
                on_thought(ThoughtStep(
                    "payer_inference", article.title, payer_name=payer_name,
                    message=f"Inferring {payer_name} perspective...",
                ))

            user_prompt = PAYER_INFERENCE_USER.format(
                title=article.title,
                source=article.source,
                summary=result.summary or text[:500],
                payer_name=payer_name,
            )

            try:
                payer_raw = _call_ollama([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ], temperature=0.4)

                result.payer_perspectives[payer_name] = payer_raw

                if on_thought:
                    # Extract first line as preview
                    preview = payer_raw.split("\n")[0][:100] if payer_raw else ""
                    on_thought(ThoughtStep(
                        "payer_inference", article.title, payer_name=payer_name,
                        message=f"✓ {payer_name}: {preview}",
                        raw_response=payer_raw,
                    ))

            except Exception as e:
                result.payer_perspectives[payer_name] = f"[Error: {e}]"
                if on_thought:
                    on_thought(ThoughtStep(
                        "payer_inference", article.title, payer_name=payer_name,
                        message=f"⚠ {payer_name} inference failed: {e}",
                    ))

    return result


def analyze_batch(
    articles: list[Article],
    on_thought: Optional[Callable[[ThoughtStep], None]] = None,
    run_payer_inference: bool = True,
) -> list[AnalysisResult]:
    results = []
    for i, article in enumerate(articles):
        if on_thought:
            on_thought(ThoughtStep(
                "analyze", article.title,
                message=f"[{i+1}/{len(articles)}] Starting analysis...",
            ))
        r = analyze_article(article, on_thought, run_payer_inference)
        if r.relevance_score >= MIN_RELEVANCE_SCORE:
            results.append(r)
    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results
