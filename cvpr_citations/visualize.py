"""Create citation-count visualizations and export a CSV summary."""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})


def create_visualizations(results: list[dict], output_dir: str = "output") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = _build_df(results)
    if df.empty:
        print("[visualize] No data to plot.")
        return

    print(f"\n[visualize] {len(df)} papers with citation data")
    print(df["citationCount"].describe().rename("citations").to_string())

    _plot_histogram(df, out)
    _plot_top_papers(df, out)
    _plot_cdf(df, out)
    _plot_percentile_bars(df, out)

    csv_path = out / "citations.csv"
    df.sort_values("citationCount", ascending=False).to_csv(csv_path, index=False)
    print(f"[visualize] CSV saved → {csv_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_df(results: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(results)
    df = df[df["found"] == True].copy()
    df["citationCount"] = pd.to_numeric(df["citationCount"], errors="coerce")
    df = df.dropna(subset=["citationCount"])
    df["citationCount"] = df["citationCount"].astype(int)
    return df


def _year_label(df: pd.DataFrame) -> str:
    if "year" in df.columns:
        years = df["year"].dropna().unique()
        if len(years) == 1:
            return str(int(years[0]))
    return ""


def _plot_histogram(df: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    year = _year_label(df)

    # --- linear scale ---
    axes[0].hist(df["citationCount"], bins=60, color="#4C72B0", edgecolor="white", linewidth=0.4)
    axes[0].set_xlabel("Citation Count")
    axes[0].set_ylabel("Number of Papers")
    axes[0].set_title("Citation Distribution (linear)")
    _add_median_line(axes[0], df["citationCount"])

    # --- log x-scale ---
    clipped = df["citationCount"].clip(lower=1)
    bins_log = np.logspace(0, np.log10(max(clipped.max(), 10)), 60)
    axes[1].hist(clipped, bins=bins_log, color="#DD8452", edgecolor="white", linewidth=0.4)
    axes[1].set_xscale("log")
    axes[1].xaxis.set_major_formatter(mticker.ScalarFormatter())
    axes[1].set_xlabel("Citation Count (log scale)")
    axes[1].set_ylabel("Number of Papers")
    axes[1].set_title("Citation Distribution (log scale)")
    _add_median_line(axes[1], clipped)

    fig.suptitle(f"CVPR {year} — Citation Count Distribution  (n = {len(df):,})", fontsize=13)
    plt.tight_layout()
    _save(fig, out / "01_citation_distribution.png")


def _plot_top_papers(df: pd.DataFrame, out: Path, n: int = 30) -> None:
    top = df.nlargest(n, "citationCount").copy()
    top["label"] = top["title"].apply(lambda t: (t[:65] + "…") if len(t) > 66 else t)

    fig, ax = plt.subplots(figsize=(13, 11))
    bars = ax.barh(range(len(top)), top["citationCount"], color="#4C72B0", edgecolor="white")
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top["label"], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Citation Count")
    ax.set_title(f"Top {n} Most Cited CVPR {_year_label(df)} Papers")

    for bar, val in zip(bars, top["citationCount"]):
        ax.text(bar.get_width() + bar.get_width() * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=8)

    plt.tight_layout()
    _save(fig, out / "02_top_papers.png")


def _plot_cdf(df: pd.DataFrame, out: Path) -> None:
    c = np.sort(df["citationCount"].clip(lower=1).values)
    cdf = np.arange(1, len(c) + 1) / len(c)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(c, cdf, color="#4C72B0", linewidth=2)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.set_xlabel("Citation Count (log scale)")
    ax.set_ylabel("Cumulative Fraction of Papers")
    ax.set_title(f"CVPR {_year_label(df)} — Cumulative Citation Distribution")
    ax.grid(True, alpha=0.3, linestyle="--")

    for pct in (25, 50, 75, 90, 95):
        val = int(np.percentile(c, pct))
        ax.axvline(val, color="gray", linestyle=":", linewidth=1, alpha=0.7)
        ax.text(val * 1.05, pct / 100 - 0.03, f"p{pct}={val}", fontsize=8, color="gray")

    plt.tight_layout()
    _save(fig, out / "03_citation_cdf.png")


def _plot_percentile_bars(df: pd.DataFrame, out: Path) -> None:
    """Bar chart of citation counts at fixed percentiles."""
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    values = [int(np.percentile(df["citationCount"], p)) for p in percentiles]
    labels = [f"p{p}" for p in percentiles]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, values, color="#55A868", edgecolor="white")
    ax.set_xlabel("Percentile")
    ax.set_ylabel("Citation Count")
    ax.set_title(f"CVPR {_year_label(df)} — Citation Count by Percentile")

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                str(val), ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    _save(fig, out / "04_percentile_bars.png")


def _add_median_line(ax: plt.Axes, series: pd.Series) -> None:
    median = series.median()
    ax.axvline(median, color="red", linestyle="--", linewidth=1.2, alpha=0.8,
               label=f"median = {int(median)}")
    ax.legend(fontsize=8)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[visualize] Saved → {path}")
