#!/usr/bin/env bash
# テスト実行：少数の論文で動作確認する
# 実行: bash run_test.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# .env が存在すれば読み込む（API キーを環境変数として設定）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ============================================================
# パラメータ設定
# ============================================================
LIMIT=20          # 処理する論文数
API_KEY="${SEMANTIC_SCHOLAR_API_KEY:-}"   # .env または環境変数から取得
OUTPUT="output/output_test"
# ============================================================

cd "$(dirname "$0")"
mkdir -p output

echo "=== CVPR Citation Analyzer — テスト実行 (${LIMIT} 本) ==="

if [ -n "$API_KEY" ]; then
    uv run python main.py \
        --limit "$LIMIT" \
        --api-key "$API_KEY" \
        --output "$OUTPUT" \
        --papers-cache "output/cache_papers_test.json" \
        --citations-cache "output/cache_citations_test.json"
else
    uv run python main.py \
        --limit "$LIMIT" \
        --output "$OUTPUT" \
        --papers-cache "output/cache_papers_test.json" \
        --citations-cache "output/cache_citations_test.json"
fi

echo ""
echo "出力先: ${OUTPUT}/"
echo "  グラフ: $(ls ${OUTPUT}/*.png 2>/dev/null | wc -l) ファイル"
echo "  CSV  : ${OUTPUT}/citations.csv"
