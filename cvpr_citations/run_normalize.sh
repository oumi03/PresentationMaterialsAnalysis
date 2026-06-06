#!/usr/bin/env bash
# キャッシュ正規化再検索：similarity < 1.0 の論文を正規化クエリで再検索し
# cvpr_match フラグ付きの _fixed キャッシュを生成する
# 実行: bash run_normalize.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# .env が存在すれば読み込む（API キーを環境変数として設定）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ============================================================
# パラメータ設定
# ============================================================
YEAR=2021           # 対象年度（run_full.sh で取得済みの年度を指定）
API_KEY="${SEMANTIC_SCHOLAR_API_KEY:-}"   # .env または環境変数から取得
# ============================================================

cd "$(dirname "$0")"
mkdir -p output/cache output/result

echo "=== CVPR Citation Normalizer (CVPR ${YEAR}) ==="
echo "  入力: output/cache/cache_citations_${YEAR}.json"
echo "  出力: output/cache/cache_citations_${YEAR}_fixed.json"
if [ -n "$API_KEY" ]; then
    echo "  API : キーあり（高速モード）"
    uv run python retry_normalized.py --year "$YEAR" --api-key "$API_KEY"
else
    echo "  API : キーなし（標準モード）"
    uv run python retry_normalized.py --year "$YEAR"
fi
echo ""
echo "=== 完了 ==="
echo "出力先: output/cache/cache_citations_${YEAR}_fixed.json"
