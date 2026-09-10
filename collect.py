# -*- coding: utf-8 -*-
"""各プロジェクトの「実測できる値だけ」を集める。

Notion 同期の後継。旧スクリプトは status/details の大半がコードへの直書きで、
放っておくと古くなった（例: WordPress の欄が「最新p6276」のまま／MEMORY.md の
送信件数も national 241 と実際 1,115 でズレていた）。
ここでは手で書いた説明を一切持たず、ファイル・CSV・git から数え直す。

出力: data.json
"""
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path.home()          # 公開リポジトリなので実パスは書かない
DESK = HOME / "Desktop"
ACTIVE = DESK / "_Projects" / "Active"
OUT = Path(__file__).resolve().parent / "data.json"

# 走査から外す（容量・件数を膨らませるだけで意味がない）
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv",
             "ms-playwright", ".playwright-mcp", "dist", "build"}


def dir_stats(path: Path):
    """容量(MB)・ファイル数・最終更新日時を実測する。"""
    if not path.exists():
        return None
    total, files, newest = 0, 0, 0.0
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            fp = os.path.join(root, n)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            total += st.st_size
            files += 1
            newest = max(newest, st.st_mtime)
    return {
        "size_mb": round(total / 1024 / 1024, 1),
        "files": files,
        "mtime": datetime.fromtimestamp(newest).isoformat(timespec="seconds") if newest else None,
    }


def git_stats(path: Path):
    """最終コミット日時とコミット数。git 管理外なら None。"""
    if not (path / ".git").exists():
        return None
    def run(args):
        try:
            r = subprocess.run(["git", "-C", str(path)] + args,
                               capture_output=True, text=True, timeout=30,
                               encoding="utf-8", errors="replace")
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None
    last = run(["log", "-1", "--format=%cI"])
    count = run(["rev-list", "--count", "HEAD"])
    dirty = run(["status", "--porcelain"])
    return {
        "last_commit": last,
        "commits": int(count) if count and count.isdigit() else None,
        "uncommitted": len([l for l in (dirty or "").splitlines() if l.strip()]),
    }


def csv_status(path: Path):
    """営業パイプラインの companies.csv を status で数える。"""
    if not path.exists():
        return None
    counts = {}
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                s = (row.get("status") or "").strip() or "(未設定)"
                counts[s] = counts.get(s, 0) + 1
    except Exception as e:
        print(f"[WARN] CSV読み取り失敗 {path}: {e}")
        return None
    return counts


def count_glob(path: Path, pattern: str):
    return len(list(path.glob(pattern))) if path.exists() else 0


def age_days(iso: str):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return (datetime.now() - d.replace(tzinfo=None)).days


def status_of(days):
    """最終更新からの日数で状態を自動判定する（手で書かない）。"""
    if days is None:
        return "unknown"
    if days <= 7:
        return "active"
    if days <= 30:
        return "slow"
    return "idle"


def pipeline(name, dirname, note):
    d = DESK / dirname
    st = dir_stats(d)
    counts = csv_status(d / "companies.csv") or {}
    total = sum(counts.values())
    sub = counts.get("submitted", 0)
    pend = counts.get("pending", 0)
    days = age_days(st["mtime"]) if st else None
    return {
        "name": name, "note": note, "dir": st, "git": git_stats(d),
        "days": days, "status": status_of(days),
        "metrics": [
            {"label": "送信済み", "value": sub, "of": total},
            {"label": "未送信", "value": pend},
            {"label": "リスト", "value": total},
        ],
    }


def build():
    projects = []

    # ── WordPress 自動投稿（コーポレート） ──────────────────
    p = HOME / "sinmido"
    st = dir_stats(p)
    projects.append({
        "name": "WordPress Webmaster AI",
        "note": "sinmido.com の記事生成・自動投稿",
        "dir": st, "git": git_stats(p),
        "days": age_days(st["mtime"]) if st else None,
        "status": status_of(age_days(st["mtime"]) if st else None),
        "metrics": [
            {"label": "投稿ログ", "value": count_glob(p, "post_result_*.json")},
            {"label": "記事JSON", "value": count_glob(p, "article_*.json")},
        ],
    })

    # ── リクルートサイト自動コラム ────────────────────────
    p = HOME / "sinmido-recruit"
    st = dir_stats(p)
    projects.append({
        "name": "リクルート自動コラム",
        "note": "sinmido-recruit.com のコラム生成・投稿",
        "dir": st, "git": git_stats(p),
        "days": age_days(st["mtime"]) if st else None,
        "status": status_of(age_days(st["mtime"]) if st else None),
        "metrics": [
            {"label": "投稿ログ", "value": count_glob(p, "post_result_*.json")},
            {"label": "記事JSON", "value": count_glob(p, "article_*.json")},
        ],
    })

    # ── 営業パイプライン3本 ──────────────────────────────
    projects.append(pipeline("埼玉フォーム営業", "form-automation-saitama", "埼玉県内企業へのフォーム送信"))
    projects.append(pipeline("SCOPE営業", "form-automation", "HP制作会社・IT企業へのフォーム送信"))
    projects.append(pipeline("全国工務店営業", "form-automation-national", "全国の工務店へのフォーム送信"))

    # ── Active 配下のその他 ──────────────────────────────
    others = [
        ("工務店DXスイート(デモ)", "koumuten-dx-suite-demo", "商談用デモ・GitHub Pages で公開中"),
        ("採用パイプライン", "recruit-pipeline", "Indeed応募者の管理ボード・GitHub Pages で公開中"),
        ("AIツールポータル", "ai-tools-portal", "自社ツールの公開ショーケース"),
        ("会員アプリ(有料版)", "sinmido-tools-app", "契約者向けのログイン付きツール"),
        ("Website Analyzer", "website-analyzer", "GA4・Search Console の分析レポート"),
        ("StrengthsFinder 分析", "strengthsfinder-analyzer", "組織の強み分析"),
        ("倍増の設計図", "baizou-2026", "経営レポートとスライド"),
        ("人員配置 2026", "人員配置-2026", "Growth事業部の配置案"),
    ]
    for name, dirname, note in others:
        d = ACTIVE / dirname
        st = dir_stats(d)
        if not st:
            continue
        days = age_days(st["mtime"])
        projects.append({
            "name": name, "note": note, "dir": st, "git": git_stats(d),
            "days": days, "status": status_of(days), "metrics": [],
        })

    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "projects": projects,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT.name}: {len(projects)} プロジェクト")
    for pr in projects:
        d = pr["dir"]
        m = " / ".join(f"{x['label']} {x['value']:,}" for x in pr["metrics"]) or "-"
        print(f"  [{pr['status']:<7}] {pr['name']:<24} {d['size_mb']:>8.1f}MB "
              f"{d['files']:>6}files  {pr['days']}日前  {m}")
    return data


if __name__ == "__main__":
    build()
