from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from content_engine import (
    audit_article,
    collect_rss_items,
    create_wechat_draft,
    env_list,
    generate_article,
    rank_items,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI行动营内容引擎", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

STATE: dict[str, object] = {"sources": [], "article": None}


class GenerateRequest(BaseModel):
    selected_urls: list[str] = []


class DraftRequest(BaseModel):
    article: dict


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status() -> dict:
    return {
        "openai_ready": bool(os.getenv("OPENAI_API_KEY")),
        "wechat_ready": all(os.getenv(k) for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET", "WECHAT_COVER_MEDIA_ID")),
        "rss_count": len(env_list("NEWS_RSS_URLS")),
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    }


@app.post("/api/collect")
def collect() -> dict:
    try:
        items = collect_rss_items(env_list("NEWS_RSS_URLS"), int(os.getenv("MAX_SOURCE_ITEMS", "30")))
        items = rank_items(items, env_list("TOPIC_KEYWORDS", "AI,agent,automation,startup"))
        STATE["sources"] = items
        return {"items": [item.__dict__ for item in items]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/generate")
def generate(payload: GenerateRequest) -> dict:
    try:
        sources = list(STATE.get("sources") or [])
        if payload.selected_urls:
            selected = set(payload.selected_urls)
            sources = [item for item in sources if item.url in selected]
        if not sources:
            raise ValueError("请先采集热点，并至少选择一个来源。")
        article = audit_article(generate_article(sources), sources)
        STATE["article"] = article
        path = OUTPUT_DIR / f"article-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"article": article, "saved": path.name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/draft")
def draft(payload: DraftRequest) -> dict:
    if not all(os.getenv(k) for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET", "WECHAT_COVER_MEDIA_ID")):
        raise HTTPException(status_code=400, detail="微信公众号参数尚未配置完整。")
    try:
        result = create_wechat_draft(payload.article)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
