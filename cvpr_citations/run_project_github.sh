#!/usr/bin/env bash
# project page / github.io から GitHub リポジトリリンクを収集・可視化する
#
# 実行: bash run_project_github.sh
# パラメータはこのファイルの変数を直接編集して変更する
#
# 処理の流れ:
#   [1] scrape_project_github.py  project page / github.io をスクレイピング
#   [2] visualize_project_github.py  結果を可視化
#
# 前提:
#   output/result_{conf}/{conf}{year}_links.csv が存在すること
#   （存在しない場合は scrape_links.py を先に実行する）

set -euo pipefail

# ============================================================
# パラメータ設定
# ============================================================
CONF=cvpr                  # 対象会議（cvpr / iccv / wacv）
YEARS=(2023 2024 2025)     # 対象年度（複数指定可）
# ============================================================

CONF_UPPER=$(echo "$CONF" | tr '[:lower:]' '[:upper:]')
CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")

cd "$(dirname "$0")"
mkdir -p "output/cache${CONF_SUFFIX}" "output/result${CONF_SUFFIX}"

echo "=== CVF Project GitHub Analyzer (${CONF_UPPER} ${YEARS[*]}) ==="

echo ""
echo "[1] project page / github.io スクレイピング"
for YEAR in "${YEARS[@]}"; do
    echo "  --- ${CONF_UPPER} ${YEAR} ---"
    uv run python scrape_project_github.py --conf "$CONF" --year "$YEAR"
done

echo ""
echo "[2] 可視化"
for YEAR in "${YEARS[@]}"; do
    echo "  --- ${CONF_UPPER} ${YEAR} ---"
    uv run python visualize_project_github.py --conf "$CONF" --year "$YEAR"
done

echo ""
echo "=== 完了 ==="
