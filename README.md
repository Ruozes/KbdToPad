# KbdToPad · 键盘 → 虚拟手柄 映射工具

把键盘按键（尤其是 Windows 掌机的自定义键，如 `F13`–`F24`）映射成 **虚拟 Xbox 360 手柄** 的
按键、扳机与**左右摇杆方向**，让不支持自定义按键的游戏也能用上掌机上的额外按键。

![platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011%20x64-0078D6)
![python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![license](https://img.shields.io/badge/license-MIT-green)

> 作者：[@Ruozes](https://github.com/Ruozes) ｜ 本项目（代码、文档与界面文案）由
> [DeepSeek](https://www.deepseek.com/) 辅助完成，详见 [致谢](#致谢)。

## 目录

* [特性](#特性)
* [界面](#界面)
* [系统要求](#系统要求)
* [下载与安装](#下载与安装)
* [从源码运行](#从源码运行)
* [使用说明](#使用说明)
* [配置与日志位置](#配置与日志位置)
* [命令行参数](#命令行参数)
* [打包 exe 与安装包](#打包-exe-与安装包)
* [项目结构](#项目结构)
* [常见问题](#常见问题)
* [免责声明](#免责声明)
* [参与贡献](#参与贡献)
* [致谢](#致谢)
* [许可](#许可)

## 特性

* **键盘侧支持全键盘任意键**：
  * 每行映射都有「⌨ 捕获」按钮，按一下目标键即可录入（`Esc`、音量键、多媒体键都能捕获）；
  * 键名输入框内置常见键名列表，输入字符即时过滤，也可直接手工输入（如 `f13`、`volume up`）；
  * 键名大小写与常见别名自动归一化（`ESCAPE` → `esc`、`PrtScn` → `print screen`），界面“含义”列显示中文名称；
  * 开始监听前会检查映射表：无法识别的键名会被提示并跳过，重复映射会提示确认。
* **手柄侧覆盖按键、扳机与摇杆**：`A/B/X/Y`、`LB/RB`、`LT/RT`、`Back/Start`、`LS/RS`、十字键，
  以及**左/右摇杆各四个方向**（按住推到满值 ±32767，松开回中；两个方向的键同时按下即斜向）。
* **常驻系统托盘**：托盘图标分「监听中（亮蓝机身 + 右下角绿色指示灯）/ 已停止（灰蓝、无指示灯）」两态，
  一眼看出当前状态；点 × 只隐藏到托盘不退出，托盘菜单为「显示主窗口 / 状态 / 开始监听（勾选态）/ 打开数据目录 / 退出」。
* **开机自启**（安装时勾选）：静默进托盘并自动开始监听。
* 映射表可随时增删改、一键保存，下次启动自动加载；配置与日志集中在 `%APPDATA%\KbdToPad`。
* 单实例运行（命名互斥体）；停止监听或退出时复位全部按键、扳机与摇杆，避免手柄“卡键”。

## 界面

主窗口（键名可捕获 / 可下拉选择，右侧为手柄目标，含摇杆方向）：

![主界面](docs/screenshot-main.png)

点「⌨ 捕获」后按下想映射的任意键：

![按键捕获](docs/screenshot-capture.png)

## 系统要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 10 / 11 x64（x64 掌机、台式机均可） |
| 驱动 | [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases)（负责虚拟手柄，安装包会自动检测并安装） |
| 运行库 | Microsoft Visual C++ 2015-2022 x64（vgamepad 的 DLL 依赖它，安装包会在缺失时自动补装） |
| 权限 | 需要管理员权限才能捕获游戏前台按键；exe 已内置 UAC 提权清单 |

## 下载与安装

1. 打开 [Releases](https://github.com/Ruozes/KbdToPad/releases/latest)，
   下载 `KbdToPad-Setup-0.1.1.exe`（约 39.5 MB，**已内含 ViGEmBus 驱动与 VC++ 运行库**）；
2. 双击安装（会请求管理员权限），可选择创建桌面快捷方式与开机自动启动；
3. 安装完成后启动程序 → 添加映射 → 点「▶ 开始监听」，按下映射的键即相当于按下手柄键。

安装包会：把程序释放到 `%ProgramFiles%\KbdToPad`；系统缺少 ViGEmBus 驱动 / VC++ 运行库时自动静默安装；
卸载时结束进程、删除程序与卸载项，并询问是否一并删除用户配置与日志。

> **绿色版**：把安装目录（默认 `C:\Program Files\KbdToPad`）整个文件夹拷到别处即可，但需自行安装 ViGEmBus 驱动。
> 从源码运行也可以，见下一节。

## 从源码运行

```powershell
git clone https://github.com/Ruozes/KbdToPad.git
cd KbdToPad
pip install -r requirements.txt
python kbd_to_pad.py            # 普通启动
python kbd_to_pad.py --tray     # 启动后直接缩到系统托盘
```

运行前请先安装 [ViGEmBus 驱动](https://github.com/nefarius/ViGEmBus/releases)。
`keyboard` 库在捕获**游戏前台**的按键时需要管理员权限，建议以管理员身份运行（打包后的 exe 会自动请求提权）。

## 使用说明

1. 先用掌机自带软件（如 AYANEO 的按键设置）把掌机自定义键映射成键盘上的某个键，
   沿用 `F13`–`F24` 这类不常用键最稳妥；
2. 打开 KbdToPad，点「＋ 添加映射」新增一行（或点「⌨ 按任意键添加」直接进入捕获）：
   * **左侧按键**：点该行的「⌨ 捕获」→ 按下想映射的键盘按键（键盘上任意键都可以，`Esc` 会被当成按键，
     要放弃请点对话框里的「取消」）；也可以从下拉列表选（输入字符会自动过滤），或手工输入键名；
   * **右侧目标**：从下拉列表选手柄目标，除常规按键外还有 `LT`/`RT` 与摇杆八个方向；
3. 需要多条就继续添加；点「保存配置」写盘（下次启动自动加载）；
4. 点「▶ 开始监听」，状态变为绿色即生效：此时按下该键盘键，游戏里就相当于按下对应的手柄键 / 拨动摇杆；
5. 点窗口右上角 × 会**隐藏到系统托盘**（不退出）；托盘图标亮蓝 + 右下角绿灯表示正在监听，
   灰蓝表示已停止；托盘菜单为「显示主窗口 / 开始监听（勾选态）/ 打开数据目录 / 退出」。

手柄目标与行为：

| 目标 | 行为 |
| --- | --- |
| `A` `B` `X` `Y` `LB` `RB` `Back` `Start` `LS` `RS` `D-Pad Up/Down/Left/Right` | 按下 / 松开对应的手柄按键 |
| `LT` / `RT` | 按下为满值（255），松开为 0 |
| `LS Up` / `LS Down` / `LS Left` / `LS Right` | 左摇杆该方向推到满值（±32767），松开回到居中（0） |
| `RS Up` / `RS Down` / `RS Left` / `RS Right` | 右摇杆同上 |

> 摇杆方向是「数字量」而不是模拟量：按住即满值、松开即回中。把两个互相垂直的方向映射到两个不同按键
> （例如 `f15` → `LS Up`、`f16` → `LS Right`），同时按下即可得到斜向；同一根轴的正反两个方向同时按下时取正向。

键名说明：键盘侧使用 [`keyboard`](https://github.com/boppreh/keyboard) 库的规范小写键名
（`esc`、`print screen`、`volume up`、`left shift`…），大小写与常见别名都会被自动归一化，
界面“含义”列显示对应的中文名称；无法识别的键名会在开始监听前提示并跳过。

### 配置示例

`%APPDATA%\KbdToPad\config.json`：

```json
[
  { "key": "f13", "button": "A" },
  { "key": "f14", "button": "LT" },
  { "key": "f15", "button": "LS Up" },
  { "key": "f16", "button": "LS Right" },
  { "key": "f17", "button": "RS Up" }
]
```

同一行里的 `f15` + `f16` 同时按下即为**左上斜向**。旧字段 `button` 与新字段 `target` 都兼容读取。

## 配置与日志位置

| 内容 | 路径 |
| --- | --- |
| 配置 | `%APPDATA%\KbdToPad\config.json` |
| 日志 | `%APPDATA%\KbdToPad\app.log`（超过 256 KB 自动轮转为 `app.log.1`） |

> 安装版（打包后运行）使用上表路径；**直接运行源码时**配置与日志放在脚本所在目录（项目根目录），
> 便于调试。旧版本把 `config.json` 放在 exe 同目录，首次运行新版本会自动迁移一次；
> 托盘菜单 → 「打开数据目录」可直接打开该文件夹（排错时把 `app.log` 附在 issue 里）。

## 命令行参数

| 参数 | 说明 |
| --- | --- |
| `--tray` | 启动后直接隐藏到系统托盘 |
| `--listen` | 启动后立即开始监听 |
| `--version` | 显示版本号后退出 |

程序同时只允许运行一个实例（命名互斥体 `Local\KbdToPad_SingleInstance`），重复启动会激活已有窗口。

## 打包 exe 与安装包

`build.py` 负责：生成图标与 exe 版本资源 → PyInstaller 打包 exe → 下载随包分发的驱动 / 运行库 → 编译中文安装包：

```powershell
pip install -r requirements-dev.txt
winget install -e --id JRSoftware.InnoSetup   # 需要 Inno Setup 6（缺省时自动跳过安装包步骤）
python build.py                # 默认：文件夹版 exe + 安装包（推荐）
python build.py --onefile      # 单文件 exe + 安装包
python build.py --no-installer # 只打包 exe
python build.py --icons-only   # 只重新生成 assets\ 下的图标
```

产物（文件名里的版本号取自 `app_info.py`）：

```text
dist\KbdToPad\KbdToPad.exe                    文件夹版 exe（默认；启动更快）
dist\KbdToPad.exe                             单文件 exe（--onefile 时）
installer\Output\KbdToPad-Setup-0.1.1.exe     中文安装包（约 39.5 MB，实测）
```

安装包里附带的驱动 / 运行库由 `build.py` 自动下载到 `installer\vendor\`（已存在则跳过，不入库）：

| 文件 | 用途 |
| --- | --- |
| `installer\vendor\ViGEmBusSetup.exe` | [ViGEmBus](https://github.com/nefarius/ViGEmBus)（BSD-3-Clause）虚拟手柄驱动，系统缺失时由安装包静默安装 |
| `installer\vendor\VC_redist.x64.exe` | 微软 VC++ 2015-2022 运行库，vgamepad 的 DLL 依赖它 |
| `installer\vendor\ChineseSimplified.isl` | Inno Setup 简体中文语言文件（取不到时安装界面回退为英文） |

下载由 `build.py` 完成（`--no-download` 可跳过、`--skip-vcredist` 只跳过运行库）；
只做开发调试时不需要这些文件。

> 也可以用 CI 构建：仓库内置 GitHub Actions 工作流 [`.github/workflows/build.yml`](.github/workflows/build.yml)，
> 在 **Actions** 页手动触发即构建并把 exe（artifact `KbdToPad-exe`）与安装包（artifact `KbdToPad-installer`）上传；
> 推送 `v*` 标签时还会自动创建草稿 Release 并附上安装包。正式发版步骤见 [`docs/RELEASING.md`](docs/RELEASING.md)。

## 项目结构

```text
KbdToPad/
├─ kbd_to_pad.py           主程序（图形界面、按键捕获、虚拟手柄映射、系统托盘）
├─ app_info.py             应用名 / 版本号 / 作者等元信息（打包与安装包共用）
├─ icon_art.py             程序图标绘制代码（托盘图标同样由它生成）
├─ build.py                一键构建脚本（图标 → PyInstaller → Inno Setup）
├─ KbdToPad.spec           PyInstaller 打包配置
├─ requirements.txt        运行依赖
├─ requirements-dev.txt    打包 / 开发依赖
├─ assets\                 图标资源（app.ico / app.png / 托盘图标，由 build.py 生成）
├─ installer\
│  ├─ KbdToPad.iss         Inno Setup 安装包脚本（中文界面）
│  └─ vendor\              ViGEmBus 驱动 / VC++ 运行库 / 中文语言文件（自动下载，不入库）
├─ tools\
│  ├─ make_icon.py         单独重新生成 assets\ 下的图标
│  └─ make_screenshot.py   重新生成 docs\ 下的界面截图
├─ docs\                   README 截图、发版说明（RELEASING.md）
└─ .github\workflows\      GitHub Actions 构建工作流
```

## 常见问题

**Q：开始监听后完全没反应？**
先确认本工具**以管理员权限运行**（`keyboard` 库在非管理员模式下捕获不到游戏前台的按键，安装版会自行提权）；
再确认 ViGEmBus 驱动已安装（设备管理器里会出现 ViGEmBus 设备）；
最后可打开在线手柄测试页（如 <https://hardwaretester.com/gamepad>）确认虚拟手柄有输出。
若状态栏提示键名无法识别，说明该行的键名写法不正确，请用「⌨ 捕获」重新录入。

**Q：某个键盘按键捕获不到？**
掌机自定义键需要先在厂商软件里映射成一个键盘按键；若某键被系统或厂商软件占用（如某些功能键直接触发 OSD），
系统不会把它传给程序，换用 `F13`–`F24` 这类空闲键位。

**Q：摇杆只能满速 / 斜向不好按？**
摇杆方向是数字量（满值 / 回中）。需要斜向就把两个垂直方向映射到两个键并同时按下。

**Q：能不能映射到多个手柄 / 键鼠？**
目前只创建 1 个虚拟 Xbox 360 手柄（XInput 1 号位），也不做键盘鼠标重新映射。

**Q：杀毒软件报毒 / 游戏反作弊报错？**
exe 由 PyInstaller 打包，容易被启发式误报（单文件版 `--onefile` 尤甚；可自行从源码构建）。反作弊（如 EAC、BattlEye）对虚拟手柄的
态度各不相同，请自行确认目标游戏的规定，由此产生的一切后果由使用者承担。

**Q：安装包会装驱动吗？**
会。系统缺少 ViGEmBus 或 VC++ 运行库时，安装包会静默安装它们；卸载程序不会自动卸载这两个系统组件
（其他软件可能也在用）。

**Q：多显示器 / 高 DPI 下界面发虚？**
界面已按 DPI 感知处理，若仍异常可在 exe 属性 → 兼容性 → 更改高 DPI 设置里调整。

## 免责声明

* 本软件**按“现状”提供**，不附带任何担保；使用本软件造成的任何问题由使用者自行负责。
* 输入映射是全局生效的：监听期间按下的映射键会被替换成手柄输入，可能影响前台其他软件，请自行评估。
* 请遵守游戏 / 平台的用户协议与反作弊规定，禁止将本软件用于作弊或绕过检测；请勿用于违反法律法规的用途。
* 本项目与 AYANEO、GPD、Valve 等硬件厂商无任何关联，截图中出现的第三方名称仅为说明用途。

## 参与贡献

* 欢迎在 [Issues](https://github.com/Ruozes/KbdToPad/issues) 报告问题，附上 Windows 版本、掌机型号、
  复现步骤，以及 `%APPDATA%\KbdToPad\app.log`。
* 提交代码前请保持现有代码风格（中文注释、`标准库 → 第三方库` 的导入顺序），
  并确认 `python -m py_compile kbd_to_pad.py app_info.py icon_art.py` 与 `python build.py --no-installer` 都能通过。
* 若新增手柄目标，请同步更新 README 的「使用说明」表格与 `CHANGELOG.md`。

## 致谢

* **本项目由 [DeepSeek](https://www.deepseek.com/) 辅助完成**：界面布局、按键捕获与虚拟手柄映射的实现、
  Inno Setup 安装包脚本，以及 README / CHANGELOG 等文档，都是在与 DeepSeek 的多轮协作中写成并逐项验证的。
  项目作者与维护者：[**@Ruozes**](https://github.com/Ruozes)。
* 感谢 [ViGEmBus](https://github.com/nefarius/ViGEmBus) 提供虚拟手柄驱动，感谢
  [vgamepad](https://github.com/yannbouteiller/vgamepad)、[keyboard](https://github.com/boppreh/keyboard)、
  [pystray](https://github.com/moses-palmer/pystray)、[Pillow](https://python-pillow.org/) 等开源项目。

## 许可

本项目基于 [MIT License](LICENSE) 开源。第三方组件与驱动说明见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)：
[vgamepad](https://github.com/yannbouteiller/vgamepad)（MIT）、
[keyboard](https://github.com/boppreh/keyboard)（MIT）、
[pystray](https://github.com/moses-palmer/pystray)（LGPLv3）、
[Pillow](https://python-pillow.org/)（MIT-CMU）、
[ViGEmBus](https://github.com/nefarius/ViGEmBus)（BSD-3-Clause）、
[pyinstaller](https://pyinstaller.org/)（GPL-2.0-with-exception，仅打包工具，仅影响生成的 exe）。

## 更新记录

各版本变更见 [`CHANGELOG.md`](CHANGELOG.md)；当前版本 **v0.1.1**。

