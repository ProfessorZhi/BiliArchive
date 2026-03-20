# -*- coding: utf-8 -*-
"""
项目配置。
"""

from __future__ import annotations

import json
import os
import re


APP_NAME = "BiliArchive"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
LOCAL_SETTINGS_PATH = os.path.join(PROJECT_ROOT, ".biliarchive.local.json")


def _load_local_settings() -> dict:
    if not os.path.exists(LOCAL_SETTINGS_PATH):
        return {}
    try:
        with open(LOCAL_SETTINGS_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_local_settings(data: dict) -> None:
    with open(LOCAL_SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


_LOCAL_SETTINGS = _load_local_settings()

SESSDATA = os.getenv(
    "BILIBILI_SESSDATA",
    "9551cf15%2C1787198747%2Cd3323%2A22CjDn0c9CUb-1skh5TOrzfVm9th_winpnASeJuFzsg9rpOD1tH2q-0yB2vz8MPow5BDYSVmJna2F6SXFOUllicjhlMDlqak53UjBFMmY4S0M0SW9INTJ2NGJXWV96QTRsd0Q3RUF4TmljLXlnVWIxNTZISmNmY09yM0FMcXM4TTk0RE9seXV6MEJ3IIEC",
)

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
    "Cookie": f"SESSDATA={SESSDATA}",
}

API_VIDEO_INFO = "https://api.bilibili.com/x/web-interface/view"
API_COMMENTS_MAIN = "https://api.bilibili.com/x/v2/reply/wbi/main"
API_COMMENTS_LIST = "https://api.bilibili.com/x/v2/reply"
API_COMMENTS_REPLY = "https://api.bilibili.com/x/v2/reply/reply"
API_COMMENTS_COUNT = "https://api.bilibili.com/x/v2/reply/count"
API_PLAYER_WBI = "https://api.bilibili.com/x/player/wbi/v2"
API_NAV = "https://api.bilibili.com/x/web-interface/nav"

COMMENT_PAGE_SIZE = 20
REPLY_PAGE_SIZE = 20
REQUEST_DELAY = 0.35

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", _LOCAL_SETTINGS.get("minimax_api_key", ""))
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", _LOCAL_SETTINGS.get("minimax_model", "MiniMax-M2.7"))


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip(" .")
    if len(name) > 80:
        name = name[:80]
    return name


def save_minimax_settings(api_key: str, model: str) -> None:
    global MINIMAX_API_KEY, MINIMAX_MODEL, _LOCAL_SETTINGS

    api_key = api_key.strip()
    model = model.strip() or "MiniMax-M2.7"
    _LOCAL_SETTINGS["minimax_api_key"] = api_key
    _LOCAL_SETTINGS["minimax_model"] = model
    _save_local_settings(_LOCAL_SETTINGS)
    MINIMAX_API_KEY = api_key
    MINIMAX_MODEL = model


def get_minimax_settings() -> tuple[str, str]:
    return MINIMAX_API_KEY, MINIMAX_MODEL
