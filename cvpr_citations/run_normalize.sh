#!/usr/bin/env bash
# キャッシュ正規化再検索：similarity < 1.0 の論文を正規化クエリで再検索し
# conf_match フラグ付きの _fixed キャッシュを生成する
# 実行: bash run_normalize.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# .env が存在すれば読み込む（API キーを環境変数として設定）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ============================================================
# パラメータ設定
# ============================================================
CONF=cvpr           # 対象会議（cvpr / iccv / wacv）
YEAR=2021           # 対象年度（run_full.sh で取得済みの年度を指定）
API_KEY="${SEMANTIC_SCHOLAR_API_KEY:-}"   # .env または環境変数から取得
# ============================================================

CONF_UPPER=$(echo "$CONF" | tr '[:lower:]' '[:upper:]')
CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")

cd "$(dirname "$0")"
mkdir -p "output/cache${CONF_SUFFIX}" "output/result${CONF_SUFFIX}"

echo "=== CVF Citation Normalizer (${CONF_UPPER} ${YEAR}) ==="
echo "  入力: output/cache${CONF_SUFFIX}/cache_citations_${YEAR}.json"
echo "  出力: output/cache${CONF_SUFFIX}/cache_citations_${YEAR}_fixed.json"
if [ -n "$API_KEY" ]; then
    echo "  API : キーあり（高速モード）"
    uv run python retry_normalized.py --conf "$CONF" --year "$YEAR" --api-key "$API_KEY"
else
    echo "  API : キーなし（標準モード）"
    uv run python retry_normalized.py --conf "$CONF" --year "$YEAR"
fi
echo ""
echo "=== 完了 ==="
echo "出力先: output/cache${CONF_SUFFIX}/cache_citations_${YEAR}_fixed.json"
