# CVPR Citation Analyzer

CVPR 採択論文の引用数を Semantic Scholar API で取得し，リンク種別・発表種別ごとに比較・可視化するツール．

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
├── scrape_links.py         # リンク種別・発表種別の収集（2023〜2025 対応）
├── citation_comparison.py  # リンク・発表種別ごとの引用数比較・可視化
├── topn.py                 # 引用数 Top-N を年度別・全年度まとめで保存
├── similarity_stats.py     # API マッチの類似度統計を集計・保存
│
├── run_full.sh             # 本番実行（全論文，年度指定）
├── run_test.sh             # テスト実行（少数の論文で動作確認）
└── run_statistics.sh       # 統計分析・可視化（scrape_links → 比較 → Top-N → 類似度）
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

`run_full.sh` の先頭にある変数を変更してから実行する：

```bash
# run_full.sh のパラメータ
YEAR=2025         # 対象年度（2021〜2026）
```

```bash
bash run_full.sh
```

複数年度を取得する場合は，`YEAR` を変えて繰り返し実行する．
Ctrl+C で中断してもキャッシュが保存されているため，再実行時は途中から再開できる．

### 統計分析・可視化

引用数キャッシュ（`run_full.sh` の出力）をもとに各種統計を計算・可視化する．

```bash
# run_statistics.sh のパラメータ
YEAR=2025         # 対象年度（2023〜2025）
TOP_N=10          # Top-N 抽出の件数
```

```bash
bash run_statistics.sh
```

以下の 4 ステップが順番に実行される．

#### [1] scrape_links.py — リンク情報の収集

`https://cvpr.thecvf.com/Conferences/{YEAR}/AcceptedPapers` から全採択論文のリンク情報を収集し，`output/result/cvpr{YEAR}_links.csv` に保存する．HTML は `output/cache/` にキャッシュされるため，2 回目以降はネットワークアクセスなしで動作する．

収集する列:

| 列 | 内容 |
|----|------|
| `title` | 論文タイトル |
| `link_type` | `github` / `project_page` / `none` |
| `link` | リンク URL（なければ空） |
| `presentation_type` | `highlight` / `award_candidate`（2023 のみ） / `poster` |

#### [2] citation_comparison.py — リンク・発表種別ごとの引用数比較

`scrape_links.py` の出力と引用数キャッシュをタイトルで突き合わせ，グループ別の統計量と比較図を生成する．

生成される図（各図: 左=ボックスプロット log スケール，右=中央値バーチャート IQR 付き）:

| ファイル | 比較軸 | グループ |
|---------|--------|---------|
| `comparison_{YEAR}_01_link_type.png` | リンク種別（3 値） | GitHub / Project Page / No Link |
| `comparison_{YEAR}_02_has_link.png` | リンク有無（2 値） | Has Link / No Link |
| `comparison_{YEAR}_03_presentation.png` | 発表種別 | Highlight / Poster（/ Award Candidate） |
| `comparison_{YEAR}_04_ptype_x_link.png` | 発表種別 × リンク有無（4 値） | Highlight+Link / Highlight+No Link / Poster+Link / Poster+No Link |

統計量（n / mean / median / std / Q25 / Q75 / max）は `citation_comparison_{YEAR}.csv` / `.json` にも保存される．

#### [3] topn.py — 全年度 Top-N 引用論文の抽出

`output/cache/cache_citations_202*.json` を全年度分読み込み，引用数上位 TOP_N 件を年度別・全年度まとめの両形式で出力する．

| ファイル | 内容 |
|---------|------|
| `output/result/output_{year}/top{N}.csv` | 年度別ランキング |
| `output/result/top{N}_all_years.csv / .json` | 全年度まとめ |

#### [4] similarity_stats.py — タイトルマッチング類似度統計

Semantic Scholar のタイトル検索が返した結果とクエリの類似度を年度ごとに集計する．類似度が 1.0 未満（完全一致でない）の論文は詳細を保存する．

| ファイル | 内容 |
|---------|------|
| `output/result/similarity_summary.csv` | 年度別サマリー |
| `output/result/similarity_details.csv / .json` | 類似度 < 1.0 の論文一覧 |

## 出力ファイル

```
output/
├── cache/                        # 再取得可能なキャッシュ（gitignore 対象）
│   ├── cache_papers_{year}.json      # 論文タイトルのキャッシュ
│   ├── cache_citations_{year}.json   # 引用数取得結果のキャッシュ
│   └── cache_cvpr{year}_accepted.html  # リンク情報ページのキャッシュ
│
└── result/                       # 分析結果（gitignore 対象）
    ├── output_{year}/                # run_full.sh の出力
    │   ├── 01_citation_distribution.png  # 引用数分布（線形・対数）
    │   ├── 02_top_papers.png             # 引用数 Top-30 横棒グラフ
    │   ├── 03_citation_cdf.png           # 累積分布関数
    │   ├── 04_percentile_bars.png        # パーセンタイル別引用数
    │   ├── citations.csv                 # 全論文の引用数データ
    │   └── top{N}.csv                    # Top-N ランキング（topn.py で生成）
    │
    ├── cvpr{year}_links.csv / .json          # リンク・発表種別一覧
    ├── citation_comparison_{year}.csv / .json # グループ別統計量
    ├── comparison_{year}_01_link_type.png
    ├── comparison_{year}_02_has_link.png
    ├── comparison_{year}_03_presentation.png
    ├── comparison_{year}_04_ptype_x_link.png
    ├── top{N}_all_years.csv / .json          # 全年度まとめ Top-N
    ├── similarity_summary.csv                # 年度別マッチ類似度サマリー
    ├── similarity_details.csv                # sim < 1.0 の論文詳細
    └── similarity_details.json
```

## レート制限

Semantic Scholar API の制限：

| 条件 | リクエスト間隔 | 2700 本の目安 |
|------|-------------|-------------|
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
