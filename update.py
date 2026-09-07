# -*- coding: utf-8 -*-
"""実測 → HTML生成 → GitHub Pages へ反映 を1本で行う。

使い方:
  python update.py            通常（変更があれば push）
  python update.py --dry-run  生成だけして push しない
"""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
DRY = "--dry-run" in sys.argv
URL = "https://takeda-png.github.io/claude-projects/"


def run(args, **kw):
    return subprocess.run(args, cwd=BASE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def main():
    for script in ("collect.py", "build.py"):
        r = run([sys.executable, script])
        if r.returncode != 0:
            print(f"[ERROR] {script}\n{r.stdout}\n{r.stderr}")
            return 1
        print(r.stdout.rstrip())

    # 公開前に毎回スキャンする（Public リポジトリなので）
    import re
    ng = []
    drive = re.compile(r"[A-Za-z]:" + re.escape(chr(92)) + r"Users|[A-Za-z]:/Users")
    pats = {
        "APIキー": re.compile(r"AIza[\w-]{20,}|sk-[\w-]{20,}|AQ\.[\w-]{20,}"
                              r"|gh[pousr]_\w{30,}|AKIA[0-9A-Z]{16}"),
        "資格情報": re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][^'\"]{8,}"),
        "メール": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
        "ローカルパス": drive,
        "企業名": re.compile(r"(株式会社|有限会社)[^\s\"'<>,]{1,12}"),
    }
    # このファイル自身は対象外。検知パターンの正規表現（「株式会社」等）と
    # コミットの co-author 表記が必ず引っかかるため。他は全部見る。
    SELF = Path(__file__).name
    for f in BASE.rglob("*"):
        if not f.is_file() or ".git" in f.parts or f.name == SELF:
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        for k, pt in pats.items():
            if pt.search(t):
                ng.append(f"{f.name}: {k}")
    if ng:
        print("[STOP] 公開できない内容が含まれています:")
        for x in ng:
            print("   ", x)
        return 1
    print("秘密情報スキャン: 検出0")

    if DRY:
        print("[dry-run] push しません。")
        return 0

    if not run(["git", "status", "--porcelain"]).stdout.strip():
        print("変更なし（push しません）")
        return 0

    # 生成時刻しか変わっていないなら push しない。
    # 自動で何度も走るので、放っておくとタイムスタンプだけのコミットが積み上がる。
    diff = run(["git", "diff", "-U0"]).stdout
    changed = [l for l in diff.splitlines()
               if (l.startswith("+") or l.startswith("-"))
               and not l.startswith(("+++", "---"))]
    if changed and all(("generated_at" in l or "時点" in l) for l in changed):
        run(["git", "checkout", "--", "."])
        print("生成時刻以外に変化なし（push しません）")
        return 0

    run(["git", "add", "-A"])
    r = run(["git", "-c", "user.name=takeda-png", "commit", "-m",
             "Update project status\n\n"
             "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"])
    if r.returncode != 0:
        print("[ERROR] commit\n" + r.stdout + r.stderr)
        return 1
    r = run(["git", "push"])
    if r.returncode != 0:
        print("[ERROR] push\n" + r.stdout + r.stderr)
        return 1
    print(f"反映しました → {URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
