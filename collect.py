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
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from pcname import pc_name  # noqa: E402

PC = pc_name()
# PCごとに別ファイル。複数のPCが同時に push してもぶつからない。
OUT = BASE / "sources" / f"{PC}.json"

# 走査から外す（容量・件数を膨らませるだけで意味がない）
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv",
             "ms-playwright", ".playwright-mcp", "dist", "build"}


def find_roots():
    """プロジェクトが置かれている親ディレクトリを探す。

    2台のPCでレイアウトが違う（片方は ~/Desktop/_Projects/Active、もう片方は
    OneDrive 配下の深い場所）。公開リポジトリに実パスを書けないので決め打ちせず、
    `_Projects/Active` を実際に探して当てる。
    """
    roots, seen = [], []

    def add(q):
        if q and q.is_dir() and str(q) not in seen:
            seen.append(str(q))
            roots.append(q)

    bases = [HOME] + sorted(HOME.glob("OneDrive*"))
    for b in bases:
        add(b / "Desktop" / "_Projects" / "Active")
        add(b / "デスクトップ" / "_Projects" / "Active")

    if not roots:   # OneDrive の日本語フォルダ対策。深さを限って探す
        for b in bases:
            if not b.is_dir():
                continue
            base_depth = len(b.parts)
            for root, dirs, _ in os.walk(b):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                if len(Path(root).parts) - base_depth >= 6:
                    dirs[:] = []
                    continue
                if os.path.basename(root) == "Active" and                         os.path.basename(os.path.dirname(root)) == "_Projects":
                    add(Path(root))
                    dirs[:] = []
    add(HOME)       # ホーム直下に置いている構成もある
    return roots


ROOTS = find_roots()


def locate(*names):
    """候補名を探し、**中身のある**パスを返す。

    PCごとにディレクトリ名が違う（sinmido / sinmido-wordpress-ai）ので別名を許す。
    移動前の古いルートに空の殻が残っていることがあるので、
    最初に見つかったものではなく「ファイル数が最も多い」候補を採る。
    """
    best, best_n = None, -1
    for n in names:
        for r in ROOTS:
            d = r / n
            if not d.is_dir():
                continue
            try:
                cnt = sum(1 for _ in d.rglob("*"))
            except OSError:
                cnt = 0
            if cnt > best_n:
                best, best_n = d, cnt
    return best if best_n > 0 else None


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
    d = locate(*(dirname if isinstance(dirname, (list, tuple)) else [dirname]))
    st = dir_stats(d) if d else None
    # 片方のPCには空の殻だけ残っていることがある。companies.csv が無ければ
    # 0件で上書きしないよう、このPCでは測らない扱いにする。
    if not st or not st["files"] or not (d / "companies.csv").exists():
        return None  # このPCには無い
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

    def posts(d):
        return [
            {"label": "投稿ログ", "value": count_glob(d, "post_result_*.json")},
            {"label": "記事JSON", "value": count_glob(d, "article_*.json")},
        ]

    def add(name, names, note, metrics_fn=None):
        d = locate(*names)
        st = dir_stats(d) if d else None
        if not st or not st["files"]:
            return                       # このPCには無い / 空の殻
        days = age_days(st["mtime"])
        projects.append({
            "name": name, "note": note, "dir": st, "git": git_stats(d),
            "days": days, "status": status_of(days),
            "metrics": metrics_fn(d) if metrics_fn else [],
        })

    # ── WordPress 自動投稿 ──────────────────────────────
    add("WordPress Webmaster AI", ["sinmido", "sinmido-wordpress-ai"],
        "sinmido.com の記事生成・自動投稿", posts)
    add("リクルート自動コラム", ["sinmido-recruit"],
        "sinmido-recruit.com のコラム生成・投稿", posts)

    # ── 営業パイプライン ────────────────────────────────
    for name, names, note in [
        ("埼玉フォーム営業", ["form-automation-saitama"], "埼玉県内企業へのフォーム送信"),
        ("SCOPE営業", ["form-automation"], "HP制作会社・IT企業へのフォーム送信"),
        ("全国工務店営業", ["form-automation-national"], "全国の工務店へのフォーム送信"),
        ("SCOPEパートナー募集", ["form-automation-scope"],
         "制作会社へのパートナー募集・送付IDで申込元を判別"),
        ("製造業SCOPE先出し", ["form-automation-scope-mfg"],
         "北関東の中小製造業へ反響レポートを先出し"),
        ("工務店AIO診断", ["form-automation-koumuten-aio"],
         "全国工務店へAI検索の無料診断を案内"),
    ]:
        projects.append(pipeline(name, names, note))

    # ── その他 ─────────────────────────────────────────
    others = [
        ("工務店DXスイート(デモ)", ["koumuten-dx-suite-demo"], "商談用デモ・GitHub Pages で公開中"),
        ("採用パイプライン", ["recruit-pipeline"], "Indeed応募者の管理ボード・GitHub Pages で公開中"),
        ("AIツールポータル", ["ai-tools-portal"], "自社ツールの公開ショーケース"),
        ("会員アプリ(有料版)", ["sinmido-tools-app"], "契約者向けのログイン付きツール"),
        ("Website Analyzer", ["website-analyzer"], "GA4・Search Console の分析レポート"),
        ("StrengthsFinder 分析", ["strengthsfinder-analyzer"], "組織の強み分析"),
        ("倍増の設計図", ["baizou-2026"], "経営レポートとスライド"),
        ("人員配置 2026", ["人員配置-2026"], "Growth事業部の配置案"),
        ("ウェビナー資料生成", ["webinar-analyzer"], "GA4・SCの分析からウェビナー資料を生成"),
        ("採用コラム静的フロント", ["sinmido-recruitment-columns"], "採用コラムのHTMLフロント"),
        ("招待状送信ツール", ["invitation-sender"], "イベント招待の一括送信"),
        ("Meta広告アナリティクス", ["meta-ads-analytics"], "Meta広告の実績集計"),
        ("プロジェクト状況ページ", ["claude-projects"], "このページ自体の生成スクリプト"),
    ]
    for name, names, note in others:
        add(name, names, note)

    projects = [x for x in projects if x]
    for x in projects:
        x["pc"] = PC
    data = {
        "pc": PC,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "projects": projects,
    }
    OUT.parent.mkdir(exist_ok=True)
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
