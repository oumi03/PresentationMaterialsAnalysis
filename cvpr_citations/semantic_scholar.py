"""Query the Semantic Scholar API for paper citation counts.

Rate limits (https://api.semanticscholar.org/):
  - Unauthenticated : 100 requests / 5 min  → ~3.1 s between calls
  - With API key    : 1 request / second     → ~1.1 s between calls

On 429: wait exactly 300 s (the rate-limit window) then retry.
After 3 retries, mark the paper as not-found and move on.
"""

import json
import time
from difflib import SequenceMatcher
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Fields returned for each paper
_FIELDS = "title,citationCount,year,venue,authors"


def fetch_citations(
    titles: list[str],
    api_key: str | None = None,
    cache_path: str = "cache_citations.json",
    delay: float | None = None,
) -> list[dict]:
    """Return citation data for each title, caching results between runs."""
    if delay is None:
        delay = 1.1 if api_key else 3.1

    cache = Path(cache_path)
    cached: dict[str, dict] = {}
    if cache.exists():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            print(f"[semantic] Loaded {len(cached)} cached entries from {cache_path}")
        except (json.JSONDecodeError, ValueError):
            print(f"[semantic] Cache is corrupt, starting fresh: {cache_path}")

    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key

    results: list[dict] = []
    new_count = 0

    for title in tqdm(titles, desc="Fetching citations", unit="paper"):
        if title in cached:
            results.append(cached[title])
            continue

        entry = _search_one(title, headers, delay)
        # Only cache definitive results (found OR genuine miss).
        # Rate-limit / network errors have an "error" key — skip caching so
        # the next run retries them rather than treating them as not-found.
        if entry.get("found") or "error" not in entry:
            cached[title] = entry
        results.append(entry)
        new_count += 1

        # Persist cache every 20 new entries so a crash loses little work
        if new_count % 20 == 0:
            _save_cache(cached, cache_path)

    _save_cache(cached, cache_path)
    print(f"[semantic] {new_count} new entries fetched; cache → {cache_path}")
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_RATE_LIMIT_WAIT_NO_KEY = 305  # 5分ウィンドウをクリアするのに必要な待機時間
_RATE_LIMIT_WAIT_WITH_KEY = 30  # APIキーありは1 RPS制限なので短い待機で十分


def _search_one(title: str, headers: dict, delay: float) -> dict:
    wait = _RATE_LIMIT_WAIT_WITH_KEY if headers else _RATE_LIMIT_WAIT_NO_KEY

    for attempt in range(_MAX_RETRIES):
        time.sleep(delay if attempt == 0 else 0)
        try:
            resp = requests.get(
                f"{BASE_URL}/paper/search",
                params={"query": title, "fields": _FIELDS, "limit": 5},
                headers=headers,
                timeout=20,
            )

            if resp.status_code == 429:
                tqdm.write(
                    f"[semantic] Rate limited (attempt {attempt+1}/{_MAX_RETRIES}) "
                    f"— waiting {wait}s …"
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            papers = resp.json().get("data", [])
            break

        except requests.RequestException as exc:
            tqdm.write(f"[semantic] Error for '{title[:60]}': {exc}")
            return _not_found(title, error=str(exc))
    else:
        tqdm.write(f"[semantic] Gave up after {_MAX_RETRIES} retries: '{title[:60]}'")
        return _not_found(title, error="max retries exceeded")

    if not papers:
        return _not_found(title)

    # Pick the candidate with the highest title similarity
    best = max(papers, key=lambda p: _sim(title, p.get("title") or ""))
    similarity = _sim(title, best.get("title") or "")

    if similarity < 0.5:
        return _not_found(title)

    authors = [a.get("name", "") for a in (best.get("authors") or [])[:5]]
    return {
        "query": title,
        "title": best.get("title"),
        "citationCount": best.get("citationCount"),
        "year": best.get("year"),
        "venue": best.get("venue"),
        "authors": authors,
        "similarity": round(similarity, 3),
        "found": True,
    }


def _not_found(title: str, error: str | None = None) -> dict:
    entry: dict = {"query": title, "title": None, "citationCount": None, "found": False}
    if error:
        entry["error"] = error
    return entry


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _save_cache(data: dict, path: str) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
