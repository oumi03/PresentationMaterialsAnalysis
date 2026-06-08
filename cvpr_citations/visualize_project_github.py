"""project page / github.io のリポジトリ公開状況を可視化する.

使い方:
  uv run python visualize_project_github.py                # CVPR 2025（デフォルト）
  uv run python visualize_project_github.py --year 2023
  uv run python visualize_project_github.py --conf cvpr --year 2023

前提:
  output/result_{conf}/{conf}{year}_links.csv       -- scrape_links.py の出力（全論文）
  output/result_{conf}/project_github_{year}.json  -- scrape_project_github.py の出力

出力:
  output/result_{conf}/project_github_{year}_01_project_page_rate.png
  output/result_{conf}/project_github_{year}_02_github_code_rate.png
  output/result_{conf}/project_github_{year}_03_by_url_type.png
  output/result_{conf}/project_github_{year}_04_by_presentation.png
  output/result_{conf}/project_github_{year}_05_fetch_status.png
  output/result_{conf}/project_github_{year}_summary.csv
  output/result_{conf}/project_github_{year}_summary.json
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from conf_utils import add_conf_argument, result_dir

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

_PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]
_HAS_REPO_COLOR    = "#55A868"
_NO_REPO_COLOR     = "#DD8452"
_NO_PROJECT_COLOR  = "#B0BEC5"

_LABEL: dict[str, str] = {
    "github_io":       "GitHub.io",
    "project_page":    "Project Page",
    "highlight":       "Highlight",
    "award_candidate": "Award Candidate",
    "poster":          "Poster",
    "success":         "Success",
    "not_found":       "Not Found",
    "timeout":         "Timeout",
    "error":           "Error",
}


def _add_pct_labels(ax, bars, counts: list[int]) -> None:
    """% 高さのバーに count と % ラベルを付ける."""
    for bar, count in zip(bars, counts):
        h = bar.get_height()
        if h == 0:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 1.0,
            f"{int(count)}\n({h:.1f}%)",
            ha="center", va="bottom", fontsize=8, color="#333",
        )


def plot_project_page_rate(
    df_all: pd.DataFrame, df: pd.DataFrame, year: int, conf: str, out_path: Path
) -> None:
    """Chart 01: 全論文のうち github.io / project page の内訳を示す棒グラフ（Q1）."""
    total_all      = len(df_all)
    n_github_io    = int((df["project_url_type"] == "github_io").sum())
    n_project_page = int((df["project_url_type"] == "project_page").sum())
    n_none         = total_all - n_github_io - n_project_page

    counts_raw = [n_github_io, n_project_page, n_none]
    pcts = [c / total_all * 100 for c in counts_raw]
    labels = ["GitHub.io", "Project Page", "No Link"]
    colors = [_PALETTE[0], _PALETTE[1], _NO_PROJECT_COLOR]

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.suptitle(
        f"{conf.upper()} {year} — Project Page / GitHub.io Rate (All Papers, n={total_all})",
        fontsize=12,
    )

    bars = ax.bar(labels, pcts, color=colors, alpha=0.8, edgecolor="white")
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    _add_pct_labels(ax, bars, counts_raw)

    has_link = n_github_io + n_project_page
    ax.set_title(
        f"Has Link (GitHub.io + Project Page): {has_link} / {total_all}  ({has_link/total_all*100:.1f}%)",
        fontsize=10, color="#333",
    )

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def plot_github_code_rate(df: pd.DataFrame, year: int, conf: str, out_path: Path) -> None:
    """Chart 02: project page / github.io 持ち論文のうち GitHub コードを持つ割合（Q2）."""
    has  = int(df["has_github_repo"].sum())
    no   = int((~df["has_github_repo"]).sum())
    total = len(df)

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.suptitle(
        f"{conf.upper()} {year} — GitHub Code Rate\n(Among Papers with Project Page / GitHub.io)",
        fontsize=12,
    )

    counts_raw = [has, no]
    pcts = [c / total * 100 for c in counts_raw]
    labels = ["Has GitHub Repo", "No GitHub Repo"]
    colors = [_HAS_REPO_COLOR, _NO_REPO_COLOR]
    bars = ax.bar(labels, pcts, color=colors, alpha=0.8, edgecolor="white")
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    _add_pct_labels(ax, bars, counts_raw)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def plot_by_url_type(df: pd.DataFrame, year: int, conf: str, out_path: Path) -> None:
    """Chart 03: project_url_type 別の GitHub リポジトリ公開率."""
    url_types = [t for t in ["github_io", "project_page"] if t in df["project_url_type"].values]
    if not url_types:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.suptitle(
        f"{conf.upper()} {year} — GitHub Repo Rate by URL Type",
        fontsize=12,
    )

    x = np.arange(len(url_types))
    width = 0.35
    has_counts = [int(df[df["project_url_type"] == t]["has_github_repo"].sum()) for t in url_types]
    no_counts  = [int((~df[df["project_url_type"] == t]["has_github_repo"]).sum()) for t in url_types]
    total_per_type = [h + n for h, n in zip(has_counts, no_counts)]
    has_pcts = [h / tot * 100 for h, tot in zip(has_counts, total_per_type)]
    no_pcts  = [n / tot * 100 for n, tot in zip(no_counts,  total_per_type)]
    tick_labels = [_LABEL.get(t, t) for t in url_types]

    b1 = ax.bar(x - width / 2, has_pcts, width, color=_HAS_REPO_COLOR, alpha=0.8, edgecolor="white", label="Has GitHub Repo")
    b2 = ax.bar(x + width / 2, no_pcts,  width, color=_NO_REPO_COLOR,  alpha=0.8, edgecolor="white", label="No GitHub Repo")
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, fontsize=11)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.legend()

    for bar, count, pct in zip(b1, has_counts, has_pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, pct + 1.0,
                f"{int(count)}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=8)
    for bar, count, pct in zip(b2, no_counts, no_pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, pct + 1.0,
                f"{int(count)}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def plot_combined_stacked(
    df_all: pd.DataFrame, df: pd.DataFrame, year: int, conf: str, out_path: Path
) -> None:
    """Chart 06: 全論文を URL種別×コード公開の 5 区分で積み上げた俯瞰チャート."""
    total_all = len(df_all)

    # 5 区分を集計
    gio_code   = int(((df["project_url_type"] == "github_io")    & df["has_github_repo"]).sum())
    gio_nocode = int(((df["project_url_type"] == "github_io")    & ~df["has_github_repo"]).sum())
    pp_code    = int(((df["project_url_type"] == "project_page") & df["has_github_repo"]).sum())
    pp_nocode  = int(((df["project_url_type"] == "project_page") & ~df["has_github_repo"]).sum())
    no_link    = total_all - len(df)

    segments = [
        ("GitHub.io + Code",         gio_code,   "#1565C0"),
        ("GitHub.io  (no code)",      gio_nocode, "#90CAF9"),
        ("Project Page + Code",       pp_code,    "#E65100"),
        ("Project Page  (no code)",   pp_nocode,  "#FFCC80"),
        ("No Link",                   no_link,    _NO_PROJECT_COLOR),
    ]

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.suptitle(
        f"{conf.upper()} {year} — Project Page / Code Release Overview\n(All Papers, n={total_all})",
        fontsize=12,
    )

    bottom = 0.0
    for label, count, color in segments:
        pct = count / total_all * 100
        bar = ax.bar(["All Papers"], [pct], bottom=bottom,
                     color=color, alpha=0.85, edgecolor="white", width=0.5, label=label)
        mid = bottom + pct / 2
        if pct >= 2.0:
            ax.text(0, mid, f"{count}  ({pct:.1f}%)",
                    ha="center", va="center", fontsize=9, color="white",
                    fontweight="bold")
        bottom += pct

    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9, frameon=False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def plot_by_presentation(df: pd.DataFrame, year: int, conf: str, out_path: Path) -> None:
    """Chart 04: presentation_type 別の GitHub リポジトリ公開率."""
    if "presentation_type" not in df.columns:
        return

    ptypes = [t for t in ["highlight", "award_candidate", "poster"] if t in df["presentation_type"].values]
    if not ptypes:
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.suptitle(
        f"{conf.upper()} {year} — GitHub Repo Rate by Presentation Type",
        fontsize=12,
    )

    x = np.arange(len(ptypes))
    width = 0.35
    has_counts = [int(df[df["presentation_type"] == t]["has_github_repo"].sum()) for t in ptypes]
    no_counts  = [int((~df[df["presentation_type"] == t]["has_github_repo"]).sum()) for t in ptypes]
    total_per_type = [h + n for h, n in zip(has_counts, no_counts)]
    has_pcts = [h / tot * 100 for h, tot in zip(has_counts, total_per_type)]
    no_pcts  = [n / tot * 100 for n, tot in zip(no_counts,  total_per_type)]
    tick_labels = [_LABEL.get(t, t) for t in ptypes]

    b1 = ax.bar(x - width / 2, has_pcts, width, color=_HAS_REPO_COLOR, alpha=0.8, edgecolor="white", label="Has GitHub Repo")
    b2 = ax.bar(x + width / 2, no_pcts,  width, color=_NO_REPO_COLOR,  alpha=0.8, edgecolor="white", label="No GitHub Repo")
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, fontsize=11)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.legend()

    for bar, count, pct in zip(b1, has_counts, has_pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, pct + 1.0,
                f"{int(count)}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=8)
    for bar, count, pct in zip(b2, no_counts, no_pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, pct + 1.0,
                f"{int(count)}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def plot_fetch_status(df: pd.DataFrame, year: int, conf: str, out_path: Path) -> None:
    """Chart 05: fetch_status の内訳."""
    status_counts = df["fetch_status"].value_counts()
    statuses = list(status_counts.index)
    counts   = list(status_counts.values)
    colors   = (_PALETTE * 4)[: len(statuses)]
    labels   = [_LABEL.get(s, s) for s in statuses]
    total    = sum(counts)

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.suptitle(f"{conf.upper()} {year} — Fetch Status", fontsize=12)

    pcts = [c / total * 100 for c in counts]
    bars = ax.bar(labels, pcts, color=colors, alpha=0.8, edgecolor="white")
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    _add_pct_labels(ax, bars, counts)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"→ 図  保存: {out_path}")


def build_summary(df_all: pd.DataFrame, df: pd.DataFrame, year: int) -> dict:
    total_all   = len(df_all)
    n_project   = len(df)
    has_repo    = int(df["has_github_repo"].sum())

    by_url_type = []
    for t in df["project_url_type"].unique():
        sub = df[df["project_url_type"] == t]
        by_url_type.append({
            "project_url_type": t,
            "n": len(sub),
            "has_github_repo": int(sub["has_github_repo"].sum()),
            "rate": round(sub["has_github_repo"].mean() * 100, 1),
        })

    by_presentation = []
    if "presentation_type" in df.columns:
        for t in df["presentation_type"].unique():
            sub = df[df["presentation_type"] == t]
            by_presentation.append({
                "presentation_type": t,
                "n": len(sub),
                "has_github_repo": int(sub["has_github_repo"].sum()),
                "rate": round(sub["has_github_repo"].mean() * 100, 1),
            })

    fetch_status = df["fetch_status"].value_counts().to_dict()

    return {
        "year": year,
        "total_papers": total_all,
        "n_project_page": n_project,
        "project_page_rate": round(n_project / total_all * 100, 1) if total_all else 0.0,
        "has_github_repo": has_repo,
        "github_code_rate": round(has_repo / n_project * 100, 1) if n_project else 0.0,
        "by_url_type": by_url_type,
        "by_presentation": by_presentation,
        "fetch_status": {k: int(v) for k, v in fetch_status.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="project page / github.io のリポジトリ公開状況を可視化"
    )
    add_conf_argument(parser)
    parser.add_argument("--year", type=int, default=2025, help="対象年度（デフォルト: 2025）")
    args = parser.parse_args()

    base = Path(__file__).parent
    r_dir = result_dir(base, args.conf)

    # 全論文データ（Q1の分母）
    links_csv = r_dir / f"{args.conf}{args.year}_links.csv"
    if not links_csv.exists():
        print(f"エラー: {links_csv} が見つかりません。scrape_links.py を先に実行してください。")
        return
    df_all = pd.read_csv(links_csv)

    # project page / github.io スクレイピング結果
    in_json = r_dir / f"project_github_{args.year}.json"
    if not in_json.exists():
        print(f"エラー: {in_json} が見つかりません。scrape_project_github.py を先に実行してください。")
        return
    df = pd.DataFrame(json.loads(in_json.read_text(encoding="utf-8")))
    df["has_github_repo"] = df["has_github_repo"].astype(bool)

    print(f"=== {args.conf.upper()} {args.year} 可視化 ===")
    print(f"  全論文数                     : {len(df_all)}")
    print(f"  project page / github.io あり: {len(df)} ({len(df)/len(df_all)*100:.1f}%)")
    print(f"  うち GitHub コードあり        : {df['has_github_repo'].sum()} ({df['has_github_repo'].mean()*100:.1f}%)")

    prefix = f"project_github_{args.year}"

    plot_project_page_rate(df_all, df, args.year, args.conf, r_dir / f"{prefix}_01_project_page_rate.png")
    plot_github_code_rate(df, args.year, args.conf, r_dir / f"{prefix}_02_github_code_rate.png")
    plot_by_url_type(df, args.year, args.conf, r_dir / f"{prefix}_03_by_url_type.png")
    plot_by_presentation(df, args.year, args.conf, r_dir / f"{prefix}_04_by_presentation.png")
    plot_fetch_status(df, args.year, args.conf, r_dir / f"{prefix}_05_fetch_status.png")
    plot_combined_stacked(df_all, df, args.year, args.conf, r_dir / f"{prefix}_06_combined_stacked.png")

    summary = build_summary(df_all, df, args.year)

    out_summary_json = r_dir / f"{prefix}_summary.json"
    out_summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ サマリ JSON 保存: {out_summary_json}")

    frames = []
    for cat, records in [("by_url_type", summary["by_url_type"]), ("by_presentation", summary["by_presentation"])]:
        if records:
            tmp = pd.DataFrame(records)
            tmp.insert(0, "category", cat)
            tmp.insert(1, "year", args.year)
            frames.append(tmp)
    if frames:
        out_summary_csv = r_dir / f"{prefix}_summary.csv"
        pd.concat(frames, ignore_index=True).to_csv(out_summary_csv, index=False)
        print(f"→ サマリ CSV 保存: {out_summary_csv}")


if __name__ == "__main__":
    main()
