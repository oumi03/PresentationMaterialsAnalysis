"""project page / github.io から GitHub リポジトリリンクを収集する.

使い方:
  uv run python scrape_project_github.py                   # CVPR 2025（デフォルト）
  uv run python scrape_project_github.py --year 2023
  uv run python scrape_project_github.py --conf cvpr --year 2023
  uv run python scrape_project_github.py --year 2023 --limit 20  # テスト用（先頭 20 件）

前提:
  output/result_{conf}/{conf}{year}_links.csv  -- scrape_links.py の出力

出力:
  output/result_{conf}/project_github_{year}.json  -- 論文ごとの詳細
  output/result_{conf}/project_github_{year}.csv
キャッシュ:
  output/cache_{conf}/cache_project_github_{year}.json  -- URL 別スクレイピング結果
"""

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from conf_utils import add_conf_argument, cache_dir, result_dir

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "CVF-citation-research/1.0 (academic use; non-commercial)"
    )
}
CRAWL_DELAY = 1.0
TIMEOUT = 15

# github.com/user/repo にマッチ（github.io は除外）
_GITHUB_REPO_RE = re.compile(
    r'https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)'
)
# リポジトリではない github.com のパス
_GITHUB_NON_REPO_USERS = {
    "features", "pricing", "marketplace", "login", "about", "topics",
    "trending", "explore", "organizations", "sponsors", "apps",
    "issues", "pulls", "settings", "notifications", "new", "orgs",
}
# コードリポジトリを示すアンカーテキストのキーワード
_CODE_KEYWORDS = {"code", "github", "source", "implementation", "repo", "repository"}


def classify_project_url_type(link_type: str, link: str) -> str:
    if link_type == "project_page":
        return "project_page"
    return "github_io"


def _parse_github_url(href: str) -> str | None:
    """href が github.com/user/repo 形式なら正規化した URL を返す. それ以外は None."""
    if not href or "github.io" in href:
        return None
    m = _GITHUB_REPO_RE.search(href)
    if not m:
        return None
    user = m.group(1)
    repo = m.group(2).rstrip(".,;:\"')")
    if user.lower() in _GITHUB_NON_REPO_USERS:
        return None
    return f"https://github.com/{user}/{repo}"


def extract_github_repos(html: str) -> list[str]:
    """HTML の <a> タグから github.com/user/repo 形式の URL を返す.

    アンカーテキストにコード関連キーワードを含むリンクを優先する.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    priority: list[str] = []   # コードキーワードあり
    others: list[str] = []     # それ以外

    for a in soup.find_all("a", href=True):
        url = _parse_github_url(a["href"])
        if url is None or url in seen:
            continue
        seen.add(url)
        text = a.get_text(strip=True).lower()
        if any(kw in text for kw in _CODE_KEYWORDS):
            priority.append(url)
        else:
            others.append(url)

    return priority + others


def fetch_page(url: str) -> tuple[str, str]:
    """ページを取得して (html, fetch_status) を返す."""
    try:
        time.sleep(CRAWL_DELAY)
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code == 404:
            return "", "not_found"
        resp.raise_for_status()
        return resp.text, "success"
    except requests.exceptions.Timeout:
        return "", "timeout"
    except Exception:
        return "", "error"


def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[cache] 破損したキャッシュを無視: {cache_path.name}")
    return {}


def save_cache(cache: dict, cache_path: Path) -> None:
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="project page / github.io から GitHub リポジトリリンクを収集"
    )
    add_conf_argument(parser)
    parser.add_argument("--year", type=int, default=2025, help="対象年度（デフォルト: 2025）")
    parser.add_argument("--limit", type=int, default=None, help="処理件数の上限（省略時は全件; テスト用）")
    args = parser.parse_args()

    base = Path(__file__).parent
    c_dir = cache_dir(base, args.conf)
    r_dir = result_dir(base, args.conf)
    c_dir.mkdir(parents=True, exist_ok=True)
    r_dir.mkdir(parents=True, exist_ok=True)

    links_csv = r_dir / f"{args.conf}{args.year}_links.csv"
    if not links_csv.exists():
        print(f"エラー: {links_csv} が見つかりません。scrape_links.py を先に実行してください。")
        return

    df = pd.read_csv(links_csv)

    # project_page または github.io に絞る
    is_project_page = df["link_type"] == "project_page"
    is_github_io = (df["link_type"] == "github") & df["link"].str.contains("github.io", na=False)
    target = df[is_project_page | is_github_io].copy()

    if args.limit:
        target = target.head(args.limit)
        print(f"[limit] 先頭 {args.limit} 件に絞って処理します")

    print(f"=== {args.conf.upper()} {args.year} Project Page / GitHub.io スクレイピング ===")
    print(f"  対象 : {len(target)} 件 / 全 {len(df)} 件")
    print(f"    project_page : {is_project_page.sum()} 件")
    print(f"    github.io    : {is_github_io.sum()} 件")

    cache_path = c_dir / f"cache_project_github_{args.year}.json"
    url_cache: dict = load_cache(cache_path)
    cached_count = sum(1 for url in target["link"] if url in url_cache)
    print(f"  キャッシュ済み: {cached_count} 件 / {len(target)} 件")
    print()

    results = []
    for i, row in enumerate(target.itertuples(), 1):
        url = row.link
        prefix = f"  [{i:4d}/{len(target)}]"

        if url in url_cache:
            cached = url_cache[url]
            github_repo_url = cached.get("github_repo_url", "")
            fetch_status = cached.get("fetch_status", "success")
            print(f"{prefix} キャッシュ: {url[:70]}")
        else:
            print(f"{prefix} フェッチ中: {url[:70]}")
            html, fetch_status = fetch_page(url)
            repos = extract_github_repos(html) if html else []
            github_repo_url = repos[0] if repos else ""
            url_cache[url] = {
                "github_repo_url": github_repo_url,
                "fetch_status": fetch_status,
            }
            save_cache(url_cache, cache_path)
            if fetch_status != "success":
                print(f"           → {fetch_status}")
            elif github_repo_url:
                print(f"           → {github_repo_url}")

        results.append({
            "title": row.title,
            "link_type": row.link_type,
            "link": row.link,
            "presentation_type": row.presentation_type,
            "year": args.year,
            "project_url_type": classify_project_url_type(row.link_type, row.link),
            "github_repo_url": github_repo_url,
            "has_github_repo": bool(github_repo_url),
            "fetch_status": fetch_status,
        })

    # 集計
    total = len(results)
    has_repo = sum(1 for r in results if r["has_github_repo"])
    n_success = sum(1 for r in results if r["fetch_status"] == "success")
    n_not_found = sum(1 for r in results if r["fetch_status"] == "not_found")
    n_error = sum(1 for r in results if r["fetch_status"] in ("timeout", "error"))

    print(f"\n=== {args.conf.upper()} {args.year} 集計 ===")
    print(f"  スクレイピング対象    : {total}")
    print(f"  GitHub リポジトリあり : {has_repo}  ({has_repo/total*100:.1f}%)")
    print(f"  GitHub リポジトリなし : {n_success - has_repo}  ({(n_success - has_repo)/total*100:.1f}%)")
    print(f"  404 Not Found         : {n_not_found}")
    print(f"  タイムアウト/エラー   : {n_error}")

    out_json = r_dir / f"project_github_{args.year}.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ JSON 保存: {out_json}")

    out_csv = r_dir / f"project_github_{args.year}.csv"
    pd.DataFrame(results).to_csv(out_csv, index=False)
    print(f"→ CSV  保存: {out_csv}")

    print(f"→ キャッシュ: {cache_path}")


if __name__ == "__main__":
    main()
