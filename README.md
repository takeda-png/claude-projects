# プロジェクト状況ダッシュボード

複数のPCの作業状況を1枚にまとめたページ。
公開URL: https://takeda-png.github.io/claude-projects/

## しくみ

```
各PC: collect.py（自動で数える）  ─┐
      report.py （手で書き込む）   ─┼→ sources/<PC名>.json / <PC名>.manual.json を push
                                    │
GitHub Actions: build.py ←──────────┘  全PCのファイルをまとめて index.html を作る
```

- **各PCは自分のファイルしか書かない**ので、何台から push してもぶつからない
- `index.html` は GitHub Actions だけが作る（PC側では触らない。手元の確認は `_preview.html`）
- 毎朝7時にも組み立て直す（どのPCも動かない日でも「何日前」が正しくなる）

## 使い方（どのPCでも同じ）

```bash
git clone https://github.com/takeda-png/claude-projects.git
cd claude-projects
echo PC2 > .pc_name          # 任意。無ければ Windows のコンピューター名を使う

python update.py --dry-run   # 集計して _preview.html を作るだけ
python update.py             # 集計 → チェック → push（1〜2分でページに反映）
```

### ファイルから数えられない作業を載せる

手で送ったフォーム営業など。

```bash
python report.py --name "製造業SCOPE営業" --note "製造業5県へのフォーム送信" \
    --metric 送信済み=120/197 --metric お断り=2
python update.py
```

- `--metric ラベル=数/全体` の最初の1つが進捗バーになる
- 同じ `--name` でもう一度実行すると上書き更新。`--list` で一覧、`--remove "名前"` で削除

## 載せてはいけないもの

**Public リポジトリ**なので、企業名・顧客名・メールアドレス・ローカルのパスは書かない（件数だけ）。
`update.py` が push 前に毎回スキャンし、見つかれば止まる。ページは `noindex`。

## ファイル

| ファイル | 役割 |
|---|---|
| `collect.py` | このPCのプロジェクトを実測して `sources/<PC名>.json` に書く（無いフォルダは飛ばす） |
| `report.py` | 手入力分を `sources/<PC名>.manual.json` に書く |
| `update.py` | pull → collect → スキャン → 自分のファイルだけ push |
| `build.py` | `sources/*.json` を全部まとめて `index.html` を組む（Actions が実行） |
| `pcname.py` | PC名の決定（`.pc_name` → コンピューター名） |
| `.github/workflows/build.yml` | push・毎朝7時に `build.py` を実行 |
