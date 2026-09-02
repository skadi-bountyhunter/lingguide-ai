# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir 配置；发布数据由 Electron resources 单独放置。"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("app") + [
    "aiosqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
]

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=collect_data_files("snownlp") + collect_data_files("jieba"),
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "chromadb",
        "sentence_transformers",
        "torch",
        "transformers",
        "numpy",
        "scipy",
        "sklearn",
        "pandas",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="lingguide-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="lingguide-backend",
)
