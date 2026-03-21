# -*- coding: utf-8 -*-
"""CLI 和 GUI 共用的业务流程。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable

import bilibili_api
import config
import downloader
import exporter
import minimax_client


ProgressCallback = Callable[[str, int], None]


@dataclass
class SaveOptions:
    max_comments: int = 0
    download_video: bool = False
    quality: str = "720p"
    generate_summary: bool = True


@dataclass
class SaveResult:
    bvid: str
    video_title: str
    output_dir: str
    json_path: str
    markdown_path: str
    video_path: str | None
    summary: str
    total_comments: int
    total_replies: int
    total_subtitle_entries: int
    total_comment_count: int
    comment_target_count: int
    total_units_fetched: int
    total_units_target: int
    login_ok: bool
    login_message: str
    root_comments_complete: bool
    reply_gap: int
    summary_note: str
    subtitle_source_type: str
    subtitle_source_api: str
    subtitle_note: str


def _emit(progress_callback: ProgressCallback | None, message: str, percent: int) -> None:
    if progress_callback:
        progress_callback(message, percent)
    else:
        print(message)


def _map_range(start: int, end: int, current: int, total: int) -> int:
    if total <= 0:
        return start
    ratio = min(max(current / total, 0), 1)
    return int(start + (end - start) * ratio)


def _resolve_login_status() -> tuple[bool, str, bool]:
    settings = config.get_runtime_settings()
    login_mode = (settings.get("login_mode") or "none").strip().lower()
    sessdata = settings.get("sessdata", "").strip()
    cookie = settings.get("cookie", "").strip()

    if login_mode == "cookie":
        ok, message = bilibili_api.validate_cookie(cookie)
        return ok, message, bool(cookie and ok)
    if login_mode == "sessdata":
        ok, message = bilibili_api.validate_sessdata(sessdata)
        return ok, message, bool(sessdata and ok)
    return True, "当前按未登录方式运行。", False


def save_bilibili_video(
    video_input: str,
    options: SaveOptions | None = None,
    progress_callback: ProgressCallback | None = None,
) -> SaveResult:
    options = options or SaveOptions()

    config.ensure_output_dir()
    bilibili_api.refresh_session_headers()

    bvid = bilibili_api.extract_bvid(video_input)
    _emit(progress_callback, f"已识别视频：{bvid}", 5)

    video_info = bilibili_api.get_video_info(bvid)
    _emit(progress_callback, f"标题：{video_info['title']}", 10)

    try:
        total_comment_count = bilibili_api.get_comment_count(video_info["aid"])
    except Exception:
        total_comment_count = int(video_info["stat"].get("reply", 0))

    total_comment_target = max(total_comment_count, 0)
    _emit(progress_callback, f"评论区总量预扫描完成：{total_comment_target} 条", 15)

    login_ok, login_message, enable_sub_reply_fetch = _resolve_login_status()
    if enable_sub_reply_fetch:
        _emit(progress_callback, f"B站登录检测通过：{login_message}", 18)
    else:
        _emit(progress_callback, login_message, 18)
        _emit(progress_callback, "当前未使用有效登录，楼中楼与部分字幕接口可能受限。", 22)

    subtitle_bundle = bilibili_api.get_subtitles_bundle(video_info["aid"], video_info["cid"])
    subtitles = subtitle_bundle["subtitles"]
    subtitle_source_type = subtitle_bundle["source_type"]
    subtitle_source_api = subtitle_bundle["source_api"]
    subtitle_note = subtitle_bundle["note"]
    _emit(progress_callback, f"字幕获取完成，共 {len(subtitles)} 组", 25)
    _emit(progress_callback, f"字幕来源：{subtitle_source_type}（{subtitle_source_api}）。{subtitle_note}", 25)

    last_progress_emit = {"fetched": -1, "percent": -1}

    def on_comment_progress(progress: bilibili_api.CommentProgress) -> None:
        percent = _map_range(25, 68, progress.total_fetched, max(progress.total_target, 1))
        should_emit = (
            progress.total_fetched <= 3
            or progress.total_fetched - last_progress_emit["fetched"] >= 5
            or percent > last_progress_emit["percent"]
            or progress.total_fetched >= progress.total_target > 0
        )
        if not should_emit:
            return

        if progress.total_target > 0:
            message = f"已抓取评论 {progress.total_fetched} 条，页面显示总评论 {progress.total_target} 条"
        else:
            message = f"已抓取评论 {progress.total_fetched} 条"
        last_progress_emit["fetched"] = progress.total_fetched
        last_progress_emit["percent"] = percent
        _emit(progress_callback, message, percent)

    comments = bilibili_api.get_all_comments(
        video_info["aid"],
        max_comments=options.max_comments,
        total_comments=total_comment_target,
        progress_callback=on_comment_progress,
        enable_sub_reply_fetch=enable_sub_reply_fetch,
    )
    _emit(progress_callback, f"评论获取完成，共 {len(comments)} 条一级评论", 68)

    final_top_level_target = min(len(comments), options.max_comments) if options.max_comments else len(comments)
    total_replies = sum(len(comment.get("replies", [])) for comment in comments)
    total_units_fetched = len(comments) + total_replies

    root_comments_complete = len(comments) >= final_top_level_target
    reply_gap = max(total_comment_target - total_units_fetched, 0)
    if reply_gap <= 0:
        summary_note = "评论区已抓取完整。"
    elif root_comments_complete:
        if enable_sub_reply_fetch:
            summary_note = f"一级评论已抓全，仍有约 {reply_gap} 条子评论可能因接口限制未补齐。"
        else:
            summary_note = f"一级评论已抓全；当前未登录或登录无效，约 {reply_gap} 条子评论未补齐。"
    else:
        summary_note = f"当前抓到 {len(comments)} 条一级评论，评论主列表可能仍未抓全。"

    _emit(
        progress_callback,
        (
            f"评论汇总：一级评论 {len(comments)} 条；"
            f"子评论 {total_replies} 条；已抓取总评论 {total_units_fetched} 条；"
            f"页面显示总评论 {total_comment_target} 条。{summary_note}"
        ),
        68,
    )

    summary = ""
    if options.generate_summary and minimax_client.has_api_key():
        _emit(progress_callback, "正在生成 AI 点评...", 72)
        summary = minimax_client.generate_summary(
            {
                "video_info": video_info,
                "subtitles": subtitles,
                "comments": comments,
            }
        )
        _emit(progress_callback, "AI 点评生成完成", 82)
    elif options.generate_summary:
        _emit(progress_callback, "未检测到 MiniMax API Key，跳过 AI 点评", 82)

    full_data = {
        "video_info": video_info,
        "subtitles": subtitles,
        "comments": comments,
        "summary": summary,
        "meta": {
            "tool": "BiliArchive",
            "bvid": bvid,
            "total_comments": len(comments),
            "total_replies": total_replies,
            "total_subtitle_entries": sum(len(item["entries"]) for item in subtitles),
            "total_comment_count": total_comment_count,
            "comment_target_count": final_top_level_target,
            "login_ok": login_ok,
            "login_message": login_message,
            "summary_note": summary_note,
            "subtitle_source_type": subtitle_source_type,
            "subtitle_source_api": subtitle_source_api,
            "subtitle_note": subtitle_note,
        },
    }

    safe_title = config.sanitize_filename(video_info["title"])
    folder_name = f"{safe_title}_{bvid}"
    output_dir = os.path.join(config.get_output_dir(), folder_name)
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, f"{bvid}.json")
    markdown_path = os.path.join(output_dir, f"{bvid}.md")

    _emit(progress_callback, f"正在导出到：{output_dir}", 86)
    exporter.export_json(full_data, json_path)
    exporter.export_markdown(full_data, markdown_path)
    _emit(progress_callback, "JSON 和 Markdown 已导出", 92)

    video_path = None
    if options.download_video:

        def on_download_progress(message: str, download_percent: int) -> None:
            percent = _map_range(92, 100, download_percent, 100)
            _emit(progress_callback, message, percent)

        video_path = downloader.download_video(
            bvid,
            output_dir,
            quality=options.quality,
            progress_callback=on_download_progress,
        )
        if not video_path or not os.path.exists(video_path):
            raise RuntimeError("视频下载失败，未生成视频文件。请查看日志后重试。")

    _emit(progress_callback, "保存完成", 100)
    return SaveResult(
        bvid=bvid,
        video_title=video_info["title"],
        output_dir=output_dir,
        json_path=json_path,
        markdown_path=markdown_path,
        video_path=video_path,
        summary=summary,
        total_comments=full_data["meta"]["total_comments"],
        total_replies=full_data["meta"]["total_replies"],
        total_subtitle_entries=full_data["meta"]["total_subtitle_entries"],
        total_comment_count=total_comment_count,
        comment_target_count=final_top_level_target,
        total_units_fetched=total_units_fetched,
        total_units_target=total_comment_target,
        login_ok=login_ok,
        login_message=login_message,
        root_comments_complete=root_comments_complete,
        reply_gap=reply_gap,
        summary_note=summary_note,
        subtitle_source_type=subtitle_source_type,
        subtitle_source_api=subtitle_source_api,
        subtitle_note=subtitle_note,
    )
