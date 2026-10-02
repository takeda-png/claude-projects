# -*- coding: utf-8 -*-
"""このPCの表示名を決める。

優先順: .pc_name ファイル（1行・git管理外） → 環境変数 COMPUTERNAME
ファイル名にも使うので英数字・ハイフン・アンダースコアだけにする。
"""
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent


def pc_name():
    f = BASE / ".pc_name"
    name = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    name = name or os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "PC"
    name = re.sub(r"[^A-Za-z0-9_-]", "", name)[:30]
    return name or "PC"
