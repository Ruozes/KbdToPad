#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键构建脚本：生成图标 → PyInstaller 打包 exe →（可选）编译 Inno Setup 安装包。

用法示例::

    python build.py                  # 文件夹版 exe + 安装包（默认，推荐）
    python build.py --onefile        # 单文件 exe + 安装包
    python build.py --no-installer   # 只打包 exe
    python build.py --icons-only     # 只重新生成 assets 下的图标
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import app_info        # noqa: E402
import icon_art        # noqa: E402

ASSETS_DIR = os.path.join(ROOT, "assets")
INSTALLER_DIR = os.path.join(ROOT, "installer")
VENDOR_DIR = os.path.join(INSTALLER_DIR, "vendor")
ISS_PATH = os.path.join(INSTALLER_DIR, "KbdToPad.iss")
DEFINES_PATH = os.path.join(INSTALLER_DIR, "build_defines.iss")
VERSION_INFO = os.path.join(ASSETS_DIR, "version_info.txt")

# 这些"环境"会随安装包一起分发：ViGEmBus 驱动 + VC++ 运行库 + 中文安装界面
VIGEMBUS_API = "https://api.github.com/repos/nefarius/ViGEmBus/releases/latest"
VIGEMBUS_FALLBACK = (
    "https://github.com/nefarius/ViGEmBus/releases/download/"
    "v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe"
)
VCREDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
CHINESE_ISL_URLS = (
    # 官方仓库主分支（inno 6.5+ 起简体中文已并入 Files/Languages 目录）
    "https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/"
    "Languages/ChineseSimplified.isl",
    # 同上，走 jsDelivr CDN（raw.githubusercontent 偶有连接重置）
    "https://cdn.jsdelivr.net/gh/jrsoftware/issrc@main/Files/"
    "Languages/ChineseSimplified.isl",
    # 该语言文件的维护者仓库，作为最后兜底
    "https://raw.githubusercontent.com/kira-96/"
    "Inno-Setup-Chinese-Simplified-Translation/master/ChineseSimplified.isl",
)
USER_AGENT = "KbdToPad-Build"

VERSION_INFO_TEMPLATE = '''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({a}, {b}, {c}, {d}), prodvers=({a}, {b}, {c}, {d}),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('080404B0', [
        StringStruct('CompanyName', '{publisher}'),
        StringStruct('FileDescription', '{description}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{exe}'),
        StringStruct('LegalCopyright', '{copyright}'),
        StringStruct('OriginalFilename', '{exe}.exe'),
        StringStruct('ProductName', '{name}'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
'''


def say(message):
    """打印构建进度。

    注意：控制台编码可能是 GBK，某些符号（如 ✔）无法编码，因此这里做一次
    降级替换，避免因为一行日志让整个构建失败。
    """
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = (getattr(sys.stdout, "encoding", None) or "utf-8")
        print(message.encode(encoding, "replace").decode(encoding, "replace"),
              flush=True)


def run(cmd, **kwargs):
    say("$ " + " ".join(cmd))
    kwargs.setdefault("cwd", ROOT)
    return subprocess.run(cmd, check=True, **kwargs)


def write_defines(definitions):
    """把构建参数写成 ISPP 定义文件（UTF-8 BOM）。

    为什么不直接用 ISCC 的 /D：程序名与项目路径含中文和空格，命令行参数在不同
    终端下会出现编码、引号解析问题（值被空格拆成多个参数等），写文件最稳，
    而且在 Inno Setup IDE 里直接编译时也能复用同一份参数。
    """
    lines = [
        "; 本文件由 build.py 自动生成，请勿手工修改。",
        "; 传入 Inno Setup 的构建参数（UTF-8 BOM 编码，避免中文乱码）。",
    ]
    for name, value in definitions:
        lines.append('#define {0} "{1}"'.format(name, str(value).replace('"', "")))
    with open(DEFINES_PATH, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    say(f"   构建参数：{os.path.relpath(DEFINES_PATH, ROOT)}")


def ensure_bom(path):
    """确保 .iss 为 UTF-8 BOM（Inno Setup 需要 BOM 才能正确识别中文）。"""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"\xef\xbb\xbf"):
        with open(path, "wb") as f:
            f.write(b"\xef\xbb\xbf" + data)
        say(f"已为 {os.path.basename(path)} 添加 UTF-8 BOM")


def download(url, dest, label):
    """下载文件（已存在且非空则跳过）。"""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        say(f"已存在，跳过下载：{os.path.relpath(dest, ROOT)}")
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    say(f"正在下载 {label} …")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=180) as response:
            with open(dest, "wb") as f:
                shutil.copyfileobj(response, f)
    except Exception as e:
        say(f"  下载失败：{e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False
    size = os.path.getsize(dest) / 1048576
    say(f"  完成：{os.path.relpath(dest, ROOT)}（{size:.1f} MB）")
    return True


def vigembus_url():
    """查询 ViGEmBus 最新版安装包地址，失败时退回内置地址。"""
    try:
        request = urllib.request.Request(
            VIGEMBUS_API,
            headers={"User-Agent": USER_AGENT,
                     "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
        for asset in data.get("assets", []):
            name = asset.get("name", "").lower()
            if name.startswith("vigembus") and name.endswith(".exe"):
                return asset["browser_download_url"], data.get("tag_name", "unknown")
    except Exception as e:
        say(f"  查询 ViGEmBus 最新版本失败（改用内置地址）：{e}")
    return VIGEMBUS_FALLBACK, "v1.22.0"


def looks_like_isl(path):
    """粗略校验下载到的确实是 Inno Setup 语言文件而不是错误页面。"""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            head = f.read(4096)
        return "LangOptions" in head or "LanguageName" in head
    except OSError:
        return False


def make_resources():
    """生成图标资源与 exe 属性里显示的版本信息。"""
    say("① 生成图标与版本资源 …")
    for path in icon_art.save_all():
        say(f"   图标：{os.path.relpath(path, ROOT)}")

    parts = [int(p) if p.isdigit() else 0 for p in app_info.APP_VERSION.split(".")]
    parts += [0] * (4 - len(parts))
    content = VERSION_INFO_TEMPLATE.format(
        a=parts[0], b=parts[1], c=parts[2], d=parts[3],
        version=app_info.APP_VERSION,
        name=app_info.APP_NAME,
        description=app_info.APP_DESCRIPTION,
        publisher=app_info.APP_PUBLISHER,
        copyright=app_info.APP_COPYRIGHT,
        exe=app_info.APP_EXE_NAME,
    )
    with open(VERSION_INFO, "w", encoding="utf-8") as f:
        f.write(content)
    say(f"   版本信息：{os.path.relpath(VERSION_INFO, ROOT)}")


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        say("未检测到 PyInstaller，正在安装 …")
        run([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"])


def build_exe(onefile):
    say("② 打包 exe（PyInstaller）…")
    env = dict(os.environ)
    env["KBD2PAD_ONEFILE"] = "1" if onefile else "0"
    env["KBD2PAD_APP_NAME"] = app_info.APP_EXE_NAME
    run([sys.executable, "-m", "PyInstaller", "--noconfirm",
         "--distpath", "dist", "--workpath", "build", "KbdToPad.spec"], env=env)

    if onefile:
        exe = os.path.join(ROOT, "dist", app_info.APP_EXE_NAME + ".exe")
    else:
        exe = os.path.join(ROOT, "dist", app_info.APP_EXE_NAME,
                           app_info.APP_EXE_NAME + ".exe")
    if not os.path.exists(exe):
        raise SystemExit(f"打包失败：未找到 {exe}")
    say(f"   exe：{os.path.relpath(exe, ROOT)}")
    return exe


def fetch_vendor_files(with_vcredist=True, with_isl=True):
    """下载随安装包分发的依赖：ViGEmBus 驱动、VC++ 运行库、中文语言文件。"""
    say("③ 准备随包分发的依赖 …")
    url, tag = vigembus_url()
    say(f"   ViGEmBus 版本：{tag}")
    download(url, os.path.join(VENDOR_DIR, "ViGEmBusSetup.exe"), "ViGEmBus 驱动")

    if with_vcredist:
        download(VCREDIST_URL, os.path.join(VENDOR_DIR, "VC_redist.x64.exe"),
                 "VC++ 2015-2022 运行库")

    if with_isl:
        dest = os.path.join(VENDOR_DIR, "ChineseSimplified.isl")
        if os.path.exists(dest) and not looks_like_isl(dest):
            os.remove(dest)
        for url in CHINESE_ISL_URLS:
            if download(url, dest, "Inno Setup 中文语言文件") and looks_like_isl(dest):
                break
            if os.path.exists(dest):
                os.remove(dest)
        else:
            say("   未能获取 Inno Setup 中文语言文件，安装界面将使用英文。")


def find_iscc():
    """定位 Inno Setup 的命令行编译器。"""
    found = shutil.which("iscc") or shutil.which("ISCC.exe")
    if found:
        return found
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                     "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""),
                     "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""),
                     "Inno Setup 6", "ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def build_installer(exe_path, onefile):
    say("④ 编译安装包（Inno Setup）…")
    iscc = find_iscc()
    if not iscc:
        say("   未找到 Inno Setup 的 ISCC.exe，跳过安装包构建。")
        say("   安装命令：winget install -e --id JRSoftware.InnoSetup")
        return None
    if not os.path.isfile(ISS_PATH):
        say(f"   未找到安装脚本：{ISS_PATH}")
        return None

    ensure_bom(ISS_PATH)
    dist_source = exe_path if onefile else os.path.dirname(exe_path)
    if not onefile:
        dist_source = os.path.join(dist_source, "*")
    # 源目录用相对 installer 目录的路径，避免把含中文的项目路径写进安装脚本
    write_defines([
        ("AppName", app_info.APP_NAME),
        ("AppVersion", app_info.APP_VERSION),
        ("AppPublisher", app_info.APP_PUBLISHER),
        ("ExeName", app_info.APP_EXE_NAME + ".exe"),
        ("DistSource", os.path.relpath(dist_source, INSTALLER_DIR)),
    ])
    run([iscc, "KbdToPad.iss"], cwd=INSTALLER_DIR)

    output = os.path.join(INSTALLER_DIR, "Output",
                          f"KbdToPad-Setup-{app_info.APP_VERSION}.exe")
    if os.path.exists(output):
        size = os.path.getsize(output) / 1048576
        say(f"   安装包：{os.path.relpath(output, ROOT)}（{size:.1f} MB）")
        return output
    say("   安装包未生成，请查看上面的编译日志。")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="构建 KbdToPad 的独立 exe 与安装包"
    )
    parser.add_argument("--onefile", action="store_true",
                        help="生成单文件 exe（启动稍慢，默认是文件夹版）")
    parser.add_argument("--icons-only", action="store_true",
                        help="只重新生成 assets 下的图标资源")
    parser.add_argument("--no-installer", action="store_true",
                        help="只打包 exe，不构建安装包")
    parser.add_argument("--no-download", action="store_true",
                        help="不联网下载 ViGEmBus / VC++ 运行库")
    parser.add_argument("--skip-vcredist", action="store_true",
                        help="安装包中不附带 VC++ 运行库")
    args = parser.parse_args()

    make_resources()
    if args.icons_only:
        say("图标资源已更新，退出。")
        return 0

    ensure_pyinstaller()
    exe = build_exe(args.onefile)

    if args.no_installer:
        say(f"\n构建完成（已跳过安装包）  exe：{os.path.relpath(exe, ROOT)}")
        return 0

    if not args.no_download:
        fetch_vendor_files(with_vcredist=not args.skip_vcredist)
    build_installer(exe, args.onefile)

    say("\n构建完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())


