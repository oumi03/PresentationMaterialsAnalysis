"""リンク種別・発表種別ごとの引用数を比較する.

使い方:
  uv run python citation_comparison.py              # 2025（デフォルト）
  uv run python citation_comparison.py --year 2025

前提:
  output/result/cvpr{year}_links.csv        -- scrape_links.py の出力
  output/cache/cache_citations_{year}.json  -- run_full.sh の出力

出力:
  output/result/citation_comparison_{year}.csv   -- グループ別統計量
  output/result/citation_comparison_{year}.json  -- 同内容 JSON
  output/result/comparison_{year}_01_link_type.png
  output/result/comparison_{year}_02_has_link.png
  output/result/comparison_{year}_03_presentation.png
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

_LABEL: dict[str, str] = {
    "github": "GitHub",
    "project_page": "Project Page",
    "none": "No Link",
    "リンクあり": "Has Link",
    "リンクなし": "No Link",
    "highlight": "Highlight",
    "award_candidate": "Award Candidate",
    "poster": "Poster",
    # presentation_type × has_link クロス集計用
    "highlight_link":          "Highlight\n+ Link",
    "highlight_nolink":        "Highlight\n+ No Link",
    "award_candidate_link":    "Award Candidate\n+ Link",
    "award_candidate_nolink":  "Award Candidate\n+ No Link",
    "poster_link":             "Poster\n+ Link",
    "poster_nolink":           "Poster\n+ No Link",
}
_PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]


def _is_valid_match(entry: dict) -> bool:
    """found かつ（similarity=1 or cvpr_match=True）のエントリを有効とみなす."""
    if not entry.get("found"):
        return False
    if entry.get("cvpr_match"):
        return True
    return entry.get("similarity", 0.0) >= 0.5


def load_citations(year: int, out_dir: Path) -> pd.DataFrame:
    # _fixed があればそちらを優先して読み込む
    fixed = out_dir / "cache" / f"cache_citations_{year}_fixed.json"
    cache = out_dir / "cache" / f"cache_citations_{year}.json"
    path = fixed if fixed.exists() else cache
    if not path.exists():
        raise FileNotFoundError(f"{cache} が見つかりません。run_full.sh を先に実行してください。")
    if path == fixed:
        print(f"  [fixed] {path.name} を使用")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        {"title_key": k, "citationCount": v["citationCount"]}
        for k, v in data.items()
        if _is_valid_match(v) and v.get("citationCount") is not None
    ]
    df = pd.DataFrame(rows)
    df["citationCount"] = pd.to_numeric(df["citationCount"], errors="coerce")
    return df.dropna(subset=["citationCount"])


def load_links(year: int, out_dir: Path) -> pd.DataFrame:
    csv = out_dir / "result" / f"cvpr{year}_links.csv"
    if not csv.exists():
        raise FileNotFoundError(f"{csv} が見つかりません。scrape_links.py を先に実行してください。")
    return pd.read_csv(csv)


def merge_on_title(links: pd.DataFrame, citations: pd.DataFrame) -> pd.DataFrame:
    """タイトルで突き合わせる（完全一致 → 大文字小文字無視の順で試みる）."""
    # 完全一致
    merged = links.merge(
        citations.rename(columns={"title_key": "title"}),
        on="title", how="left",
    )
    # 未マッチ分を小文字正規化で再試行
    unmatched_mask = merged["citationCount"].isna()
    if unmatched_mask.any():
        cit_lower = citations.copy()
        cit_lower["title_lower"] = cit_lower["title_key"].str.lower().str.strip()
        merged["title_lower"] = merged["title"].str.lower().str.strip()
        fill = merged[unmatched_mask][["title_lower"]].merge(
            cit_lower[["title_lower", "citationCount"]], on="title_lower", how="left"
        )
        merged.loc[unmatched_mask, "citationCount"] = fill["citationCount"].values
        merged.drop(columns=["title_lower"], inplace=True)

    matched = merged["citationCount"].notna().sum()
    total = len(merged)
    print(f"  マッチ: {matched} / {total} 件 ({matched/total*100:.1f}%)")
    return merged[merged["citationCount"].notna()].copy()


def group_stats(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for name, g in df.groupby(group_col):
        c = g["citationCount"]
        rows.append({
            "group": name,
            "n": len(c),
            "mean": round(c.mean(), 1),
            "median": round(c.median(), 1),
            "std": round(c.std(), 1),
            "q25": round(c.quantile(0.25), 1),
            "q75": round(c.quantile(0.75), 1),
            "max": int(c.max()),
        })
    return pd.DataFrame(rows).sort_values("median", ascending=False).reset_index(drop=True)


def print_stats(label: str, stats: pd.DataFrame) -> None:
    print(f"\n--- {label} ---")
    print(stats.to_string(index=False))


def plot_group(
    df: pd.DataFrame,
    group_col: str,
    title: str,
    year: int,
    out_path: Path,
) -> None:
    """グループ別引用数のボックスプロット＋中央値バーチャートを保存する."""
    # 中央値降順でグループを並べる
    order = (
        df.groupby(group_col)["citationCount"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    groups = df.groupby(group_col)["citationCount"]
    labels = [_LABEL.get(g, g) for g in order]
    data = [groups.get_group(g).clip(lower=1).values for g in order]
    counts = [len(d) for d in data]
    medians = [float(np.median(d)) for d in data]
    q25 = [float(np.percentile(d, 25)) for d in data]
    q75 = [float(np.percentile(d, 75)) for d in data]
    colors = (_PALETTE * 4)[: len(order)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"CVPR {year} — {title}", fontsize=13)

    # ---- 左: ボックスプロット（log スケール）----
    bp = ax1.boxplot(
        data,
        tick_labels=labels,
        patch_artist=True,
        showfliers=True,
        flierprops=dict(marker=".", markersize=2, alpha=0.25, color="gray"),
        medianprops=dict(color="red", linewidth=1.5),
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.65)
    ax1.set_yscale("log")
    ax1.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax1.set_ylabel("Citation Count (log scale)")
    ax1.set_title("Distribution")
    y_bot = ax1.get_ylim()[0]
    for i, n in enumerate(counts):
        ax1.text(i + 1, y_bot, f"n={n}", ha="center", va="bottom", fontsize=8, color="#444")

    # ---- 右: 中央値バーチャート（IQR をエラーバー）----
    x = list(range(len(order)))
    yerr_lo = [m - q for m, q in zip(medians, q25)]
    yerr_hi = [q - m for q, m in zip(q75, medians)]
    bars = ax2.bar(x, medians, color=colors, alpha=0.8, edgecolor="white")
    ax2.errorbar(
        x, medians,
        yerr=[yerr_lo, yerr_hi],
        fmt="none", color="black", capsize=6, linewidth=1.5,
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Median Citation Count")
    ax2.set_title("Median ± IQR")
    top_val = max(medians) if medians else 1
    for bar, med in zip(bars, medians):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + top_val * 0.02,
            f"{med:.0f}",
            ha="center", va="bottom", fontsize=9,
        )

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="リンク・発表種別ごとの引用数比較")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()

    out_dir = Path(__file__).parent / "output"

    print(f"=== CVPR {args.year} 引用数比較 ===")
    print("\n[1] データ読み込み")
    cit_df = load_citations(args.year, out_dir)
    link_df = load_links(args.year, out_dir)
    print(f"  citations: {len(cit_df)} 件 / links: {len(link_df)} 件")

    print("\n[2] タイトルでマージ")
    df = merge_on_title(link_df, cit_df)

    # --- 3分類: リンク種別 ---
    stats_3 = group_stats(df, "link_type")
    print_stats("リンク種別（3分類）", stats_3)

    # --- 2分類: リンクあり / なし ---
    df["has_link"] = df["link_type"].apply(lambda x: "リンクあり" if x != "none" else "リンクなし")
    stats_2link = group_stats(df, "has_link")
    print_stats("リンクあり / なし（2分類）", stats_2link)

    # --- 2分類: 発表種別（highlight / poster）---
    if "presentation_type" in df.columns:
        stats_2pres = group_stats(df, "presentation_type")
        print_stats("発表種別（2分類）", stats_2pres)
    else:
        print("\n  ※ presentation_type 列がありません。scrape_links.py を再実行してください。")
        stats_2pres = pd.DataFrame()

    # --- 保存 ---
    all_stats = {
        "link_type_3way": stats_3.to_dict(orient="records"),
        "has_link_2way": stats_2link.to_dict(orient="records"),
        "presentation_type_2way": stats_2pres.to_dict(orient="records") if not stats_2pres.empty else [],
    }

    result_dir = out_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    out_csv = result_dir / f"citation_comparison_{args.year}.csv"
    # 全テーブルを縦積みして保存（category列で識別）
    frames = []
    for cat, records in all_stats.items():
        tmp = pd.DataFrame(records)
        tmp.insert(0, "category", cat)
        frames.append(tmp)
    pd.concat(frames, ignore_index=True).to_csv(out_csv, index=False)
    print(f"\n→ CSV  保存: {out_csv}")

    out_json = result_dir / f"citation_comparison_{args.year}.json"
    out_json.write_text(json.dumps(all_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ JSON 保存: {out_json}")

    # --- 可視化 ---
    print("\n[可視化]")
    plot_group(
        df, "link_type", "Citation Count by Link Type",
        args.year,
        result_dir / f"comparison_{args.year}_01_link_type.png",
    )
    plot_group(
        df, "has_link", "Citation Count: Has Link vs No Link",
        args.year,
        result_dir / f"comparison_{args.year}_02_has_link.png",
    )
    if not stats_2pres.empty:
        plot_group(
            df, "presentation_type", "Citation Count by Presentation Type",
            args.year,
            result_dir / f"comparison_{args.year}_03_presentation.png",
        )
        # 発表種別 × リンク有無の4値クロス比較
        df["ptype_link"] = df.apply(
            lambda r: r["presentation_type"] + (
                "_link" if r["has_link"] == "リンクあり" else "_nolink"
            ),
            axis=1,
        )
        plot_group(
            df, "ptype_link",
            "Citation Count by Presentation Type × Link",
            args.year,
            result_dir / f"comparison_{args.year}_04_ptype_x_link.png",
        )


if __name__ == "__main__":
    main()
