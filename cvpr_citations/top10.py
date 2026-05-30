"""各年度の cache_citations_202x.json から引用数上位10本を抽出して保存する."""

import json
import re
from pathlib import Path

import pandas as pd


def extract_year(path: Path) -> str | None:
    m = re.search(r"(\d{4})", path.name)
    return m.group(1) if m else None


def top10_for_year(cache_path: Path, output_dir: Path) -> pd.DataFrame:
    data = json.loads(cache_path.read_text(encoding="utf-8"))

    rows = [v for v in data.values() if v.get("found") and v.get("citationCount") is not None]
    if not rows:
        print(f"  [skip] 有効なデータなし: {cache_path.name}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["citationCount"] = pd.to_numeric(df["citationCount"], errors="coerce")
    df = df.dropna(subset=["citationCount"])
    df = df.sort_values("citationCount", ascending=False).head(10).reset_index(drop=True)
    df.index += 1  # 順位を1始まりにする
    df.index.name = "rank"

    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / "top10.csv"
    df[["title", "citationCount", "year", "venue", "authors"]].to_csv(out_csv)

    return df


def main() -> None:
    base = Path(__file__).parent
    cache_files = sorted(base.glob("cache_citations_202*.json"))

    if not cache_files:
        print("cache_citations_202x.json が見つかりません。")
        return

    for cache_path in cache_files:
        year = extract_year(cache_path)
        if year is None:
            continue

        output_dir = base / f"output_{year}"
        print(f"\n=== CVPR {year} ===")

        df = top10_for_year(cache_path, output_dir)
        if df.empty:
            continue

        for rank, row in df.iterrows():
            authors = ", ".join(row["authors"][:3]) if isinstance(row.get("authors"), list) else ""
            print(f"  {rank:2}. [{row['citationCount']:>5}] {row['title']}")
            if authors:
                print(f"       {authors}")

        print(f"  → 保存: {output_dir / 'top10.csv'}")


if __name__ == "__main__":
    main()
