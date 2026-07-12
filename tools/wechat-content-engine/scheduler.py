from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from audit_tools import audit_content
from content_engine import audit_article, collect_rss_items, env_list, generate_article, rank_items

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


def generate_scheduled_candidate() -> dict:
    sources = collect_rss_items(
        env_list("NEWS_RSS_URLS"), int(os.getenv("MAX_SOURCE_ITEMS", "30"))
    )
    sources = rank_items(
        sources, env_list("TOPIC_KEYWORDS", "AI,agent,automation,startup")
    )
    article = audit_article(generate_article(sources), sources)
    audit = audit_content(article, (x.summary for x in sources))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"scheduled-candidate-{stamp}.json"
    payload = {
        "status": "awaiting_manual_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article": article,
        "audit": audit,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"saved": str(path), "audit": audit}, ensure_ascii=False))
    return payload


def main() -> None:
    hour = int(os.getenv("SCHEDULE_HOUR", "6"))
    minute = int(os.getenv("SCHEDULE_MINUTE", "0"))
    timezone_name = os.getenv("SCHEDULE_TIMEZONE", "Asia/Shanghai")

    scheduler = BlockingScheduler(timezone=timezone_name)
    scheduler.add_job(
        generate_scheduled_candidate,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily-content-candidate",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    print(f"Scheduler started: {hour:02d}:{minute:02d} {timezone_name}")
    scheduler.start()


if __name__ == "__main__":
    main()
