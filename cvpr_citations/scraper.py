"""Fetch CVPR paper titles from the CVF website."""

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "CVPR-citation-research/1.0 (academic use; non-commercial)"
    )
}

# Polite crawl delay (seconds) — respect robots.txt spirit
CRAWL_DELAY = 2.0


def fetch_cvpr_papers(url: str, cache_path: str = "cache_papers.json") -> list[str]:
    """Return a list of paper titles, using a local cache when available."""
    cache = Path(cache_path)
    if cache.exists():
        try:
            titles = json.loads(cache.read_text(encoding="utf-8"))
            if titles:
                print(f"[scraper] Loaded {len(titles)} titles from cache: {cache_path}")
                return titles
            print(f"[scraper] Cache is empty, re-fetching: {cache_path}")
        except json.JSONDecodeError:
            print(f"[scraper] Cache is corrupt, re-fetching: {cache_path}")

    print(f"[scraper] Fetching {url}")
    time.sleep(CRAWL_DELAY)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    titles = _parse(resp.text, url)
    if not titles:
        raise ValueError(
            f"Could not extract paper titles from {url}\n"
            "Try the openaccess URL instead: "
            "https://openaccess.thecvf.com/CVPR2024?day=all"
        )

    cache.write_text(
        json.dumps(titles, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[scraper] Saved {len(titles)} titles → {cache_path}")
    return titles


def _parse(html: str, url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    titles: list[str] = []

    # 1. openaccess.thecvf.com — <dt class="ptitle"><a>Title</a></dt>
    for el in soup.select("dt.ptitle a"):
        t = el.get_text(strip=True)
        if t:
            titles.append(t)
    if titles:
        return _dedup(titles)

    # 2. cvpr.thecvf.com conference page — paper title links inside a list
    #    The page wraps each paper in a container; titles are the first <a>
    #    with substantial text inside each paper block.
    for el in soup.select(".paper-title, .papertitle, a.paper-title"):
        t = el.get_text(strip=True)
        if t:
            titles.append(t)
    if titles:
        return _dedup(titles)

    # 3. cvpr.thecvf.com/Conferences/YYYY/AcceptedPapers
    #    Each paper is a <td> containing a <div class="indented"> (authors).
    #    Title is in <a> (papers with project page) or <strong> (others).
    for indented in soup.select("div.indented"):
        td = indented.parent
        if td.name != "td":
            continue
        a = td.find("a", recursive=False)
        if a:
            t = a.get_text(strip=True)
        else:
            strong = td.find("strong", recursive=False)
            t = strong.get_text(strip=True) if strong else ""
        if t:
            titles.append(t)
    if titles:
        return _dedup(titles)

    # 4. Generic fallback: look for <a> tags that look like paper titles
    #    (between 10 and 300 chars, not navigational)
    nav_keywords = {
        "home", "about", "program", "login", "register",
        "schedule", "workshop", "tutorial", "sponsor",
    }
    for el in soup.select("a"):
        t = el.get_text(strip=True)
        if 15 < len(t) < 300 and t.lower() not in nav_keywords:
            parent_classes = " ".join(el.parent.get("class", []))
            # Skip nav/header/footer links
            if not any(k in parent_classes for k in ("nav", "menu", "header", "footer")):
                titles.append(t)
    return _dedup(titles)


def _dedup(titles: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for t in titles:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result
