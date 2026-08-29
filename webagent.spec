# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：all-in-one onedir 打包。

产物：dist/WebAgent/WebAgent.exe（浏览器二进制由 scripts/build_exe.py 复制到
dist/WebAgent/browsers/，运行时通过 PLAYWRIGHT_BROWSERS_PATH 定位）。
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).resolve()

# 前端静态资源随包分发；playwright/playwright_stealth 的资源文件由钩子收集
datas = [
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
]
datas += collect_data_files("playwright", include_py_files=False)
datas += collect_data_files("playwright_stealth", include_py_files=False)

hiddenimports = [
    "api.app",  # uvicorn 以字符串 "api.app:app" 导入，静态分析不可见
    # 以下包未被 desktop.py 静态导入，但运行时由字符串导入触发
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "sqlalchemy.dialects.sqlite",
    "pydantic_core._pydantic_core",
    "webview.winforms",
]

a = Analysis(
    ["api/desktop.py"],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "numpy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WebAgent",
    debug=False,
    console=False,  # 桌面 GUI 应用，不带控制台窗口
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="WebAgent",
)
