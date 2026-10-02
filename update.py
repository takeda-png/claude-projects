# -*- coding: utf-8 -*-
"""このPCの実測 → sources/<PC名>.json を push する。

ページ(index.html)は GitHub Actions が全PCの sources/*.json から組み立てる。
各PCは自分のファイルしか触らないので、複数PCから push してもぶつからない。

使い方:
  python update.py            通常（変更があれば push）
  python update.py --dry-run  集計と確認用ページ(_preview.html)だけ作って push しない
"""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
DRY = "--dry-run" in sys.argv
URL = "https://takeda-png.github.io/claude-projects/"
sys.path.insert(0, str(BASE))
from pcname import pc_name  # noqa: E402
PC = pc_name()


def run(args, **kw):
    return subprocess.run(args, cwd=BASE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def main():
    # 先に他のPCの分を取り込む（自分のファイルしか書かないので衝突しない）
    if not DRY:
        r = run(["git", "pull", "--rebase", "--autostash"])
        if r.returncode != 0:
            print("[ERROR] pull\n" + r.stdout + r.stderr)
            return 1
    for script in (["collect.py"], ["build.py", "--out", "_preview.html"]):
        r = run([sys.executable] + script)
        if r.returncode != 0:
            print(f"[ERROR] {script[0]}\n{r.stdout}\n{r.stderr}")
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
        if not f.is_file() or ".git" in f.parts or "__pycache__" in f.parts or f.name in (SELF, "_preview.html", ".pc_name"):
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

    if not run(["git", "status", "--porcelain", "--", "sources"]).stdout.strip():
        print("変更なし（push しません）")
        return 0

    # 生成時刻しか変わっていないなら push しない。
    # 自動で何度も走るので、放っておくとタイムスタンプだけのコミットが積み上がる。
    diff = run(["git", "diff", "-U0", "--", "sources"]).stdout
    changed = [l for l in diff.splitlines()
               if (l.startswith("+") or l.startswith("-"))
               and not l.startswith(("+++", "---"))]
    if changed and all(("generated_at" in l or "時点" in l) for l in changed):
        run(["git", "checkout", "--", "sources"])
        print("生成時刻以外に変化なし（push しません）")
        return 0

    run(["git", "add", "--", "sources"])
    r = run(["git", "commit", "-m", f"Update project status ({PC})\n\n"
             "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"])
    if r.returncode != 0:
        print("[ERROR] commit\n" + r.stdout + r.stderr)
        return 1
    r = run(["git", "push"])
    if r.returncode != 0:  # 直前に他のPCが push していたら取り込んでやり直す
        run(["git", "pull", "--rebase", "--autostash"])
        r = run(["git", "push"])
    if r.returncode != 0:
        print("[ERROR] push\n" + r.stdout + r.stderr)
        return 1
    print(f"push しました（1〜2分でページに反映） → {URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
