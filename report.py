# -*- coding: utf-8 -*-
"""ファイルから数えられない作業を、手で（または Claude が）書き込む。

例: 手で送ったフォーム営業、他ツールでやっている作業など。
書き先は sources/<PC名>.manual.json（collect.py は触らないので消えない）。

使い方:
  python report.py --name "製造業SCOPE営業" --note "製造業5県へのフォーム送信" \
      --metric 送信済み=120/197 --metric お断り=2
  python report.py --list                 このPCの手入力分を一覧
  python report.py --remove "製造業SCOPE営業"

--metric は「ラベル=数」または「ラベル=数/全体」。全体を付けた最初の
metric は進捗バーになる。
⚠️ Public ページに出るので、企業名・顧客名・メールアドレスは書かない（件数だけ）。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from pcname import pc_name  # noqa: E402

PC = pc_name()
OUT = BASE / "sources" / f"{PC}.manual.json"


def load():
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {"pc": PC, "projects": []}


def save(data):
    data["generated_at"] = datetime.now().isoformat(timespec="seconds")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def parse_metric(s):
    if "=" not in s:
        sys.exit(f"[ERROR] --metric は ラベル=数 の形で: {s}")
    label, v = s.split("=", 1)
    of = None
    if "/" in v:
        v, of = v.split("/", 1)
    try:
        m = {"label": label.strip(), "value": int(v.replace(",", ""))}
        if of:
            m["of"] = int(of.replace(",", ""))
    except ValueError:
        sys.exit(f"[ERROR] 数字にできません: {s}")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--note", default="")
    ap.add_argument("--metric", action="append", default=[])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--remove")
    a = ap.parse_args()
    data = load()

    if a.list:
        print(f"{OUT.name}")
        for p in data["projects"]:
            m = " / ".join(f"{x['label']} {x['value']:,}" for x in p["metrics"])
            print(f"  {p['name']}  ({p['updated'][:16]})  {m}")
        return
    if a.remove:
        before = len(data["projects"])
        data["projects"] = [p for p in data["projects"] if p["name"] != a.remove]
        save(data)
        print(f"削除: {before - len(data['projects'])} 件")
        return
    if not a.name:
        sys.exit("[ERROR] --name が必要です（--list / --remove 以外）")

    now = datetime.now().isoformat(timespec="seconds")
    entry = {"name": a.name, "note": a.note, "pc": PC, "manual": True,
             "updated": now, "metrics": [parse_metric(s) for s in a.metric]}
    old = next((p for p in data["projects"] if p["name"] == a.name), None)
    if old:
        if not a.note:
            entry["note"] = old.get("note", "")
        if not a.metric:
            entry["metrics"] = old.get("metrics", [])
        data["projects"][data["projects"].index(old)] = entry
        print(f"更新: {a.name}")
    else:
        data["projects"].append(entry)
        print(f"追加: {a.name}")
    save(data)
    print("ページへの反映は  python update.py")


if __name__ == "__main__":
    main()
