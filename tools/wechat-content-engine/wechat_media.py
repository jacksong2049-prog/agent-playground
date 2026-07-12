from __future__ import annotations

import mimetypes
from pathlib import Path

import httpx

from content_engine import get_wechat_access_token


def upload_permanent_image(image_path: str) -> dict:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Cover image not found: {path}")
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Cover image exceeds 10 MB")

    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    token = get_wechat_access_token()
    with path.open("rb") as file_obj:
        response = httpx.post(
            "https://api.weixin.qq.com/cgi-bin/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (path.name, file_obj, mime)},
            timeout=60,
        )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode", 0) != 0:
        raise RuntimeError(f"WeChat material upload error: {data}")
    if not data.get("media_id"):
        raise RuntimeError(f"WeChat did not return media_id: {data}")
    return data
