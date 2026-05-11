"""
Fetches articles from RSS feeds and scraped web pages.
Filters for topic relevance and tags geographic relevance (NY/CT/NJ).
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from app.knowledge import (
    GEO_KEYWORDS, MAX_ARTICLES_PER_SOURCE, RSS_FEEDS,
    SCRAPE_SOURCES, TOPIC_KEYWORDS,
)

logger = logging.getLogger(__name__)

# Browser-like headers: many publishers return 403 to library/script user agents or bare bots.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, application/xml, "
        "text/xml;q=0.9, text/html;q=0.8, */*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 20


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: Optional[datetime] = None
    summary: str = ""
    content: str = ""
    uid: str = ""
    matched_keywords: list = field(default_factory=list)
    geo_tags: list = field(default_factory=list)  # e.g. ["NY", "CT"]

    def __post_init__(self):
        if not self.uid:
            self.uid = hashlib.sha256(self.url.encode()).hexdigest()[:16]


def _match_topics(text: str) -> list[str]:
    low = text.lower()
    return [kw for kw in TOPIC_KEYWORDS if kw.lower() in low]


def _match_geo(text: str) -> list[str]:
    low = text.lower()
    tags = []
    for state, keywords in GEO_KEYWORDS.items():
        if any(kw.lower() in low for kw in keywords):
            tags.append(state)
    return tags


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        p = getattr(entry, attr, None)
        if p:
            try:
                return datetime(*p[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _strip_html(html: str, max_chars: int = 3000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header", "aside"]):
        t.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)[:max_chars]


def _rss_title_and_link(entry, feed_home: str | None = None) -> tuple[str, str]:
    """Plain-text title and canonical URL. Some feeds (e.g. CMS) put HTML <a> in title and broken links."""
    raw_title = getattr(entry, "title", "") or ""
    link = (getattr(entry, "link", "") or "").strip()
    base = (feed_home or "").rstrip("/") + "/" if feed_home else None

    title = _strip_html(raw_title, 500) if "<" in raw_title else raw_title.strip()
    if not title:
        title = raw_title.strip()

    if "<" in raw_title and ">" in raw_title:
        soup = BeautifulSoup(raw_title, "html.parser")
        a = soup.find("a", href=True)
        if a:
            t = soup.get_text(separator=" ", strip=True)
            if t:
                title = re.sub(r"\s+", " ", t)[:500]
            href = (a.get("href") or "").strip()
            if href:
                if href.startswith("/") or not href.startswith("http"):
                    href = urljoin(base or "https://www.cms.gov/", href)
                bad = "%3C" in link or "%3ca" in link.lower() or "/%3Ca%20href" in link
                if not link or bad or (link.startswith("https://www.cms.gov/") and "%" in link[:40]):
                    link = href

    if not link or "%3C" in link:
        for item in getattr(entry, "links", []) or []:
            h = (item.get("href") or "").strip()
            if h and "%3C" not in h and not h.startswith("https://www.cms.gov/%"):
                link = h
                break

    return title, link


def fetch_article_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return _strip_html(r.text, 5000)
    except Exception as e:
        logger.warning(f"Content fetch failed {url}: {e}")
        return ""


def fetch_rss(on_status=None) -> list[Article]:
    """Fetch from all RSS feeds. on_status(msg) called per feed for UI updates."""
    articles = []
    for i, feed_cfg in enumerate(RSS_FEEDS):
        name = feed_cfg["name"]
        if on_status:
            on_status(f"[{i+1}/{len(RSS_FEEDS)}] Fetching {name}...")
        try:
            r = requests.get(feed_cfg["url"], headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            feed = feedparser.parse(r.text)
        except Exception as e:
            logger.warning(f"RSS fail {name}: {e}")
            continue

        feed_home = getattr(feed.feed, "link", None) or None
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            title, link = _rss_title_and_link(entry, feed_home=feed_home)
            if not title or not link:
                continue
            summary_html = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = _strip_html(summary_html, 1500)
            searchable = f"{title} {summary}"

            matched = _match_topics(searchable)
            if not matched:
                continue

            articles.append(Article(
                title=title.strip(),
                url=link.strip(),
                source=name,
                published=_parse_date(entry),
                summary=summary[:500],
                matched_keywords=matched,
                geo_tags=_match_geo(searchable),
            ))
        time.sleep(0.3)

    return articles


def fetch_scraped(on_status=None) -> list[Article]:
    articles = []
    for src in SCRAPE_SOURCES:
        name = src["name"]
        if on_status:
            on_status(f"Scraping {name}...")
        try:
            r = requests.get(src["url"], headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            logger.warning(f"Scrape fail {name}: {e}")
            continue

        seen = set()
        count = 0
        for tag in soup.select(src["selector"])[:MAX_ARTICLES_PER_SOURCE * 2]:
            title = tag.get_text(strip=True)
            href = tag.get("href", "")
            if not title or not href:
                continue
            url = urljoin(src.get("base_url", ""), href) if not href.startswith("http") else href
            if url in seen:
                continue
            seen.add(url)
            matched = _match_topics(title)
            if not matched:
                continue
            articles.append(Article(
                title=title, url=url, source=name,
                matched_keywords=matched, geo_tags=_match_geo(title),
            ))
            count += 1
            if count >= MAX_ARTICLES_PER_SOURCE:
                break
        time.sleep(0.3)

    return articles


def fetch_all(on_status=None) -> list[Article]:
    articles = fetch_rss(on_status) + fetch_scraped(on_status)
    articles.sort(key=lambda a: (len(a.geo_tags), len(a.matched_keywords)), reverse=True)
    if on_status:
        on_status(f"Found {len(articles)} relevant articles ({sum(1 for a in articles if a.geo_tags)} geo-tagged)")
    return articles
