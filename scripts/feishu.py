#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# Force UTF-8 encoding FIRST, before any output
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Also try to set stdout/stderr encoding directly
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

from feishu_client import FeishuMCPClient
from url_parser import parse_url


class DocOrchestrator:
    def __init__(self):
        self.client = FeishuMCPClient()

    def read_document(self, url: str) -> Dict[str, Any]:
        parsed = parse_url(url)
        doc_type = parsed.get("type")
        doc_id = parsed.get("id")

        if not doc_id:
            raise ValueError(f"Cannot parse URL: {url}")

        if doc_type == "doc":
            return self.client.fetch_doc(doc_id)
        elif doc_type == "wiki":
            return self.client.fetch_doc(doc_id)
        elif doc_type == "bitable":
            return self.client.fetch_bitable(doc_id)
        elif doc_type == "whiteboard":
            return self.client.fetch_whiteboard(doc_id)
        else:
            raise ValueError(f"Unsupported type: {doc_type}")

    def create_document(self, title: str, content: Optional[str] = None, doc_type: str = "doc") -> Dict[str, Any]:
        if doc_type == "doc":
            return self.client.create_doc(title, content)
        elif doc_type == "wiki":
            return self.client.create_doc(title, content)
        elif doc_type == "bitable":
            return self.client.create_bitable(title)
        elif doc_type == "whiteboard":
            return self.client.create_whiteboard(title)
        else:
            raise ValueError(f"Unsupported type: {doc_type}")

    def update_document(self, url: str, content: str, mode: str = "append") -> Dict[str, Any]:
        parsed = parse_url(url)
        doc_type = parsed.get("type")
        doc_id = parsed.get("id")

        if not doc_id:
            raise ValueError(f"Cannot parse URL: {url}")

        if doc_type in ("doc", "wiki"):
            return self.client.update_doc(doc_id, content, mode)
        elif doc_type == "bitable":
            return {"error": "bitable not supported, use update_bitable"}
        elif doc_type == "whiteboard":
            return self.client.update_whiteboard(doc_id, {"content": content})
        else:
            raise ValueError(f"Unsupported type: {doc_type}")

    def search_documents(self, keyword: str) -> Dict[str, Any]:
        return self.client.search_doc(keyword)

    def list_documents(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        return self.client.list_docs(node_id)

    def get_document_comments(self, url: str) -> Dict[str, Any]:
        parsed = parse_url(url)
        doc_id = parsed.get("id")
        if not doc_id:
            raise ValueError(f"Cannot parse URL: {url}")
        return self.client.get_comments(doc_id)

    def add_document_comment(self, url: str, comment: str) -> Dict[str, Any]:
        parsed = parse_url(url)
        doc_id = parsed.get("id")
        if not doc_id:
            raise ValueError(f"Cannot parse URL: {url}")
        return self.client.add_comments(doc_id, comment)


def main():
    if len(sys.argv) < 2:
        print("Feishu Doc CLI")
        print("")
        print("Usage: feishu.py <command> [args...]")
        print("")
        print("Commands:")
        print("  create <title> [content]     Create a new document")
        print("  read <url>                 Read document")
        print("  update <url> <content>      Update document")
        print("  search <keyword>           Search documents")
        print("  list                      List documents")
        print("  comments <url>            Get comments")
        print("  status                   Show config status")
        print("  setup                    Initial setup")
        print("  help                     Show this help")
        print("")
        print("Examples:")
        print("  feishu.py create \"My Doc\"")
        print("  feishu.py read \"https://xxx.feishu.cn/docx/xxx\"")
        print("  feishu.py search \"project\"")
        sys.exit(1)

    cmd = sys.argv[1]

    # Special commands that don't need orchestrator
    if cmd == "status":
        from auth import status as check_status
        check_status()
        return

    if cmd == "setup":
        import auth
        auth.setup_interactive()
        return

    if cmd == "help":
        print("Feishu Doc CLI")
        print("")
        print("Usage: feishu.py <command> [args...]")
        print("")
        print("Commands:")
        print("  create <title> [content]     Create a new document")
        print("  read <url>                 Read document")
        print("  update <url> <content>      Update document")
        print("  search <keyword>           Search documents")
        print("  list                      List documents")
        print("  comments <url>            Get comments")
        print("  status                   Show config status")
        print("  setup                    Initial setup")
        print("  help                     Show this help")
        return

    # Commands that need orchestrator
    orchestrator = DocOrchestrator()

    try:
        if cmd == "read":
            if len(sys.argv) < 3:
                print("Usage: feishu.py read <url>", file=sys.stderr)
                sys.exit(1)
            url = sys.argv[2]
            result = orchestrator.read_document(url)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "create":
            if len(sys.argv) < 3:
                print("Usage: feishu.py create <title> [content]", file=sys.stderr)
                sys.exit(1)
            title = sys.argv[2]
            content = sys.argv[3] if len(sys.argv) > 3 else None
            result = orchestrator.create_document(title, content)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "update":
            if len(sys.argv) < 4:
                print("Usage: feishu.py update <url> <content>", file=sys.stderr)
                sys.exit(1)
            url = sys.argv[2]
            # Join all remaining args as content (supports multi-word content)
            # Use quotes around content or join with spaces
            if len(sys.argv) > 4 and sys.argv[3].startswith('"'):
                # Handle quoted content: update "url" "content with spaces"
                content = " ".join(sys.argv[3:]).strip('"')
            else:
                content = " ".join(sys.argv[3:])
            if not content:
                print("Error: content cannot be empty", file=sys.stderr)
                sys.exit(1)
            result = orchestrator.update_document(url, content)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "search":
            if len(sys.argv) < 3:
                print("Usage: feishu.py search <keyword>", file=sys.stderr)
                sys.exit(1)
            keyword = sys.argv[2]
            result = orchestrator.search_documents(keyword)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "list":
            node_id = sys.argv[2] if len(sys.argv) > 2 else None
            result = orchestrator.list_documents(node_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "comments":
            if len(sys.argv) < 3:
                print("Usage: feishu.py comments <url>", file=sys.stderr)
                sys.exit(1)
            url = sys.argv[2]
            result = orchestrator.get_document_comments(url)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            print("Run: feishu.py help", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()