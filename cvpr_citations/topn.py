"""各年度の cache_citations_202x.json から引用数 Top-N を抽出して保存する.

使い方:
  uv run python topn.py           # デフォルト Top-10
  uv run python topn.py --top 5   # Top-5
  uv run python topn.py --top 30  # Top-30

出力:
  output/result/output_{year}/top{N}.csv   -- 年度別ランキング
  output/result/top{N}_all_years.csv       -- 全年度まとめ CSV
  output/result/top{N}_all_years.json      -- 全年度まとめ JSON
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from conf_utils import add_conf_argument, cache_dir as get_cache_dir, result_dir as get_result_dir


def extract_year(path: Path) -> str | None:
    m = re.search(r"(\d{4})", path.name)
    return m.group(1) if m else None


def _is_valid(entry: dict) -> bool:
    if not entry.get("found"):
        return False
    if entry.get("cvpr_match"):
        return True
    return entry.get("similarity", 0.0) >= 0.5


def _resolve_cache(cache_path: Path) -> Path:
    """_fixed があればそちらを優先する."""
    fixed = cache_path.with_name(cache_path.stem + "_fixed.json")
    return fixed if fixed.exists() else cache_path


def topn_for_year(cache_path: Path, n: int) -> pd.DataFrame:
    path = _resolve_cache(cache_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [v for v in data.values() if _is_valid(v) and v.get("citationCount") is not None]
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
    parser = argparse.ArgumentParser(description="引用数 Top-N 抽出")
    add_conf_argument(parser)
    parser.add_argument("--top", type=int, default=10, metavar="N", help="取得する上位件数（デフォルト: 10）")
    parser.add_argument("--years", type=int, nargs="+", default=None, metavar="YEAR",
                        help="対象年度（省略時: キャッシュにある全年度）")
    args = parser.parse_args()
    n = args.top

    base = Path(__file__).parent
    c_dir = get_cache_dir(base, args.conf)
    r_dir = get_result_dir(base, args.conf)
    cache_files = sorted(
        p for p in c_dir.glob("cache_citations_202*.json")
        if not p.stem.endswith("_fixed")
    )

    if args.years:
        year_set = {str(y) for y in args.years}
        cache_files = [p for p in cache_files if extract_year(p) in year_set]

    if not cache_files:
        print(f"{c_dir}/cache_citations_202x.json が見つかりません。")
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

        print(f"\n=== {args.conf.upper()} {year} ===")
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

        year_dir = r_dir / f"output_{year}"
        year_dir.mkdir(parents=True, exist_ok=True)
        year_csv = year_dir / f"top{n}.csv"
        df[["title", "citationCount", "year", "venue", "authors"]].to_csv(year_csv)
        print(f"  → 保存: {year_csv}")

    if not all_rows:
        print("出力データがありません。")
        return

    r_dir.mkdir(parents=True, exist_ok=True)
    out_csv = r_dir / f"top{n}_all_years.csv"
    pd.DataFrame(all_rows).to_csv(out_csv, index=False)
    print(f"\n→ 全年度 CSV  : {out_csv}")

    out_json = r_dir / f"top{n}_all_years.json"
    out_json.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ 全年度 JSON : {out_json}")


if __name__ == "__main__":
    main()
