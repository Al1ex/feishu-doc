# -*- coding: utf-8 -*-
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import base64
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from crypto import get_token, get_app_config, set_token, set_app_config


MCP_URL = "https://mcp.feishu.cn/mcp"
DEFAULT_TOOLS = [
    "search-user", "get-user", "fetch-file",
    "search-doc", "create-doc", "fetch-doc", "update-doc", "list-docs", "get-comments", "add-comments",
    "fetch-bitable", "create-bitable", "update-bitable",
    "fetch-whiteboard", "create-whiteboard", "update-whiteboard",
    "list-wiki", "get-wiki-node"
]


class FeishuMCPClient:
    def __init__(self, tool_names: Optional[list] = None):
        self.tool_names = tool_names or DEFAULT_TOOLS
        self._uat = None

    @property
    def uat(self) -> Optional[str]:
        if self._uat is None:
            try:
                self._uat = get_token("uat")
            except Exception:
                pass
        return self._uat

    def _build_headers(self, additional_tools: Optional[list] = None) -> Dict[str, str]:
        tools = self.tool_names + (additional_tools or [])
        headers = {
            "Content-Type": "application/json",
            "X-Lark-MCP-Allowed-Tools": ",".join(tools)
        }
        if self.uat:
            headers["X-Lark-MCP-UAT"] = self.uat
        else:
            app_id, app_secret = get_app_config()
            if app_id and app_secret:
                headers["X-Lark-MCP-TAT"] = self._get_tat(app_id, app_secret)
        return headers

    def _get_tat(self, app_id: str, app_secret: str) -> str:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        body = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data.get("tenant_access_token", "")
        except Exception as e:
            raise RuntimeError(f"获取 TAT 失败: {e}")

    def _call(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        body = {
            "jsonrpc": "2.0",
            "id": id(self),
            "method": method,
            "params": params or {}
        }

        headers = self._build_headers()
        full_headers = {k: v for k, v in headers.items() if v}

        req = urllib.request.Request(
            MCP_URL,
            data=json.dumps(body).encode(),
            headers=full_headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                if "result" in result:
                    content = result["result"].get("content", [])
                    if content and content[0].get("type") == "text":
                        try:
                            return json.loads(content[0]["text"])
                        except json.JSONDecodeError:
                            return {"text": content[0]["text"]}
                    return result["result"]
                elif "error" in result:
                    raise RuntimeError(f"MCP 错误: {result['error']}")
                return result
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP 错误 {e.code}: {e.read().decode()}")
        except Exception as e:
            raise RuntimeError(f"请求失败: {e}")

    def initialize(self) -> Dict[str, Any]:
        return self._call("initialize")

    def list_tools(self) -> list:
        result = self._call("tools/list")
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._call("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

    def search_doc(self, keyword: str, doc_types: Optional[list] = None) -> Dict[str, Any]:
        return self.call_tool("search-doc", {
            "keyword": keyword,
            "doc_type": doc_types or ["doc", "docx"]
        })

    def fetch_doc(self, doc_id: str) -> Dict[str, Any]:
        return self.call_tool("fetch-doc", {"doc_id": doc_id})

    def create_doc(self, title: str, content: Optional[str] = None, parent_node_id: Optional[str] = None) -> Dict[str, Any]:
        args = {"title": title}
        if content:
            args["content"] = content
        if parent_node_id:
            args["parent_node_id"] = parent_node_id
        return self.call_tool("create-doc", args)

    def update_doc(self, doc_id: str, content: str, mode: str = "append") -> Dict[str, Any]:
        return self.call_tool("update-doc", {
            "doc_id": doc_id,
            "markdown": content,
            "mode": mode
        })

    def list_docs(self, node_id: Optional[str] = None, page_size: int = 20, my_library: bool = True) -> Dict[str, Any]:
        args = {"page_size": page_size, "my_library": my_library}
        if node_id:
            args["node_id"] = node_id
        return self.call_tool("list-docs", args)

    def get_comments(self, doc_id: str) -> Dict[str, Any]:
        return self.call_tool("get-comments", {"doc_id": doc_id})

    def add_comments(self, doc_id: str, comment: str) -> Dict[str, Any]:
        return self.call_tool("add-comments", {"doc_id": doc_id, "comment": comment})

    def fetch_bitable(self, app_id: str, table_id: Optional[str] = None) -> Dict[str, Any]:
        args = {"app_id": app_id}
        if table_id:
            args["table_id"] = table_id
        return self.call_tool("fetch-bitable", args)

    def create_bitable(self, name: str) -> Dict[str, Any]:
        return self.call_tool("create-bitable", {"name": name})

    def update_bitable(self, app_id: str, table_id: str, data: Dict) -> Dict[str, Any]:
        return self.call_tool("update-bitable", {
            "app_id": app_id,
            "table_id": table_id,
            "data": data
        })

    def fetch_whiteboard(self, node_id: str) -> Dict[str, Any]:
        return self.call_tool("fetch-whiteboard", {"node_id": node_id})

    def create_whiteboard(self, title: str) -> Dict[str, Any]:
        return self.call_tool("create-whiteboard", {"title": title})

    def update_whiteboard(self, node_id: str, content: Dict) -> Dict[str, Any]:
        return self.call_tool("update-whiteboard", {
            "node_id": node_id,
            "content": content
        })

    def search_user(self, keyword: str) -> Dict[str, Any]:
        return self.call_tool("search-user", {"keyword": keyword})

    def get_user(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        args = {}
        if user_id:
            args["user_id"] = user_id
        return self.call_tool("get-user", args)


def main():
    if len(sys.argv) < 2:
        print("用法: feishu_client.py <命令> [参数...]")
        print("命令:")
        print("  init              初始化配置")
        print("  list              列出可用工具")
        print("  fetch <doc_id>   读取文档")
        print("  create <title>   创建文档")
        print("  update <doc_id> <content>  更新文档")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        client = FeishuMCPClient()
        result = client.initialize()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    try:
        client = FeishuMCPClient()
    except Exception as e:
        print(f"初始化失败: {e}", file=sys.stderr)
        sys.exit(1)

    if cmd == "list":
        result = client.list_tools()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "fetch":
        if len(sys.argv) < 3:
            print("用法: fetch <doc_id>", file=sys.stderr)
            sys.exit(1)
        doc_id = sys.argv[2]
        result = client.fetch_doc(doc_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "create":
        if len(sys.argv) < 3:
            print("用法: create <title>", file=sys.stderr)
            sys.exit(1)
        title = sys.argv[2]
        result = client.create_doc(title)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "update":
        if len(sys.argv) < 4:
            print("用法: update <doc_id> <content>", file=sys.stderr)
            sys.exit(1)
        doc_id = sys.argv[2]
        content = sys.argv[3]
        result = client.update_doc(doc_id, content)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()