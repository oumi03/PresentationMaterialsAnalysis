"""会議別のディレクトリ・設定を返すユーティリティ."""

from pathlib import Path

# サポートする会議の一覧
SUPPORTED_CONFS = ("cvpr", "iccv", "wacv")

# Semantic Scholar の venue キーワード
CONF_VENUE_KEYWORDS: dict[str, str] = {
    "cvpr": "computer vision and pattern recognition",
    "iccv": "international conference on computer vision",
    "wacv": "winter conference on applications of computer vision",
}

# scrape_links.py: 会議・年度別の accepted papers URL
CONF_YEAR_URLS: dict[str, dict[int, str]] = {
    "cvpr": {
        2023: "https://cvpr.thecvf.com/Conferences/2023/AcceptedPapers",
        2024: "https://cvpr.thecvf.com/Conferences/2024/AcceptedPapers",
        2025: "https://cvpr.thecvf.com/Conferences/2025/AcceptedPapers",
    },
    "iccv": {
        2021: "https://iccv.thecvf.com/Conferences/2021/AcceptedPapers",
        2023: "https://iccv.thecvf.com/Conferences/2023/AcceptedPapers",
    },
    "wacv": {
        2022: "https://wacv.thecvf.com/Conferences/2022/AcceptedPapers",
        2023: "https://wacv.thecvf.com/Conferences/2023/AcceptedPapers",
        2024: "https://wacv.thecvf.com/Conferences/2024/AcceptedPapers",
        2025: "https://wacv.thecvf.com/Conferences/2025/AcceptedPapers",
    },
}

# scrape_links.py: 年度ごとの追加バッジ（presentation_type に反映）
CONF_EXTRA_BADGES: dict[str, dict[int, list[str]]] = {
    "cvpr": {2023: ["Award Candidate"]},
    "iccv": {2021: ["Oral"], 2023: ["Oral"]},
    "wacv": {},
}


def cache_dir(base: Path, conf: str) -> Path:
    """キャッシュディレクトリを返す.

    cvpr → output/cache/
    iccv → output/cache_iccv/
    wacv → output/cache_wacv/
    """
    suffix = f"_{conf}" if conf != "cvpr" else ""
    return base / "output" / f"cache{suffix}"


def result_dir(base: Path, conf: str) -> Path:
    """結果ディレクトリを返す."""
    suffix = f"_{conf}" if conf != "cvpr" else ""
    return base / "output" / f"result{suffix}"


def add_conf_argument(parser) -> None:
    """argparse パーサーに --conf 引数を追加する."""
    parser.add_argument(
        "--conf", default="cvpr",
        choices=SUPPORTED_CONFS,
        help="対象会議（デフォルト: cvpr）",
    )
