# 第三方组件与许可说明

本项目的**自身代码**以 [MIT](LICENSE) 许可发布，但运行、打包与安装包分发过程中会用到下列第三方组件，
它们各自遵循自己的许可协议。**这些第三方组件均未修改**，全部以原样使用。

本项目由 [@Ruozes](https://github.com/Ruozes) 维护，代码、文档与构建脚本均在
[DeepSeek](https://www.deepseek.com/) 的辅助下完成；DeepSeek 只是开发工具，**不随任何产物分发**，
也不引入额外的依赖或许可约束。

## 1. 运行依赖（随 exe 一起打包）

| 组件 | 版本参考 | 许可 | 用途 |
| --- | --- | --- | --- |
| [keyboard](https://github.com/boppreh/keyboard) | 0.13.5 | MIT | 全局键盘钩子（监听 / 捕获按键） |
| [vgamepad](https://github.com/yannbouteiller/vgamepad) | 0.1.0 | MIT | 创建虚拟 Xbox 360 手柄（通过 ViGEmBus） |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | **LGPL-3.0** | 系统托盘图标与菜单 |
| [Pillow](https://github.com/python-pillow/Pillow) | 9.2+ | MIT-CMU（HPND） | 绘制图标（`icon_art.py`） |
| [Python](https://www.python.org/) | 3.9+（开发环境 3.13） | PSF-2.0 | 运行时 |
| [PyInstaller](https://pyinstaller.org/) | 6.6+ | GPL-2.0 + 启动器例外条款 | 仅构建期使用，用于打包 exe |

关于 **LGPL-3.0 的 pystray**：本项目未修改其源码，仅通过 `import pystray` 调用；
构建产物中它与其他依赖一起由 PyInstaller 打包。若需替换该组件，可直接在
`pip install -r requirements.txt` 后重新执行 `python build.py`
（或替换 `kbd_to_pad.py` 中的托盘实现）后重新打包。

## 2. 随安装包分发的第三方程序（构建时下载，**不存放在本仓库**）

| 文件 | 来源 | 许可 | 说明 |
| --- | --- | --- | --- |
| `installer/vendor/ViGEmBusSetup.exe` | <https://github.com/nefarius/ViGEmBus/releases> | BSD-3-Clause | 虚拟手柄驱动；安装包仅在系统缺失时静默安装 |
| `installer/vendor/VC_redist.x64.exe` | <https://aka.ms/vs/17/release/vc_redist.x64.exe> | Microsoft 可再分发运行库许可 | vgamepad 的 DLL 依赖；仅在系统缺失时静默安装 |
| `installer/vendor/ChineseSimplified.isl` | [Inno Setup 官方仓库](https://github.com/jrsoftware/issrc) | Inno Setup License | 安装界面中文语言文件，缺失时自动回退英文界面 |

这些二进制体积较大（约 31 MB）且需要保持较新版本，因此**没有提交到仓库**：
`build.py` 在每次构建时自动下载（`python build.py --no-download` 可跳过下载、使用已有文件）。

## 3. 构建期工具

* [Inno Setup 6](https://jrsoftware.org/isinfo.php)：生成安装包（`installer/KbdToPad.iss`），免费但非开源许可，
  仅在你本机/CI 上使用，不随产物分发。

## 4. 商标声明

“Xbox”“Xbox 360”“Windows” 是 Microsoft Corporation 的商标。
本项目与 Microsoft、nefarius（ViGEmBus 作者）以及上述各组件作者**均无隶属或赞助关系**。
