# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for AID Medical Report Analysis System."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH)

# Collect all streamlit data and dependencies
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")
tornado_datas, tornado_binaries, tornado_hiddenimports = collect_all("tornado")
altair_datas, altair_binaries, altair_hiddenimports = collect_all("altair")
vega_datas, vega_binaries, vega_hiddenimports = collect_all("vega_datasets")

datas = []
datas += streamlit_datas
datas += tornado_datas
datas += altair_datas
datas += vega_datas
datas += [
    (str(project_root / "configs"), "configs"),
    (str(project_root / "src"), "aid"),
]

binaries = []
binaries += streamlit_binaries
binaries += tornado_binaries
binaries += altair_binaries
binaries += vega_binaries

hiddenimports = []
hiddenimports += streamlit_hiddenimports
hiddenimports += tornado_hiddenimports
hiddenimports += altair_hiddenimports
hiddenimports += vega_hiddenimports
hiddenimports += collect_submodules("charset_normalizer")
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("tornado")
hiddenimports += collect_submodules("altair")
hiddenimports += collect_submodules("vega_datasets")
hiddenimports += [
    "src",
    "src.main",
    "src.llm",
    "src.llm.client",
    "src.agent",
    "src.agent.base",
    "src.agent.react_agent",
    "src.tool",
    "src.tool.datetime_tool",
    "src.tool.search_tool",
    "src.tool.report_parser",
    "src.tool.location_tool",
    "src.tool.memory_tool",
    "src.ui",
    "src.ui.streamlit_app",
    "openai",
    "httpx",
    "httpx._transports",
    "httpx._transports.default",
    "h11",
    "langchain",
    "langchain_core",
    "pydantic",
    "yaml",
    "PIL",
    "dotenv",
    "tavily",
    "pytesseract",
    "charset_normalizer",
    "jsonschema",
    "jsonschema_specifications",
    "referencing",
    "referencing.jsonschema",
]

block_cipher = None

a = Analysis(
    [str(project_root / "src" / "main.py")],
    pathex=[str(project_root), str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
        "torchvision",
        "torchaudio",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AID",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.ico") if (project_root / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AID",
)
