# -*- coding: utf-8 -*-
"""
Bilibili API 交互。
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import re
import sys
import time

import requests

import config
import wbi


@dataclass
class CommentProgress:
    top_level_fetched: int
    top_level_target: int | None
    total_fetched: int
    total_target: int


CommentProgressCallback = Callable[[CommentProgress], None]
SUB_REPLY_WORKERS = 4
REQUEST_RETRIES = 3

_SESSION = requests.Session()
_SESSION.headers.update(config.BASE_HEADERS)


def refresh_session_headers() -> None:
    _SESSION.headers.clear()
    _SESSION.headers.update(config.BASE_HEADERS)


def _log(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write((message + "\n").encode("gbk", errors="replace"))
        else:
            print(message.encode("ascii", errors="replace").decode("ascii"))


def _request_json(
    url: str,
    api_name: str,
    *,
    params: dict | None = None,
    use_session: bool = True,
    timeout: int = 15,
) -> dict:
    client = _SESSION if use_session else requests
    last_error: Exception | None = None
    for attempt in range(REQUEST_RETRIES):
        try:
            resp = client.get(url, params=params, headers=config.BASE_HEADERS, timeout=timeout)
            try:
                return resp.json()
            except ValueError as exc:
                snippet = resp.text[:200].strip().replace("\n", " ")
                raise RuntimeError(
                    f"{api_name} 返回了非 JSON 内容，状态码 {resp.status_code}，内容片段: {snippet or '<empty>'}"
                ) from exc
        except Exception as exc:
            last_error = exc
            if attempt < REQUEST_RETRIES - 1:
                time.sleep(0.25 * (attempt + 1))
                continue
            raise RuntimeError(f"{api_name} 请求失败: {exc}") from exc
    raise RuntimeError(f"{api_name} 请求失败: {last_error}")


def extract_bvid(input_str: str) -> str:
    match = re.search(r"(BV[a-zA-Z0-9]+)", input_str.strip())
    if match:
        return match.group(1)
    raise ValueError(f"无法从输入中提取 BV 号: {input_str}")


def get_video_info(bvid: str) -> dict:
    _log(f"正在获取视频信息: {bvid}")
    data = _request_json(
        config.API_VIDEO_INFO,
        "视频信息接口",
        params={"bvid": bvid},
    )
    if data.get("code") != 0:
        raise RuntimeError(f"获取视频信息失败: {data.get('message', '未知错误')}")

    video = data["data"]
    return {
        "bvid": video["bvid"],
        "aid": video["aid"],
        "cid": video["cid"],
        "title": video["title"],
        "desc": video.get("desc", ""),
        "owner": {
            "mid": video["owner"]["mid"],
            "name": video["owner"]["name"],
        },
        "stat": {
            "view": video["stat"]["view"],
            "like": video["stat"]["like"],
            "coin": video["stat"]["coin"],
            "favorite": video["stat"]["favorite"],
            "share": video["stat"]["share"],
            "danmaku": video["stat"]["danmaku"],
            "reply": video["stat"]["reply"],
        },
        "pages": [
            {"cid": page["cid"], "part": page["part"], "page": page["page"]}
            for page in video.get("pages", [])
        ],
        "pubdate": video.get("pubdate", 0),
        "duration": video.get("duration", 0),
    }


def get_comment_count(oid: int) -> int:
    data = _request_json(
        config.API_COMMENTS_COUNT,
        "评论计数接口",
        params={"oid": oid, "type": 1},
    )
    if data.get("code") != 0:
        raise RuntimeError(f"获取评论总数失败: {data.get('message', '未知错误')}")
    return int(data.get("data", {}).get("count", 0))


def _format_comment(comment: dict) -> dict:
    member = comment.get("member", {})
    level_info = member.get("level_info", {})
    return {
        "rpid": comment["rpid"],
        "user": {
            "mid": member.get("mid", ""),
            "name": member.get("uname", ""),
            "avatar": member.get("avatar", ""),
            "level": level_info.get("current_level", 0),
        },
        "content": comment.get("content", {}).get("message", ""),
        "like": comment.get("like", 0),
        "ctime": comment.get("ctime", 0),
        "ctime_text": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(comment.get("ctime", 0))),
        "replies": [],
    }


def _normalize_lang_tag(value: str) -> str:
    return (value or "").strip().lower().replace("_", "-")


def _is_chinese_subtitle(subtitle: dict) -> bool:
    lang = _normalize_lang_tag(subtitle.get("lan", ""))
    name = subtitle.get("lang", "")
    return lang.startswith("zh") or "中文" in name or "汉语" in name or "汉字" in name


def _is_english_subtitle(subtitle: dict) -> bool:
    lang = _normalize_lang_tag(subtitle.get("lan", ""))
    name = subtitle.get("lang", "")
    return lang.startswith("en") or "english" in name.lower() or "英文" in name


def _select_preferred_subtitles(subtitles: list[dict]) -> list[dict]:
    chinese = [item for item in subtitles if _is_chinese_subtitle(item)]
    english = [item for item in subtitles if _is_english_subtitle(item)]

    selected: list[dict] = []
    if chinese:
        selected.append(chinese[0])
    if english:
        english_item = english[0]
        if all(english_item.get("lan") != item.get("lan") for item in selected):
            selected.append(english_item)
    if selected:
        return selected

    return subtitles[:1]


def _get_sub_replies(oid: int, root_rpid: int) -> list[dict]:
    all_replies: list[dict] = []
    pn = 1
    while True:
        data = _request_json(
            config.API_COMMENTS_REPLY,
            "子评论接口",
            params={
                "oid": oid,
                "type": 1,
                "root": root_rpid,
                "pn": pn,
                "ps": config.REPLY_PAGE_SIZE,
            },
            use_session=False,
        )
        if data.get("code") != 0:
            _log(f"获取子评论失败(rpid={root_rpid}, pn={pn}): {data.get('message')}")
            break

        replies = data.get("data", {}).get("replies") or []
        if not replies:
            break

        all_replies.extend(_format_comment(reply) for reply in replies)

        total = int(data.get("data", {}).get("page", {}).get("count", 0))
        if pn * config.REPLY_PAGE_SIZE >= total:
            break
        pn += 1

    return all_replies


def _fill_sub_replies_parallel(oid: int, page_comments: list[tuple[dict, dict]]) -> None:
    pending: list[tuple[int, dict, str]] = []
    for raw_comment, formatted in page_comments:
        inline_replies = raw_comment.get("replies") or []
        formatted["replies"] = [_format_comment(reply) for reply in inline_replies]
        pending.append((raw_comment["rpid"], formatted, formatted["user"]["name"]))

    if not pending:
        return

    with ThreadPoolExecutor(max_workers=SUB_REPLY_WORKERS) as executor:
        future_map = {
            executor.submit(_get_sub_replies, oid, rpid): (formatted, user_name)
            for rpid, formatted, user_name in pending
        }
        for future in as_completed(future_map):
            formatted, user_name = future_map[future]
            try:
                fetched_replies = future.result()
                if fetched_replies:
                    formatted["replies"] = fetched_replies
                    _log(f"补抓子评论 {len(fetched_replies)} 条: {user_name}")
            except Exception as exc:
                _log(f"补抓子评论失败: {user_name} ({exc})")


def get_all_comments(
    oid: int,
    max_comments: int = 0,
    total_comments: int = 0,
    progress_callback: CommentProgressCallback | None = None,
) -> list[dict]:
    all_comments: list[dict] = []
    pn = 1
    top_level_target: int | None = max_comments if max_comments else None
    total_fetched = 0

    _log("正在获取评论区...")

    while True:
        data = _request_json(
            config.API_COMMENTS_LIST,
            "评论列表接口",
            params={
                "oid": oid,
                "type": 1,
                "sort": 2,
                "pn": pn,
                "ps": config.COMMENT_PAGE_SIZE,
            },
        )
        if data.get("code") != 0:
            raise RuntimeError(f"获取评论失败: {data.get('message', '未知错误')}")

        replies = data.get("data", {}).get("replies") or []
        if not replies:
            break

        page_comments = [(comment, _format_comment(comment)) for comment in replies]
        _fill_sub_replies_parallel(oid, page_comments)

        for _, formatted in page_comments:
            all_comments.append(formatted)
            total_fetched += 1 + len(formatted.get("replies", []))
            if progress_callback:
                total_target = max(total_comments, total_fetched)
                progress_callback(
                    CommentProgress(
                        top_level_fetched=len(all_comments),
                        top_level_target=(
                            max(top_level_target, len(all_comments))
                            if top_level_target is not None
                            else None
                        ),
                        total_fetched=total_fetched,
                        total_target=total_target,
                    )
                )
            if max_comments and len(all_comments) >= max_comments:
                _log(f"已达到评论上限: {max_comments}")
                return all_comments

        if len(replies) < config.COMMENT_PAGE_SIZE:
            break

        pn += 1
        _log(f"已获取 {len(all_comments)} 条一级评论，继续第 {pn} 页...")

    _log(f"评论获取完毕，共 {len(all_comments)} 条一级评论")
    return all_comments


def get_subtitles(aid: int, cid: int) -> list[dict]:
    _log("正在获取字幕...")
    data = _request_json(
        config.API_PLAYER_WBI,
        "字幕信息接口",
        params=wbi.sign_params({"aid": aid, "cid": cid}),
    )
    if data.get("code") != 0:
        _log(f"获取字幕信息失败: {data.get('message')}")
        return []

    subtitle_list = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
    if not subtitle_list:
        _log("该视频没有字幕")
        return []

    all_subtitles: list[dict] = []
    for sub_meta in subtitle_list:
        lang = sub_meta.get("lan_doc", sub_meta.get("lan", "未知"))
        url = sub_meta.get("subtitle_url", "")
        if not url:
            continue
        if url.startswith("//"):
            url = "https:" + url

        _log(f"下载字幕: {lang}")
        sub_data = _request_json(url, f"字幕下载接口({lang})", use_session=False)
        entries = [
            {
                "from": item.get("from", 0),
                "to": item.get("to", 0),
                "content": item.get("content", ""),
            }
            for item in sub_data.get("body", [])
        ]
        all_subtitles.append(
            {
                "lang": lang,
                "lan": sub_meta.get("lan", ""),
                "entries": entries,
            }
        )

    selected_subtitles = _select_preferred_subtitles(all_subtitles)
    total_entries = sum(len(item["entries"]) for item in selected_subtitles)
    selected_label = ", ".join(item["lang"] for item in selected_subtitles)
    _log(f"字幕获取完毕，已保留: {selected_label}，共 {total_entries} 条")
    return selected_subtitles
