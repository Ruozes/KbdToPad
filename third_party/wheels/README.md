# 预置 wheel（CI 与本地安装使用）

| 文件 | 来源 | 说明 |
| --- | --- | --- |
| `vgamepad-0.1.0-py3-none-any.whl` | 由 PyPI 的 `vgamepad-0.1.0.tar.gz` 构建而来 | `vgamepad` 在 PyPI 上**只有源码包**，没有官方 wheel |

校验和：

```text
上游 sdist（PyPI 元数据公布的 sha256，与本目录 wheel 的构建输入一致）
57f6bd01aec0c172947517fb782d150ef9b285f7f4d524c317374fa5c24a89de  vgamepad-0.1.0.tar.gz          (1 174 896 字节)

本目录内的 wheel
0d2af8894188cfb246195c3b1d52a5d6a80bc29e2792774879af4583cd4ad8fa  vgamepad-0.1.0-py3-none-any.whl (1 169 298 字节)
```

## 为什么要预置这个 wheel

`vgamepad` 的 sdist 里 `setup.py` 有这么一段（原样摘录）：

```python
# Prompt installation of the ViGEmBus driver (blocking call)
if sys.argv[1] != 'egg_info' and sys.argv[1] != 'sdist':
    if not vigem_installed:
        subprocess.call(['msiexec', '/i', '%s' % str(pathMsi)], shell=True)
```

也就是说：**安装或构建 `vgamepad` 时，只要系统里没检测到 ViGEmBus 驱动，它就会直接启动驱动安装程序**。
pip 在 `prepare_metadata` 阶段执行的是 `setup.py dist_info`（既不是 `egg_info` 也不是 `sdist`，因此这段会执行），结果：

* 在 GitHub Actions 运行器上（没装 ViGEmBus，也没有人点「下一步」）→ **永久卡在
  `Preparing metadata (pyproject.toml)`**，直到超时或手工取消；日志收尾会留下
  `Terminate orphan process: … (msiexec)`，这就是卡死的证据；
* 在本机没装 ViGEmBus 时 → 弹出一个驱动安装向导，安装过程被「顺手」插进 pip 安装里。

用本目录预置的 wheel 安装时，pip 完全不会执行 `setup.py`，上述问题就都不存在了。

## 用法

```powershell
# 强制所有依赖都走 wheel（不允许现场编译），并用本目录补上 vgamepad
pip install --only-binary=:all: --find-links third_party/wheels -r requirements-dev.txt
```

`--only-binary=:all:` 的作用是：万一将来某个依赖也只有源码包，pip 会**立刻报错**，
而不是在构建阶段悄悄挂住。

## 如何重新生成（升级 vgamepad 版本时）

```powershell
# ① 从 PyPI 取 sdist，并核对 sha256 与 PyPI 公布的一致
python -m pip download vgamepad==0.1.0 --no-binary :all: --no-deps -d $env:TEMP\vgsrc

# ② 构建 wheel（本机已装 ViGEmBus 时不会弹任何东西；若未安装，会弹出 ViGEmBus
#    安装向导 —— 那正是我们要绕开的行为，构建完成关闭即可）
python -m pip wheel --no-deps -w third_party/wheels $env:TEMP\vgsrc\vgamepad-0.1.0.tar.gz

# ③ 记录新 wheel 的 sha256，并同步更新本文件的表格与 requirements.txt 里的版本号
Get-FileHash third_party/wheels/vgamepad-0.1.0-py3-none-any.whl -Algorithm SHA256
```

> 该 wheel 是 `py3-none-any` 纯 Python 包，内含 `vgamepad/win/vigem/client/{x64,x86}/ViGEmClient.dll`
> 与 `vgamepad/win/vigem/install/{x64,x86}/ViGEmBusSetup_*.msi`（与 sdist 内容一致；
> `KbdToPad.spec` 打包时需要这些文件）。内容来自上游 MIT 许可项目
> <https://github.com/yannbouteiller/vgamepad>，许可信息见仓库根的 `THIRD_PARTY_NOTICES.md`。
