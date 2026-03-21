# -*- coding: utf-8 -*-
"""项目配置。"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any


APP_NAME = "BiliArchive"

if getattr(sys, "frozen", False):
    executable_dir = os.path.dirname(os.path.abspath(sys.executable))
    parent_dir = os.path.dirname(executable_dir)
    if os.path.basename(executable_dir).lower() == "dist" and os.path.isdir(os.path.join(parent_dir, "src")):
        PROJECT_ROOT = parent_dir
    else:
        PROJECT_ROOT = executable_dir
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
LOCAL_SETTINGS_PATH = os.path.join(PROJECT_ROOT, ".biliarchive.local.json")


def _load_local_settings() -> dict[str, Any]:
    if not os.path.exists(LOCAL_SETTINGS_PATH):
        return {}
    try:
        with open(LOCAL_SETTINGS_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_local_settings(data: dict[str, Any]) -> None:
    with open(LOCAL_SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


_LOCAL_SETTINGS = _load_local_settings()
OUTPUT_DIR = os.getenv("BILIARCHIVE_OUTPUT_DIR", _LOCAL_SETTINGS.get("output_dir", DEFAULT_OUTPUT_DIR))
LOGIN_MODE = os.getenv("BILIARCHIVE_LOGIN_MODE", _LOCAL_SETTINGS.get("login_mode", "none"))
SESSDATA = os.getenv("BILIBILI_SESSDATA", _LOCAL_SETTINGS.get("sessdata", ""))
COOKIE = os.getenv("BILIBILI_COOKIE", _LOCAL_SETTINGS.get("cookie", ""))
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", _LOCAL_SETTINGS.get("minimax_api_key", ""))
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", _LOCAL_SETTINGS.get("minimax_model", "MiniMax-M2.7"))

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}

API_VIDEO_INFO = "https://api.bilibili.com/x/web-interface/view"
API_COMMENTS_MAIN = "https://api.bilibili.com/x/v2/reply/wbi/main"
API_COMMENTS_DETAIL = "https://api.bilibili.com/x/v2/reply/detail"
API_COMMENTS_REPLY = "https://api.bilibili.com/x/v2/reply/reply"
API_COMMENTS_COUNT = "https://api.bilibili.com/x/v2/reply/count"
API_PLAYER = "https://api.bilibili.com/x/player/v2"
API_PLAYER_WBI = "https://api.bilibili.com/x/player/wbi/v2"
API_NAV = "https://api.bilibili.com/x/web-interface/nav"

COMMENT_PAGE_SIZE = 20
REPLY_PAGE_SIZE = 20
REQUEST_DELAY = 0.35


def build_cookie_header(login_mode: str | None = None, sessdata: str | None = None, cookie: str | None = None) -> str:
    mode = (LOGIN_MODE if login_mode is None else login_mode).strip().lower() or "none"
    sessdata_value = (SESSDATA if sessdata is None else sessdata).strip()
    cookie_value = (COOKIE if cookie is None else cookie).strip()
    if mode == "cookie":
        return cookie_value
    if mode == "sessdata":
        return f"SESSDATA={sessdata_value}" if sessdata_value else ""
    return ""


def _sync_headers() -> None:
    global OUTPUT_DIR
    OUTPUT_DIR = os.path.abspath((OUTPUT_DIR or DEFAULT_OUTPUT_DIR).strip())
    BASE_HEADERS.pop("Cookie", None)
    cookie_header = build_cookie_header()
    if cookie_header:
        BASE_HEADERS["Cookie"] = cookie_header


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip(" .")
    if len(name) > 80:
        name = name[:80]
    return name


def get_output_dir() -> str:
    return OUTPUT_DIR


def ensure_output_dir() -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


def get_runtime_settings() -> dict[str, str]:
    return {
        "login_mode": LOGIN_MODE,
        "sessdata": SESSDATA,
        "cookie": COOKIE,
        "output_dir": OUTPUT_DIR,
        "minimax_api_key": MINIMAX_API_KEY,
        "minimax_model": MINIMAX_MODEL,
    }


def save_runtime_settings(
    login_mode: str,
    sessdata: str,
    cookie: str,
    output_dir: str,
    minimax_api_key: str | None = None,
    minimax_model: str | None = None,
) -> None:
    global LOGIN_MODE, SESSDATA, COOKIE, OUTPUT_DIR, MINIMAX_API_KEY, MINIMAX_MODEL, _LOCAL_SETTINGS

    LOGIN_MODE = (login_mode or "none").strip().lower()
    SESSDATA = (sessdata or "").strip()
    COOKIE = (cookie or "").strip()
    OUTPUT_DIR = os.path.abspath((output_dir or DEFAULT_OUTPUT_DIR).strip())
    MINIMAX_API_KEY = (MINIMAX_API_KEY if minimax_api_key is None else minimax_api_key.strip())
    MINIMAX_MODEL = (MINIMAX_MODEL if minimax_model is None else (minimax_model.strip() or "MiniMax-M2.7"))

    _LOCAL_SETTINGS["login_mode"] = LOGIN_MODE
    _LOCAL_SETTINGS["sessdata"] = SESSDATA
    _LOCAL_SETTINGS["cookie"] = COOKIE
    _LOCAL_SETTINGS["output_dir"] = OUTPUT_DIR
    _LOCAL_SETTINGS["minimax_api_key"] = MINIMAX_API_KEY
    _LOCAL_SETTINGS["minimax_model"] = MINIMAX_MODEL
    _save_local_settings(_LOCAL_SETTINGS)
    _sync_headers()


def save_minimax_settings(api_key: str, model: str) -> None:
    save_runtime_settings(LOGIN_MODE, SESSDATA, COOKIE, OUTPUT_DIR, api_key, model)


def get_minimax_settings() -> tuple[str, str]:
    return MINIMAX_API_KEY, MINIMAX_MODEL


_sync_headers()
