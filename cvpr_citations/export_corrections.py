"""cvpr_match=False かつ similarity < 1.0 の論文を JSON に書き出す.

出力 JSON の "url" 欄を手動で記入し，apply_corrections.py で修正を適用する．

使い方:
  uv run python export_corrections.py              # 2021〜2025
  uv run python export_corrections.py --years 2024 2025

"url" 欄の記入方法:
  同一論文とみなせる場合  : "ok"
  別論文を指定したい場合  : https://www.semanticscholar.org の論文 URL をそのままコピー
                           （URL 全体でも末尾の ID 部分だけでも可）
"""

import argparse
import json
from pathlib import Path

from conf_utils import add_conf_argument, cache_dir, result_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="修正候補 JSON を生成する")
    add_conf_argument(parser)
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
    parser.add_argument(
        "--output", default=None, metavar="FILE",
        help="出力先 JSON ファイルパス（省略時: output/cache_{conf}/corrections.json）",
    )
    args = parser.parse_args()

    base = Path(__file__).parent
    c_dir = cache_dir(base, args.conf)
    r_dir = result_dir(base, args.conf)
    r_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    for year in sorted(args.years):
        fixed = c_dir / f"cache_citations_{year}_fixed.json"
        base_cache = c_dir / f"cache_citations_{year}.json"
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
                "url":           "",   # ← "ok" または Semantic Scholar の論文 URL を記入する
            })

    rows.sort(key=lambda r: (r["target_year"], r["similarity"]))

    out = Path(args.output) if args.output else c_dir / "corrections.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"→ 保存: {out}  ({len(rows)} 件)")
    print()
    print('  "url" 欄に記入してください:')
    print('    同一論文とみなせる場合 : "ok"')
    print('    別論文を指定したい場合 : Semantic Scholar の論文 URL（全体 or 末尾 ID どちらでも可）')
    print('  例: "url": "https://www.semanticscholar.org/paper/Title/649def34f8be52c8b66281af98ae884c09aef38b"')


if __name__ == "__main__":
    main()
