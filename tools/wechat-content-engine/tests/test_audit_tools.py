from audit_tools import audit_content


def article(content: str, title: str = "测试标题") -> dict:
    return {
        "title": title,
        "digest": "测试摘要",
        "content_html": f"<p>{content}</p>" * 120,
        "source_notes": [
            {"title": "来源一", "url": "https://example.com/1"},
            {"title": "来源二", "url": "https://example.com/2"},
        ],
    }


def test_clean_article_passes() -> None:
    report = audit_content(article("AI产品需要从真实需求出发，并通过小范围测试持续验证。"))
    assert report["passed"] is True
    assert report["errors"] == 0


def test_sensitive_claim_blocks_draft() -> None:
    report = audit_content(article("这个项目保证赚钱。"))
    assert report["passed"] is False
    assert any(item["code"] == "sensitive_word" for item in report["issues"])


def test_unsupported_number_is_warning() -> None:
    report = audit_content(article("市场规模达到100亿元。"), ["行业正在增长"])
    assert report["passed"] is True
    assert any(item["code"] == "number_not_in_sources" for item in report["issues"])


def test_number_supported_by_source_is_not_flagged() -> None:
    report = audit_content(article("市场规模达到100亿元。"), ["市场规模达到100亿元"])
    assert not any(item["code"] == "number_not_in_sources" for item in report["issues"])
