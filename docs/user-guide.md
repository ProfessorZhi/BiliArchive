# BiliArchive 用户指南

## 1. 工具是做什么的

BiliArchive 用来把一个 Bilibili 视频相关的内容保存到本地。

它可以保存：

- 视频标题、简介、UP 主、发布时间等信息
- 一级评论与子评论
- 字幕
- 结构化 JSON
- 可阅读的 Markdown
- 可选的视频文件
- 可选的 AI 点评

## 2. 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

如果后续需要打包 EXE，再执行：

```bash
pip install pyinstaller
```

## 3. 启动方式

### 图形客户端

双击项目根目录中的：

```text
启动 BiliArchive.bat
```

或者运行：

```bash
python src/gui_qt.py
```

### 命令行

```bash
python src/main.py <BV号或视频链接>
```

## 4. 客户端怎么使用

### 输入视频

在输入框中填写：

- Bilibili 视频链接
- 或 BV 号

### 评论数量

- `全部`：尽量抓取可获取的全部评论
- 指定数字：限制一级评论数量，适合快速测试

### 同时下载视频

勾选后会一并下载视频文件。

支持这些画质：

- `360p`
- `480p`
- `720p`
- `1080p`
- `best`

如果你选择的画质不可用，程序会自动回退到可用格式。

### 生成 AI 点评

勾选后会调用 MiniMax 生成 AI 点评并写入 Markdown。

如果没有配置 API Key，程序会跳过 AI 点评。

## 5. 客户端设置

点击客户端中的“客户端设置”，可以配置以下内容。

### B站登录信息

- 可以填写 B 站登录信息
- 也可以留空
- 留空时程序会按未登录方式运行

说明：

- 某些视频或评论在登录状态下更稳定
- 登录信息只保存在本机，不会写进仓库源码

### 输出文件夹

- 可以自定义导出目录
- 后续 JSON、Markdown、视频文件都会保存到这里

### MiniMax API Key

- 用于生成 AI 点评
- 可留空
- 留空时程序会跳过 AI 点评

### MiniMax 模型

默认值：

```text
MiniMax-M2.7
```

## 6. 本地配置保存在哪里

客户端设置会保存在项目根目录：

```text
.biliarchive.local.json
```

这个文件只用于本机，不建议上传 GitHub。

## 7. 输出结果说明

默认输出结构类似这样：

```text
output/
└── 视频标题_BV号/
    ├── BV号.json
    ├── BV号.md
    └── BV号_清晰度.mp4
```

其中：

- `json`：结构化数据
- `md`：适合阅读和归档的文档
- `mp4`：勾选下载视频时才会生成

## 8. 打包 EXE

打包脚本位于：

```text
tools/packaging/build_biliarchive.bat
```

生成后的 EXE 位于：

```text
dist/BiliArchive.exe
```

## 9. 安全建议

- 不要把真实的 B 站登录信息提交到 GitHub
- 不要把真实的 MiniMax API Key 提交到 GitHub
- 不要把 `.biliarchive.local.json` 提交到 GitHub
- 不要把 `output/` 里的个人测试数据直接公开上传
