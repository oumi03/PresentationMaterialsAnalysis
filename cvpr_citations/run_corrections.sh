#!/usr/bin/env bash
# 手動修正の適用：corrections_{YEAR}.json の記入内容を _fixed キャッシュに反映する
#
# 実行: bash run_corrections.sh
# パラメータはこのファイルの変数を直接編集して変更する
#
# 前提:
#   run_full.sh 実行済み（output/cache${CONF_SUFFIX}/corrections_${YEAR}.json が存在する）
#   corrections_${YEAR}.json の "url" 欄に記入済み:
#     "ok"  → 同一論文とみなす（conf_match=True に昇格）
#     URL   → その論文を正解として引用数・タイトルを更新

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ============================================================
# パラメータ設定
# ============================================================
CONF=cvpr
YEAR=2025
API_KEY="${SEMANTIC_SCHOLAR_API_KEY:-}"
# ============================================================

CONF_UPPER=$(echo "$CONF" | tr '[:lower:]' '[:upper:]')
CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")
CORRECTIONS="output/cache${CONF_SUFFIX}/corrections_${YEAR}.json"

cd "$(dirname "$0")"

if [ ! -f "$CORRECTIONS" ]; then
    echo "エラー: ${CORRECTIONS} が見つかりません。"
    echo "先に bash run_full.sh を実行してください。"
    exit 1
fi

echo "=== 修正適用 (${CONF_UPPER} ${YEAR}) ==="
echo "  入力: ${CORRECTIONS}"
echo ""

if [ -n "$API_KEY" ]; then
    uv run python apply_corrections.py \
        --conf "$CONF" \
        --input "$CORRECTIONS" \
        --api-key "$API_KEY"
else
    uv run python apply_corrections.py \
        --conf "$CONF" \
        --input "$CORRECTIONS"
fi

echo ""
echo "=== 完了 ==="
echo "  output/cache${CONF_SUFFIX}/cache_citations_${YEAR}_fixed.json を更新しました。"
echo "  続けて bash run_statistics.sh を実行すると統計・可視化を生成できます。"
