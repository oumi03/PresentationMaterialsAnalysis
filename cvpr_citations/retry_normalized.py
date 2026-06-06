"""similarity < 1.0 の論文をクエリ正規化して再検索し、修正済みキャッシュを生成する.

使い方:
  uv run python retry_normalized.py --year 2025
  uv run python retry_normalized.py --conf iccv --year 2023
  uv run python retry_normalized.py --conf wacv --year 2024
"""

import argparse
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

from conf_utils import CONF_VENUE_KEYWORDS, add_conf_argument, cache_dir
from semantic_scholar import _save_cache, _search_one


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def normalize_title(title: str) -> str:
    title = re.sub(r"  +", " ", title)
    title = re.sub(r"\^(\w+)", r"\1", title)
    title = (title
             .replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"'))
    return title.strip()


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_conf_match(entry: dict, conf: str, target_year: int) -> bool:
    """venue と year から採択会議を確認する.

    year は arXiv 公開年（target_year-2 〜 target_year）の範囲を許容する.
    """
    venue = (entry.get("venue") or "").lower()
    year = entry.get("year")
    keyword = CONF_VENUE_KEYWORDS.get(conf, "")
    return (
        keyword in venue
        and year in (target_year - 2, target_year - 1, target_year)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="similarity < 1.0 の論文を正規化再検索して _fixed キャッシュを生成する"
    )
    add_conf_argument(parser)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--api-key", default=None, metavar="KEY")
    parser.add_argument("--threshold", type=float, default=1.0)
    args = parser.parse_args()

    base = Path(__file__).parent
    load_env(base / ".env")
    api_key = args.api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or None

    c_dir = cache_dir(base, args.conf)
    cache_path = c_dir / f"cache_citations_{args.year}.json"
    fixed_path = c_dir / f"cache_citations_{args.year}_fixed.json"

    if not cache_path.exists():
        print(f"キャッシュが見つかりません: {cache_path}")
        return

    data: dict = json.loads(cache_path.read_text(encoding="utf-8"))
    headers: dict = {"x-api-key": api_key} if api_key else {}
    delay = 1.1 if api_key else 3.1

    fixed: dict = dict(data)

    targets = [
        (orig, entry)
        for orig, entry in data.items()
        if entry.get("found") and entry.get("similarity", 1.0) < args.threshold
    ]
    sim1_count = sum(
        1 for e in data.values()
        if e.get("found") and e.get("similarity", 1.0) >= args.threshold
    )

    conf_upper = args.conf.upper()
    print(f"=== {conf_upper} {args.year} 正規化再検索 ===")
    print(f"API          : {'キーあり（高速モード）' if api_key else 'キーなし（標準モード）'}")
    print(f"再検索対象   : {len(targets)} 件  (similarity < {args.threshold})")
    print(f"コピー済み   : {sim1_count} 件  (similarity >= {args.threshold})")
    print(f"出力先       : {fixed_path.name}")
    print()

    improved = skipped_no_change = skipped_no_improve = 0

    for orig, entry in targets:
        normalized = normalize_title(orig)
        if normalized == orig:
            skipped_no_change += 1
            continue

        old_sim = entry.get("similarity", 1.0)
        old_title = entry.get("title", "")
        new_entry = _search_one(normalized, headers, delay)

        if not new_entry.get("found"):
            skipped_no_improve += 1
            continue

        sim_with_orig = _sim(orig, new_entry.get("title", ""))
        effective_sim = max(new_entry.get("similarity", 0.0), sim_with_orig)

        if effective_sim <= old_sim:
            skipped_no_improve += 1
            continue

        improved += 1
        print(f"[{improved:3}] {old_sim:.3f} → {effective_sim:.3f}")
        print(f"      orig : {orig}")
        print(f"      norm : {normalized}")
        print(f"      old  : {old_title}")
        print(f"      new  : {new_entry['title']}")
        print()

        new_entry["query"] = orig
        new_entry["similarity"] = round(effective_sim, 3)
        fixed[orig] = new_entry

    # conf_match フラグを全エントリに付与
    match_ok = match_ng = 0
    for entry in fixed.values():
        flag = entry.get("found", False) and is_conf_match(entry, args.conf, args.year)
        entry["cvpr_match"] = flag   # 既存キー名を維持（後続スクリプトとの互換性）
        if entry.get("found"):
            if flag:
                match_ok += 1
            else:
                match_ng += 1

    _save_cache(fixed, str(fixed_path))

    print("=" * 55)
    print(f"改善            : {improved} 件")
    print(f"正規化で変化なし: {skipped_no_change} 件")
    print(f"改善なし        : {skipped_no_improve} 件")
    print(f"sim=1.0 コピー  : {sim1_count} 件")
    print(f"合計エントリ数  : {len(fixed)} 件")
    print()
    print(f"conf_match=True : {match_ok} 件")
    print(f"conf_match=False: {match_ng} 件")
    print(f"\n→ 保存完了: {fixed_path}")


if __name__ == "__main__":
    main()
