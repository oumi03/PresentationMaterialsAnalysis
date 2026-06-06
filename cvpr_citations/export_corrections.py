"""cvpr_match=False かつ similarity < 1.0 の論文を JSON に書き出す.

出力 JSON の "api" 欄に Semantic Scholar の paper ID（または URL）を
手動で記入し，apply_corrections.py で修正を適用する．

使い方:
  uv run python export_corrections.py              # 2021〜2025
  uv run python export_corrections.py --years 2024 2025

paper ID の確認方法:
  https://www.semanticscholar.org で正しい論文を検索し，
  URL 末尾の英数字部分（例: abc1234abcd...）を "api" 欄にコピーする．
  https://api.semanticscholar.org/graph/v1/paper/{paper_id} の形式でも可．
"""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="修正候補 JSON を生成する")
    parser.add_argument(
        "--years", type=int, nargs="+", default=list(range(2021, 2026)),
        metavar="YEAR", help="対象年度（デフォルト: 2021〜2025）",
    )
    parser.add_argument(
        "--sim-threshold", type=float, default=1.0,
        help="この値未満の similarity を対象にする（デフォルト: 1.0）",
    )
    parser.add_argument(
        "--year-window", type=int, default=2,
        help="paper_year >= target_year - N のみ対象（デフォルト: 2）",
    )
    args = parser.parse_args()

    base = Path(__file__).parent
    cache_dir = base / "output" / "cache"
    result_dir = base / "output" / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    for year in sorted(args.years):
        fixed = cache_dir / f"cache_citations_{year}_fixed.json"
        base_cache = cache_dir / f"cache_citations_{year}.json"
        path = fixed if fixed.exists() else base_cache
        if not path.exists():
            print(f"  [skip] キャッシュなし: {year}")
            continue

        data: dict = json.loads(path.read_text(encoding="utf-8"))

        for query, v in data.items():
            if not v.get("found") or v.get("cvpr_match", True):
                continue
            sim = v.get("similarity", 1.0)
            py = v.get("year")

            if sim >= args.sim_threshold:
                continue
            if py is None or py < year - args.year_window:
                continue

            rows.append({
                "target_year":   year,
                "query_title":   query,
                "matched_title": v.get("title", ""),
                "similarity":    sim,
                "paper_year":    py,
                "venue":         v.get("venue", ""),
                "citationCount": v.get("citationCount"),
                "api":           "",   # ← Semantic Scholar の paper ID を記入する
            })

    rows.sort(key=lambda r: (r["target_year"], r["similarity"]))

    out = result_dir / "corrections.json"
    out.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"→ 保存: {out}  ({len(rows)} 件)")
    print()
    print('  "api" 欄に Semantic Scholar の paper ID を記入してください．')
    print('  例: "api": "649def34f8be52c8b66281af98ae884c09aef38b"')
    print('  ID は https://www.semanticscholar.org の論文 URL 末尾から取得できます．')


if __name__ == "__main__":
    main()
