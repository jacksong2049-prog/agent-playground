from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Iterable

from bs4 import BeautifulSoup


@dataclass
class AuditIssue:
    level: str
    code: str
    message: str
    excerpt: str = ""


DEFAULT_SENSITIVE_WORDS = [
    "保证赚钱", "稳赚不赔", "零风险", "百分百成功", "内幕消息", "绝对安全",
]

RISK_PATTERNS = {
    "unsupported_number": re.compile(r"(?<![A-Za-z0-9_])\d+(?:\.\d+)?(?:%|亿|万|美元|人民币|元)"),
    "absolute_claim": re.compile(r"(一定会|必然|绝对|唯一|彻底取代|全部消失)"),
    "quote": re.compile(r"[“\"]([^”\"]{8,80})[”\"]"),
}


def _plain_text(content_html: str) -> str:
    return BeautifulSoup(content_html or "", "html.parser").get_text(" ", strip=True)


def audit_content(article: dict, source_summaries: Iterable[str] = ()) -> dict:
    issues: list[AuditIssue] = []
    title = str(article.get("title", "")).strip()
    digest = str(article.get("digest", "")).strip()
    text = _plain_text(str(article.get("content_html", "")))
    corpus = " ".join(source_summaries)

    if not title:
        issues.append(AuditIssue("error", "missing_title", "文章标题不能为空"))
    if len(title) > 64:
        issues.append(AuditIssue("error", "title_too_long", "标题超过微信公众号常用长度限制"))
    if not digest:
        issues.append(AuditIssue("warning", "missing_digest", "建议补充文章摘要"))
    if len(text) < 800:
        issues.append(AuditIssue("warning", "content_too_short", "正文偏短，可能不足以形成完整观点"))

    words = DEFAULT_SENSITIVE_WORDS + [
        x.strip() for x in os.getenv("CUSTOM_SENSITIVE_WORDS", "").split(",") if x.strip()
    ]
    for word in words:
        if word and word in f"{title} {digest} {text}":
            issues.append(AuditIssue("error", "sensitive_word", f"检测到高风险表述：{word}", word))

    for match in RISK_PATTERNS["absolute_claim"].finditer(text):
        issues.append(AuditIssue("warning", "absolute_claim", "检测到绝对化表达，建议改为有条件判断", match.group(0)))

    for match in RISK_PATTERNS["unsupported_number"].finditer(text):
        value = match.group(0)
        if value not in corpus:
            issues.append(AuditIssue("warning", "number_not_in_sources", "正文数字未在采集摘要中直接找到，请人工核验", value))

    for match in RISK_PATTERNS["quote"].finditer(text):
        quote = match.group(1)
        if quote not in corpus:
            issues.append(AuditIssue("warning", "quote_not_in_sources", "正文引语未在采集摘要中直接找到，请核验原文", quote[:60]))

    source_notes = article.get("source_notes") or []
    if len(source_notes) < 2:
        issues.append(AuditIssue("warning", "few_sources", "引用来源少于2个，建议增加交叉验证"))

    errors = sum(i.level == "error" for i in issues)
    warnings = sum(i.level == "warning" for i in issues)
    return {
        "passed": errors == 0,
        "errors": errors,
        "warnings": warnings,
        "issues": [asdict(i) for i in issues],
    }
