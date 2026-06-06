#!/usr/bin/env bash
# 統計分析：リンク種別・発表種別ごとの引用数比較 & Top-N 抽出
# 実行: bash run_statistics.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# ============================================================
# パラメータ設定
# ============================================================
# YEARS=(2023 2024 2025)   # 対象年度（複数指定可）
YEARS=(2021 2022)       # 対象年度（複数指定可）
TOP_N=10                  # 取得する上位件数
# ============================================================

cd "$(dirname "$0")"
mkdir -p output/cache output/result

echo "=== CVPR Citation Analyzer — 統計分析 (${YEARS[*]}) ==="

echo ""
echo "[1] リンク情報スクレイピング"
for YEAR in "${YEARS[@]}"; do
    echo "  --- CVPR ${YEAR} ---"
    uv run python scrape_links.py --year "$YEAR"
done

echo ""
echo "[2] リンク種別・発表種別ごとの引用数比較"
for YEAR in "${YEARS[@]}"; do
    echo "  --- CVPR ${YEAR} ---"
    uv run python citation_comparison.py --year "$YEAR"
done

echo ""
echo "[3] Top-${TOP_N} 引用論文の抽出"
uv run python topn.py --top "$TOP_N" --years "${YEARS[@]}"

echo ""
echo "[4] タイトルマッチング類似度統計"
uv run python similarity_stats.py --years "${YEARS[@]}"

echo ""
echo "=== 完了 ==="
