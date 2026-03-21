# -*- coding: utf-8 -*-
"""导出 JSON 和 Markdown。"""

from __future__ import annotations

import json
import os
import re
import sys
import time


def _log(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write((message + "\n").encode("gbk", errors="replace"))
        else:
            print(message.encode("ascii", errors="replace").decode("ascii"))


def export_json(data: dict, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    _log(f"JSON 已保存：{filepath}")


def _format_timestamp(ts: float) -> str:
    ts = int(ts)
    hours = ts // 3600
    minutes = (ts % 3600) // 60
    seconds = ts % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _format_number(number: int) -> str:
    if number >= 10000:
        return f"{number / 10000:.1f}万"
    return str(number)


def _format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remain_seconds = seconds % 60
    if hours > 0:
        return f"{hours}小时{minutes}分钟{remain_seconds}秒"
    if minutes > 0:
        return f"{minutes}分钟{remain_seconds}秒"
    return f"{remain_seconds}秒"


def _append_summary_sections(lines: list[str], summary: str) -> None:
    text = (summary or "").strip()
    if not text:
        lines.append("*未生成 AI 点评。若要启用，请先配置 MiniMax API Key。*")
        return

    parts = re.split(r"(?=^### )", text, flags=re.MULTILINE)
    if len(parts) <= 1:
        lines.append(text)
        return

    for part in parts:
        block = part.strip()
        if not block:
            continue
        chunk_lines = block.splitlines()
        heading = chunk_lines[0].replace("### ", "", 1).strip()
        body = "\n".join(chunk_lines[1:]).strip()
        lines.append("<details open>")
        lines.append(f"<summary><strong>{heading}</strong></summary>")
        lines.append("")
        if body:
            lines.append(body)
            lines.append("")
        lines.append("</details>")
        lines.append("")


def export_markdown(data: dict, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    video = data["video_info"]
    comments = data["comments"]
    subtitles = data["subtitles"]
    summary = data.get("summary", "")
    meta = data.get("meta", {})
    total_replies = sum(len(comment.get("replies", [])) for comment in comments)

    lines: list[str] = []
    lines.append("<!-- markdownlint-disable -->")
    lines.append("")
    lines.append(f"# {video['title']}")
    lines.append("")
    lines.append(f"> **BV号**: {video['bvid']}  ")
    lines.append(f"> **UP主**: {video['owner']['name']}  ")
    pub_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(video["pubdate"]))
    lines.append(f"> **发布时间**: {pub_time}  ")
    lines.append(f"> **时长**: {_format_duration(video['duration'])}")
    lines.append("")

    stat = video["stat"]
    lines.append("| 播放量 | 点赞 | 投币 | 收藏 | 分享 | 弹幕 | 评论 |")
    lines.append("|--------|------|------|------|------|------|------|")
    lines.append(
        f"| {_format_number(stat['view'])} "
        f"| {_format_number(stat['like'])} "
        f"| {_format_number(stat['coin'])} "
        f"| {_format_number(stat['favorite'])} "
        f"| {_format_number(stat['share'])} "
        f"| {_format_number(stat['danmaku'])} "
        f"| {_format_number(stat['reply'])} |"
    )
    lines.append("")

    desc = video.get("desc", "").strip()
    if desc and desc not in ("-", "--", "无", "暂无简介"):
        lines.append("<details open>")
        lines.append("<summary><strong>视频简介</strong></summary>")
        lines.append("")
        lines.append(desc)
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("<details open>")
    lines.append("<summary><strong>抓取说明</strong></summary>")
    lines.append("")
    lines.append(f"- 字幕来源类型：{meta.get('subtitle_source_type', '未知')}")
    lines.append(f"- 字幕来源接口：{meta.get('subtitle_source_api', '未知')}")
    lines.append(f"- 字幕说明：{meta.get('subtitle_note', '无')}")
    lines.append(f"- 评论说明：{meta.get('summary_note', '无')}")
    lines.append(
        f"- 评论统计：一级评论 {meta.get('total_comments', len(comments))} 条；"
        f"子评论 {meta.get('total_replies', total_replies)} 条；"
        f"页面显示总评论 {meta.get('total_comment_count', 0)} 条。"
    )
    lines.append("")
    lines.append("说明：不同视频的字幕源可能不同，可能是人工/官方字幕，也可能是 AI 字幕；楼中楼评论也可能因接口限制出现缺口。")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<details open>")
    lines.append("<summary><strong>AI 点评</strong></summary>")
    lines.append("")
    _append_summary_sections(lines, summary)
    lines.append("</details>")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<details open>")
    lines.append("<summary><strong>视频字幕区</strong></summary>")
    lines.append("")
    if subtitles:
        for sub in subtitles:
            label = sub["lang"]
            if sub.get("is_ai"):
                label += " · AI 字幕"
            lines.append("<details open>")
            lines.append(f"<summary><strong>{label} ({len(sub['entries'])} 条)</strong></summary>")
            lines.append("")
            for entry in sub["entries"]:
                ts = _format_timestamp(entry["from"])
                lines.append(f"**[{ts}]** {entry['content']}  ")
            lines.append("")
            lines.append("</details>")
            lines.append("")
    else:
        lines.append(f"*未保存字幕。原因：{meta.get('subtitle_note', '当前未获取到可用字幕。')}*")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<details open>")
    lines.append(f"<summary><strong>评论区（{len(comments)} 条一级评论，{total_replies} 条子评论）</strong></summary>")
    lines.append("")
    lines.append(f"*评论抓取说明：{meta.get('summary_note', '无')}*")
    lines.append("")

    for index, comment in enumerate(comments, 1):
        lines.append(f"### {index}. {comment['user']['name']} (Lv.{comment['user']['level']})")
        lines.append("")
        lines.append(comment["content"])
        lines.append("")
        lines.append(f"*点赞 {comment['like']} | {comment['ctime_text']}*")
        lines.append("")

        if comment.get("replies"):
            reply_count = len(comment["replies"])
            lines.append("<details open>")
            lines.append(f"<summary><strong>查看 {reply_count} 条回复</strong></summary>")
            lines.append("")
            for reply in comment["replies"]:
                lines.append(f"> **{reply['user']['name']}**: {reply['content']}")
                lines.append(">")
                lines.append(f"> *点赞 {reply['like']} | {reply['ctime_text']}*")
                lines.append(">")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("</details>")
    lines.append("")
    lines.append("<!-- markdownlint-enable -->")

    with open(filepath, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    _log(f"Markdown 已保存：{filepath}")


def update_summary_in_markdown(filepath: str, summary: str) -> None:
    with open(filepath, "r", encoding="utf-8") as file:
        content = file.read()

    placeholder = "*未生成 AI 点评。若要启用，请先配置 MiniMax API Key。*"
    if placeholder in content:
        content = content.replace(placeholder, summary)
    else:
        pattern = r"(<summary><strong>AI 点评</strong></summary>\s*)(.*?)(\s*</details>)"
        content = re.sub(pattern, f"\\g<1>\n{summary}\n\\g<3>", content, count=1, flags=re.DOTALL)

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)
    _log(f"AI 点评已更新：{filepath}")
