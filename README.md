# CVPR Citation Analyzer

CVPR 採択論文の引用数を Semantic Scholar API で取得し，リンク種別・発表種別ごとに比較・可視化するツール．

## ファイル構成

```
cvpr_citations/
├── pyproject.toml            # 依存関係（uv プロジェクト）
├── uv.lock                   # 依存バージョン固定
├── .env.example              # API キーのテンプレート
│
├── main.py                   # 引用数取得 CLI（スクレイプ→API取得→可視化）
├── scraper.py                # CVF ページから論文タイトルをスクレイプ
├── semantic_scholar.py       # Semantic Scholar API クライアント
├── visualize.py              # グラフ生成（4 種）
│
├── retry_normalized.py       # タイトル正規化・再検索・cvpr_match フラグ付与
├── export_corrections.py     # cvpr_match=False の要確認論文を JSON に書き出す
├── apply_corrections.py      # 手動記入済み JSON を _fixed キャッシュに反映する
│
├── scrape_links.py           # リンク種別・発表種別の収集（2021〜2025 対応）
├── citation_comparison.py    # リンク・発表種別ごとの引用数比較・可視化
├── topn.py                   # 引用数 Top-N を年度別・全年度まとめで保存
├── similarity_stats.py       # API マッチの類似度統計を集計・保存
│
├── run_full.sh               # [自動] 引用数取得 → フィルタリング → 修正候補出力
├── run_corrections.sh        # [手動後] 修正 JSON の適用
├── run_statistics.sh         # [自動] 統計分析・可視化
├── run_test.sh               # 少数の論文で動作確認
└── run_normalize.sh          # retry_normalized.py の単体実行（再処理用）
```

すべての出力・キャッシュは `output/` 以下に保存される（git 管理外）．

---

## セットアップ

### 1. uv のインストール（未インストールの場合）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. API キーの設定

```bash
cp .env.example .env
```

`.env` を開き，Semantic Scholar の API キーを設定する：

```
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
```

API キーなしでも動作するが，レート制限が厳しくなる（後述）．  
取得先: https://www.semanticscholar.org/product/api#api-key-form

---

## 実行フロー

全体は 3 段階に分かれる．年度ごとに繰り返す．

```
[自動] bash run_full.sh
           ↓ output/cache/corrections_{YEAR}.json を生成
[手動] corrections_{YEAR}.json の "api" 欄を記入
           ↓
[自動] bash run_corrections.sh
           ↓ output/cache/cache_citations_{YEAR}_fixed.json を更新
[自動] bash run_statistics.sh
           ↓ 統計・グラフを output/result/ に保存
```

---

## Stage 1 — 引用数取得・フィルタリング（`run_full.sh`）

`run_full.sh` の先頭にある変数を編集してから実行する：

```bash
# run_full.sh のパラメータ
YEAR=2025         # 対象年度（2021〜2026）
```

```bash
bash run_full.sh
```

内部で以下の 3 ステップが順番に実行される．

#### [1] main.py — 論文タイトル取得・引用数収集

CVF の公開ページをスクレイプして論文タイトルを収集し，Semantic Scholar API で引用数を取得する．  
結果は `output/cache/cache_citations_{YEAR}.json` にキャッシュされるため，Ctrl+C で中断しても再実行時は途中から再開できる．

#### [2] retry_normalized.py — タイトル正規化・再検索・cvpr_match 付与

タイトルに表記揺れ（二重スペース・`^N` 記法・カーリークォート等）がある論文を正規化クエリで再検索し，マッチ精度を改善する．  
また全エントリに `cvpr_match` フラグを付与する：

| `cvpr_match` | 条件 |
|---|---|
| `True` | `venue` に "Computer Vision and Pattern Recognition" を含む かつ `year ∈ {YEAR-2, YEAR-1, YEAR}` |
| `False` | それ以外（別会議・別年度・arXiv のみ など） |

結果は `output/cache/cache_citations_{YEAR}_fixed.json` に保存される．

#### [3] export_corrections.py — 修正候補の書き出し

`cvpr_match=False` のうち，`similarity < 1.0` かつ `paper_year >= YEAR-2` のエントリを  
`output/cache/corrections_{YEAR}.json` に書き出す．

---

## Stage 2 — 手動修正（`corrections_{YEAR}.json` の編集）

`output/cache/corrections_{YEAR}.json` を開き，各エントリの `"api"` 欄を記入する．

```json
{
  "target_year": 2025,
  "query_title": "論文タイトル（CVF ページ記載）",
  "matched_title": "S2 が返したタイトル",
  "similarity": 0.83,
  "url": ""   ← ここを記入
}
```

| 記入値 | 意味 |
|---|---|
| `"ok"` | クエリと一致しないが同一論文とみなせる → `cvpr_match=True` に昇格 |
| Semantic Scholar の論文 URL | その論文が正解 → タイトル・引用数を差し替え |
| `""` (空欄のまま) | スキップ（変更なし） |

**URL の取得方法:**  
`https://www.semanticscholar.org` で正しい論文を検索し，URL をそのままコピーして貼り付ける．URL 全体でも末尾の ID 部分だけでも，どちらでも動作する．

```
https://www.semanticscholar.org/paper/Title-of-Paper/649def34f8be52c8b66281af98ae884c09aef38b
↑ URL 全体をそのままコピーして貼ればよい
```

---

## Stage 3 — 修正の適用（`run_corrections.sh`）

`run_corrections.sh` の先頭にある変数を編集してから実行する：

```bash
# run_corrections.sh のパラメータ
YEAR=2025
```

```bash
bash run_corrections.sh
```

`corrections_{YEAR}.json` の記入内容を読み込み，`cache_citations_{YEAR}_fixed.json` を更新する．  
`api` 欄に URL が指定されたエントリは Semantic Scholar API で正しいデータを再取得してから保存する．

---

## Stage 4 — 統計分析・可視化（`run_statistics.sh`）

引用数キャッシュ（`_fixed.json`）をもとに各種統計を計算・可視化する．

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
|---|---|
| `title` | 論文タイトル |
| `link_type` | `github` / `project_page` / `none` |
| `link` | リンク URL（なければ空） |
| `presentation_type` | `highlight` / `award_candidate`（2023 のみ） / `poster` |

#### [2] citation_comparison.py — リンク・発表種別ごとの引用数比較

`scrape_links.py` の出力と引用数キャッシュをタイトルで突き合わせ，グループ別の統計量と比較図を生成する．

生成される図（各図: 左=ボックスプロット log スケール，右=中央値バーチャート IQR 付き）:

| ファイル | 比較軸 | グループ |
|---|---|---|
| `comparison_{YEAR}_01_link_type.png` | リンク種別（3 値） | GitHub / Project Page / No Link |
| `comparison_{YEAR}_02_has_link.png` | リンク有無（2 値） | Has Link / No Link |
| `comparison_{YEAR}_03_presentation.png` | 発表種別 | Highlight / Poster（/ Award Candidate） |
| `comparison_{YEAR}_04_ptype_x_link.png` | 発表種別 × リンク有無（4 値） | Highlight+Link / Highlight+No Link / Poster+Link / Poster+No Link |

統計量（n / mean / median / std / Q25 / Q75 / max）は `citation_comparison_{YEAR}.csv` / `.json` にも保存される．

#### [3] topn.py — 全年度 Top-N 引用論文の抽出

`output/cache/cache_citations_202*_fixed.json` を全年度分読み込み，引用数上位 TOP_N 件を年度別・全年度まとめの両形式で出力する．

| ファイル | 内容 |
|---|---|
| `output/result/output_{year}/top{N}.csv` | 年度別ランキング |
| `output/result/top{N}_all_years.csv / .json` | 全年度まとめ |

#### [4] similarity_stats.py — タイトルマッチング類似度統計

Semantic Scholar のタイトル検索が返した結果とクエリの類似度を年度ごとに集計する．

| ファイル | 内容 |
|---|---|
| `output/result/similarity_summary.csv` | 年度別サマリー |
| `output/result/similarity_details.csv / .json` | 類似度 < 1.0 の論文一覧 |

---

## テスト実行

少数の論文で動作確認をしたい場合は `run_test.sh` を使用する：

```bash
# run_test.sh のパラメータ
LIMIT=20          # 処理する論文数
```

```bash
bash run_test.sh
```

---

## 出力ファイル

```
output/
├── cache/                            # 再取得可能なキャッシュ（gitignore 対象）
│   ├── cache_papers_{year}.json          # 論文タイトルのキャッシュ
│   ├── cache_citations_{year}.json       # 引用数取得結果（生データ）
│   ├── cache_citations_{year}_fixed.json # 正規化・修正済みキャッシュ（分析に使用）
│   ├── corrections_{year}.json           # 手動修正候補（run_full.sh が生成）
│   └── cache_cvpr{year}_accepted.html    # リンク情報ページのキャッシュ
│
└── result/                           # 分析結果（gitignore 対象）
    ├── output_{year}/                    # run_full.sh の出力
    │   ├── 01_citation_distribution.png      # 引用数分布（線形・対数）
    │   ├── 02_top_papers.png                 # 引用数 Top-30 横棒グラフ
    │   ├── 03_citation_cdf.png               # 累積分布関数
    │   ├── 04_percentile_bars.png            # パーセンタイル別引用数
    │   └── citations.csv                     # 全論文の引用数データ
    │
    ├── cvpr{year}_links.csv / .json      # リンク・発表種別一覧
    ├── citation_comparison_{year}.csv / .json  # グループ別統計量
    ├── comparison_{year}_01_link_type.png
    ├── comparison_{year}_02_has_link.png
    ├── comparison_{year}_03_presentation.png
    ├── comparison_{year}_04_ptype_x_link.png
    ├── top{N}_all_years.csv / .json      # 全年度まとめ Top-N
    ├── similarity_summary.csv            # 年度別マッチ類似度サマリー
    └── similarity_details.csv / .json   # 類似度 < 1.0 の論文詳細
```

---

## レート制限

Semantic Scholar API の制限：

| 条件 | リクエスト間隔 | 2700 本の目安 |
|---|---|---|
| API キーなし | 3.1 秒 | 約 2.3 時間 |
| API キーあり（推奨） | 1.1 秒 | 約 50 分 |

429（Too Many Requests）が返った場合は自動的に待機してリトライする（最大 3 回）．  
API エラーで取得に失敗した論文はキャッシュされないため，再実行すると自動的にリトライされる．
