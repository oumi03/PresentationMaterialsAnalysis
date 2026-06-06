#!/usr/bin/env bash
# 本番実行：引用数取得 → 会議フィルタリング → 修正候補 JSON 生成
#
# 実行: bash run_full.sh
# パラメータはこのファイルの変数を直接編集して変更する
#
# 処理の流れ:
#   [1] main.py             論文タイトルをスクレイプし引用数を取得
#   [2] retry_normalized.py タイトル正規化・再検索で精度向上，conf_match フラグ付与
#   [3] export_corrections.py conf_match=False のうち要確認論文を JSON に書き出す
#
# 続きの手順:
#   手動: output/cache${CONF_SUFFIX}/corrections_${YEAR}.json の "url" 欄を記入
#   自動: bash run_corrections.sh

set -euo pipefail

# .env が存在すれば読み込む（API キーを環境変数として設定）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ============================================================
# パラメータ設定
# ============================================================
CONF=iccv         # 対象会議（cvpr / iccv / wacv）
YEAR=2025         # 対象年度
API_KEY="${SEMANTIC_SCHOLAR_API_KEY:-}"   # .env または環境変数から取得
                  # キー取得先: https://www.semanticscholar.org/product/api#api-key-form
# ============================================================

CONF_UPPER=$(echo "$CONF" | tr '[:lower:]' '[:upper:]')
CONF_SUFFIX=$([[ "$CONF" == "cvpr" ]] && echo "" || echo "_${CONF}")
URL="https://openaccess.thecvf.com/${CONF_UPPER}${YEAR}?day=all"
OUTPUT="output/result${CONF_SUFFIX}/output_${YEAR}"
CORRECTIONS="output/cache${CONF_SUFFIX}/corrections_${YEAR}.json"

cd "$(dirname "$0")"
mkdir -p "output/cache${CONF_SUFFIX}" "output/result${CONF_SUFFIX}"

echo "=== CVF Citation Analyzer — 本番実行 (${CONF_UPPER} ${YEAR}) ==="
if [ -n "$API_KEY" ]; then
    echo "  API : キーあり（高速モード）"
else
    echo "  API : キーなし（標準モード，完了まで数時間かかる場合があります）"
    echo "        Ctrl+C で中断しても，再実行時はキャッシュから再開できます"
fi
echo ""

# ── [1] 引用数取得 ────────────────────────────────────────────
echo "--- [1/3] 引用数取得 ---"
if [ -n "$API_KEY" ]; then
    uv run python main.py \
        --url "$URL" \
        --api-key "$API_KEY" \
        --output "$OUTPUT" \
        --papers-cache "output/cache${CONF_SUFFIX}/cache_papers_${YEAR}.json" \
        --citations-cache "output/cache${CONF_SUFFIX}/cache_citations_${YEAR}.json"
else
    uv run python main.py \
        --url "$URL" \
        --output "$OUTPUT" \
        --papers-cache "output/cache${CONF_SUFFIX}/cache_papers_${YEAR}.json" \
        --citations-cache "output/cache${CONF_SUFFIX}/cache_citations_${YEAR}.json"
fi

# ── [2] タイトル正規化・再検索・conf_match フラグ付与 ─────────
echo ""
echo "--- [2/3] 会議フィルタリング（retry_normalized.py）---"
if [ -n "$API_KEY" ]; then
    uv run python retry_normalized.py --conf "$CONF" --year "$YEAR" --api-key "$API_KEY"
else
    uv run python retry_normalized.py --conf "$CONF" --year "$YEAR"
fi

# ── [3] 修正候補 JSON 生成 ────────────────────────────────────
echo ""
echo "--- [3/3] 修正候補エクスポート（export_corrections.py）---"
uv run python export_corrections.py \
    --conf "$CONF" \
    --years "$YEAR" \
    --output "$CORRECTIONS"

echo ""
echo "=== 完了 ==="
echo ""
echo "次のステップ:"
echo "  1. ${CORRECTIONS} を開き，誤マッチ論文の \"url\" 欄を記入する"
echo "     - 同一論文とみなせる場合 : \"ok\""
echo "     - 別論文を指定したい場合 : Semantic Scholar の論文 URL"
echo "  2. bash run_corrections.sh"
