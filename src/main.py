# -*- coding: utf-8 -*-
"""CLI / GUI 入口。"""

from __future__ import annotations

import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BiliArchive：Bilibili 内容归档工具")
    parser.add_argument("video", nargs="?", help="BV 号或视频链接")
    parser.add_argument("--max-comments", type=int, default=0, help="评论上限，0 为全部")
    parser.add_argument("--download", action="store_true", help="下载视频")
    parser.add_argument(
        "--quality",
        default="720p",
        choices=["360p", "480p", "720p", "1080p", "best"],
        help="下载视频画质",
    )
    parser.add_argument("--no-ai", action="store_true", help="不生成 AI 点评")
    parser.add_argument("--gui", action="store_true", help="启动图形界面")
    return parser


def launch_gui() -> int:
    from gui_qt import run_gui

    run_gui()
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        return launch_gui()

    if not args.video:
        parser.error("请提供 BV 号或视频链接，或者使用 --gui。")

    from app_service import SaveOptions, save_bilibili_video

    result = save_bilibili_video(
        args.video,
        options=SaveOptions(
            max_comments=args.max_comments,
            download_video=args.download,
            quality=args.quality,
            generate_summary=not args.no_ai,
        ),
    )

    print("=" * 60)
    print(f"标题: {result.video_title}")
    print(f"输出目录: {result.output_dir}")
    print(f"JSON: {result.json_path}")
    print(f"Markdown: {result.markdown_path}")
    if result.video_path:
        print(f"视频: {result.video_path}")
    print(f"评论: 一级评论 {result.total_comments}，子评论 {result.total_replies}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
