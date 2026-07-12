from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import feedparser
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass
class SourceItem:
    title: str
    url: str
    summary: str
    published: str = ""


def env_list(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


def collect_rss_items(urls: Iterable[str], limit: int = 30) -> list[SourceItem]:
    items: list[SourceItem] = []
    seen: set[str] = set()
    for feed_url in urls:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            url = str(entry.get("link", "")).strip()
            title = str(entry.get("title", "")).strip()
            if not url or not title or url in seen:
                continue
            raw = str(entry.get("summary", entry.get("description", "")))
            summary = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
            items.append(SourceItem(title, url, summary[:800], str(entry.get("published", ""))))
            seen.add(url)
            if len(items) >= limit:
                return items
    return items


def rank_items(items: list[SourceItem], keywords: list[str]) -> list[SourceItem]:
    keys = [k.lower() for k in keywords]
    return sorted(
        items,
        key=lambda item: sum(f"{item.title} {item.summary}".lower().count(k) for k in keys),
        reverse=True,
    )


def generate_article(items: list[SourceItem]) -> dict:
    if not items:
        raise RuntimeError("No source items collected. Check NEWS_RSS_URLS.")
    sources = "\n\n".join(
        f"[{i + 1}] {x.title}\nURL: {x.url}\nPublished: {x.published}\nSummary: {x.summary}"
        for i, x in enumerate(items[:12])
    )
    prompt = f"""你是微信公众号“AI行动营”的主编。请基于下列公开来源写一篇原创中文文章。
读者是普通创业者、副业者和内容创作者。文章必须提炼一个总判断，解释热点背后的需求、机会和行动方案，而不是新闻拼盘。
只写来源支持的事实；不确定内容明确标注为判断，不得编造数字、日期、融资额或引语。
正文1800—2600字，短段落。输出JSON，字段为 title、digest、content_html、source_notes。
content_html仅用p、h2、strong、blockquote、ul、li、a标签。文末写“普通人现在可以做的3件事”。
source_notes为包含title和url的数组。

来源：
{sources}"""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        input=prompt,
        text={"format": {"type": "json_object"}},
    )
    return json.loads(response.output_text)


def audit_article(article: dict, sources: list[SourceItem]) -> dict:
    required = {"title", "digest", "content_html", "source_notes"}
    missing = required - set(article)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    if len(article["title"]) > 64:
        raise ValueError("WeChat title exceeds 64 characters")
    if len(article["digest"]) > 120:
        article["digest"] = article["digest"][:117] + "..."
    known_urls = {x.url for x in sources}
    unknown = [n.get("url") for n in article["source_notes"] if isinstance(n, dict) and n.get("url") not in known_urls]
    if unknown:
        raise ValueError(f"Unknown source URLs: {unknown}")
    return article


def get_wechat_access_token() -> str:
    response = httpx.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": os.environ["WECHAT_APP_ID"], "secret": os.environ["WECHAT_APP_SECRET"]},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data:
        raise RuntimeError(f"WeChat token error: {data}")
    return data["access_token"]


def create_wechat_draft(article: dict) -> dict:
    token = get_wechat_access_token()
    payload = {"articles": [{
        "title": article["title"],
        "author": os.getenv("WECHAT_AUTHOR", "JACKSONG"),
        "digest": article["digest"],
        "content": article["content_html"],
        "thumb_media_id": os.environ["WECHAT_COVER_MEDIA_ID"],
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }]}
    response = httpx.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token": token}, json=payload, timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode", 0) != 0:
        raise RuntimeError(f"WeChat draft error: {data}")
    return data


def main() -> None:
    sources = collect_rss_items(env_list("NEWS_RSS_URLS"), int(os.getenv("MAX_SOURCE_ITEMS", "30")))
    sources = rank_items(sources, env_list("TOPIC_KEYWORDS", "AI,agent,automation,startup"))
    article = audit_article(generate_article(sources), sources)
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"article-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)
    ready = all(os.getenv(k) for k in ("WECHAT_APP_ID", "WECHAT_APP_SECRET", "WECHAT_COVER_MEDIA_ID"))
    result = create_wechat_draft(article) if ready else "skipped: WeChat credentials incomplete"
    print(json.dumps({"saved": path, "wechat": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
