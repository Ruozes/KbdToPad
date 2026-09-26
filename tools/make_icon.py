# -*- coding: utf-8 -*-
"""生成 assets 目录下的图标资源（窗口图标 / 托盘图标 / 安装包图标）。

用法（在工作目录根下执行）::

    python tools/make_icon.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import icon_art  # noqa: E402  (需要在插入 sys.path 之后导入)


def main():
    written = icon_art.save_all()
    print("已生成图标资源：")
    for path in written:
        print(f"  {path}  ({os.path.getsize(path)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
