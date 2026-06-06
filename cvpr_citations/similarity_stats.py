"""各年度の cache_citations_202x.json から similarity 統計を集計して保存する."""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from conf_utils import add_conf_argument, cache_dir as get_cache_dir, result_dir as get_result_dir


def extract_year(path: Path) -> str | None:
    m = re.search(r"(\d{4})", path.name)
    return m.group(1) if m else None


def main() -> None:
    parser = argparse.ArgumentParser(description="similarity 統計集計")
    add_conf_argument(parser)
    parser.add_argument("--years", type=int, nargs="+", default=None, metavar="YEAR",
                        help="対象年度（省略時: キャッシュにある全年度）")
    args = parser.parse_args()

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

    summary_rows: list[dict] = []
    detail_rows: list[dict] = []

    for cache_path in cache_files:
        year = extract_year(cache_path)
        if year is None:
            continue

        # _fixed があればそちらを優先
        fixed = cache_path.with_name(cache_path.stem + "_fixed.json")
        path = fixed if fixed.exists() else cache_path
        data = json.loads(path.read_text(encoding="utf-8"))
        found = [v for v in data.values() if v.get("found")]

        if not found:
            continue

        sims = [v.get("similarity", 1.0) for v in found]

        summary_rows.append({
            "year": year,
            "total_found": len(found),
            "sim_eq_1":  sum(1 for s in sims if s == 1.0),
            "sim_lt_1":  sum(1 for s in sims if s < 1.0),
            "sim_lt_095": sum(1 for s in sims if s < 0.95),
            "sim_lt_09":  sum(1 for s in sims if s < 0.9),
            "sim_lt_08":  sum(1 for s in sims if s < 0.8),
            "sim_min":   round(min(sims), 3),
            "sim_mean":  round(sum(sims) / len(sims), 4),
        })

        for query, v in data.items():
            if not v.get("found"):
                continue
            sim = v.get("similarity", 1.0)
            if sim < 1.0:
                detail_rows.append({
                    "year": year,
                    "similarity": sim,
                    "query_title": query,
                    "matched_title": v.get("title", ""),
                    "citationCount": v.get("citationCount"),
                })

    # --- サマリー表示 ---
    print("=== similarity 統計サマリー ===")
    df_sum = pd.DataFrame(summary_rows)
    print(df_sum.to_string(index=False))

    print("\n=== similarity < 0.8 の詳細 ===")
    df_det = pd.DataFrame(detail_rows).sort_values(["year", "similarity"])
    low = df_det[df_det["similarity"] < 0.8]
    for _, row in low.iterrows():
        print(f"  [{row['year']}] sim={row['similarity']:.3f}")
        print(f"    query : {row['query_title'][:80]}")
        print(f"    found : {row['matched_title'][:80]}")

    # --- 保存 ---
    r_dir.mkdir(parents=True, exist_ok=True)
    sum_csv = r_dir / "similarity_summary.csv"
    df_sum.to_csv(sum_csv, index=False)
    print(f"\n→ サマリー CSV: {sum_csv}")

    det_csv = r_dir / "similarity_details.csv"
    df_det.to_csv(det_csv, index=False)
    print(f"→ 詳細 CSV    : {det_csv}  ({len(df_det)} 件, sim < 1.0)")

    det_json = r_dir / "similarity_details.json"
    det_json.write_text(
        json.dumps(detail_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"→ 詳細 JSON   : {det_json}")


if __name__ == "__main__":
    main()
