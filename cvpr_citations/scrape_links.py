"""CVPR 採択論文のタイトルとプロジェクトリンクを収集して保存する.

使い方:
  uv run python scrape_links.py              # 2025（デフォルト）
  uv run python scrape_links.py --year 2023  # 2023〜2025 に対応

出力:
  output/cvpr{year}_links.csv   -- タイトル・リンク種別・URL の一覧
  output/cvpr{year}_links.json  -- 同内容の JSON

presentation_type の値:
  highlight       -- Highlight バッジあり（2023〜2025 共通）
  award_candidate -- Award Candidate バッジあり（2023 のみ）
  poster          -- 上記以外
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "CVPR-citation-research/1.0 (academic use; non-commercial)"
    )
}
CRAWL_DELAY = 2.0

YEAR_URLS = {
    2023: "https://cvpr.thecvf.com/Conferences/2023/AcceptedPapers",
    2024: "https://cvpr.thecvf.com/Conferences/2024/AcceptedPapers",
    2025: "https://cvpr.thecvf.com/Conferences/2025/AcceptedPapers",
    # 2026: "https://cvpr.thecvf.com/Conferences/2026/AcceptedPapers",
}

# 年ごとに追加で検出するバッジ（presentation_type に反映）
# 値が多い場合は先に書いたものが優先される
EXTRA_BADGES: dict[int, list[str]] = {
    2023: ["Award Candidate"],
}


def classify_link(href: str) -> str:
    """リンクの種別を返す: 'github' / 'project_page' / 'none'"""
    if not href or not href.startswith("http"):
        return "none"
    if "github.com" in href or ".github.io" in href:
        return "github"
    return "project_page"


def parse_papers(html: str, extra_badges: list[str] | None = None) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    papers: list[dict] = []

    for indented in soup.select("div.indented"):
        td = indented.parent
        if td.name != "td":
            continue

        a = td.find("a", recursive=False)
        if a:
            title = a.get_text(strip=True)
            href = a.get("href", "").strip()
            link_type = classify_link(href)
            link = href if link_type != "none" else ""
        else:
            strong = td.find("strong", recursive=False)
            if not strong:
                continue
            title = strong.get_text(strip=True)
            link_type = "none"
            link = ""

        if not title:
            continue

        # タイトル要素とdiv.indentedの間のバッジを確認して発表種別を判定
        # 優先順: Highlight > Award Candidate（extra_badges）> poster
        title_el = a if a else strong
        presentation_type = "poster"
        badge_map = {"Highlight": "highlight"}
        for badge in (extra_badges or []):
            badge_key = badge.lower().replace(" ", "_")
            badge_map[badge] = badge_key
        for sib in title_el.next_siblings:
            if hasattr(sib, "name") and sib.name:
                if sib.name == "div":
                    break
                if sib.name == "img":
                    img_title = sib.get("title", "")
                    if img_title in badge_map:
                        presentation_type = badge_map[img_title]
                        break

        papers.append({
            "title": title,
            "link_type": link_type,
            "link": link,
            "presentation_type": presentation_type,
        })

    return papers


def fetch_html(url: str, cache_path: Path) -> str:
    if cache_path.exists():
        print(f"[scraper] キャッシュから読み込み: {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    print(f"[scraper] フェッチ中: {url}")
    time.sleep(CRAWL_DELAY)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    print(f"[scraper] キャッシュ保存: {cache_path.name}")
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser(description="CVPR 採択論文のリンク情報を収集")
    parser.add_argument("--year", type=int, default=2025, help="対象年度（デフォルト: 2025）")
    args = parser.parse_args()

    if args.year not in YEAR_URLS:
        supported = ", ".join(str(y) for y in YEAR_URLS)
        print(f"エラー: 未対応の年度 {args.year}（対応: {supported}）")
        return

    url = YEAR_URLS[args.year]
    base = Path(__file__).parent / "output"
    cache_dir = base / "cache"
    result_dir = base / "result"
    cache_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    cache_html = cache_dir / f"cache_cvpr{args.year}_accepted.html"

    html = fetch_html(url, cache_html)
    extra_badges = EXTRA_BADGES.get(args.year, [])
    papers = parse_papers(html, extra_badges)

    if not papers:
        print("論文が見つかりませんでした。HTML 構造が変わっている可能性があります。")
        return

    # 統計表示
    n = len(papers)
    link_counts: dict[str, int] = {"github": 0, "project_page": 0, "none": 0}
    ptype_counts: dict[str, int] = {}
    for p in papers:
        link_counts[p["link_type"]] = link_counts.get(p["link_type"], 0) + 1
        ptype_counts[p["presentation_type"]] = ptype_counts.get(p["presentation_type"], 0) + 1

    print(f"\n=== CVPR {args.year} リンク集計 ===")
    print(f"  総論文数         : {n}")
    print(f"  GitHub           : {link_counts['github']}  ({link_counts['github']/n*100:.1f}%)")
    print(f"  他 project page  : {link_counts['project_page']}  ({link_counts['project_page']/n*100:.1f}%)")
    print(f"  リンクなし       : {link_counts['none']}  ({link_counts['none']/n*100:.1f}%)")
    print(f"  Highlight        : {ptype_counts.get('highlight', 0)}  ({ptype_counts.get('highlight', 0)/n*100:.1f}%)")
    if extra_badges:
        for badge in extra_badges:
            key = badge.lower().replace(" ", "_")
            cnt = ptype_counts.get(key, 0)
            print(f"  {badge:<16} : {cnt}  ({cnt/n*100:.1f}%)")
    posters = ptype_counts.get("poster", 0)
    print(f"  通常 Poster      : {posters}  ({posters/n*100:.1f}%)")

    # 保存
    df = pd.DataFrame(papers)
    out_csv = result_dir / f"cvpr{args.year}_links.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n→ CSV  保存: {out_csv}")

    out_json = result_dir / f"cvpr{args.year}_links.json"
    out_json.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ JSON 保存: {out_json}")


if __name__ == "__main__":
    main()
