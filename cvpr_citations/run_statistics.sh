#!/usr/bin/env bash
# 統計分析：リンク種別・発表種別ごとの引用数比較 & Top-N 抽出
# 実行: bash run_statistics.sh
# パラメータはこのファイルの変数を直接編集して変更する

set -euo pipefail

# ============================================================
# パラメータ設定
# ============================================================
YEAR=2023         # 対象年度
TOP_N=10          # 取得する上位件数
# ============================================================

cd "$(dirname "$0")"
mkdir -p output/cache output/result

echo "=== CVPR Citation Analyzer — 統計分析 (CVPR ${YEAR}) ==="

echo ""
echo "[1] リンク情報スクレイピング"
uv run python scrape_links.py --year "$YEAR"

echo ""
echo "[2] リンク種別・発表種別ごとの引用数比較"
uv run python citation_comparison.py --year "$YEAR"

echo ""
echo "[3] Top-${TOP_N} 引用論文の抽出"
uv run python topn.py --top "$TOP_N"

echo ""
echo "[4] タイトルマッチング類似度統計"
uv run python similarity_stats.py

echo ""
echo "=== 完了 ==="
