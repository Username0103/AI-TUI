# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('mdv')
datas += [(str(Path('config.toml').resolve()),  '.')]
datas += [(str(Path('.env').resolve()), '.')]
datas += [(str(Path('conversation_log.md').resolve()), '.')]


a = Analysis(
    ['main.py'],
    pathex=[],
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
        name='main',
        console=True,
        debug=False,
        upx=True,
)
