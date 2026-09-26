# -*- coding: utf-8 -*-
"""生成 README 用的界面截图：``docs/screenshot-main.png`` 与 ``docs/screenshot-capture.png``。

只截取本程序**自己的窗口**（用 ``PrintWindow`` 直接向窗口索取像素），不会把桌面上的
其他窗口或内容拍进去；脚本使用临时配置文件，不会读写 ``%APPDATA%\\KbdToPad`` 下的真实配置。

用法（在工作目录根下执行）::

    python tools/make_screenshot.py

前置条件：已安装 ViGEmBus 驱动（创建虚拟手柄需要）与 ``pip install -r requirements.txt``。
"""

import ctypes
import os
import sys
import tempfile
import time
import tkinter as tk
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image  # noqa: E402

import kbd_to_pad  # noqa: E402

DOCS_DIR = os.path.join(ROOT, "docs")

# 截图里展示的示例映射（覆盖普通按键、扳机与摇杆方向）
SAMPLE_ROWS = [
    ("f13", "A"),
    ("f14", "B"),
    ("f15", "LT"),
    ("f16", "LS Up"),
    ("f17", "LS Right"),
    ("f18", "RS Up"),
    ("volume up", "D-Pad Up"),
]

PW_RENDERFULLCONTENT = 0x00000002
PW_CLIENTONLY = 0x00000001
# PrintWindow 的标志：2 = 包含 DWM 合成内容（一般最好）；1 = 仅客户区；0 = 默认
PRINT_FLAGS = (PW_RENDERFULLCONTENT, PW_CLIENTONLY, 0)
GA_ROOT = 2
BI_RGB = 0

# GetSystemMetrics 索引（兜底抓屏时用来换算 DPI 缩放）
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


# 显式声明签名：64 位下句柄是 64 位，交给 ctypes 默认的 int 会被截断
_user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetAncestor.restype = wintypes.HWND
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.GetWindowDC.argtypes = [wintypes.HWND]
_user32.GetWindowDC.restype = wintypes.HDC
_user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
_user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
_user32.PrintWindow.restype = wintypes.BOOL
_gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
_gdi32.CreateCompatibleDC.restype = wintypes.HDC
_gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
_gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
_gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
_gdi32.SelectObject.restype = wintypes.HGDIOBJ
_gdi32.GetDIBits.argtypes = [
    wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
    ctypes.c_void_p, ctypes.POINTER(_BITMAPINFO), wintypes.UINT,
]
_gdi32.GetDIBits.restype = ctypes.c_int
_gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
_gdi32.DeleteObject.restype = wintypes.BOOL
_gdi32.DeleteDC.argtypes = [wintypes.HDC]
_gdi32.DeleteDC.restype = wintypes.BOOL


def _window_handle(widget):
    """取 Tk 窗口对应的顶层窗口句柄（``winfo_id`` 给的其实是子窗口）。"""
    hwnd = _user32.GetAncestor(int(widget.winfo_id()), GA_ROOT)
    return hwnd or int(widget.winfo_id())


def _window_rect(hwnd):
    rect = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise OSError(f"GetWindowRect 失败（GetLastError={ctypes.get_last_error()}）")
    return rect


def _is_blank(image):
    """判断截图是否“什么都没画出来”（例如 PrintWindow 对个别窗口返回整幅黑）。

    注意：``Image.getcolors(maxcolors)`` 在颜色数超过上限时返回 ``None``，
    那说明图像内容很丰富，不能当成空白。
    """
    try:
        colors = image.getcolors(4096)
    except Exception:
        return False
    if colors is None:
        return False
    return len(colors) <= 1


def _print_window(hwnd, width, height, flag):
    """用 PrintWindow 抓取窗口像素，失败返回 None。"""
    window_dc = _user32.GetWindowDC(hwnd)
    mem_dc = _gdi32.CreateCompatibleDC(window_dc)
    bitmap = _gdi32.CreateCompatibleBitmap(window_dc, width, height)
    try:
        _gdi32.SelectObject(mem_dc, bitmap)
        if not _user32.PrintWindow(hwnd, mem_dc, flag):
            return None
        info = _BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height        # 负高度 = 自上而下
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        buffer = ctypes.create_string_buffer(width * height * 4)
        if not _gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer,
                                ctypes.byref(info), 0):
            return None
        return Image.frombuffer("RGB", (width, height), buffer,
                                "raw", "BGRX", 0, 1).copy()
    finally:
        _gdi32.DeleteObject(bitmap)
        _gdi32.DeleteDC(mem_dc)
        _user32.ReleaseDC(hwnd, window_dc)


def _grab_from_screen(rect):
    """兜底方案：抓取屏幕上该窗口所在的区域。

    本脚本与主程序一样是 DPI 非感知的进程，``GetWindowRect`` 给出的是**逻辑**像素，
    而 ``ImageGrab`` 返回的是**物理**像素，因此这里先整屏截图再按比例裁剪，
    避免在高 DPI 显示器上截错位置。
    """
    from PIL import ImageGrab
    screen = ImageGrab.grab(all_screens=True)
    logical_w = _user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    logical_h = _user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if not logical_w or not logical_h:
        return screen.crop((rect.left, rect.top, rect.right, rect.bottom))
    scale_x = screen.width / float(logical_w)
    scale_y = screen.height / float(logical_h)
    left = _user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = _user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    box = (
        round((rect.left - left) * scale_x), round((rect.top - top) * scale_y),
        round((rect.right - left) * scale_x), round((rect.bottom - top) * scale_y),
    )
    return screen.crop(box)


def capture_window(widget):
    """把窗口（含标题栏）截取成 PIL 图像。

    优先用 ``PrintWindow``：即使窗口被其他窗口遮挡，拿到的也是它自己的像素；
    依次尝试多个标志，全部失败才退化为抓取屏幕上的该窗口区域。
    """
    widget.update_idletasks()
    widget.update()
    hwnd = _window_handle(widget)
    rect = _window_rect(hwnd)
    width = rect.right - rect.left
    height = rect.bottom - rect.top

    for flag in PRINT_FLAGS:
        image = _print_window(hwnd, width, height, flag)
        if image is not None and not _is_blank(image):
            return image

    print("  PrintWindow 未拿到有效像素，退化为抓取屏幕上的该窗口区域 …")
    return _grab_from_screen(rect)


def save(image, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, format="PNG")
    print(f"  {os.path.relpath(path, ROOT)}  {image.width}×{image.height}")
    return path


def main():
    # 用临时配置文件，避免影响用户真实配置（GamepadMapperApp 启动时会补默认行）
    kbd_to_pad.CONFIG_FILE = os.path.join(
        tempfile.gettempdir(), "kbd2pad_screenshot_config.json"
    )
    if os.path.exists(kbd_to_pad.CONFIG_FILE):
        os.remove(kbd_to_pad.CONFIG_FILE)

    root = tk.Tk()
    app = kbd_to_pad.GamepadMapperApp(root)

    # 清掉默认行（不走 clear_all，避免弹确认框），换成示例映射
    for row, *_rest in list(app.row_widgets):
        row.destroy()
    app.row_widgets.clear()
    for key, target in SAMPLE_ROWS:
        app.add_mapping_row(key, target)

    root.deiconify()
    root.lift()
    root.update()
    time.sleep(0.8)          # 等窗口与控件彻底绘制完
    root.update()

    print("正在生成截图：")
    save(capture_window(root), os.path.join(DOCS_DIR, "screenshot-main.png"))

    # 「按键捕获」对话框：模态显示，等它画好后截图并取消（show() 返回 None）
    dialog = kbd_to_pad.KeyCaptureDialog(root, app)
    dialog_path = os.path.join(DOCS_DIR, "screenshot-capture.png")

    def grab_dialog():
        try:
            dialog.update()
            save(capture_window(dialog), dialog_path)
        except Exception as e:            # 截图失败不应中断流程
            print(f"  捕获对话框截图失败：{e}")
        finally:
            try:
                dialog._cancel()          # 结束模态等待
            except Exception:
                pass

    root.after(900, grab_dialog)
    dialog.show()

    app.quit_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
