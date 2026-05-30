# CVPR Citation Analyzer

CVPRの採択論文の引用数を Semantic Scholar API で取得し，傾向を可視化・集計するツール．

## ファイル構成

```
cvpr_citations/
├── pyproject.toml          # 依存関係（uv プロジェクト）
├── uv.lock                 # 依存バージョン固定
├── .env.example            # API キーのテンプレート
│
├── main.py                 # CLI エントリポイント（スクレイプ→API取得→可視化）
├── scraper.py              # CVF ページから論文タイトルをスクレイプ
├── semantic_scholar.py     # Semantic Scholar API クライアント
├── visualize.py            # グラフ生成（4 種）
│
├── topn.py                 # 引用数 Top-N を年度別・全年度まとめで保存
├── similarity_stats.py     # API マッチの類似度統計を集計・保存
│
├── run_full.sh             # 本番実行（全論文，年度指定）
└── run_test.sh             # テスト実行（少数の論文で動作確認）
```

すべての出力・キャッシュは `output/` 以下に保存される（git 管理外）．

## セットアップ

### 1. uv のインストール（未インストールの場合）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. リポジトリのクローン

```bash
git clone <repository_url>
cd cvpr_citations
```

依存パッケージは `uv run` 実行時に自動でインストールされるため，`uv sync` の手動実行は不要．

### 3. API キーの設定

```bash
cp .env.example .env
```

`.env` を開き，Semantic Scholar の API キーを設定する：

```
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
```

API キーなしでも動作するが，レート制限が厳しくなる（後述）．
取得先: https://www.semanticscholar.org/product/api#api-key-form

## 実行方法

### テスト実行（少数の論文で動作確認）

`run_test.sh` の先頭にあるパラメータを編集してから実行する：

```bash
# run_test.sh のパラメータ
LIMIT=20          # 処理する論文数
```

```bash
bash run_test.sh
```

### 本番実行（全論文）

`run_full.sh` の先頭にある `YEAR` を変更してから実行する：

```bash
# run_full.sh のパラメータ
YEAR=2024         # 対象年度（2021〜2026）
```

```bash
bash run_full.sh
```

複数年度を取得する場合は，`YEAR` を変えて繰り返し実行する．
Ctrl+C で中断してもキャッシュが保存されているため，再実行時は途中から再開できる．

## 分析スクリプト

本番実行後，`output/` にキャッシュが蓄積されてから実行する．

### 引用数 Top-N の抽出

```bash
uv run python topn.py           # デフォルト Top-10
uv run python topn.py --top 5   # Top-5
uv run python topn.py --top 30  # Top-30
```

### API マッチの類似度統計

```bash
uv run python similarity_stats.py
```

## 出力ファイル

```
output/
├── cache_papers_{year}.json      # 論文タイトルのキャッシュ
├── cache_citations_{year}.json   # 引用数取得結果のキャッシュ
│
├── output_{year}/                # 年度別出力
│   ├── 01_citation_distribution.png  # 引用数分布（線形・対数）
│   ├── 02_top_papers.png             # 引用数 Top-30 横棒グラフ
│   ├── 03_citation_cdf.png           # 累積分布関数
│   ├── 04_percentile_bars.png        # パーセンタイル別引用数
│   ├── citations.csv                 # 全論文の引用数データ
│   └── top{N}.csv                    # Top-N ランキング（topn.py で生成）
│
├── top{N}_all_years.csv          # 全年度まとめ Top-N（CSV）
├── top{N}_all_years.json         # 全年度まとめ Top-N（JSON）
├── similarity_summary.csv        # 年度別マッチ類似度サマリー
├── similarity_details.csv        # sim < 1.0 の論文詳細
└── similarity_details.json       # 同上（JSON）
```

## レート制限

Semantic Scholar API の制限：

| 条件 | リクエスト間隔 | 2700 本の目安 |
|---|---|---|
| API キーなし | 3.1 秒 | 約 2.3 時間 |
| API キーあり（推奨） | 1.1 秒 | 約 50 分 |

429（Too Many Requests）が返った場合は自動的に待機してリトライする（最大 3 回）．
API エラーで取得に失敗した論文はキャッシュされないため，再実行すると自動的にリトライされる．

## すべてのオプション（main.py）

```
uv run python main.py --help

  --url URL              論文一覧ページの URL
  --limit N              処理する論文数の上限（テスト用）
  --api-key KEY          Semantic Scholar API キー
  --delay SEC            API 呼び出し間隔（秒）を手動指定
  --output DIR           出力ディレクトリ
  --papers-cache FILE    論文タイトルのキャッシュファイル
  --citations-cache FILE 引用数のキャッシュファイル
```
