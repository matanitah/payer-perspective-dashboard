#!/usr/bin/env python3
"""
CLI entry point — runs the pipeline once or on schedule.
For the Streamlit dashboard, run: uv run streamlit run app/dashboard.py
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

from app.knowledge import LOG_PATH, REPORTS_DIR
from app.analyzer import analyze_batch, check_ollama, ThoughtStep
from app.fetcher import fetch_all
from app.persistence import load_seen, save_seen, filter_unseen, mark_seen


def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler(),
        ],
    )


def severity(score):
    if score >= 9: return "🔴"
    if score >= 7: return "🟠"
    return "🟡"


def run_pipeline():
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting scan cycle")

    articles = fetch_all(on_status=lambda m: logger.info(m))
    if not articles:
        logger.info("No relevant articles.")
        return

    seen_db = load_seen()
    new = filter_unseen(articles, seen_db)
    if not new:
        logger.info("All articles already seen.")
        return

    logger.info(f"{len(new)} new articles to analyze")

    def on_thought(step: ThoughtStep):
        tag = f"[{step.payer_name}] " if step.payer_name else ""
        logger.info(f"  {tag}{step.message}")

    results = analyze_batch(new, on_thought=on_thought)
    seen_db = mark_seen(new, seen_db)
    save_seen(seen_db)

    if results:
        print(f"\n{'='*60}")
        print(f"  RESULTS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  {len(results)} articles above threshold")
        print(f"{'='*60}\n")
        for r in results[:10]:
            geo = " ".join(r.states_affected) if r.states_affected else "NAT"
            print(f"  {severity(r.relevance_score)} [{r.relevance_score}/10] [{geo}] {r.article.title[:65]}")
            if r.key_insight:
                print(f"     {r.key_insight[:80]}")
            print()
    else:
        print("\n  No articles above threshold.\n")


def main():
    parser = argparse.ArgumentParser(description="Healthcare Negotiation Monitor CLI")
    parser.add_argument("--schedule", action="store_true", help="Run every 60 minutes")
    parser.add_argument("--test", action="store_true", help="Test Ollama connection")
    parser.add_argument("--fetch-only", action="store_true", help="Fetch without Ollama")
    args = parser.parse_args()

    setup_logging()

    if args.test:
        ok, msg = check_ollama()
        print(f"{'✅' if ok else '❌'} {msg}")
        sys.exit(0 if ok else 1)

    if args.fetch_only:
        articles = fetch_all(on_status=print)
        seen = load_seen()
        new = filter_unseen(articles, seen)
        print(f"\n{len(articles)} relevant, {len(new)} new")
        for a in new[:15]:
            geo = " ".join(a.geo_tags) if a.geo_tags else ""
            print(f"  • [{geo}] {a.source}: {a.title[:65]}")
        return

    if not check_ollama()[0]:
        print("❌ Ollama not available. Start it or use --fetch-only.")
        sys.exit(1)

    if args.schedule:
        print("Running every 60 minutes. Ctrl+C to stop.\n")
        run_pipeline()
        schedule.every(60).minutes.do(run_pipeline)
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        run_pipeline()


if __name__ == "__main__":
    main()
