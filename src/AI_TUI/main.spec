# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import sys
from pathlib import Path

datas = collect_data_files('mdv')
datas.append(('./tools/tools.json', 'tools'))

def get_project_root(root: "Path", target_folder="src") -> Path:
    """this is copy pasted from main.py. sorry not sorry"""
    i = 0
    if root.name == target_folder:
        return root.parent if root.parent else root
    for parent in root.parents:
        i += 1
        if i > 4:
            break
        if parent.name == target_folder:
            return parent.parent if parent.parent else parent  # lol
    return root

# __file__ doesn't work for some reason so i need to use cwd
spec_folder = Path.cwd()
root = Path(spec_folder).resolve()
home = get_project_root(root)
source = home / "src"


if sys.platform == "win32":
    icon = f"{home}/icon.ico"
else:
    icon = f"{home}/icon.png"

a = Analysis(
    [home/"src"/"AI_TUI"/"entry.py"],
    pathex=[home, source],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='AI-TUI',
        icon=icon,
        console=True,
        debug=False,
        upx=True,
)
