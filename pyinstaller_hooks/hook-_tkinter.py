"""Hook local para coletar Tcl/Tk quando o hook padrao falha no ambiente."""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.building.datastruct import Tree


python_root = Path(sys.base_prefix)
tcl_root = python_root / "tcl" / "tcl8.6"
tk_root = python_root / "tcl" / "tk8.6"
tcl_modules_root = python_root / "tcl" / "tcl8"

def hook(hook_api):
    datas = []

    if tcl_root.is_dir():
        datas += Tree(str(tcl_root), prefix="tcl", excludes=["demos", "*.lib", "tclConfig.sh"])

    if tk_root.is_dir():
        datas += Tree(str(tk_root), prefix="tk", excludes=["demos", "*.lib", "tkConfig.sh"])

    if tcl_modules_root.is_dir():
        datas += Tree(str(tcl_modules_root), prefix="tcl8")

    hook_api.add_datas(datas)
