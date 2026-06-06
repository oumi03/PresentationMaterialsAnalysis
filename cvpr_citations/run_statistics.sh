#!/usr/bin/env bash
# 統計分析：リンク種別・発表種別ごとの引用数比較 & Top-N 抽出
# 実行: bash run_statistics.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# ============================================================
# パラメータ設定
# ============================================================
CONF=cvpr                  # 対象会議（cvpr / iccv / wacv）
YEARS=(2023 2024 2025)     # 対象年度（複数指定可）
TOP_N=10                   # 取得する上位件数
# ============================================================

CONF_UPPER=$(echo "$CONF" | tr '[:lower:]' '[:upper:]')
CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")

cd "$(dirname "$0")"
mkdir -p "output/cache${CONF_SUFFIX}" "output/result${CONF_SUFFIX}"

echo "=== CVF Citation Analyzer — 統計分析 (${CONF_UPPER} ${YEARS[*]}) ==="

echo ""
echo "[1] リンク情報スクレイピング"
for YEAR in "${YEARS[@]}"; do
    echo "  --- ${CONF_UPPER} ${YEAR} ---"
    uv run python scrape_links.py --conf "$CONF" --year "$YEAR"
done

echo ""
echo "[2] リンク種別・発表種別ごとの引用数比較"
for YEAR in "${YEARS[@]}"; do
    echo "  --- ${CONF_UPPER} ${YEAR} ---"
    uv run python citation_comparison.py --conf "$CONF" --year "$YEAR"
done

echo ""
echo "[3] Top-${TOP_N} 引用論文の抽出"
uv run python topn.py --conf "$CONF" --top "$TOP_N" --years "${YEARS[@]}"

echo ""
echo "[4] タイトルマッチング類似度統計"
uv run python similarity_stats.py --conf "$CONF" --years "${YEARS[@]}"

echo ""
echo "=== 完了 ==="
