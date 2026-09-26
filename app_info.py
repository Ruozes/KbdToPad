# -*- coding: utf-8 -*-
"""应用元信息（程序、PyInstaller 版本资源、Inno Setup 安装包共用同一份定义）。"""

APP_NAME = "键盘 → 虚拟手柄 映射工具"
APP_NAME_EN = "Keyboard to Virtual Gamepad Mapper"
APP_SHORT = "KbdToPad"
APP_VERSION = "0.1.1"
# 作者（GitHub 用户名）：exe 版本资源、安装包“发布者”与版权署名都用它
APP_AUTHOR = "Ruozes"
APP_PUBLISHER = APP_AUTHOR
APP_COPYRIGHT = f"Copyright (C) 2026 {APP_AUTHOR}"
APP_DESCRIPTION = "把全键盘任意按键映射为虚拟 Xbox 360 手柄的按键、扳机与左右摇杆方向。"
# 项目主页
APP_URL = "https://github.com/Ruozes/KbdToPad"
# 开发方式说明（本项目由 DeepSeek 辅助完成），启动时会写进 app.log
APP_DEV_NOTE = "本项目由 DeepSeek 辅助完成"
# 用户数据目录名（%APPDATA%\\<DATA_DIRNAME>）
DATA_DIRNAME = "KbdToPad"
# 主程序文件名（PyInstaller 输出名 / 安装后的可执行文件名）
APP_EXE_NAME = "KbdToPad"
