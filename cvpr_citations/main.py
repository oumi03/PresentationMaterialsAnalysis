"""CVPR Citation Analyzer — entry point.

Usage examples:
  # Test with 20 papers (no API key needed, uses 3.1-s delay)
  uv run python main.py --limit 20

  # Full run with Semantic Scholar API key (faster: 1.1-s delay)
  uv run python main.py --api-key YOUR_KEY

  # Different CVPR year
  uv run python main.py --url https://openaccess.thecvf.com/CVPR2023?day=all

  # Specify output directory
  uv run python main.py --limit 50 --output results_test
"""

import argparse
import sys

from scraper import fetch_cvpr_papers
from semantic_scholar import fetch_citations
from visualize import create_visualizations

DEFAULT_URL = "https://openaccess.thecvf.com/CVPR2024?day=all"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze CVPR paper citation counts via Semantic Scholar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Accepted papers page URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N papers (useful for testing)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="Semantic Scholar API key — raises rate limit from ~19 to 60 req/min",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        metavar="SEC",
        help="Override API call interval in seconds (default: 3.1 without key, 1.1 with key)",
    )
    parser.add_argument(
        "--output",
        default="output/result/output",
        metavar="DIR",
        help="Directory for plots and CSV (default: output/result/output)",
    )
    parser.add_argument(
        "--papers-cache",
        default="output/cache/cache_papers.json",
        metavar="FILE",
        help="Cache file for scraped paper titles (default: output/cache/cache_papers.json)",
    )
    parser.add_argument(
        "--citations-cache",
        default="output/cache/cache_citations.json",
        metavar="FILE",
        help="Cache file for Semantic Scholar results (default: output/cache/cache_citations.json)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Step 1: collect paper titles
    # ------------------------------------------------------------------
    print("=" * 60)
    print("Step 1  Fetch CVPR paper titles")
    print("=" * 60)
    try:
        papers = fetch_cvpr_papers(args.url, cache_path=args.papers_cache)
    except Exception as exc:
        sys.exit(f"[error] Could not fetch papers: {exc}")

    print(f"Total papers: {len(papers)}")

    if args.limit:
        papers = papers[: args.limit]
        print(f"Limiting to {args.limit} papers")

    if not papers:
        sys.exit("[error] No papers found. Check the URL or cache file.")

    # ------------------------------------------------------------------
    # Step 2: citation counts from Semantic Scholar
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Step 2  Fetch citation counts (Semantic Scholar)")
    print("=" * 60)

    delay = args.delay  # None → auto-select in fetch_citations
    results = fetch_citations(
        papers,
        api_key=args.api_key,
        cache_path=args.citations_cache,
        delay=delay,
    )

    found = sum(1 for r in results if r.get("found"))
    print(f"Matched: {found} / {len(results)} papers on Semantic Scholar")

    # ------------------------------------------------------------------
    # Step 3: visualize
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Step 3  Visualize")
    print("=" * 60)
    create_visualizations(results, output_dir=args.output)

    print(f"\nAll done — outputs in ./{args.output}/")


if __name__ == "__main__":
    main()
