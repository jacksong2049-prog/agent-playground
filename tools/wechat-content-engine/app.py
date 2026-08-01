from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from audit_tools import audit_content
from content_engine import (
    audit_article,
    collect_rss_items,
    create_wechat_draft,
    env_list,
    generate_article,
    rank_items,
)
from wechat_media import upload_permanent_image

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI行动营内容引擎", version="0.3.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

STATE: dict[str, object] = {"sources": [], "article": None, "audit": None, "cover_media_id": ""}


@app.middleware("http")
async def require_admin_token(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method != "GET":
        expected = os.getenv("ADMIN_TOKEN", "")
        if not expected:
            return JSONResponse(status_code=503, content={"detail": "ADMIN_TOKEN 尚未配置"})
        authorization = request.headers.get("Authorization", "")
        supplied = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
        if not supplied or not secrets.compare_digest(supplied, expected):
            return JSONResponse(status_code=401, content={"detail": "未授权"})
    return await call_next(request)


class GenerateRequest(BaseModel):
    selected_urls: list[str] = Field(default_factory=list)


class AuditRequest(BaseModel):
    article: dict


class DraftRequest(BaseModel):
    article: dict
    acknowledged_warnings: bool = False
    cover_media_id: str = ""


def current_sources() -> list:
    return list(STATE.get("sources") or [])


def run_enhanced_audit(article: dict) -> dict:
    sources = current_sources()
    return audit_content(article, [item.summary for item in sources])


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status() -> dict:
    wechat_credentials = all(os.getenv(k) for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET"))
    cover_ready = bool(STATE.get("cover_media_id") or os.getenv("WECHAT_COVER_MEDIA_ID"))
    return {
        "openai_ready": bool(os.getenv("OPENAI_API_KEY")),
        "wechat_credentials_ready": wechat_credentials,
        "cover_ready": cover_ready,
        "wechat_ready": wechat_credentials and cover_ready,
        "rss_count": len(env_list("NEWS_RSS_URLS")),
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    }


@app.post("/api/collect")
def collect() -> dict:
    try:
        items = collect_rss_items(env_list("NEWS_RSS_URLS"), int(os.getenv("MAX_SOURCE_ITEMS", "30")))
        items = rank_items(items, env_list("TOPIC_KEYWORDS", "AI,agent,automation,startup"))
        STATE["sources"] = items
        STATE["article"] = None
        STATE["audit"] = None
        return {"items": [item.__dict__ for item in items]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/generate")
def generate(payload: GenerateRequest) -> dict:
    try:
        sources = current_sources()
        if payload.selected_urls:
            selected = set(payload.selected_urls)
            sources = [item for item in sources if item.url in selected]
        if not sources:
            raise ValueError("请先采集热点，并至少选择一个来源。")
        article = audit_article(generate_article(sources), sources)
        report = audit_content(article, [item.summary for item in sources])
        STATE["article"] = article
        STATE["audit"] = report
        path = OUTPUT_DIR / f"article-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps({"article": article, "audit": report}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"article": article, "audit": report, "saved": path.name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/audit")
def audit(payload: AuditRequest) -> dict:
    try:
        report = run_enhanced_audit(payload.article)
        STATE["article"] = payload.article
        STATE["audit"] = report
        return {"audit": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/cover")
async def upload_cover(file: UploadFile = File(...)) -> dict:
    if not all(os.getenv(k) for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET")):
        raise HTTPException(status_code=400, detail="请先配置微信公众号 AppID 和 AppSecret。")
    suffix = Path(file.filename or "cover.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".bmp"}:
        raise HTTPException(status_code=400, detail="封面仅支持 jpg、jpeg、png、gif、bmp。")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
        result = upload_permanent_image(temp_path)
        media_id = result["media_id"]
        STATE["cover_media_id"] = media_id
        return {"ok": True, "media_id": media_id, "url": result.get("url", "")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
        await file.close()


@app.post("/api/draft")
def draft(payload: DraftRequest) -> dict:
    if not all(os.getenv(k) for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET")):
        raise HTTPException(status_code=400, detail="微信公众号 AppID 或 AppSecret 尚未配置。")
    try:
        article = audit_article(dict(payload.article), current_sources())
    except (TypeError, ValueError, KeyError):
        raise HTTPException(status_code=400, detail="文章字段或来源校验失败") from None
    report = run_enhanced_audit(article)
    if not report["passed"]:
        raise HTTPException(status_code=400, detail="文章存在审核错误，请修正后再推送。")
    if report["warnings"] and not payload.acknowledged_warnings:
        raise HTTPException(status_code=400, detail="文章仍有审核警告，请勾选已人工复核后再推送。")
    media_id = payload.cover_media_id or str(STATE.get("cover_media_id") or "") or os.getenv("WECHAT_COVER_MEDIA_ID", "")
    if not media_id:
        raise HTTPException(status_code=400, detail="请先上传封面图，或配置 WECHAT_COVER_MEDIA_ID。")
    try:
        result = create_wechat_draft(article, media_id)
        return {"ok": True, "result": result, "audit": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
