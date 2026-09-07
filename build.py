# -*- coding: utf-8 -*-
"""data.json から index.html を組む。

方針: 手で書いた説明を載せない。数字はすべて collect.py が実測したもの。
公開先は Public リポジトリの GitHub Pages なので、
ローカルパス・企業名・顧客名は一切出さない（件数だけ）。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
DATA = BASE / "data.json"
OUT = BASE / "index.html"

# 測っているのは「最終更新日」であって稼働状況そのものではない。
# 成果物フォルダまで「稼働中」と出ると誤解するので、事実どおりの言い方にする。
LABEL = {"active": "今週更新", "slow": "1ヶ月以内", "idle": "1ヶ月以上前", "unknown": "不明"}

CSS = """
:root{
  --bg:#f6f7f9; --card:#fff; --line:#e4e8ee; --tx:#1a2233; --sub:#6b7686;
  --active:#0E7C5A; --slow:#B4690E; --idle:#6B7280; --bar:#dfe4ea;
}
@media(prefers-color-scheme:dark){
  :root{--bg:#12161c; --card:#1a1f27; --line:#2b323c; --tx:#e8ecf2; --sub:#9aa5b4;
        --active:#4BBF95; --slow:#E0A45C; --idle:#8892A0; --bar:#2b323c;}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
     font-family:-apple-system,"Segoe UI","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
     line-height:1.6;-webkit-text-size-adjust:100%}
.wrap{max-width:940px;margin:0 auto;padding:28px 18px 60px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px;margin-bottom:6px}
h1{font-size:21px;margin:0;letter-spacing:.02em}
.gen{font-size:12px;color:var(--sub)}
.lead{font-size:13px;color:var(--sub);margin:0 0 22px}
.sec{font-size:12px;font-weight:700;color:var(--sub);letter-spacing:.08em;
     margin:26px 0 10px;text-transform:uppercase}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
      padding:15px 17px;margin-bottom:10px}
.top{display:flex;flex-wrap:wrap;align-items:center;gap:9px}
.nm{font-size:16px;font-weight:700;margin:0}
.pill{font-size:11px;font-weight:700;padding:2px 9px;border-radius:99px;
      border:1px solid currentColor;white-space:nowrap}
.pill.active{color:var(--active)} .pill.slow{color:var(--slow)}
.pill.idle{color:var(--idle)} .pill.unknown{color:var(--idle)}
.age{font-size:12px;color:var(--sub);margin-left:auto;white-space:nowrap}
.note{font-size:12.5px;color:var(--sub);margin:3px 0 0}
.mets{display:flex;flex-wrap:wrap;gap:18px;margin-top:11px}
.met .v{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2}
.met .l{font-size:11px;color:var(--sub)}
.bar{height:5px;background:var(--bar);border-radius:99px;overflow:hidden;margin-top:11px}
.bar>i{display:block;height:100%;background:var(--active);border-radius:99px}
.barlab{font-size:11px;color:var(--sub);margin-top:5px}
.foot{display:flex;flex-wrap:wrap;gap:14px;margin-top:11px;padding-top:10px;
      border-top:1px solid var(--line);font-size:11.5px;color:var(--sub)}
.foot b{font-weight:600;color:var(--tx);font-variant-numeric:tabular-nums}
footer{margin-top:34px;font-size:11.5px;color:var(--sub);line-height:1.8}
@media(max-width:520px){
  .wrap{padding:20px 13px 44px} h1{font-size:18px}
  .age{margin-left:0;width:100%} .mets{gap:14px} .met .v{font-size:17px}
}
"""


def fmt_age(d):
    if d is None:
        return "更新日不明"
    if d == 0:
        return "本日更新"
    if d == 1:
        return "昨日更新"
    return f"{d:,}日前に更新"


def card(p):
    st = p["status"]
    h = ['<div class="card">']
    h.append('<div class="top">')
    h.append(f'<h2 class="nm">{p["name"]}</h2>')
    h.append(f'<span class="pill {st}">{LABEL[st]}</span>')
    h.append(f'<span class="age">{fmt_age(p["days"])}</span>')
    h.append("</div>")
    if p.get("note"):
        h.append(f'<p class="note">{p["note"]}</p>')

    if p["metrics"]:
        h.append('<div class="mets">')
        for m in p["metrics"]:
            h.append(f'<div class="met"><div class="v">{m["value"]:,}</div>'
                     f'<div class="l">{m["label"]}</div></div>')
        h.append("</div>")
        # 送信済み / リスト の進捗があれば棒で出す
        first = p["metrics"][0]
        if first.get("of"):
            pct = first["value"] / first["of"] * 100
            h.append(f'<div class="bar"><i style="width:{pct:.1f}%"></i></div>')
            h.append(f'<div class="barlab">リスト {first["of"]:,} 件のうち '
                     f'{first["value"]:,} 件が送信済み（{pct:.1f}%）</div>')

    d, g = p["dir"], p.get("git")
    foot = [f'ファイル <b>{d["files"]:,}</b>', f'容量 <b>{d["size_mb"]:,.1f}</b> MB']
    if g:
        if g.get("commits"):
            foot.append(f'コミット <b>{g["commits"]:,}</b>')
        if g.get("uncommitted"):
            foot.append(f'未コミット <b>{g["uncommitted"]}</b> 件')
    h.append('<div class="foot">' + "".join(f"<span>{x}</span>" for x in foot) + "</div>")
    h.append("</div>")
    return "\n".join(h)


def build():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    gen = datetime.fromisoformat(data["generated_at"])
    ps = data["projects"]
    order = {"active": 0, "slow": 1, "idle": 2, "unknown": 3}
    ps.sort(key=lambda x: (order[x["status"]], x["days"] if x["days"] is not None else 9999))

    groups = [("直近1週間で更新", ["active"]), ("1ヶ月以内に更新", ["slow"]),
              ("1ヶ月以上さわっていない", ["idle", "unknown"])]
    body = []
    for title, keys in groups:
        sel = [p for p in ps if p["status"] in keys]
        if not sel:
            continue
        body.append(f'<div class="sec">{title}（{len(sel)}）</div>')
        body += [card(p) for p in sel]

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>プロジェクト状況</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>プロジェクト状況</h1>
  <span class="gen">{gen.strftime('%Y-%m-%d %H:%M')} 時点</span>
</header>
<p class="lead">数字はすべてファイル・CSV・git から自動で数えたものです（手入力なし）。
グループ分けは<strong>ファイルの最終更新日</strong>だけで決めています（作業の進捗ではありません）。</p>
{"".join(body)}
<footer>
  自動生成：<code>collect.py</code> → <code>build.py</code>。企業名・顧客名・ローカルのパスは載せていません。<br>
  検索エンジンには載りません（noindex）。
</footer>
</div>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name}: {len(html):,} bytes / {len(ps)} プロジェクト")
    for t, k in groups:
        n = len([p for p in ps if p["status"] in k])
        if n:
            print(f"  {t}: {n}")


if __name__ == "__main__":
    build()
