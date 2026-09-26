# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（通常通过 ``python build.py`` 调用）。

环境变量：
    KBD2PAD_ONEFILE=1   生成单文件 exe；
                        默认生成文件夹版（启动更快、杀软误报更少）。
"""

import os

from PyInstaller.utils.hooks import collect_all

APP_NAME = os.environ.get("KBD2PAD_APP_NAME", "KbdToPad")
ONE_FILE = os.environ.get("KBD2PAD_ONEFILE") == "1"
ICON = os.path.join("assets", "app.ico")
VERSION_FILE = os.path.join("assets", "version_info.txt")

# vgamepad 的 vigemclient DLL、keyboard 的平台后端、pystray 的 Windows 后端
# 都是运行时/动态加载的，collect_all 才能把它们完整收进来。
datas, binaries, hiddenimports = [], [], []
for package in ("vgamepad", "keyboard", "pystray"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# 程序运行时要用到的图标资源
datas += [("assets/app.ico", "assets")]

a = Analysis(
    ["kbd_to_pad.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 只用到 Pillow 的绘图功能，排除体积大且用不到的第三方库
    excludes=[
        "numpy", "scipy", "pandas", "matplotlib", "cv2", "PyQt5", "PyQt6",
        "PySide2", "PySide6", "wx", "PIL.ImageQt", "PIL.ImageShow",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if ONE_FILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON,
        version=VERSION_FILE,
        uac_admin=True,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON,
        version=VERSION_FILE,
        uac_admin=True,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name=APP_NAME,
    )
