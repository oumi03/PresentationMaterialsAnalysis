# CVPR Citation Analyzer

CVPRの採択論文の引用数を Semantic Scholar API で取得し，傾向を可視化するツール．

## ファイル構成

```
cvpr_citations/
├── pyproject.toml         # 依存関係定義（uv プロジェクト）
├── main.py                # CLI エントリポイント
├── scraper.py             # CVF ページから論文タイトルを取得
├── semantic_scholar.py    # Semantic Scholar API クライアント
├── visualize.py           # グラフ生成（4 種）
├── run_test.sh            # テスト実行スクリプト（少数の論文）
└── run_full.sh            # 本番実行スクリプト（全論文）
```

## セットアップ

```bash
# uv がない場合はインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存パッケージをインストール
cd cvpr_citations
uv sync
```

## 実行方法

### テスト（少数の論文で動作確認）

`run_test.sh` の先頭にあるパラメータ欄を編集してから実行する：

```bash
# run_test.sh の変数を編集
LIMIT=20        # 処理する論文数
API_KEY=""      # API キー（不要なら空のまま）
OUTPUT="output_test"
```

```bash
bash run_test.sh
```

### 本番実行（全論文）

`run_full.sh` の先頭にあるパラメータ欄を編集してから実行する：

```bash
# run_full.sh の変数を編集
YEAR=2024       # 対象年度（2021〜2024）
API_KEY=""      # API キー（不要なら空のまま）
```

無料 API キーの取得先：https://www.semanticscholar.org/product/api#api-key-form

```bash
bash run_full.sh
```

## 出力ファイル

実行後，`output/`（または `--output` で指定したディレクトリ）に保存される：

| ファイル | 内容 |
|---|---|
| `01_citation_distribution.png` | 引用数の分布（線形・対数スケール，中央値線付き） |
| `02_top_papers.png` | 引用数 Top 30 論文の横棒グラフ |
| `03_citation_cdf.png` | 累積分布関数（p25/50/75/90/95 マーカー付き） |
| `04_percentile_bars.png` | パーセンタイル（p10〜p99）ごとの引用数 |
| `citations.csv` | 全論文の引用数データ（引用数降順） |

## キャッシュ

取得済みデータはローカルに保存され，2 回目以降の実行は高速に完了する：

| ファイル | 内容 |
|---|---|
| `cache_papers.json` | 論文タイトル一覧（CVF ページのスクレイピング結果） |
| `cache_citations.json` | Semantic Scholar の引用数取得結果 |

キャッシュを削除すれば再取得できる：

```bash
rm cache_papers.json cache_citations.json
```

API エラー（レート制限など）で取得に失敗した論文はキャッシュされないため，
再実行すると自動的にリトライされる．

## レート制限について

Semantic Scholar API の制限：

| 条件 | リクエスト間隔 | 2716 本の目安 |
|---|---|---|
| APIキーなし | 3.1 秒 | 約 2.3 時間 |
| APIキーあり（推奨） | 1.1 秒 | 約 50 分 |

429（Too Many Requests）が返った場合は自動的に 305 秒待機してリトライする（最大 3 回）．

## すべてのオプション

```
uv run python main.py --help

  --url URL           論文一覧ページの URL
  --limit N           処理する論文数の上限（テスト用）
  --api-key KEY       Semantic Scholar API キー
  --delay SEC         API 呼び出し間隔（秒）を手動指定
  --output DIR        出力ディレクトリ（デフォルト: ./output）
  --papers-cache FILE 論文タイトルのキャッシュファイル
  --citations-cache FILE 引用数のキャッシュファイル
```
