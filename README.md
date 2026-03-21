# BiliArchive

BiliArchive 是一个面向 Windows 桌面场景的 Bilibili 内容归档工具。

它可以围绕单个 B 站视频，保存并整理这些内容：

- 视频基础信息
- 一级评论与子评论
- 字幕内容
- 结构化 `JSON` 和 `Markdown`
- 可选下载视频文件
- 可选生成 AI 点评

## 项目介绍

这个项目的目标不是只抓一份原始数据，而是把一个视频相关的重要内容尽量整理成适合继续阅读、归档和分析的本地资料。

相比纯命令行脚本，BiliArchive 更偏向“本地桌面工具”体验：

- 有图形客户端
- 可以设置 B 站登录信息或选择未登录运行
- 可以设置输出文件夹
- 可以直接看到导出的 JSON、Markdown 和视频文件路径

## 功能特性

- 支持输入视频链接或 BV 号
- 抓取视频基础信息
- 抓取一级评论与子评论
- 抓取并保存字幕
- 导出 `JSON` 和 `Markdown`
- 按清晰度下载视频
- 调用兼容的 AI API 生成 AI 点评
- 登录信息、AI API Key、本地输出目录都只保存在本机

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动客户端

```text
启动 BiliArchive.bat
```

3. 在客户端中输入 Bilibili 视频链接或 BV 号并开始保存

## 文档

- 用户指南：[`docs/user-guide.md`](docs/user-guide.md)

## 目录结构

```text
assets/                     图标等资源
docs/                       项目文档与用户指南
src/                        主程序源码
tools/packaging/            EXE 打包配置与脚本
启动 BiliArchive.bat         Windows 启动脚本
requirements.txt            Python 依赖
README.md                   项目介绍
```

## 打包说明

打包脚本已经放到：

```text
tools/packaging/build_biliarchive.bat
```

生成后的 EXE 位于：

```text
dist/BiliArchive.exe
```

## 安全说明

- B 站登录信息不应写入源码
- AI API Key 不应写入源码
- `.biliarchive.local.json` 只用于本地配置
- `output/`、`dist/`、`.biliarchive.local.json` 默认不纳入版本控制
