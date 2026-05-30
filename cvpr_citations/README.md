# CVPR Citation Analyzer

CVPR 採択論文の引用数を Semantic Scholar API で取得し、リンク種別・発表種別ごとに比較・可視化するツールです。

## 必要環境

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) （パッケージマネージャ）

## セットアップ

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd cvpr_citations

# 2. API キーを設定（任意。設定するとレート制限が緩和されて高速になる）
cp .env.example .env
# .env を編集して SEMANTIC_SCHOLAR_API_KEY= の後にキーを記入
# キー取得先: https://www.semanticscholar.org/product/api#api-key-form
```

依存パッケージは `uv run` 実行時に自動でインストールされます（`uv sync` の手動実行は不要）。

## 実行方法

### 引用数の全件取得（メインパイプライン）

```bash
bash run_full.sh
```

`run_full.sh` 内の変数で年度・API キーを指定します。

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `YEAR` | 対象年度（2021〜2026） | `2026` |
| `API_KEY` | Semantic Scholar API キー（`.env` から自動読み込み） | なし |

完了まで数時間かかる場合があります。Ctrl+C で中断してもキャッシュから再開できます。

### 動作確認（20 件のみ）

```bash
bash run_test.sh
```

### 統計分析・可視化

引用数キャッシュ（`run_full.sh` の出力）をもとに各種統計を計算・可視化します。

```bash
bash run_statistics.sh
```

ファイル冒頭の変数で対象年度と件数を指定します。

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `YEAR` | 対象年度（2023〜2025） | `2025` |
| `TOP_N` | Top-N 抽出の件数 | `10` |

以下の4ステップが順番に実行されます。

#### [1] scrape_links.py — リンク情報の収集

`https://cvpr.thecvf.com/Conferences/{YEAR}/AcceptedPapers` から全採択論文のリンク情報を収集し、`output/result/cvpr{YEAR}_links.csv` に保存します。HTML は `output/cache/` にキャッシュされるため、2回目以降はネットワークアクセスなしで動作します。

収集する列:

| 列 | 内容 |
|----|------|
| `title` | 論文タイトル |
| `link_type` | `github` / `project_page` / `none` |
| `link` | リンク URL（なければ空） |
| `presentation_type` | `highlight` / `award_candidate`（2023 のみ） / `poster` |

#### [2] citation_comparison.py — リンク・発表種別ごとの引用数比較

`scrape_links.py` の出力と `run_full.sh` で取得した引用数キャッシュをタイトルで突き合わせ、グループ別の統計量と比較図を生成します。

生成される図（各図: 左=ボックスプロット log スケール、右=中央値バーチャート IQR 付き）:

| ファイル | 比較軸 | グループ |
|---------|--------|---------|
| `comparison_{YEAR}_01_link_type.png` | リンク種別（3値） | GitHub / Project Page / No Link |
| `comparison_{YEAR}_02_has_link.png` | リンク有無（2値） | Has Link / No Link |
| `comparison_{YEAR}_03_presentation.png` | 発表種別 | Highlight / Poster（/ Award Candidate） |
| `comparison_{YEAR}_04_ptype_x_link.png` | 発表種別 × リンク有無（4値） | Highlight+Link / Highlight+No Link / Poster+Link / Poster+No Link |

統計量（n / mean / median / std / Q25 / Q75 / max）は `citation_comparison_{YEAR}.csv` / `.json` にも保存されます。

#### [3] topn.py — 全年度 Top-N 引用論文の抽出

`output/cache/cache_citations_202*.json` を全年度分読み込み、引用数上位 TOP_N 件を年度別・全年度まとめの両形式で出力します。

| ファイル | 内容 |
|---------|------|
| `output/result/output_{year}/top{N}.csv` | 年度別ランキング |
| `output/result/top{N}_all_years.csv / .json` | 全年度まとめ |

#### [4] similarity_stats.py — タイトルマッチング類似度統計

Semantic Scholar のタイトル検索が返した結果とクエリの類似度を年度ごとに集計します。類似度が 1.0 未満（完全一致でない）の論文は `similarity_details.csv` / `.json` に詳細を保存します。

| ファイル | 内容 |
|---------|------|
| `output/result/similarity_summary.csv` | 年度別サマリー |
| `output/result/similarity_details.csv / .json` | 類似度 < 1.0 の論文一覧 |

## ファイル構成

```
cvpr_citations/
├── main.py               # 引用数取得パイプライン（エントリポイント）
├── scraper.py            # CVF サイトから論文タイトルを収集
├── semantic_scholar.py   # Semantic Scholar API で引用数を取得
├── visualize.py          # 引用数分布の可視化（ヒストグラム・CDF 等）
├── scrape_links.py       # リンク種別・発表種別の収集（2023〜2025 対応）
├── citation_comparison.py # リンク・発表種別ごとの引用数比較・可視化
├── topn.py               # 全年度 Top-N 引用論文の抽出
├── similarity_stats.py   # タイトルマッチング類似度統計
├── run_full.sh           # 本番実行（全件取得）
├── run_test.sh           # テスト実行（20 件）
├── run_statistics.sh     # 統計分析・可視化
├── pyproject.toml        # uv プロジェクト設定
├── .env.example          # API キー設定テンプレート
└── output/
    ├── cache/            # 再取得可能なキャッシュ（gitignore 対象）
    │   ├── cache_papers_{year}.json
    │   ├── cache_citations_{year}.json
    │   └── cache_cvpr{year}_accepted.html
    └── result/           # 分析結果（gitignore 対象）
        ├── output_{year}/              # run_full.sh の出力
        │   ├── 01_citation_distribution.png
        │   ├── 02_top_papers.png
        │   ├── 03_citation_cdf.png
        │   ├── 04_percentile_bars.png
        │   ├── citations.csv
        │   └── top{N}.csv
        ├── cvpr{year}_links.csv / .json
        ├── citation_comparison_{year}.csv / .json
        ├── comparison_{year}_01_link_type.png
        ├── comparison_{year}_02_has_link.png
        ├── comparison_{year}_03_presentation.png
        ├── comparison_{year}_04_ptype_x_link.png
        ├── top{N}_all_years.csv / .json
        ├── similarity_summary.csv
        ├── similarity_details.csv
        └── similarity_details.json
```

## API レート制限

| 条件 | レート上限 | 呼び出し間隔 |
|------|-----------|------------|
| API キーなし | 100 req / 5 min | 3.1 秒 |
| API キーあり | 1 req / sec | 1.1 秒 |

429 エラー時は自動でリトライします。中断・再実行してもキャッシュから途中再開できます。
