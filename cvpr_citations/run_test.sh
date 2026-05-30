#!/usr/bin/env bash
# テスト実行：少数の論文で動作確認する
# 実行: bash run_test.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# ============================================================
# パラメータ設定
# ============================================================
LIMIT=20          # 処理する論文数
API_KEY="s2k-PUTbCVeGQSQueTxRiQ23GVW0icNPqscf4MO2HljI"        # Semantic Scholar API キー（不要なら空のまま）
OUTPUT="output_test"
# ============================================================

cd "$(dirname "$0")"

echo "=== CVPR Citation Analyzer — テスト実行 (${LIMIT} 本) ==="

if [ -n "$API_KEY" ]; then
    uv run python main.py \
        --limit "$LIMIT" \
        --api-key "$API_KEY" \
        --output "$OUTPUT"
else
    uv run python main.py \
        --limit "$LIMIT" \
        --output "$OUTPUT"
fi

echo ""
echo "出力先: ${OUTPUT}/"
echo "  グラフ: $(ls ${OUTPUT}/*.png 2>/dev/null | wc -l) ファイル"
echo "  CSV  : ${OUTPUT}/citations.csv"
