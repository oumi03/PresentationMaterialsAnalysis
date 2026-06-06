"""corrections.json の指示に従い，_fixed キャッシュを修正する.

api フィールドの意味:
  "ok"       同一論文とみなす → cvpr_match=True にしてそのまま保持
  URL/ID     その論文が正解 → S2 API で取得して matched_title・引用数を更新
  タイトル文字列  タイトル検索で正解を探す → 取得して更新
  ""（空）   スキップ

使い方:
  uv run python apply_corrections.py              # output/result/corrections.json を使用
  uv run python apply_corrections.py --dry-run    # 変更内容の確認のみ（保存しない）
  uv run python apply_corrections.py --input path/to/corrections.json
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import requests

from semantic_scholar import _search_one, _save_cache

_FIELDS = "title,citationCount,year,venue,authors"
_API_BASE = "https://api.semanticscholar.org/graph/v1/paper"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def _extract_paper_id(api_value: str) -> str | None:
    """URL または生 ID から 40 桁の S2 paper ID を抽出する."""
    m = re.search(r"[0-9a-f]{40}", api_value, re.IGNORECASE)
    return m.group(0) if m else None


def _is_ok(api_value: str) -> bool:
    return api_value.strip().lower() == "ok"


def _fetch_by_id(paper_id: str, headers: dict, delay: float) -> dict | None:
    """paper ID を指定して S2 API から論文データを取得する."""
    url = f"{_API_BASE}/{paper_id}?fields={_FIELDS}"
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                d = resp.json()
                return {
                    "found":         True,
                    "title":         d.get("title", ""),
                    "citationCount": d.get("citationCount"),
                    "year":          d.get("year"),
                    "venue":         d.get("venue", ""),
                    "authors":       [a.get("name", "") for a in d.get("authors", [])],
                    "similarity":    1.0,
                }
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"    [429] {wait}s 待機...")
                time.sleep(wait)
                continue
            print(f"    [HTTP {resp.status_code}] paper_id={paper_id}")
            return None
        except requests.RequestException as e:
            print(f"    [error] {e}")
            time.sleep(5)
    return None


def is_cvpr_match(entry: dict, target_year: int) -> bool:
    venue = (entry.get("venue") or "").lower()
    year = entry.get("year")
    return (
        "computer vision and pattern recognition" in venue
        and year in (target_year - 2, target_year - 1, target_year)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="corrections.json を適用して _fixed キャッシュを修正する")
    parser.add_argument("--input", default=None, metavar="FILE")
    parser.add_argument("--api-key", default=None, metavar="KEY")
    parser.add_argument("--dry-run", action="store_true", help="保存せずに変更内容を確認する")
    args = parser.parse_args()

    base = Path(__file__).parent
    load_env(base / ".env")
    api_key = args.api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or None
    headers: dict = {"x-api-key": api_key} if api_key else {}
    delay = 1.1 if api_key else 3.1

    corrections_path = Path(args.input) if args.input else base / "output" / "result" / "corrections.json"
    if not corrections_path.exists():
        print(f"ファイルが見つかりません: {corrections_path}")
        return

    corrections: list[dict] = json.loads(corrections_path.read_text(encoding="utf-8"))

    ok_entries  = [c for c in corrections if _is_ok(c.get("api", ""))]
    url_entries = [c for c in corrections if c.get("api", "").strip() and not _is_ok(c.get("api", ""))]
    skip_entries = [c for c in corrections if not c.get("api", "").strip()]

    print(f"=== 修正適用 ({'dry-run' if args.dry_run else '実行'}) ===")
    print(f"  ok（cvpr_match=True に昇格） : {len(ok_entries)} 件")
    print(f"  url/title（正解に差し替え）  : {len(url_entries)} 件")
    print(f"  空欄（スキップ）             : {len(skip_entries)} 件")
    print()

    # ── キャッシュ読み込み ───────────────────────────────────────
    cache_dir = base / "output" / "cache"
    caches: dict[int, dict] = {}

    def _get_cache(year: int) -> dict:
        if year not in caches:
            path = cache_dir / f"cache_citations_{year}_fixed.json"
            if not path.exists():
                path = cache_dir / f"cache_citations_{year}.json"
            caches[year] = json.loads(path.read_text(encoding="utf-8"))
        return caches[year]

    # ── "ok" 処理：cvpr_match=True にするだけ ───────────────────
    print("─" * 60)
    print("【ok】cvpr_match=True に昇格")
    print("─" * 60)
    ok_count = 0
    for c in ok_entries:
        year  = c["target_year"]
        query = c["query_title"]
        cache = _get_cache(year)

        if query not in cache:
            print(f"  [not found in cache] [{year}] {query[:70]}")
            continue

        entry = cache[query]
        old_flag = entry.get("cvpr_match")
        print(f"  [{year}] {query[:70]}")
        print(f"    cvpr_match: {old_flag} → True")

        if not args.dry_run:
            entry["cvpr_match"] = True
        ok_count += 1

    print(f"  合計: {ok_count} 件\n")

    # ── URL / タイトル処理：正解で差し替え ───────────────────────
    print("─" * 60)
    print("【url/title】正解に差し替え")
    print("─" * 60)
    applied = errors = 0
    for c in url_entries:
        year  = c["target_year"]
        query = c["query_title"]
        api   = c["api"].strip()
        cache = _get_cache(year)

        print(f"  [{year}] {query[:70]}")
        print(f"    api  : {api[:80]}")

        # paper ID が抽出できれば ID 取得，できなければタイトル検索
        paper_id = _extract_paper_id(api)
        if paper_id:
            new_data = _fetch_by_id(paper_id, headers, delay)
        else:
            print(f"    → タイトル検索: {api[:60]}")
            new_data = _search_one(api, headers, delay)
            if new_data and new_data.get("found"):
                new_data["similarity"] = 1.0

        time.sleep(delay)

        if not new_data or not new_data.get("found"):
            print("    → 取得失敗、スキップ")
            errors += 1
            continue

        new_data["query"]      = query
        new_data["cvpr_match"] = is_cvpr_match(new_data, year)

        old = cache.get(query, {})
        print(f"    old title  : {old.get('title', '(なし)')[:80]}")
        print(f"    new title  : {new_data['title'][:80]}")
        print(f"    cite       : {old.get('citationCount')} → {new_data['citationCount']}")
        print(f"    cvpr_match : {old.get('cvpr_match')} → {new_data['cvpr_match']}")

        if not args.dry_run:
            cache[query] = new_data
        applied += 1
        print()

    # ── 保存 ──────────────────────────────────────────────────────
    if not args.dry_run:
        for year, data in caches.items():
            out = cache_dir / f"cache_citations_{year}_fixed.json"
            _save_cache(data, str(out))
            print(f"→ 保存: {out}")
        print()

    print("=" * 60)
    print(f"ok 昇格  : {ok_count} 件")
    print(f"差し替え : {applied} 件  /  エラー: {errors} 件")
    if args.dry_run:
        print("（dry-run のため保存はされていません）")


if __name__ == "__main__":
    main()
