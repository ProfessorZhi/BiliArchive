# -*- coding: utf-8 -*-
"""
MiniMax OpenAI 兼容接口客户端。
"""

from __future__ import annotations

import json
import re

import requests

import config


def has_api_key() -> bool:
    return bool(config.MINIMAX_API_KEY.strip())


def _clip(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...[已截断]"


def _build_prompt(data: dict) -> str:
    video = data["video_info"]
    subtitles = data["subtitles"]
    comments = data["comments"]

    subtitle_chunks: list[str] = []
    for sub in subtitles[:2]:
        lines = [
            f"[{entry['from']:.1f}-{entry['to']:.1f}] {entry['content']}"
            for entry in sub["entries"][:120]
        ]
        subtitle_chunks.append(f"语言: {sub['lang']}\n" + "\n".join(lines))

    comment_chunks: list[str] = []
    for index, comment in enumerate(comments[:80], 1):
        reply_lines = [
            f"  - {reply['user']['name']}: {reply['content']}"
            for reply in comment.get("replies", [])[:4]
        ]
        comment_chunks.append(
            f"{index}. {comment['user']['name']} | 点赞 {comment['like']}\n"
            f"{comment['content']}\n"
            + "\n".join(reply_lines)
        )

    payload = {
        "title": video["title"],
        "desc": video.get("desc", ""),
        "owner": video["owner"]["name"],
        "stats": video["stat"],
        "subtitles_excerpt": _clip("\n\n".join(subtitle_chunks), 10000),
        "comments_excerpt": _clip("\n\n".join(comment_chunks), 12000),
    }

    return (
        "请基于以下 Bilibili 视频信息、字幕片段和评论片段，输出一段中文 Markdown，"
        "用于文档里的“AI 点评”章节。不要输出代码块。\n\n"
        "请严格使用以下结构：\n"
        "### 内容概览\n"
        "### 讨论焦点\n"
        "### 观众观点分布\n"
        "### 有代表性的评论\n"
        "### 总结\n\n"
        "要求：\n"
        "1. 观点要具体，不要泛泛而谈。\n"
        "2. 如果判断依赖样本有限，要明确说明。\n"
        "3. 有代表性的评论请简短转述，不要长篇复制原文。\n\n"
        f"原始材料：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def generate_summary(data: dict) -> str:
    if not has_api_key():
        return ""

    url = config.MINIMAX_BASE_URL.rstrip("/") + "/chat/completions"
    body = {
        "model": config.MINIMAX_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个擅长分析视频内容和评论舆情的中文助手。",
            },
            {
                "role": "user",
                "content": _build_prompt(data),
            },
        ],
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {config.MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    content = payload["choices"][0]["message"]["content"].strip()
    content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
    return content.strip()
