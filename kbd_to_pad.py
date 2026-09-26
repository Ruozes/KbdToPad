#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
键盘按键 → 虚拟手柄按键 映射工具

适用于 Windows 掌机（如 AYANEO FLIP）：把掌机自定义键输出的键盘信号
转换为虚拟 Xbox 360 手柄按键。

键盘侧支持全键盘任意按键（点「⌨ 捕获」直接按下目标键即可录入）；手柄侧
除常规按键与 LT/RT 扳机外，还支持左右摇杆的上下左右四个方向，按下时该轴
推到满值，松开后回到居中。

注意：keyboard 库按“键名”识别按键，小键盘数字键报告的名字与主键盘相同
（例如小键盘 5 → "5"），映射时填该名字即可，无法与主键盘区分。

依赖（直接运行源码时）：
    pip install -r requirements.txt
    并安装 ViGEmBus 驱动：https://github.com/nefarius/ViGEmBus/releases

打包为 exe 后无需本机 Python 环境，安装程序会自动安装 ViGEmBus 驱动与
VC++ 运行库。程序需要管理员权限（keyboard 库在无管理员权限时无法捕获
游戏前台的按键），exe 清单已声明 requireAdministrator。
"""

import argparse
import ctypes
import json
import os
import shutil
import sys
import threading
import time
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

import app_info
import icon_art

# ---------- 基础路径 / 日志 ----------

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    """返回打包资源（如 assets/app.ico）的真实路径，兼容 PyInstaller 模式。"""
    base = getattr(sys, "_MEIPASS", None) or _APP_DIR
    return os.path.join(base, *parts)


def data_dir():
    """用户数据目录。

    打包后写入 ``%APPDATA%\\KbdToPad``（exe 通常被安装到 Program Files 下，
    同目录没有写权限）；直接运行源码时仍使用脚本所在目录，便于调试。
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, app_info.DATA_DIRNAME)
    else:
        path = _APP_DIR
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_FILE = os.path.join(data_dir(), "config.json")
LOG_FILE = os.path.join(data_dir(), "app.log")
LOG_MAX_BYTES = 256 * 1024

_log_lock = threading.Lock()


def log(message):
    """输出日志：有控制台就打印，同时写入日志文件（打包后没有控制台）。"""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    if sys.stdout is not None:
        try:
            print(line)
        except Exception:
            pass
    try:
        with _log_lock:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
                os.replace(LOG_FILE, LOG_FILE + ".1")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


def splash_error(title, message):
    """弹窗报错并写日志（打包版没有控制台，用户只能靠弹窗/日志）。"""
    log(f"{title}: {message}")
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass


def _missing_dependency(name, hint):
    splash_error(
        app_info.APP_NAME,
        f"缺少 {name} 库。\n\n{hint}\n\n如果使用的是打包版本，请重新安装本程序。",
    )
    sys.exit(1)


# ---------- 依赖导入 ----------
try:
    import keyboard
except ImportError:
    _missing_dependency("keyboard", "源码运行请执行：pip install keyboard")

try:
    import vgamepad as vg
except ImportError:
    _missing_dependency(
        "vgamepad",
        "源码运行请执行：pip install vgamepad\n"
        "并安装 ViGEmBus 驱动：https://github.com/nefarius/ViGEmBus/releases",
    )

try:
    from PIL import Image
    import pystray
except ImportError:
    _missing_dependency("pystray / Pillow", "源码运行请执行：pip install pystray Pillow")


# ---------- 常量 ----------

GAMEPAD_BUTTON_MAP = {
    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "Back": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "Start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "D-Pad Up": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "D-Pad Down": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "D-Pad Left": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "D-Pad Right": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    "LT": "__LT_TRIGGER__",
    "RT": "__RT_TRIGGER__",
}

# 摇杆方向映射：手柄目标名 -> (摇杆, 轴, 方向)
#   方向 +1 / -1 表示把该轴推到正向 / 反向满值；同一轴上的多个方向键同时按下时，
#   取正向优先（例如同时按下「LS 左」与「LS 右」时 X 轴为满值正方向）。
STICK_DIRECTIONS = {
    "LS Up": ("left", "y", 1),
    "LS Down": ("left", "y", -1),
    "LS Left": ("left", "x", -1),
    "LS Right": ("left", "x", 1),
    "RS Up": ("right", "y", 1),
    "RS Down": ("right", "y", -1),
    "RS Left": ("right", "x", -1),
    "RS Right": ("right", "x", 1),
}

# 摇杆轴满值（XInput 范围为 -32768..32767）与扳机满值
STICK_AXIS_MAX = 32767
TRIGGER_MAX = 255

# 手柄目标下拉列表（顺序即界面展示顺序）
GAMEPAD_TARGETS = (
    ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "Back", "Start", "LS", "RS",
     "D-Pad Up", "D-Pad Down", "D-Pad Left", "D-Pad Right"]
    + list(STICK_DIRECTIONS)
)

MUTEX_NAME = "Local\\" + app_info.APP_SHORT + "_SingleInstance"
ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


# ---------- 工具函数 ----------

def window_title():
    """窗口标题（同时用于查找已运行实例的窗口）。"""
    return f"{app_info.APP_NAME} v{app_info.APP_VERSION}"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def acquire_single_instance():
    """用命名互斥体防止重复启动。

    返回互斥体句柄；若已有实例在运行则返回 None。
    """
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p
        ]
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not handle or ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            return None
        return handle
    except Exception as e:
        log(f"单实例检查失败（忽略并继续启动）：{e}")
        return 1


def focus_existing_window():
    """把已在运行的窗口恢复到前台。"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, window_title())
        if hwnd:
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        log(f"激活已有窗口失败：{e}")
    return False


def migrate_legacy_config():
    """旧版本把 config.json 放在 exe 同目录，这里做一次性搬家。"""
    if not getattr(sys, "frozen", False) or os.path.exists(CONFIG_FILE):
        return
    legacy = os.path.join(
        os.path.dirname(os.path.abspath(sys.executable)), "config.json"
    )
    if not os.path.exists(legacy):
        return
    try:
        shutil.copyfile(legacy, CONFIG_FILE)
        log(f"已从 exe 目录迁移旧配置：{legacy}")
    except OSError as e:
        log(f"迁移旧配置失败：{e}")


# ---------- 键盘按键目录 ----------

# 分组只用于排序，键名统一使用 keyboard 库的小写规范名（即事件里的 e.name）。
# 允许用别名书写键名（ESCAPE、PrtScn、VolUp…），normalize_key_name 会统一成规范名。
KEY_GROUPS = (
    ("字母", [chr(c) for c in range(ord("a"), ord("z") + 1)]),
    ("数字（主键盘与小键盘同名）", [str(d) for d in range(10)]),
    ("符号", ["`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/", "space"]),
    ("功能键", [f"f{i}" for i in range(1, 25)]),
    ("控制键 / 编辑键", [
        "esc", "tab", "caps lock", "enter", "backspace", "insert", "delete",
        "home", "end", "page up", "page down", "print screen", "pause",
        "menu", "scroll lock", "num lock", "clear",
    ]),
    ("方向键", ["up", "down", "left", "right"]),
    ("修饰键", [
        "shift", "left shift", "right shift",
        "ctrl", "left ctrl", "right ctrl",
        "alt", "left alt", "right alt", "alt gr",
        "windows", "left windows", "right windows",
    ]),
    ("小键盘符号", ["decimal", "num +", "num -", "num *", "num /"]),
    ("多媒体 / 系统键", [
        "volume up", "volume down", "volume mute",
        "next track", "previous track", "stop media", "play/pause media",
        "select media", "start mail",
        "browser back", "browser forward", "browser refresh", "browser stop",
        "browser favorites", "browser start and home",
        "start application 1", "start application 2", "sleep",
    ]),
)

# 键名的中文 / 易读显示（列表仍使用规范键名，避免配置里出现中文）
KEY_LABELS = {
    "space": "空格", "esc": "Esc", "tab": "Tab", "enter": "回车",
    "backspace": "退格", "caps lock": "Caps Lock", "menu": "菜单键",
    "print screen": "Print Screen", "scroll lock": "Scroll Lock",
    "num lock": "Num Lock", "pause": "Pause", "clear": "Clear",
    "insert": "Insert", "delete": "Delete", "home": "Home", "end": "End",
    "page up": "Page Up", "page down": "Page Down",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "shift": "Shift", "left shift": "左 Shift", "right shift": "右 Shift",
    "ctrl": "Ctrl", "left ctrl": "左 Ctrl", "right ctrl": "右 Ctrl",
    "alt": "Alt", "left alt": "左 Alt", "right alt": "右 Alt",
    "alt gr": "Alt Gr", "windows": "Win", "left windows": "左 Win",
    "right windows": "右 Win",
    "volume up": "音量 +", "volume down": "音量 −", "volume mute": "静音",
    "next track": "下一曲", "previous track": "上一曲", "stop media": "停止播放",
    "play/pause media": "播放 / 暂停", "select media": "媒体选择",
    "start mail": "邮件", "browser back": "浏览器后退",
    "browser forward": "浏览器前进", "browser refresh": "浏览器刷新",
    "browser stop": "浏览器停止", "browser favorites": "浏览器收藏夹",
    "browser start and home": "浏览器主页", "start application 1": "启动应用 1",
    "start application 2": "启动应用 2", "sleep": "睡眠",
    "decimal": "小键盘 .",
}

_key_names_cache = None


def is_known_key(name):
    """判断 keyboard 库是否认识该键名（用于校验手输键名与配置文件）。"""
    if not name:
        return False
    try:
        return bool(keyboard.key_to_scan_codes(name, error_if_missing=False))
    except Exception:
        return False


def normalize_key_name(name):
    """把键名统一成 keyboard 库的规范写法。

    支持大小写与常见别名（ESCAPE → esc、PrtScn → print screen、VolUp → volume up），
    单字符键名（字母 / 符号）只做小写化。
    """
    text = (name or "").strip()
    if not text:
        return ""
    if len(text) == 1:
        return text.lower()
    try:
        return keyboard.normalize_name(text)
    except Exception:
        return text.lower()


def key_label(name):
    """键名的界面显示文本，例如 f13 → F13、volume up → 音量 +。"""
    text = normalize_key_name(name)
    if not text:
        return ""
    if text in KEY_LABELS:
        return KEY_LABELS[text]
    if len(text) == 1:
        return text.upper()
    if text[0] == "f" and text[1:].isdigit():
        return text.upper()
    return text


def all_key_names():
    """全部可映射键名（按分组顺序展开；首次调用时生成并缓存）。"""
    global _key_names_cache
    if _key_names_cache is None:
        names = []
        for _, group in KEY_GROUPS:
            names.extend(name for name in group if is_known_key(name))
        _key_names_cache = names
    return _key_names_cache


# ---------- 按键捕获对话框 ----------

class KeyCaptureDialog(tk.Toplevel):
    """“按下任意键”捕获对话框。

    打开期间临时挂一个 keyboard 钩子，捕获到第一个“按下”事件后回显并关闭；
    `show()` 返回该按键在 keyboard 库中的规范键名，取消时返回 None。
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.result = None
        self.hook_id = None

        self.title("按键捕获")
        self.resizable(False, False)
        self.transient(parent)

        body = ttk.Frame(self, padding=(18, 16, 18, 10))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="请按下要映射的键盘按键…",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.key_var = tk.StringVar(value="等待按键…")
        ttk.Label(body, textvariable=self.key_var, font=("Consolas", 11),
                  foreground="#1E5FA8").pack(anchor="w", pady=(10, 6))
        ttk.Label(
            body,
            text="提示：键盘上任意按键都能捕获（含 Esc、音量键、多媒体键）。\n"
                 "Esc 会被当成要映射的按键，要放弃请点下面的「取消」。",
            style="Hint.TLabel", wraplength=330, justify="left",
        ).pack(anchor="w")

        buttons = ttk.Frame(self, padding=(18, 0, 18, 14))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="取消", width=10,
                   command=self._cancel).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    # ---------- 显示 / 关闭 ----------
    def show(self):
        """模态显示并等待结果：返回捕获到的键名，取消返回 None。"""
        self._center()
        self.app.begin_capture()
        try:
            try:
                self.grab_set()
            except Exception as e:
                log(f"设置模态抓取失败（继续捕获）：{e}")
            try:
                self.hook_id = keyboard.hook(self._on_event)
            except Exception as e:
                log(f"按键捕获失败：{e}")
                messagebox.showerror("按键捕获", f"无法监听键盘：\n{e}", parent=self)
                return None
            self.wait_window(self)
        finally:
            self._unhook()
            self.app.end_capture()
        return self.result

    def _center(self):
        """把对话框大致居中显示在主窗口上。"""
        self.update_idletasks()
        try:
            parent = self.master
            x = parent.winfo_rootx() + max(
                0, (parent.winfo_width() - self.winfo_width()) // 2
            )
            y = parent.winfo_rooty() + max(
                0, (parent.winfo_height() - self.winfo_height()) // 3
            )
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _unhook(self):
        if self.hook_id is None:
            return
        try:
            keyboard.unhook(self.hook_id)
        except Exception:
            pass
        self.hook_id = None

    # ---------- 捕获 ----------
    def _on_event(self, event):
        """keyboard 钩子回调（运行在监听线程），只取“按下”事件。"""
        if self.result is not None:
            return
        if getattr(event, "event_type", None) != "down":
            return
        name = normalize_key_name(getattr(event, "name", "") or "")
        if not name:
            return
        self.result = name
        # 切回 Tk 主线程显示结果并关闭（在钩子线程里直接操作窗口不安全）
        try:
            self.after(0, self._preview_then_close)
        except Exception:
            pass

    def _preview_then_close(self):
        """先在对话框里回显捕获到的键名，稍等一下再关闭，便于用户确认。"""
        try:
            self.key_var.set(f"{key_label(self.result)}（键名：{self.result}）")
        except Exception:
            pass
        self.after(420, self._finish)

    def _finish(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _cancel(self):
        self.result = None
        self._finish()


# ---------- 主应用 ----------

class GamepadMapperApp:
    """主窗口、映射逻辑与系统托盘的组合体。"""

    def __init__(self, root, start_hidden=False, auto_listen=False):
        self.root = root
        self.root.title(window_title())
        self.root.geometry("660x600")
        self.root.minsize(600, 440)
        self._apply_window_icon()

        # 创建虚拟手柄（依赖 ViGEmBus 驱动）
        try:
            self.pad = vg.VX360Gamepad()
        except Exception as e:
            log(f"创建虚拟手柄失败：{e}")
            messagebox.showerror(
                "错误",
                f"创建虚拟手柄失败：\n{e}\n\n"
                "请确认已安装 ViGEmBus 驱动。\n"
                "下载地址：https://github.com/nefarius/ViGEmBus/releases"
            )
            sys.exit(1)

        self.listening = False
        self.hook_id = None
        self.mappings = {}          # 键名 -> 手柄目标名（按键 / 扳机 / 摇杆方向）
        self.row_widgets = []       # [(row_frame, key_combo, btn_combo, key_hint), ...]
        # 摇杆各轴当前被按下的方向集合：{(摇杆, 轴): {+1 / -1, ...}}
        self.stick_pressed = {
            (stick, axis): set() for stick, axis, _ in STICK_DIRECTIONS.values()
        }
        self._capturing = False     # 按键捕获对话框打开期间暂停映射动作
        self.tray_icon = None
        self._tray_hint_shown = False

        self._build_ui()
        migrate_legacy_config()
        self._load_config()
        self._setup_tray()
        self._refresh_state_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        # 开机自启场景：直接缩到托盘，必要时立即开始监听
        if start_hidden:
            self.hide_to_tray(show_hint=False)
        if auto_listen:
            self.root.after(300, self.start_listening)

        log(
            f"程序启动完成（版本 {app_info.APP_VERSION}，管理员={is_admin()}，"
            f"隐藏启动={start_hidden}，自动监听={auto_listen}）"
        )
        log(f"{app_info.APP_NAME} · {app_info.APP_DEV_NOTE}")

    def _apply_window_icon(self):
        """设置窗口 / 任务栏图标（使用 assets 中的多尺寸 .ico）。"""
        try:
            self.root.iconbitmap(default=icon_art.ensure_ico_file())
        except Exception as e:
            log(f"设置窗口图标失败：{e}")

    # ---------- UI ----------
    def _build_ui(self):
        style = ttk.Style(self.root)
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Hint.TLabel", foreground="#5A6474")
        style.configure("Status.TLabel", foreground="#3F4856")
        style.configure(
            "StatusOn.TLabel", foreground="#1E8E4A", font=("Segoe UI", 9, "bold")
        )

        # 顶部标题
        header = ttk.Frame(self.root, padding=(14, 12, 14, 0))
        header.pack(fill="x")
        ttk.Label(
            header, text="键盘按键  →  虚拟手柄按键", style="Title.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="键盘按键支持全键盘任意键（点「⌨ 捕获」按下目标键即可录入）；"
                 "手柄目标含按键、扳机与左右摇杆四个方向。",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        ttk.Separator(self.root, orient="horizontal").pack(
            fill="x", padx=14, pady=(10, 0)
        )

        # 工具栏
        toolbar = ttk.Frame(self.root, padding=(14, 10, 14, 6))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="＋ 添加映射",
                   command=self.add_mapping_row).pack(side="left")
        ttk.Button(toolbar, text="⌨ 按任意键添加",
                   command=self.add_mapping_with_capture).pack(side="left", padx=6)
        ttk.Button(toolbar, text="保存配置",
                   command=self.save_config).pack(side="left")
        ttk.Button(toolbar, text="清空全部",
                   command=self.clear_all).pack(side="left", padx=6)
        ttk.Button(toolbar, text="隐藏到托盘",
                   command=self.hide_to_tray).pack(side="right")

        # 列表头
        list_header = ttk.Frame(self.root, padding=(18, 0, 18, 2))
        list_header.pack(fill="x")
        # 与下面的行保持同样的控件宽度顺序：键名 / 捕获按钮占位 / 含义 / 箭头 / 目标
        ttk.Label(list_header, text="键盘按键（任意键）", width=16).pack(side="left")
        ttk.Label(list_header, text="", width=8).pack(side="left", padx=(0, 6))
        ttk.Label(list_header, text="含义", width=12).pack(side="left")
        ttk.Label(list_header, text="→", width=3, anchor="center").pack(side="left")
        ttk.Label(list_header, text="手柄目标（按键 / 摇杆方向）").pack(
            side="left", padx=(8, 0)
        )

        # 滚动区域
        container = ttk.Frame(self.root, padding=(14, 2))
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        vbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.rows_frame = ttk.Frame(canvas)

        self.rows_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(canvas_window, width=e.width)
        )
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # 底部状态栏（先放状态栏、再放分隔线，分隔线才会落在状态栏上方）
        bottom = ttk.Frame(self.root, padding=(14, 10))
        bottom.pack(fill="x", side="bottom")
        ttk.Separator(self.root, orient="horizontal").pack(
            fill="x", side="bottom", padx=14
        )
        self.toggle_btn = ttk.Button(
            bottom, text="▶ 开始监听", command=self.toggle_listening, width=14
        )
        self.toggle_btn.pack(side="left")
        self.status_var = tk.StringVar(value="状态：未启动")
        self.status_label = ttk.Label(
            bottom, textvariable=self.status_var, style="Status.TLabel"
        )
        self.status_label.pack(side="right")


    # ---------- 行操作 ----------
    def add_mapping_row(self, key="f13", target="A", capture=False):
        """新增一行映射。

        key 为 keyboard 库的键名（大小写 / 别名会自动规范化），target 为手柄目标
        （按键、LT/RT 或摇杆方向）。capture=True 时紧接着弹出「按键捕获」对话框。
        """
        row = ttk.Frame(self.rows_frame, padding=(4, 3))
        row.pack(fill="x")

        key_combo = ttk.Combobox(row, values=all_key_names(), width=16)
        key_combo.set(normalize_key_name(key) or str(key))
        key_combo.pack(side="left", padx=(0, 4))

        ttk.Button(
            row, text="⌨ 捕获", width=8,
            command=lambda combo=key_combo: self.capture_key_into(combo),
        ).pack(side="left", padx=(0, 6))

        key_hint = tk.StringVar(value=key_label(key))
        ttk.Label(row, textvariable=key_hint, width=12,
                  style="Hint.TLabel").pack(side="left")

        ttk.Label(row, text="→", width=3, anchor="center").pack(side="left")

        btn_combo = ttk.Combobox(row, values=GAMEPAD_TARGETS,
                                 width=16, state="readonly")
        btn_combo.set(target if target in GAMEPAD_TARGETS else "A")
        btn_combo.pack(side="left", padx=(8, 0))

        entry = (row, key_combo, btn_combo, key_hint)

        def sync_hint(*_args):
            key_hint.set(key_label(key_combo.get()))

        key_combo.bind(
            "<KeyRelease>",
            lambda event, combo=key_combo: (
                self._filter_key_combo(combo), sync_hint()
            ),
        )
        key_combo.bind("<<ComboboxSelected>>", sync_hint)
        key_combo.bind("<FocusOut>", sync_hint)

        def delete_row():
            try:
                self.row_widgets.remove(entry)
            except ValueError:
                pass
            row.destroy()

        ttk.Button(row, text="删除", width=6,
                   command=delete_row).pack(side="right")

        self.row_widgets.append(entry)
        if capture:
            self.root.after(80, lambda combo=key_combo: self.capture_key_into(combo))
        return entry

    def add_mapping_with_capture(self):
        """工具栏按钮：新增一行并立即进入按键捕获。"""
        self.add_mapping_row(capture=True)

    def _filter_key_combo(self, combo):
        """边输边过滤下拉列表，方便在 150 多个键名里快速定位目标键。"""
        text = combo.get().strip().lower()
        names = all_key_names()
        combo["values"] = names if not text else [n for n in names if text in n]

    def capture_key_into(self, combo):
        """弹出按键捕获对话框，把捕获到的键名写进指定输入框。"""
        dialog = KeyCaptureDialog(self.root, self)
        key = dialog.show()
        if not key:
            return
        combo.set(key)
        for row, key_combo, _btn_combo, key_hint in self.row_widgets:
            if key_combo is combo:
                key_hint.set(key_label(key))
                break
        self.status_var.set(f"已捕获按键：{key_label(key)}（{key}）")

    def clear_all(self):
        if not self.row_widgets:
            return
        if not messagebox.askyesno("确认", "确定要清空所有映射吗？"):
            return
        for row, _, _, _ in self.row_widgets:
            row.destroy()
        self.row_widgets.clear()

    # ---------- 界面状态同步 ----------
    def _refresh_state_ui(self):
        """把监听状态同步到按钮文案、状态文字与系统托盘图标。"""
        if self.listening:
            self.toggle_btn.config(text="■ 停止监听")
            self.status_var.set(f"状态：监听中（{len(self.mappings)} 条映射）")
            self.status_label.configure(style="StatusOn.TLabel")
        else:
            self.toggle_btn.config(text="▶ 开始监听")
            self.status_var.set("状态：已停止")
            self.status_label.configure(style="Status.TLabel")
        self._update_tray()


    # ---------- 监听控制 ----------
    def toggle_listening(self):
        if self.listening:
            self.stop_listening()
        else:
            self.start_listening()

    def collect_mappings(self):
        """读取界面上的映射。

        返回 ``(mappings, problems)``：mappings 为 ``{键名: 手柄目标}``，
        problems 为需要提示用户的问题文本列表（无法识别的键名、重复的按键）。
        """
        mappings = {}
        unknown = []
        duplicates = []
        for _row, key_combo, btn_combo, _hint in self.row_widgets:
            key = normalize_key_name(key_combo.get())
            target = btn_combo.get().strip()
            if not key or not target:
                continue
            if not is_known_key(key):
                unknown.append(key_combo.get().strip())
                continue
            if key in mappings:
                duplicates.append(key)
            mappings[key] = target

        problems = []
        if unknown:
            problems.append(
                "以下按键名无法识别，已跳过：\n  " + "、".join(unknown) +
                "\n（可点该行的「⌨ 捕获」重新录入）"
            )
        if duplicates:
            problems.append(
                "以下按键被映射了多次，只有最后一行生效：\n  " +
                "、".join(sorted(set(duplicates)))
            )
        return mappings, problems

    def start_listening(self):
        if self.listening:
            return
        mappings, problems = self.collect_mappings()
        if problems and not messagebox.askyesno(
            "映射检查", "\n\n".join(problems) + "\n\n是否仍然开始监听？"
        ):
            return
        if not mappings:
            messagebox.showwarning("提示", "请至少添加一条有效映射。")
            return

        self.mappings = mappings
        self.hook_id = keyboard.hook(self._on_key_event, suppress=False)
        self.listening = True
        self._refresh_state_ui()
        log(f"开始监听：{mappings}")
        if not is_admin():
            log("警告：未以管理员权限运行，可能无法捕获游戏前台的按键")

    def stop_listening(self):
        if not self.listening:
            return
        if self.hook_id is not None:
            try:
                keyboard.unhook(self.hook_id)
            except Exception:
                try:
                    keyboard.unhook_all()
                except Exception:
                    pass
            self.hook_id = None
        self.listening = False
        self._release_all()
        self._refresh_state_ui()
        log("已停止监听")

    def _release_all(self):
        """松开所有映射到的手柄按键 / 扳机，并把两根摇杆复位到居中。"""
        try:
            for target in set(self.mappings.values()):
                if target in ("LT", "RT") or target in STICK_DIRECTIONS:
                    continue
                button = GAMEPAD_BUTTON_MAP.get(target)
                if button is not None:
                    self.pad.release_button(button)
            self.pad.left_trigger(0)
            self.pad.right_trigger(0)
            self._reset_sticks()
            self.pad.update()
        except Exception:
            pass

    # ---------- 手柄输出 ----------
    def begin_capture(self):
        """按键捕获对话框已打开：暂停按键回调里的映射动作。"""
        self._capturing = True

    def end_capture(self):
        self._capturing = False

    def apply_target(self, target, pressed):
        """把一个手柄目标设为按下 / 松开（供按键回调与自动化测试复用）。

        注意：本方法不调用 ``pad.update()``，由调用方写完（可能多个目标）后统一提交。
        """
        if target == "LT":
            self.pad.left_trigger(TRIGGER_MAX if pressed else 0)
        elif target == "RT":
            self.pad.right_trigger(TRIGGER_MAX if pressed else 0)
        elif target in STICK_DIRECTIONS:
            stick, axis, sign = STICK_DIRECTIONS[target]
            self._set_stick_direction(stick, axis, sign, pressed)
        else:
            button = GAMEPAD_BUTTON_MAP.get(target)
            if button is None:
                raise ValueError(f"未知的手柄目标：{target}")
            if pressed:
                self.pad.press_button(button)
            else:
                self.pad.release_button(button)

    def _set_stick_direction(self, stick, axis, sign, pressed):
        """记录摇杆某方向的按下状态，并把该轴写到满值 / 归零。"""
        directions = self.stick_pressed[(stick, axis)]
        if pressed:
            directions.add(sign)
        else:
            directions.discard(sign)
        self._write_stick(stick)

    def _write_stick(self, stick):
        """按当前按下的方向集合算出两根轴的值并写入虚拟手柄。"""
        x = self._axis_value(stick, "x")
        y = self._axis_value(stick, "y")
        if stick == "left":
            self.pad.left_joystick(x, y)
        else:
            self.pad.right_joystick(x, y)

    def _axis_value(self, stick, axis):
        """同一轴上正反两个方向都按下时取正向，都没按下则居中（0）。"""
        directions = self.stick_pressed[(stick, axis)]
        return STICK_AXIS_MAX * max(directions) if directions else 0

    def _reset_sticks(self):
        """清空摇杆方向状态，并让两根摇杆回到居中。"""
        for directions in self.stick_pressed.values():
            directions.clear()
        self.pad.left_joystick(0, 0)
        self.pad.right_joystick(0, 0)

    # ---------- 按键回调 ----------
    def _on_key_event(self, event):
        try:
            if self._capturing:
                return
            key = normalize_key_name(getattr(event, "name", "") or "")
            if not key or key not in self.mappings:
                return
            target = self.mappings[key]
            if event.event_type == "down":
                self.apply_target(target, True)
            elif event.event_type == "up":
                self.apply_target(target, False)
            else:
                return
            self.pad.update()
        except Exception as ex:
            log(f"[映射错误] {ex}")

    # ---------- 配置持久化 ----------
    def save_config(self):
        data = []
        for _row, key_combo, btn_combo, _hint in self.row_widgets:
            data.append({
                "key": normalize_key_name(key_combo.get()),
                "button": btn_combo.get().strip(),
            })
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_var.set(f"配置已保存 → {os.path.basename(CONFIG_FILE)}")
            log(f"配置已保存：{CONFIG_FILE}")
        except Exception as e:
            log(f"保存配置失败：{e}")
            messagebox.showerror("错误", f"保存配置失败：\n{e}")

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.add_mapping_row("f13", "A")
            self.add_mapping_row("f14", "B")
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    self.add_mapping_row(
                        item.get("key", "f13"),
                        item.get("target", item.get("button", "A")),
                    )
            if not self.row_widgets:
                self.add_mapping_row("f13", "A")
                self.add_mapping_row("f14", "B")
            log(f"已加载配置：{CONFIG_FILE}（{len(self.row_widgets)} 条）")
        except Exception as e:
            log(f"加载配置失败：{e}")
            self.add_mapping_row("f13", "A")
            self.add_mapping_row("f14", "B")

    def open_data_dir(self):
        """打开配置 / 日志所在目录（便于排错）。"""
        try:
            os.startfile(data_dir())
        except Exception as e:
            log(f"打开数据目录失败：{e}")


    # ---------- 系统托盘 ----------
    def _tooltip(self):
        """托盘悬停提示（Windows 上限 128 字符）。"""
        state = f"监听中 · {len(self.mappings)} 条映射" if self.listening else "已停止"
        return f"{app_info.APP_NAME} v{app_info.APP_VERSION} ｜ {state}"

    def _status_menu_text(self, item=None):
        return "状态：监听中（亮蓝图标）" if self.listening else "状态：已停止（灰色图标）"

    def _setup_tray(self):
        """创建系统托盘图标：监听中为亮蓝手柄，停止后变灰蓝。"""
        menu = pystray.Menu(
            pystray.MenuItem("显示主窗口", self._tray_show, default=True),
            pystray.MenuItem(self._status_menu_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "开始监听", self._tray_toggle_listening,
                checked=lambda item: self.listening,
            ),
            pystray.MenuItem("打开数据目录", self._tray_open_data_dir),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._tray_quit),
        )
        self.tray_icon = pystray.Icon(
            app_info.APP_SHORT,
            icon_art.tray_image(False),
            self._tooltip(),
            menu,
        )
        threading.Thread(
            target=self.tray_icon.run, daemon=True, name="kbd2pad-tray"
        ).start()
        log("系统托盘图标已创建")

    def _update_tray(self):
        """按监听状态刷新托盘图标、提示文字与菜单勾选状态。"""
        icon = self.tray_icon
        if icon is None:
            return
        try:
            icon.icon = icon_art.tray_image(self.listening)
            icon.title = self._tooltip()
            icon.update_menu()
        except Exception as e:
            log(f"刷新托盘图标失败：{e}")

    # ---------- 托盘菜单回调（pystray 在后台线程调用，统一切回主线程） ----------
    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self._restore_window)

    def _tray_toggle_listening(self, icon=None, item=None):
        self.root.after(0, self.toggle_listening)

    def _tray_open_data_dir(self, icon=None, item=None):
        self.root.after(0, self.open_data_dir)

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self.quit_app)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.attributes("-topmost", True)
            self.root.after(150,
                            lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def hide_to_tray(self, show_hint=True):
        """隐藏窗口到托盘（首次隐藏时弹一次气泡提示）。"""
        self.root.withdraw()
        if show_hint and not self._tray_hint_shown and self.tray_icon is not None:
            self._tray_hint_shown = True
            try:
                self.tray_icon.notify(
                    "程序已在后台继续运行，双击托盘图标可重新打开窗口。",
                    app_info.APP_NAME,
                )
            except Exception as e:
                log(f"托盘气泡提示失败：{e}")

    def quit_app(self):
        log("正在退出程序")
        try:
            self.stop_listening()
        except Exception:
            pass
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


# ---------- 入口 ----------

def _install_excepthooks():
    """把未处理异常写进日志（打包版本没有控制台，否则什么也看不到）。"""

    def hook(exc_type, exc, tb):
        log("未处理异常：\n" + "".join(
            traceback.format_exception(exc_type, exc, tb)
        ))

    sys.excepthook = hook

    def thread_hook(args):
        log("后台线程异常：\n" + "".join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        )))

    threading.excepthook = thread_hook


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog=app_info.APP_EXE_NAME, description=app_info.APP_DESCRIPTION
    )
    parser.add_argument("--tray", action="store_true",
                        help="启动后直接隐藏到系统托盘")
    parser.add_argument("--listen", action="store_true",
                        help="启动后立即开始监听（常与 --tray 同用于开机自启）")
    parser.add_argument("--version", action="version",
                        version=f"{app_info.APP_NAME} v{app_info.APP_VERSION}")
    args = parser.parse_args(argv)

    _install_excepthooks()

    mutex = acquire_single_instance()
    if mutex is None:
        if focus_existing_window():
            log("已有实例在运行，已尝试激活其主窗口")
        else:
            splash_error(app_info.APP_NAME, "程序已经在运行了，请在系统托盘中查看。")
        return 0

    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except Exception:
        pass

    GamepadMapperApp(root, start_hidden=args.tray, auto_listen=args.listen)

    if not is_admin() and not args.tray:
        root.after(600, lambda: messagebox.showwarning(
            "权限提示",
            "当前未以管理员权限运行。\n\n"
            "keyboard 库在非管理员模式下可能无法捕获游戏前台的按键。\n"
            "建议关闭后，右键 → 以管理员身份运行。"
        ))

    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())




