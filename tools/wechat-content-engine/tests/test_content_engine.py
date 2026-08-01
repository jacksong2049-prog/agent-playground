from types import SimpleNamespace

import content_engine


def test_collect_ignores_non_http_source_links(monkeypatch) -> None:
    feed = SimpleNamespace(
        entries=[
            {"title": "恶意来源", "link": "javascript:alert(1)", "summary": "摘要"},
            {"title": "正常来源", "link": "https://example.com/article", "summary": "摘要"},
        ]
    )
    monkeypatch.setattr(content_engine.feedparser, "parse", lambda _url: feed)

    items = content_engine.collect_rss_items(["https://example.com/feed"])

    assert [item.url for item in items] == ["https://example.com/article"]
