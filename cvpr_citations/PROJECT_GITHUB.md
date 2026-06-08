# Project GitHub Analyzer

project page / github.io から GitHub リポジトリリンクを収集・可視化するサブパイプライン．  
メインパイプライン（`run_statistics.sh`）で生成された `{conf}{year}_links.csv` を前提とする．

---

## ファイル構成

```
cvpr_citations/
├── scrape_project_github.py    # project page / github.io をスクレイピングして GitHub リポジトリ URL を収集
├── visualize_project_github.py # 収集結果を可視化（グラフ 6 種 + サマリ CSV/JSON）
├── run_project_github.sh       # [自動] 上記 2 ステップを一括実行
└── run_test_project_github.sh  # 少数の論文で動作確認
```

---

## 前提

`scrape_links.py`（`run_statistics.sh` 内で実行される）が生成する以下のファイルが必要：

```
output/result{CONF_SUFFIX}/{conf}{year}_links.csv
```

---

## 実行フロー

```
bash run_project_github.sh
    ↓
[1] scrape_project_github.py   project page / github.io をフェッチして GitHub リポジトリ URL を抽出
    ↓ output/result_{conf}/project_github_{year}.json / .csv
[2] visualize_project_github.py  収集結果をグラフ化・集計
    ↓ output/result_{conf}/project_github_{year}_0N_*.png / _summary.json / .csv
```

---

## パラメータ

### `run_project_github.sh`（本番実行）

```bash
CONF=cvpr                  # 対象会議（cvpr / iccv / wacv）
YEARS=(2023 2024 2025)     # 対象年度（複数指定可）
```

```bash
bash run_project_github.sh
```

### `run_test_project_github.sh`（動作確認）

```bash
CONF=cvpr    # 対象会議
YEAR=2023    # 対象年度
LIMIT=20     # 処理する論文数
```

```bash
bash run_test_project_github.sh
```

---

## 出力ファイル

`output/result{CONF_SUFFIX}/` 以下に保存される．

| ファイル | 内容 |
|---|---|
| `project_github_{year}.json` | 論文ごとの詳細（リンク種別・GitHub URL・フェッチ状態） |
| `project_github_{year}.csv` | 同上（CSV 形式） |
| `project_github_{year}_01_project_page_rate.png` | 全論文に占める Project Page / GitHub.io の割合 |
| `project_github_{year}_02_github_code_rate.png` | Project Page / GitHub.io 持ち論文のうち GitHub コードを持つ割合 |
| `project_github_{year}_03_by_url_type.png` | URL 種別（github.io / project page）ごとの GitHub リポジトリ公開率 |
| `project_github_{year}_04_by_presentation.png` | 発表種別ごとの GitHub リポジトリ公開率 |
| `project_github_{year}_05_fetch_status.png` | フェッチ成否の内訳 |
| `project_github_{year}_06_combined_stacked.png` | 全論文を URL種別×コード公開の 5 区分で積み上げた俯瞰チャート |
| `project_github_{year}_summary.json` | 集計サマリ（URL 種別・発表種別ごとの公開率） |
| `project_github_{year}_summary.csv` | 同上（CSV 形式） |

キャッシュ（`output/cache{CONF_SUFFIX}/cache_project_github_{year}.json`）にスクレイピング結果が保存されるため，中断・再実行時は途中から再開できる．

---

## スクレイピングの仕組み

`scrape_project_github.py` は次のルールで GitHub リポジトリ URL を抽出する：

1. `link_type = "project_page"` または `link_type = "github"` かつ URL に `github.io` を含む論文を対象とする
2. 対象 URL をフェッチし，HTML 内の `<a>` タグから `github.com/{user}/{repo}` 形式の URL を取得する
3. アンカーテキストに `code / github / source / implementation / repo / repository` を含むリンクを優先する
4. 先頭 1 件を `github_repo_url` として保存する（見つからなければ空文字列）
