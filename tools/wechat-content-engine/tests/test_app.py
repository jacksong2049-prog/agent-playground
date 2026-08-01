from fastapi.testclient import TestClient

import app as app_module
from content_engine import SourceItem


client = TestClient(app_module.app)


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-secret"}


def test_write_api_rejects_missing_admin_token(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_TOKEN", "test-secret")

    response = client.post("/api/collect")

    assert response.status_code == 401
    assert response.json() == {"detail": "未授权"}


def test_generate_sanitizes_model_html_before_browser_preview(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_TOKEN", "test-secret")
    source = SourceItem("来源", "https://example.com/source", "摘要")
    app_module.STATE["sources"] = [source]
    monkeypatch.setattr(
        app_module,
        "generate_article",
        lambda _sources: {
            "title": "安全标题",
            "digest": "摘要",
            "content_html": (
                '<p>正文</p><script>alert(1)</script>'
                '<img src="x" onerror="alert(2)">'
                '<a href="javascript:alert(3)" onclick="alert(4)">链接</a>'
            ),
            "source_notes": [{"title": "来源", "url": source.url}],
        },
    )

    response = client.post("/api/generate", headers=auth_headers(), json={})

    assert response.status_code == 200
    html = response.json()["article"]["content_html"]
    assert "<script" not in html
    assert "onerror" not in html
    assert "onclick" not in html
    assert "javascript:" not in html
    assert "<p>正文</p>" in html


def test_draft_revalidates_edited_source_urls(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_TOKEN", "test-secret")
    monkeypatch.setenv("WECHAT_APP_ID", "app-id")
    monkeypatch.setenv("WECHAT_APP_SECRET", "app-secret")
    source = SourceItem("来源", "https://example.com/source", "摘要")
    app_module.STATE["sources"] = [source]
    called = False

    def create_draft(_article, _media_id):
        nonlocal called
        called = True
        return {"media_id": "draft-id"}

    monkeypatch.setattr(app_module, "create_wechat_draft", create_draft)
    article = {
        "title": "安全标题",
        "digest": "摘要",
        "content_html": "<p>正文内容足够完整。</p>" * 100,
        "source_notes": [{"title": "伪造来源", "url": "https://evil.example/claim"}],
    }

    response = client.post(
        "/api/draft",
        headers=auth_headers(),
        json={
            "article": article,
            "acknowledged_warnings": True,
            "cover_media_id": "cover-id",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "文章字段或来源校验失败"}
    assert called is False
