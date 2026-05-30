#!/usr/bin/env bash
# 本番実行：CVPR 採択論文の引用数を全件取得して可視化する
# 実行: bash run_full.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# .env が存在すれば読み込む（API キーを環境変数として設定）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ============================================================
# パラメータ設定
# ============================================================
YEAR=2026         # 対象年度（2021〜2026）
API_KEY="${SEMANTIC_SCHOLAR_API_KEY:-}"   # .env または環境変数から取得
                  # キー取得先: https://www.semanticscholar.org/product/api#api-key-form
# ============================================================

OUTPUT="output/output_${YEAR}"

# 年度に対応する URL
case "$YEAR" in
    2026) URL="https://openaccess.thecvf.com/CVPR2026?day=all" ;;
    2025) URL="https://openaccess.thecvf.com/CVPR2025?day=all" ;;
    2024) URL="https://openaccess.thecvf.com/CVPR2024?day=all" ;;
    2023) URL="https://openaccess.thecvf.com/CVPR2023?day=all" ;;
    2022) URL="https://openaccess.thecvf.com/CVPR2022?day=all" ;;
    2021) URL="https://openaccess.thecvf.com/CVPR2021?day=all" ;;
    *)
        echo "エラー: 未対応の年度 '$YEAR'（2021〜2026 が利用可能）"
        exit 1
        ;;
esac

cd "$(dirname "$0")"
mkdir -p output

echo "=== CVPR Citation Analyzer — 本番実行 ==="
echo "  対象: CVPR ${YEAR}"
echo "  URL : ${URL}"
echo "  出力: ${OUTPUT}/"
if [ -n "$API_KEY" ]; then
    echo "  API : キーあり（高速モード）"
else
    echo "  API : キーなし（標準モード，完了まで数時間かかる場合があります）"
    echo "        Ctrl+C で中断しても，再実行時はキャッシュから再開できます"
fi
echo ""

if [ -n "$API_KEY" ]; then
    uv run python main.py \
        --url "$URL" \
        --api-key "$API_KEY" \
        --output "$OUTPUT" \
        --papers-cache "output/cache_papers_${YEAR}.json" \
        --citations-cache "output/cache_citations_${YEAR}.json"
else
    uv run python main.py \
        --url "$URL" \
        --output "$OUTPUT" \
        --papers-cache "output/cache_papers_${YEAR}.json" \
        --citations-cache "output/cache_citations_${YEAR}.json"
fi

echo ""
echo "=== 完了 ==="
echo "出力先: ${OUTPUT}/"
ls -lh "${OUTPUT}/" 2>/dev/null || true
