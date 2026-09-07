# プロジェクト状況ダッシュボード

手元のプロジェクトの状態を1枚にまとめたページ。
**Notion 同期の後継**として作った（Notion は会社ワークスペースがブロック上限に達したため）。

公開URL: https://takeda-png.github.io/claude-projects/

## 方針

**手で書いた説明を持たない。** 数字はすべてファイル・CSV・git から数え直す。

旧 Notion 同期は `status` と `details` の大半がコードへの直書きで、
放っておくと古くなった（WordPress の欄が「最新p6276」のまま、
営業件数のメモが `national 241` に対し実際は `1,115` 等）。
ここではその轍を踏まないよう、集められない情報は載せない。

グループ分けも**ファイルの最終更新日だけ**で決めている（作業の進捗判定ではない）。

## 使い方

```bash
python collect.py   # 実測 → data.json
python build.py     # data.json → index.html
git add -A && git commit -m "update" && git push
```

## 載せていないもの

Public リポジトリなので、**企業名・顧客名・ローカルのパス**は一切出していない
（営業パイプラインは件数だけ）。ページには `noindex` を入れてあるので検索には出ない。

## ファイル

| ファイル | 役割 |
|---|---|
| `collect.py` | 各プロジェクトを走査して実測値を `data.json` に書く |
| `build.py` | `data.json` から `index.html` を組む |
| `data.json` | 実測結果 |
| `index.html` | 公開ページ |
