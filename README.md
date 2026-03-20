# BiliArchive

BiliArchive 是一个 Bilibili 内容归档工具，可以保存视频评论、字幕，以及可选的视频文件，并导出为 `Markdown + JSON`。

## 功能

- 保存视频基础信息
- 保存一级评论与子评论
- 保存字幕
- 导出 `JSON` 和 `Markdown`
- 可选下载视频文件
- 支持 Qt 图形客户端
- 支持 AI 点评

## 安装

```bash
pip install -r requirements.txt
```

## 登录配置（可选）

如需访问需要登录的内容，请设置环境变量 `BILIBILI_SESSDATA`：

```bash
export BILIBILI_SESSDATA="你的 SESSDATA"
```

## 命令行使用

```bash
# 基本用法
python src/main.py <BV号或视频链接>

# 限制评论数量
python src/main.py BV1xx411c7mD --max-comments 50

# 同时下载视频
python src/main.py BV1xx411c7mD --download

# 启动 Qt 客户端
python src/main.py --gui
```

## Qt 客户端

也可以直接运行：

```bash
python src/gui_qt.py
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

打包完成后，生成文件位于：

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

## ????

- ???????? Bilibili ??????????????? `BILIBILI_SESSDATA` ??????????
- MiniMax API Key ????????????????????????
