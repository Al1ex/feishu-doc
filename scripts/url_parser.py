import re
from typing import Optional, Tuple


DOC_URL_PATTERN = re.compile(r"https?://[\w.-]+\.feishu\.cn/(docx|document)/([A-Za-z0-9_-]+)")
WIKI_URL_PATTERN = re.compile(r"https?://[\w.-]+\.feishu\.cn/wiki/([A-Za-z0-9_-]+)")
BASE_URL_PATTERN = re.compile(r"https?://[\w.-]+\.feishu\.cn/base/([A-Za-z0-9_-]+)")
WHITEBOARD_URL_PATTERN = re.compile(r"https?://[\w.-]+\.feishu\.cn/whiteboard/([A-Za-z0-9_-]+)")


def parse_doc_url(url: str) -> Optional[Tuple[str, str]]:
    match = DOC_URL_PATTERN.match(url)
    if match:
        doc_type = match.group(1)
        doc_id = match.group(2)
        return doc_type, doc_id
    return None


def parse_wiki_url(url: str) -> Optional[str]:
    match = WIKI_URL_PATTERN.match(url)
    if match:
        return match.group(1)
    return None


def parse_base_url(url: str) -> Optional[Tuple[str, Optional[str]]]:
    match = BASE_URL_PATTERN.match(url)
    if match:
        app_id = match.group(1)
        return app_id, None
    return None


def parse_whiteboard_url(url: str) -> Optional[str]:
    match = WHITEBOARD_URL_PATTERN.match(url)
    if match:
        return match.group(1)
    return None


def parse_url(url: str) -> dict:
    result = {"type": None, "id": None, "raw": url}

    if parsed := parse_doc_url(url):
        result["type"] = "doc"
        result["doc_type"] = parsed[0]
        result["id"] = parsed[1]
    elif parsed := parse_wiki_url(url):
        result["type"] = "wiki"
        result["id"] = parsed
    elif parsed := parse_base_url(url):
        result["type"] = "bitable"
        result["id"] = parsed[0]
    elif parsed := parse_whiteboard_url(url):
        result["type"] = "whiteboard"
        result["id"] = parsed

    return result


if __name__ == "__main__":
    import sys

    test_urls = [
        "https://abc.feishu.cn/docx/ABC123def456ghi",
        "https://xyz.feishu.cn/wiki/DEF456ghi789jkl",
        "https://test.feishu.cn/base/GHI789jkl012mno",
        "https://demo.feishu.cn/whiteboard/PQR012stu345vwx",
    ]

    for url in test_urls:
        result = parse_url(url)
        print(f"{url} -> {result}")