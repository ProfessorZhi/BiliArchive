# -*- coding: utf-8 -*-
"""Bilibili 视频下载模块。"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Callable

import config


ProgressCallback = Callable[[str, int], None]

QUALITY_MAP = {
    "360p": "bv*[height<=360]+ba*/b[height<=360]/b*[height<=360]/worst",
    "480p": "bv*[height<=480]+ba*/b[height<=480]/b*[height<=480]/worst",
    "720p": "bv*[height<=720]+ba*/b[height<=720]/b*[height<=720]",
    "1080p": "bv*[height<=1080]+ba*/b[height<=1080]/b*[height<=1080]",
    "best": "bv*+ba*/b",
}

SINGLE_FILE_QUALITY_MAP = {
    "360p": "b[height<=360]/b*[height<=360]/worst",
    "480p": "b[height<=480]/b*[height<=480]/worst",
    "720p": "b[height<=720]/b*[height<=720]/b",
    "1080p": "b[height<=1080]/b*[height<=1080]/b",
    "best": "b/best",
}

LOWEST_QUALITY_WITH_FFMPEG = "worstvideo*+worstaudio/worst"
LOWEST_QUALITY_SINGLE_FILE = "worst"


def _log(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write((message + "\n").encode("gbk", errors="replace"))
        else:
            print(message.encode("ascii", errors="replace").decode("ascii"))


def _emit(progress_callback: ProgressCallback | None, message: str, percent: int) -> None:
    if progress_callback:
        progress_callback(message, percent)
    else:
        _log(message)


def _find_downloaded_file(output_dir: str, bvid: str, prepared_filename: str | None) -> str | None:
    candidates = [
        prepared_filename,
        os.path.join(output_dir, f"{bvid}.mp4"),
        os.path.join(output_dir, f"{bvid}.mkv"),
        os.path.join(output_dir, f"{bvid}.webm"),
        os.path.join(output_dir, f"{bvid}.flv"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _detect_quality_label(info: dict, requested_quality: str, fallback_used: bool) -> str:
    heights: list[int] = []
    requested_formats = info.get("requested_formats") or []
    for fmt in requested_formats:
        height = fmt.get("height")
        if isinstance(height, int) and height > 0:
            heights.append(height)

    height = info.get("height")
    if isinstance(height, int) and height > 0:
        heights.append(height)

    if heights:
        return f"{max(heights)}p"
    if requested_quality == "best":
        return "best"
    if fallback_used:
        return "lowest"
    return requested_quality


def _rename_with_quality(path: str, quality_label: str) -> str:
    directory, filename = os.path.split(path)
    stem, ext = os.path.splitext(filename)
    target = os.path.join(directory, f"{stem}_{quality_label}{ext}")
    if os.path.normcase(target) == os.path.normcase(path):
        return path
    if os.path.exists(target):
        os.remove(target)
    os.replace(path, target)
    return target


def _build_ydl_opts(
    output_dir: str,
    bvid: str,
    format_selector: str,
    ffmpeg_location: str | None,
    progress_hook,
) -> dict:
    cookie_header = config.build_cookie_header()
    ydl_opts = {
        "outtmpl": os.path.join(output_dir, f"{bvid}.%(ext)s"),
        "format": format_selector,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "http_headers": {
            "User-Agent": config.BASE_HEADERS["User-Agent"],
            "Referer": "https://www.bilibili.com",
        },
        "cookiefile": None,
    }
    if cookie_header:
        ydl_opts["http_headers"]["Cookie"] = cookie_header
    if ffmpeg_location:
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["ffmpeg_location"] = ffmpeg_location
    return ydl_opts


def _describe_stream(info_dict: dict) -> str:
    vcodec = info_dict.get("vcodec")
    acodec = info_dict.get("acodec")
    if vcodec and vcodec != "none" and acodec == "none":
        return "视频流"
    if acodec and acodec != "none" and vcodec == "none":
        return "音频流"
    return "媒体流"


def _download_once(
    yt_dlp_module,
    *,
    url: str,
    output_dir: str,
    bvid: str,
    format_selector: str,
    ffmpeg_location: str | None,
    progress_callback: ProgressCallback | None,
    requested_quality: str,
    fallback_used: bool,
) -> str:
    last_progress = {"stream": "", "percent": -1}

    def on_progress(status: dict) -> None:
        stage = status.get("status")
        info_dict = status.get("info_dict") or {}
        stream_label = _describe_stream(info_dict)
        if stage == "downloading":
            downloaded = status.get("downloaded_bytes", 0)
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            if total:
                percent = int(downloaded * 100 / total)
                if stream_label != last_progress["stream"] or percent != last_progress["percent"]:
                    _emit(progress_callback, f"正在下载{stream_label}: {percent}%", percent)
                    last_progress["stream"] = stream_label
                    last_progress["percent"] = percent
            elif last_progress["stream"] != stream_label:
                _emit(progress_callback, f"正在下载{stream_label}...", 0)
                last_progress["stream"] = stream_label
                last_progress["percent"] = 0
        elif stage == "finished":
            _emit(progress_callback, f"{stream_label}下载完成，正在整理文件...", 100)
        elif stage == "post_process":
            _emit(progress_callback, "正在合并音视频...", 100)

    ydl_opts = _build_ydl_opts(
        output_dir=output_dir,
        bvid=bvid,
        format_selector=format_selector,
        ffmpeg_location=ffmpeg_location,
        progress_hook=on_progress,
    )

    with yt_dlp_module.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = _find_downloaded_file(output_dir, bvid, ydl.prepare_filename(info))
        if not filename:
            raise RuntimeError("下载流程已结束，但输出目录里没有找到视频文件")

        quality_label = _detect_quality_label(info, requested_quality, fallback_used)
        renamed = _rename_with_quality(filename, quality_label)
        _emit(progress_callback, f"视频文件已保存为: {os.path.basename(renamed)}", 100)
        return renamed


def download_video(
    bvid: str,
    output_dir: str,
    quality: str = "720p",
    progress_callback: ProgressCallback | None = None,
) -> str | None:
    try:
        import yt_dlp
    except ImportError:
        _log("未安装 yt-dlp，请先执行 pip install yt-dlp")
        return None

    ffmpeg_location = shutil.which("ffmpeg")
    if not ffmpeg_location:
        try:
            import imageio_ffmpeg

            ffmpeg_location = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_location = None

    has_ffmpeg = ffmpeg_location is not None
    primary_selector = (
        QUALITY_MAP.get(quality, QUALITY_MAP["720p"])
        if has_ffmpeg
        else SINGLE_FILE_QUALITY_MAP.get(quality, SINGLE_FILE_QUALITY_MAP["720p"])
    )
    fallback_selector = LOWEST_QUALITY_WITH_FFMPEG if has_ffmpeg else LOWEST_QUALITY_SINGLE_FILE

    if not has_ffmpeg:
        _emit(progress_callback, "未检测到 ffmpeg，自动切换为单文件下载模式", 0)

    url = f"https://www.bilibili.com/video/{bvid}/"
    _emit(progress_callback, f"开始下载视频: {bvid}", 0)
    _emit(progress_callback, f"画质: {quality}", 0)
    _emit(progress_callback, f"保存到: {output_dir}", 0)

    try:
        return _download_once(
            yt_dlp,
            url=url,
            output_dir=output_dir,
            bvid=bvid,
            format_selector=primary_selector,
            ffmpeg_location=ffmpeg_location,
            progress_callback=progress_callback,
            requested_quality=quality,
            fallback_used=False,
        )
    except Exception as primary_exc:
        message = str(primary_exc)
        if quality == "best" or "Requested format is not available" not in message:
            _emit(progress_callback, f"视频下载失败: {message}", 100)
            _log(f"视频下载失败: {message}")
            return None

        _emit(progress_callback, "所选清晰度不可用，自动切换到当前可用的最低清晰度...", 0)
        try:
            return _download_once(
                yt_dlp,
                url=url,
                output_dir=output_dir,
                bvid=bvid,
                format_selector=fallback_selector,
                ffmpeg_location=ffmpeg_location,
                progress_callback=progress_callback,
                requested_quality=quality,
                fallback_used=True,
            )
        except Exception as fallback_exc:
            _emit(progress_callback, f"视频下载失败: {fallback_exc}", 100)
            _log(f"视频下载失败: {fallback_exc}")
            return None
