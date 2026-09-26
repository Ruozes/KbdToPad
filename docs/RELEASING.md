# 发布流程（维护者用）

本文件说明怎样把 KbdToPad 发布到 GitHub，以及哪些文件应当入库、哪些不入库。

## 1. 仓库里有什么

| 入库 | 说明 |
| --- | --- |
| `kbd_to_pad.py`、`app_info.py`、`icon_art.py` | 程序源码 |
| `build.py`、`KbdToPad.spec`、`requirements*.txt` | 构建脚本与依赖清单 |
| `installer/KbdToPad.iss` | 安装包脚本（第 16 行的 `AppVersion` 是“直接用 IDE 编译”时的默认版本） |
| `tools/make_icon.py`、`tools/make_screenshot.py` | 图标 / README 截图生成工具 |
| `assets/app.ico`、`assets/*.png` | 图标资源（由 `build.py` 生成，体积小、直接入库便于查看） |
| `docs/`、`README.md`、`README.en.md`、`CHANGELOG.md`、`LICENSE`、`THIRD_PARTY_NOTICES.md` | 文档（`README.md` 为中文主页、`README.en.md` 为英文版，两份顶部互相链接）；作者 / 版权署名统一为 `Ruozes`（`app_info.py` 的 `APP_AUTHOR` 与 `LICENSE`，构建时会写进 exe 版本资源与安装包“发布者”） |

| 不入库（见 `.gitignore`） | 原因 |
| --- | --- |
| `build/`、`dist/` | PyInstaller 中间产物与 exe |
| `installer/Output/` | 安装包产物（作为 Release 附件上传，约 39.5 MB） |
| `installer/vendor/` | ViGEmBus 驱动 + VC++ 运行库 + 中文语言文件（约 31 MB，`build.py` 自动下载） |
| `installer/build_defines.iss`、`assets/version_info.txt` | 每次构建自动生成 |
| `backup/`、`_*.py`、`app.log`、`config.json` | 本地备份、临时脚本、运行期文件 |

## 2. 发布新版本（例如 v0.1.2）

```powershell
# ① 改版本号（三处）
#    app_info.py                     APP_VERSION = "0.1.2"
#    installer/KbdToPad.iss          #define AppVersion "0.1.2"
#    CHANGELOG.md                    新增 0.1.2 段落（含日期）

# ② 生成 README 截图（界面有改动时才需要）
python tools/make_screenshot.py

# ③ 构建 exe 与安装包（需要 Inno Setup 6）
pip install -r requirements-dev.txt
winget install -e --id JRSoftware.InnoSetup
python build.py
#   → dist\KbdToPad\KbdToPad.exe
#   → installer\Output\KbdToPad-Setup-0.1.2.exe

# ④ 自检：exe 版本资源、界面功能、摇杆方向、开机自启与卸载

# ⑤ 提交并打标签
git add -A
git commit -m "release: v0.1.2"
git tag -a v0.1.2 -m "KbdToPad v0.1.2"
git push origin main
git push origin v0.1.2

# ⑥ 创建 Release（二选一）
#    A. 网页：Releases → Draft a new release → 选择标签 v0.1.2，
#       把 CHANGELOG.md 中该版本段落粘贴为说明，上传 installer\Output\KbdToPad-Setup-0.1.2.exe
#    B. GitHub CLI：gh release create v0.1.2 installer\Output\KbdToPad-Setup-0.1.2.exe `
#         --title "KbdToPad v0.1.2" --notes-file CHANGELOG.md
```

> 安装包已内含 ViGEmBus 驱动与 VC++ 运行库，因此约 39.5 MB；GitHub Release 附件上限 2 GB，无需分卷。
> 以 v0.1.1 实测为例：`dist\KbdToPad\KbdToPad.exe` 约 3.5 MB，安装包 39.5 MB。

## 3. CI 自动构建

`.github/workflows/build.yml` 已配置好：推送 `v*` 标签时在 GitHub 的 Windows 运行器上
自动执行 `python build.py`，并把 `KbdToPad-Setup-*.exe` 作为 Release 附件上传（同时保留
exe 文件夹版作为 workflow artifact）。也可以手动触发（Actions → Build → Run workflow）。

注意事项：

* 运行器需要联网下载 `installer/vendor/` 里的第三方二进制；若下载失败（如 GitHub API 限流），
  安装包会缺少驱动，此时改用本地构建的产物上传；
* 若某个步骤长时间无进展（例如「安装依赖」一直停在 `pip install`），多为运行器网络问题：
  在 Actions 页面取消该运行后点 **Re-run jobs** 重试，或改用本地 `python build.py` 的产物上传；
* 中文语言文件下载失败时会自动回退为英文安装界面（不影响安装）；
* workflow 首次运行请在 Actions 页面确认成功后再对外发布。

## 4. 首次创建仓库

```powershell
# ① 确认 Git 身份（首次使用 Git 必须先设置，否则无法提交）
git config --global user.name              # 为空则设置：
git config --global user.name  "你的名字"
git config --global user.email "你的邮箱"

# ② 首次提交
git add -A
git commit -m "release: v0.1.1"
git log --oneline

# ③ 关联远程并推送
#   在 GitHub 网页新建空仓库（不要勾选 README/.gitignore/License），名字建议 KbdToPad
git remote add origin https://github.com/<你的用户名>/KbdToPad.git
git branch -M main
git push -u origin main
git push origin --tags
```

> 习惯用命令行发版可以直接 `git tag -a v0.1.1 -m "KbdToPad v0.1.1"` 后 `git push origin v0.1.1`，
> CI 会自动创建草稿 Release（见第 3 节），再在网页上传安装包并发布即可。

仓库简介（About）建议填写：
`把键盘（掌机自定义键）映射为虚拟 Xbox 360 手柄的按键 / 扳机 / 摇杆方向 | Keyboard-to-virtual-gamepad mapper for Windows handhelds`；
末尾可追加 `｜本项目由 DeepSeek 辅助完成（Built with DeepSeek assistance）`。
Topics 建议：`windows` `handheld` `gamepad` `vigembus` `keyboard-mapper` `vgamepad` `xbox360` `tray-app`。

仓库地址与署名已按作者 `Ruozes` 填写：`app_info.py` 的 `APP_AUTHOR` / `APP_URL`、README 的下载 / clone /
Issues 链接、CHANGELOG 的版本链接、`LICENSE` 的版权署名；README、CHANGELOG、`THIRD_PARTY_NOTICES.md`
中均已注明**本项目由 DeepSeek 辅助完成**。若将来迁移到别的账号或组织，按同样位置逐处替换即可。
