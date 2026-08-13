# 抖音、小红书昵称抓取器 / Nickname Scraper

一个用于根据抖音或小红书分享链接获取账号昵称的 Windows 桌面工具。

程序支持批量粘贴链接、显示抓取结果并导出 Excel。当平台触发滑块、验证码或安全验证时，程序会打开前台 Chromium 浏览器；用户完成验证后，程序自动继续抓取，不会将“验证码中间页”等验证提示误认为昵称。

> 本项目仅适用于用户有权访问的公开链接，并应遵守抖音、小红书及相关平台的服务条款、robots 规则和法律法规。请勿用于规避平台风控、批量滥用或收集非公开信息。

## 功能

- 支持抖音视频页、主页及短分享链接。
- 支持小红书笔记页、用户页及短分享链接。
- 支持一次输入多条 URL，自动跳过重复链接。
- 优先通过普通 HTTP 页面信息提取昵称，必要时使用浏览器渲染。
- 浏览器以**前台可见**模式运行，遇到验证码可手工完成验证。
- 自动识别常见验证页面，避免将“验证码中间页”写入昵称结果。
- 在界面中显示 URL、平台、昵称和处理状态。
- 支持将结果导出为 `.xlsx` 文件。
- 提供 PyInstaller 打包脚本，可生成独立的 Windows 应用目录。

## 软件截图

![抖音、小红书昵称抓取器主界面](https://raw.githubusercontent.com/Tom8the/nickname-scraper/7a5515e6d71de4bc18b9b428db75563bcae166c0/assets/screenshots/main-window.png)

## 项目结构

```text
fetch-nickname/
├─ fetch-nickname.py     # 主程序：Tkinter 图形界面与昵称提取逻辑
├─ build_exe.py          # Windows 打包脚本
├─ douyinNickname.py     # 早期的抖音昵称提取工具
├─ fetch_nickname.py     # 早期命令行提取脚本
└─ dist_output/          # 打包输出目录（执行打包后生成）
```

## 使用成品程序（推荐）

适合不需要修改代码的 Windows 用户。

1. 从 GitHub Releases 下载与系统匹配的发布压缩包。
2. 解压整个 `fetch-nickname` 文件夹。
3. 双击 `fetch-nickname.exe` 启动程序。
4. 在输入框中每行粘贴一个抖音或小红书分享链接。
5. 点击“开始批量抓取”。
6. 若弹出 Chromium 浏览器并显示滑块或验证码，请在该浏览器窗口中手工完成验证；验证完成后无需额外点击，程序会自动继续。
7. 抓取完成后，点击“导出到 Excel”保存结果。

> 不要只复制 `fetch-nickname.exe`。它依赖同级的 `_internal` 目录，其中包含 Chromium 和运行所需的库文件。

## 开发环境

当前项目在以下环境中开发和打包：

| 项目 | 版本/说明 |
| --- | --- |
| 操作系统 | Windows 10 / Windows 11（64 位） |
| Python | Python 3.12（建议使用 3.10+） |
| GUI | Tkinter（Python 官方 Windows 安装包自带） |
| 浏览器自动化 | Playwright + Chromium |
| 数据导出 | pandas + openpyxl |
| 打包工具 | PyInstaller |

## 从源码安装与运行

### 1. 获取代码

```bash
git clone https://github.com/<your-github-id>/fetch-nickname.git
cd fetch-nickname
```

请将 `<your-github-id>` 替换为实际仓库所有者。

### 2. 创建虚拟环境（可选但推荐）

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
python -m pip install --upgrade pip
python -m pip install playwright requests pandas openpyxl pyinstaller pillow
python -m playwright install chromium
```

### 4. 启动程序

```bash
python fetch-nickname.py
```

启动后在图形界面中粘贴链接即可使用。

## 打包为 Windows 程序

在已完成上述依赖安装的 Windows 环境中运行：

```bash
python build_exe.py
```

打包结果位于：

```text
dist_output/fetch-nickname/
├─ fetch-nickname.exe
└─ _internal/
```

发布或复制给其他用户时，请压缩并分发整个 `dist_output/fetch-nickname` 文件夹。

## 验证码处理说明

部分链接可能被平台要求进行安全验证。这是平台的正常风控流程，程序不会尝试绕过验证。

当检测到验证页时：

1. 程序日志会提示“检测到平台验证”。
2. 前台 Chromium 窗口会保持打开。
3. 请自行完成滑块、图片验证码、登录或其他页面要求的操作。
4. 验证完成且页面跳转后，程序会等待页面加载并继续提取昵称。
5. 最长等待 5 分钟；超时或点击“停止”后，该链接会被跳过。

## 常见问题

### 程序启动时报 `No module named 'tkinter'`

请确认下载并替换的是完整的新版本目录，而非只替换 `.exe` 文件。正式发布包必须包含 `_internal` 目录。

如果从源码运行，请安装官方 Python Windows 版本，并在安装器中保留 `tcl/tk and IDLE` 组件。

### 浏览器没有出现

源码运行时，请执行：

```bash
python -m playwright install chromium
```

成品程序则请确认 `_internal/chrome-win64` 目录仍与 `fetch-nickname.exe` 保持同级，且没有被安全软件隔离。

### 结果为空或抓取失败

- 检查链接是否可在正常浏览器中访问。
- 平台可能要求验证、登录，或临时限制访问；请在弹出的浏览器中完成相应操作后等待程序继续。
- 短链接解析、页面结构和平台规则可能变化，请提交 Issue 并附上可公开复现的链接类型、日志和截图（请先隐藏隐私信息）。

### 为什么浏览器会短暂打开后关闭？

当普通 HTTP 请求未直接获得昵称时，程序会打开浏览器加载页面并提取信息。成功、失败或超时后，浏览器会自动关闭；遇到验证页时则会保持打开，等待手工处理。

## 贡献

欢迎提交 Issue 和 Pull Request。提交问题时建议说明：

- 使用的是源码版还是打包版；
- Windows 与 Python 版本；
- 平台类型（抖音/小红书）和链接类型（视频、主页、笔记等）；
- 操作步骤、预期结果、实际结果和日志截图；
- 可公开复现的最小示例（请勿提交账号 Cookie、个人信息或私密链接）。

## 许可证

当前仓库尚未声明开源许可证。发布到 GitHub 前，建议根据你的分发意图添加 `LICENSE` 文件，例如 MIT License 或 Apache License 2.0。
