# BiliArchive

BiliArchive 是一个面向 Windows 桌面场景的 Bilibili 内容归档工具，支持抓取视频信息、评论、子评论、字幕，并导出结构化的 `Markdown + JSON`；也支持按清晰度下载视频，以及基于 MiniMax 的 AI 点评。

## 功能特性

- 保存视频基础信息
- 保存一级评论与子评论
- 保存字幕内容
- 导出 `JSON` 和 `Markdown`
- 可选下载视频文件
- 提供 PySide6 图形客户端
- 支持 MiniMax AI 点评
- 本地配置与敏感信息分离保存

## 安装

```bash
pip install -r requirements.txt
```

## 登录配置（可选）

如需访问需要登录后才能获取的数据，请配置环境变量 `BILIBILI_SESSDATA`：

```bash
export BILIBILI_SESSDATA="你的 SESSDATA"
```

Windows PowerShell 示例：

```powershell
$env:BILIBILI_SESSDATA = "你的 SESSDATA"
```

## AI 配置

MiniMax API Key 不写入仓库源码。

你可以通过两种方式配置：

1. 在客户端内打开“AI 设置”并保存到本地配置文件 `.biliarchive.local.json`
2. 通过环境变量配置 `MINIMAX_API_KEY`

本地配置文件已被 `.gitignore` 忽略，不会默认进入版本控制。

## 命令行使用

```bash
# 基本用法
python src/main.py <BV号或视频链接>

# 限制评论数量
python src/main.py BV1xx411c7mD --max-comments 50

# 同时下载视频
python src/main.py BV1xx411c7mD --download

# 启动图形客户端
python src/main.py --gui
```

## 图形客户端

也可以直接运行：

```bash
python src/gui_qt.py
```

或在 Windows 下双击：

```text
启动 BiliArchive.bat
```

## 打包 EXE

先安装依赖：

```bash
pip install -r requirements.txt
pip install pyinstaller
```

然后在项目根目录执行：

```bash
build_biliarchive.bat
```

生成文件位于：

```text
dist/BiliArchive.exe
```

## 输出结构

```text
output/
└── 视频标题_BV号/
    ├── BV号.json
    ├── BV号.md
    └── BV号_清晰度.mp4
```

## 项目结构

```text
assets/                  图标等资源
src/                     主程序源码
BiliArchive.spec         PyInstaller 打包配置
build_biliarchive.bat    EXE 构建脚本
启动 BiliArchive.bat      Windows 启动脚本
```

## 安全说明

- 仓库不应提交任何真实的 `BILIBILI_SESSDATA`
- 仓库不应提交任何真实的 MiniMax API Key
- `.biliarchive.local.json`、`output/`、`dist/` 等本地文件默认不纳入版本控制
