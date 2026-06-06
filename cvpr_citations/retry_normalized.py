"""similarity < 1.0 の論文をクエリ正規化して再検索し、修正済みキャッシュを生成する.

使い方:
  uv run python retry_normalized.py --year 2025

処理の流れ:
  1. cache_citations_{year}.json を読み込む
  2. similarity < 1.0 のエントリに正規化クエリで再検索をかける
  3. similarity が向上したエントリを更新
  4. similarity = 1.0 のエントリはそのままコピー
  5. 全エントリに cvpr_match フラグを付与する
     True  : venue=’Computer Vision and Pattern Recognition’
             かつ year ∈ {target_year-1, target_year}
     False : それ以外（別年度・別会議・arXiv のみ など）
  6. cache_citations_{year}_fixed.json に保存

正規化の内容:
  - 二重スペース → 単スペース           例: "from  Multi" → "from Multi"
  - ^N 記法 → プレーン数字              例: "MC^2" → "MC2"
  - カーリークォート → ストレート        例: "Don’t" → "Don’t"
"""

import argparse
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

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
    """Semantic Scholar 検索クエリ用にタイトルを正規化する."""
    title = re.sub(r"  +", " ", title)                          # 二重スペース
    title = re.sub(r"\^(\w+)", r"\1", title)                    # ^N 記法
    title = (title
             .replace("’", "'").replace("‘", "'")     # curly apostrophe
             .replace("“", '"').replace("”", '"'))     # curly double quote
    return title.strip()


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_cvpr_match(entry: dict, target_year: int) -> bool:
    """venue と year から CVPR 採択を確認する.

    year は arXiv 公開年（target_year-2 〜 target_year）の範囲を許容する.
    """
    venue = (entry.get("venue") or "").lower()
    year = entry.get("year")
    return (
        "computer vision and pattern recognition" in venue
        and year in (target_year - 2, target_year - 1, target_year)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="similarity < 1.0 の論文を正規化再検索して _fixed キャッシュを生成する"
    )
    parser.add_argument("--year", type=int, default=2025, help="対象年度（デフォルト: 2025）")
    parser.add_argument("--api-key", default=None, metavar="KEY",
                        help="Semantic Scholar API キー（省略時は .env から読み込み）")
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="この値未満のエントリを再検索する（デフォルト: 1.0）")
    args = parser.parse_args()

    base = Path(__file__).parent
    load_env(base / ".env")
    api_key = args.api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or None

    cache_path = base / "output" / "cache" / f"cache_citations_{args.year}.json"
    fixed_path = base / "output" / "cache" / f"cache_citations_{args.year}_fixed.json"

    if not cache_path.exists():
        print(f"キャッシュが見つかりません: {cache_path}")
        return

    data: dict = json.loads(cache_path.read_text(encoding="utf-8"))
    headers: dict = {"x-api-key": api_key} if api_key else {}
    delay = 1.1 if api_key else 3.1

    # fixed は元データの完全コピーから始める（sim=1.0 のエントリはここで取り込まれる）
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

    print(f"=== CVPR {args.year} 正規化再検索 ===")
    print(f"API          : {'キーあり（高速モード）' if api_key else 'キーなし（標準モード）'}")
    print(f"再検索対象   : {len(targets)} 件  (similarity < {args.threshold})")
    print(f"コピー済み   : {sim1_count} 件  (similarity >= {args.threshold})")
    print(f"出力先       : {fixed_path.name}")
    print()

    improved = 0
    skipped_no_change = 0
    skipped_no_improve = 0

    for i, (orig, entry) in enumerate(targets, 1):
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

        # 元クエリとの類似度も考慮して effective_sim を決定
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

    # --- cvpr_match フラグを全エントリに付与 ---
    cvpr_ok = cvpr_ng = 0
    for entry in fixed.values():
        flag = entry.get("found", False) and is_cvpr_match(entry, args.year)
        entry["cvpr_match"] = flag
        if entry.get("found"):
            if flag:
                cvpr_ok += 1
            else:
                cvpr_ng += 1

    # 保存
    _save_cache(fixed, str(fixed_path))

    print("=" * 55)
    print(f"改善            : {improved} 件")
    print(f"正規化で変化なし: {skipped_no_change} 件")
    print(f"改善なし        : {skipped_no_improve} 件")
    print(f"sim=1.0 コピー  : {sim1_count} 件")
    print(f"合計エントリ数  : {len(fixed)} 件")
    print()
    print(f"cvpr_match=True : {cvpr_ok} 件  (venue=CVPR かつ year∈{{{args.year-1},{args.year}}})")
    print(f"cvpr_match=False: {cvpr_ng} 件  (別会議・別年度・未マッチ など)")
    print(f"\n→ 保存完了: {fixed_path}")


if __name__ == "__main__":
    main()
