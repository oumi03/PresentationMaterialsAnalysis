"""各年度の cache_citations_202x.json から引用数 Top-5 を抽出し、一つの CSV/JSON にまとめる."""

import json
import re
from pathlib import Path

import pandas as pd


def extract_year(path: Path) -> str | None:
    m = re.search(r"(\d{4})", path.name)
    return m.group(1) if m else None


def top5_for_year(cache_path: Path) -> pd.DataFrame:
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    rows = [v for v in data.values() if v.get("found") and v.get("citationCount") is not None]
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["citationCount"] = pd.to_numeric(df["citationCount"], errors="coerce")
    df = df.dropna(subset=["citationCount"])
    df = df.sort_values("citationCount", ascending=False).head(5).reset_index(drop=True)
    df.index += 1
    df.index.name = "rank"
    return df


def main() -> None:
    base = Path(__file__).parent
    cache_files = sorted(base.glob("cache_citations_202*.json"))

    if not cache_files:
        print("cache_citations_202x.json が見つかりません。")
        return

    all_rows: list[dict] = []

    for cache_path in cache_files:
        year = extract_year(cache_path)
        if year is None:
            continue

        df = top5_for_year(cache_path)
        if df.empty:
            print(f"  [skip] 有効なデータなし: {cache_path.name}")
            continue

        print(f"\n=== CVPR {year} ===")
        for rank, row in df.iterrows():
            authors_str = ", ".join(row["authors"][:3]) if isinstance(row.get("authors"), list) else ""
            print(f"  {rank}. [{int(row['citationCount']):>6}] {row['title']}")
            if authors_str:
                print(f"        {authors_str}")
            all_rows.append({
                "year": year,
                "rank": rank,
                "title": row["title"],
                "citationCount": int(row["citationCount"]),
                "venue": row.get("venue", ""),
                "authors": ", ".join(row["authors"][:3]) if isinstance(row.get("authors"), list) else "",
            })

    if not all_rows:
        print("出力データがありません。")
        return

    out_df = pd.DataFrame(all_rows)

    out_csv = base / "top5_all_years.csv"
    out_df.to_csv(out_csv, index=False)
    print(f"\n→ CSV 保存: {out_csv}")

    out_json = base / "top5_all_years.json"
    out_json.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"→ JSON 保存: {out_json}")


if __name__ == "__main__":
    main()
