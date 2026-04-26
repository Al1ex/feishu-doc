#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import base64
import json
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

try:
    import cryptography
except ImportError:
    print("Need to install cryptography library")
    print("Run: pip install cryptography")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))

from crypto import (
    get_platform_key_dir, ensure_key_dir, has_key, generate_key, save_key,
    load_key, set_token, get_token, set_app_config, get_app_config, load_secrets, save_secrets
)


APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_REDIRECT_URI = "http://localhost:8239/callback"
AUTH_URL_TEMPLATE = "https://open.feishu.cn/open-apis/authen/v1/authorize?app_id={app_id}&redirect_uri={redirect_uri}&scope={scope}"


def get_authorization_url(app_id: str, scope: str = "") -> str:
    redirect_uri = urllib.parse.quote(FEISHU_REDIRECT_URI, safe="")
    scope_encoded = urllib.parse.quote(scope, safe="")
    return AUTH_URL_TEMPLATE.format(app_id=app_id, redirect_uri=redirect_uri, scope=scope_encoded)


def get_user_access_token(app_id: str, app_secret: str, code: str) -> Tuple[str, str]:
    url = "https://open.feishu.cn/open-apis/authen/v1/access_token"
    body = json.dumps({
        "grant_type": "authorization_code",
        "code": code,
        "app_id": app_id,
        "app_secret": app_secret
    }).encode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        if data.get("code"):
            raise RuntimeError(f"获取 token 失败: {data.get('msg')}")
        return data["data"]["access_token"], data["data"]["refresh_token"]


def refresh_user_access_token(app_id: str, app_secret: str, refresh_token: str) -> Tuple[str, str]:
    url = "https://open.feishu.cn/open-apis/authen/v1/refresh_access_token"
    body = json.dumps({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "app_id": app_id,
        "app_secret": app_secret
    }).encode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        if data.get("code"):
            raise RuntimeError(f"刷新 token 失败: {data.get('msg')}")
        return data["data"]["access_token"], data["data"]["refresh_token"]


def start_callback_server():
    import socket
    import http.server
    import threading
    import time

    # Global variable to store code
    callback_code = {"code": None}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in query:
                callback_code["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization Success! Close this window.</h1></body></html>")

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("localhost", 8239), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, callback_code


def wait_for_code(timeout=60):
    """Wait for authorization code from callback server"""
    import time
    server, callback_code = start_callback_server()
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if callback_code.get("code"):
            code = callback_code["code"]
            print(f"[Info] Code captured automatically!")
            return code
        time.sleep(0.5)
    
    print(f"[Info] Timeout after {timeout}s, please enter code manually")
    return None


def setup_interactive():
    print("=" * 50)
    print("飞书文档 Skill 授权设置")
    print("=" * 50)

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("\nPlease provide Feishu app credentials:")
        app_id = input("App ID (cli_xxxxx): ").strip()
        app_secret = input("App Secret: ").strip()

    if not app_id or not app_secret:
        print("[Error] App ID and App Secret are required")
        sys.exit(1)

    # First generate key, then save app config (encrypt needs key)
    ensure_key_dir()
    if not has_key():
        key = generate_key()
        save_key(key)
        print("[OK] Encryption key generated")
    else:
        print("[OK] Encryption key exists")

    set_app_config(app_id, app_secret)
    print(f"\n[OK] Credentials encrypted and saved")

    print("\nOpening Feishu authorization page...")
    scope = "docx:document wiki:wiki"
    auth_url = get_authorization_url(app_id, scope)
    # Mask sensitive info in log
    masked_url = auth_url.replace(f"app_id={app_id}", "app_id=***")
    print(f"Authorization URL: {masked_url}")
    webbrowser.open(auth_url)

    print("\nPlease complete authorization in browser,")
    print("then copy the code shown and paste it below.")
    print("(Or wait 60 seconds for automatic capture...)")

    # Start callback server and get the shared callback_code dict
    server, callback_code = start_callback_server()
    print("\n[Info] Callback server started on localhost:8239")
    print("[Info] Waiting for authorization... (checking every 0.5s)")

    # Wait for code with timeout - auto check
    start_time = time.time()
    code = None
    while time.time() - start_time < 60:
        code = callback_code.get("code")
        if code:
            print(f"[Info] Code captured: {code[:10]}***")
            break
        time.sleep(0.5)
    
    # If not captured, ask user
    if not code:
        print("\n[Info] Code not auto-captured, please enter manually")
        code = input("Authorization code: ").strip()

    if not code:
        print("[Error] Authorization code required")
        sys.exit(1)

    try:
        uat, refresh_token = get_user_access_token(app_id, app_secret, code)
        set_token("uat", uat, app_id)
        set_token("refresh", refresh_token, app_id)
        print("\n授权成功！")
        print(f"凭证已加密保存到: {get_platform_key_dir() / 'secrets.json'}")
    except Exception as e:
        print(f"授权失败: {e}")
        sys.exit(1)


def setup_env():
    global APP_ID, APP_SECRET

    if not APP_ID or not APP_SECRET:
        APP_ID = os.environ.get("FEISHU_APP_ID")
        APP_SECRET = os.environ.get("FEISHU_APP_SECRET")

    if not APP_ID or not APP_SECRET:
        print("错误: 请设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        print("或运行 'python auth.py setup' 进行交互式配置")
        sys.exit(1)

    ensure_key_dir()
    if not has_key():
        key = generate_key()
        save_key(key)
        print("加密密钥已生成")

    set_app_config(APP_ID, APP_SECRET)
    print("应用凭证已保存")


def refresh_token_if_needed():
    app_id, app_secret = get_app_config()
    if not app_id or not app_secret:
        return False

    try:
        refresh_token = get_token("refresh")
        if not refresh_token:
            return False

        print("正在刷新 token...")
        uat, new_refresh = refresh_user_access_token(app_id, app_secret, refresh_token)
        set_token("uat", uat, app_id)
        set_token("refresh", new_refresh, app_id)
        print("Token 已刷新")
        return True
    except Exception as e:
        print(f"Token 刷新失败: {e}")
        return False


def status():
    key_dir = get_platform_key_dir()
    print(f"Key directory: {key_dir}")
    print(f"Key exists: {has_key()}")

    app_id, _ = get_app_config()
    # Mask sensitive app_id
    if app_id:
        masked = app_id[:4] + "***" + app_id[-4:] if len(app_id) > 8 else "***"
        print(f"App ID: {masked}")
    else:
        print("App ID: not configured")

    secrets = load_secrets()
    token_types = list(secrets.get("tokens", {}).keys())
    print(f"Stored tokens: {token_types if token_types else 'none'}")

    if has_key():
        try:
            uat = get_token("uat")
            print(f"UAT status: {'decrypted' if uat else 'failed'}")
        except Exception as e:
            print(f"UAT status: failed - {e}")


def main():
    if len(sys.argv) < 2:
        print("用法: auth.py <命令>")
        print("命令:")
        print("  setup      交互式授权配置")
        print("  status     查看配置状态")
        print("  refresh    刷新 token")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "setup":
        setup_interactive()
    elif cmd == "status":
        status()
    elif cmd == "refresh":
        refresh_token_if_needed()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()