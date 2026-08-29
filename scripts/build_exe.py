"""一键打包脚本：前端构建 -> Chromium 安装 -> PyInstaller onedir -> 浏览器复制。

用法（项目根目录）：
    uv run python scripts/build_exe.py

产物：dist/WebAgent/WebAgent.exe（all-in-one，浏览器已内置）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
STAGING_BROWSERS = ROOT / "build_tmp" / "browsers"
DIST_APP = ROOT / "dist" / "WebAgent"


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print(f"\n>>> {' '.join(cmd)}")
    merged = os.environ | env if env else None
    # Windows 下 npm 为批处理脚本（npm.cmd），需经 shell 解析
    result = subprocess.run(cmd, cwd=cwd, env=merged, shell=os.name == "nt")
    if result.returncode != 0:
        sys.exit(f"步骤失败：{' '.join(cmd)}")


def main() -> None:
    # 1. 前端构建（零 Python 依赖，产物进 dist/）
    if not (FRONTEND / "node_modules").is_dir():
        run(["npm", "install"], cwd=FRONTEND)
    run(["npm", "run", "build"], cwd=FRONTEND)

    # 2. Chromium 安装到独立 staging 目录（不污染用户默认缓存）
    env = {"PLAYWRIGHT_BROWSERS_PATH": str(STAGING_BROWSERS)}
    run(["uv", "run", "playwright", "install", "chromium"], cwd=ROOT, env=env)

    # 3. PyInstaller 打包（onedir）
    run(["uv", "run", "pyinstaller", "webagent.spec", "--noconfirm", "--clean"], cwd=ROOT)

    # 4. 浏览器二进制随包分发
    target = DIST_APP / "browsers"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(STAGING_BROWSERS, target)

    print(f"\n打包完成：{DIST_APP / 'WebAgent.exe'}")
    print("提示：.env / data / logs / screenshots 会在首次运行时生成于 EXE 同目录。")


if __name__ == "__main__":
    main()
