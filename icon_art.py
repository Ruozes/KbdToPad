# -*- coding: utf-8 -*-
"""图标绘制模块：窗口图标、系统托盘图标、exe 图标与安装包图标统一风格。

设计说明
--------
* 所有图形先在 ``DESIGN_SIZE × SUPERSAMPLE`` 的画布上绘制，再用 LANCZOS
  缩小到目标尺寸，因此 16px 的托盘尺寸下依然锐利、不发虚；
* 造型 = 胶囊形手柄机身 + 十字方向键 + 四颗白色面键，小尺寸下仍可辨识，
  相比原先"蓝色方块 + 默认字体的 G"更清晰、更现代；
* 两种状态：``active``（监听中，亮蓝渐变 + 右下角绿灯）与 ``idle``（已停止，
  灰蓝渐变、无指示灯），与托盘 tooltip、菜单勾选项一起表达运行状态。

用法
----
主程序运行时调用 :func:`tray_image` 生成托盘图标；
构建脚本调用 :func:`save_ico` / :func:`save_png` 生成 ``assets`` 下的资源文件。
"""

import os
import tempfile

from PIL import Image, ImageChops, ImageDraw

SUPERSAMPLE = 4                    # 超采样倍数
DESIGN_SIZE = 256                  # 设计基准坐标系大小
ICON_SIZES = (256, 128, 64, 48, 32, 24, 16)   # ico 内嵌的多分辨率尺寸

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ICO_PATH = os.path.join(ASSET_DIR, "app.ico")
PNG_PATH = os.path.join(ASSET_DIR, "app.png")
TRAY_ACTIVE_PATH = os.path.join(ASSET_DIR, "tray_active.png")
TRAY_IDLE_PATH = os.path.join(ASSET_DIR, "tray_idle.png")

# 状态配色：状态 -> (渐变顶色, 渐变底色, 描边色)
THEMES = {
    True: ((0x63, 0xB4, 0xFF), (0x18, 0x4C, 0xC2), (0x0F, 0x2F, 0x80)),
    False: ((0xB6, 0xC0, 0xCD), (0x5A, 0x65, 0x76), (0x3B, 0x44, 0x51)),
}

_WHITE = (255, 255, 255, 255)
_GREEN = (0x22, 0xC5, 0x5E, 255)       # 运行指示灯


def _vertical_gradient(size, top, bottom):
    """生成自上而下的线性渐变图（RGB）。"""
    grad = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(grad)
    last = max(size - 1, 1)
    for y in range(size):
        t = y / last
        draw.line(
            (0, y, size, y),
            fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)),
        )
    return grad


def render(size=DESIGN_SIZE, active=True, badge=False):
    """绘制并返回指定尺寸的 RGBA 图标。

    :param size: 输出边长（像素），会自动限制到不小于 8。
    :param active: True 表示"监听中"（亮蓝），False 表示"已停止"（灰蓝）。
    :param badge: 是否在机身右下角画一枚绿色指示灯（托盘"监听中"状态用）。
    """
    size = max(int(size), 8)
    top, bottom, outline = THEMES[bool(active)]

    work = DESIGN_SIZE * SUPERSAMPLE
    k = work / DESIGN_SIZE

    def box(x1, y1, x2, y2):
        """把设计坐标（256 基准）换算成画布坐标。"""
        return (round(x1 * k), round(y1 * k), round(x2 * k), round(y2 * k))

    def radius(value):
        return max(round(value * k), 1)

    layer = Image.new("RGBA", (work, work), (0, 0, 0, 0))

    # ---- 机身：胶囊形 + 竖直渐变 ----
    body = box(16, 60, 240, 196)
    body_mask = Image.new("L", (work, work), 0)
    ImageDraw.Draw(body_mask).rounded_rectangle(body, radius=radius(68), fill=255)
    layer.paste(_vertical_gradient(work, top, bottom), (0, 0), body_mask)

    # ---- 顶部高光（用机身遮罩裁剪，避免溢出到透明区域）----
    gloss = Image.new("RGBA", (work, work), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).rounded_rectangle(
        box(28, 70, 228, 98), radius=radius(14), fill=(255, 255, 255, 48)
    )
    gloss.putalpha(ImageChops.multiply(gloss.getchannel("A"), body_mask))
    layer = Image.alpha_composite(layer, gloss)

    draw = ImageDraw.Draw(layer, "RGBA")

    # ---- 描边，增强在浅色背景上的轮廓感 ----
    draw.rounded_rectangle(
        body, radius=radius(68), outline=outline + (255,), width=radius(6)
    )

    # ---- 十字方向键 ----
    draw.rounded_rectangle(box(52, 116, 108, 140), radius=radius(5), fill=_WHITE)
    draw.rounded_rectangle(box(68, 100, 92, 156), radius=radius(5), fill=_WHITE)

    # ---- 四颗面键 ----
    for cx, cy in ((176, 101), (203, 128), (176, 155), (149, 128)):
        draw.ellipse(
            (round((cx - 13) * k), round((cy - 13) * k),
             round((cx + 13) * k), round((cy + 13) * k)),
            fill=_WHITE,
        )

    # ---- 运行指示灯（绿色小灯，带白色描边，嵌在机身右下角的描边上）----
    if badge:
        draw.ellipse(box(193, 153, 223, 183), fill=_WHITE)
        draw.ellipse(box(197, 157, 219, 179), fill=_GREEN)

    return layer.resize((size, size), Image.LANCZOS)


def tray_image(active=True):
    """托盘图标用的图像对象（监听中带绿色指示灯）。

    返回 256px 的图：pystray 在 Windows 上写出的 .ico 会包含
    16/24/32/48/64/128/256 各档尺寸，Windows 按 DPI 自动挑选最合适的一档。
    """
    return render(DESIGN_SIZE, active, badge=bool(active))


def save_ico(path=ICO_PATH, active=True, sizes=ICON_SIZES):
    """保存多分辨率 .ico（每档都独立绘制，避免连续缩放导致糊边）。"""
    frames = [render(size, active) for size in sorted(sizes, reverse=True)]
    base = frames[0]
    base.save(
        path,
        format="ICO",
        sizes=[(im.width, im.height) for im in frames],
        append_images=frames[1:],
    )
    return path


def save_png(path, size=DESIGN_SIZE, active=True, badge=False):
    """保存普通 PNG（用于文档、托盘状态预览）。"""
    render(size, active, badge=badge).save(path, format="PNG")
    return path


def save_all(asset_dir=ASSET_DIR):
    """一次性生成 assets 目录下的全部图标资源，返回生成的文件列表。"""
    os.makedirs(asset_dir, exist_ok=True)
    written = [
        save_ico(os.path.join(asset_dir, "app.ico")),
        save_png(os.path.join(asset_dir, "app.png"), 256, True),
        save_png(os.path.join(asset_dir, "tray_active.png"), 64, True, True),
        save_png(os.path.join(asset_dir, "tray_idle.png"), 64, False),
    ]
    return written


def ensure_ico_file(active=True):
    """返回一个可用的 .ico 文件路径。

    优先使用打包/源码目录下的 ``assets/app.ico``；若不存在（例如直接跑源码
    且尚未生成资源），则即时生成到临时目录，保证窗口图标可用。
    """
    if os.path.exists(ICO_PATH):
        return ICO_PATH
    cache_dir = os.path.join(tempfile.gettempdir(), "kbd2pad")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "tray_active.ico" if active else "tray_idle.ico")
    return save_ico(path, active)


if __name__ == "__main__":  # 便捷调试：直接生成资源
    for f in save_all():
        print(f)
