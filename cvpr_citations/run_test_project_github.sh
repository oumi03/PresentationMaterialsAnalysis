#!/usr/bin/env bash
# テスト実行：少数の論文で project page / github.io スクレイピングの動作確認
# 実行: bash run_test_project_github.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# ============================================================
# パラメータ設定
# ============================================================
CONF=cvpr    # 対象会議（cvpr / iccv / wacv）
YEAR=2023    # 対象年度
LIMIT=20     # 処理する論文数
# ============================================================

CONF_UPPER=$(echo "$CONF" | tr '[:lower:]' '[:upper:]')
CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")

cd "$(dirname "$0")"
mkdir -p "output/cache${CONF_SUFFIX}" "output/result${CONF_SUFFIX}"

echo "=== CVF Project GitHub Analyzer — テスト実行 (${CONF_UPPER} ${YEAR}, ${LIMIT} 件) ==="

echo ""
echo "[1] project page / github.io スクレイピング"
uv run python scrape_project_github.py --conf "$CONF" --year "$YEAR" --limit "$LIMIT"

echo ""
echo "[2] 可視化"
uv run python visualize_project_github.py --conf "$CONF" --year "$YEAR"

CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")
OUT_DIR="output/result${CONF_SUFFIX}"
echo ""
echo "出力先: ${OUT_DIR}/"
echo "  JSON : ${OUT_DIR}/project_github_${YEAR}.json"
echo "  CSV  : ${OUT_DIR}/project_github_${YEAR}.csv"
echo "  グラフ: $(ls ${OUT_DIR}/project_github_${YEAR}_*.png 2>/dev/null | wc -l) ファイル"
