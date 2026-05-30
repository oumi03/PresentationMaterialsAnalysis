"""各年度の cache_citations_202x.json から引用数 Top-N を抽出して保存する.

使い方:
  uv run python topn.py           # デフォルト Top-10
  uv run python topn.py --top 5   # Top-5
  uv run python topn.py --top 30  # Top-30

出力:
  output/output_{year}/top{N}.csv   -- 年度別ランキング
  output/top{N}_all_years.csv       -- 全年度まとめ CSV
  output/top{N}_all_years.json      -- 全年度まとめ JSON
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def extract_year(path: Path) -> str | None:
    m = re.search(r"(\d{4})", path.name)
    return m.group(1) if m else None


def topn_for_year(cache_path: Path, n: int) -> pd.DataFrame:
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    rows = [v for v in data.values() if v.get("found") and v.get("citationCount") is not None]
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["citationCount"] = pd.to_numeric(df["citationCount"], errors="coerce")
    df = df.dropna(subset=["citationCount"])
    df = df.sort_values("citationCount", ascending=False).head(n).reset_index(drop=True)
    df.index += 1
    df.index.name = "rank"
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="CVPR 引用数 Top-N 抽出")
    parser.add_argument("--top", type=int, default=10, metavar="N", help="取得する上位件数（デフォルト: 10）")
    args = parser.parse_args()
    n = args.top

    base = Path(__file__).parent
    out_base = base / "output"
    cache_files = sorted(out_base.glob("cache_citations_202*.json"))

    if not cache_files:
        print("output/cache_citations_202x.json が見つかりません。")
        return

    all_rows: list[dict] = []

    for cache_path in cache_files:
        year = extract_year(cache_path)
        if year is None:
            continue

        df = topn_for_year(cache_path, n)
        if df.empty:
            print(f"  [skip] 有効なデータなし: {cache_path.name}")
            continue

        print(f"\n=== CVPR {year} ===")
        for rank, row in df.iterrows():
            authors_str = ", ".join(row["authors"][:3]) if isinstance(row.get("authors"), list) else ""
            print(f"  {rank:2}. [{int(row['citationCount']):>6}] {row['title']}")
            if authors_str:
                print(f"        {authors_str}")

            all_rows.append({
                "year": year,
                "rank": rank,
                "title": row["title"],
                "citationCount": int(row["citationCount"]),
                "venue": row.get("venue", ""),
                "authors": authors_str,
            })

        year_dir = out_base / f"output_{year}"
        year_dir.mkdir(parents=True, exist_ok=True)
        year_csv = year_dir / f"top{n}.csv"
        df[["title", "citationCount", "year", "venue", "authors"]].to_csv(year_csv)
        print(f"  → 保存: {year_csv}")

    if not all_rows:
        print("出力データがありません。")
        return

    out_base.mkdir(parents=True, exist_ok=True)
    out_csv = out_base / f"top{n}_all_years.csv"
    pd.DataFrame(all_rows).to_csv(out_csv, index=False)
    print(f"\n→ 全年度 CSV  : {out_csv}")

    out_json = out_base / f"top{n}_all_years.json"
    out_json.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ 全年度 JSON : {out_json}")


if __name__ == "__main__":
    main()
