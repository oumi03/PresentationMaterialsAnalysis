#!/usr/bin/env bash
# 本番実行：引用数取得 → CVPR フィルタリング → 修正候補 JSON 生成
#
# 実行: bash run_full.sh
# パラメータはこのファイルの変数を直接編集して変更する
#
# 処理の流れ:
#   [1] main.py             論文タイトルをスクレイプし引用数を取得
#   [2] retry_normalized.py タイトル正規化・再検索で精度向上，cvpr_match フラグ付与
#   [3] export_corrections.py cvpr_match=False のうち要確認論文を JSON に書き出す
#
# 続きの手順:
#   手動: output/result/corrections_${YEAR}.json の "api" 欄を記入
#   自動: bash run_corrections.sh

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

OUTPUT="output/result/output_${YEAR}"
CORRECTIONS="output/cache/corrections_${YEAR}.json"

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
mkdir -p output/cache output/result

echo "=== CVPR Citation Analyzer — 本番実行 (CVPR ${YEAR}) ==="
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
        --papers-cache "output/cache/cache_papers_${YEAR}.json" \
        --citations-cache "output/cache/cache_citations_${YEAR}.json"
else
    uv run python main.py \
        --url "$URL" \
        --output "$OUTPUT" \
        --papers-cache "output/cache/cache_papers_${YEAR}.json" \
        --citations-cache "output/cache/cache_citations_${YEAR}.json"
fi

# ── [2] タイトル正規化・再検索・cvpr_match フラグ付与 ────────
echo ""
echo "--- [2/3] CVPR フィルタリング（retry_normalized.py）---"
if [ -n "$API_KEY" ]; then
    uv run python retry_normalized.py --year "$YEAR" --api-key "$API_KEY"
else
    uv run python retry_normalized.py --year "$YEAR"
fi

# ── [3] 修正候補 JSON 生成 ────────────────────────────────────
echo ""
echo "--- [3/3] 修正候補エクスポート（export_corrections.py）---"
uv run python export_corrections.py \
    --years "$YEAR" \
    --output "$CORRECTIONS"

echo ""
echo "=== 完了 ==="
echo ""
echo "次のステップ:"
echo "  1. ${CORRECTIONS} を開き，誤マッチ論文の \"api\" 欄を記入する"
echo "     - 同一論文とみなせる場合 : \"ok\""
echo "     - 別論文を指定したい場合 : Semantic Scholar の論文 URL"
echo "  2. bash run_corrections.sh"
