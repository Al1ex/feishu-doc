import base64
import json
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("需要安装 cryptography 库: pip install cryptography")
    sys.exit(1)


PLATFORM_KEY_DIR = Path.home() / ".feishu-claude"
KEY_FILE = PLATFORM_KEY_DIR / "key.bin"
SECRETS_FILE = PLATFORM_KEY_DIR / "secrets.json"

KEY_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits


def get_platform_key_dir() -> Path:
    return PLATFORM_KEY_DIR


def ensure_key_dir() -> None:
    PLATFORM_KEY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(PLATFORM_KEY_DIR), 0o700)
    except Exception:
        pass


def generate_key() -> bytes:
    return os.urandom(KEY_SIZE)


def load_key() -> Optional[bytes]:
    if not KEY_FILE.exists():
        return None
    key = KEY_FILE.read_bytes()
    if len(key) != KEY_SIZE:
        raise ValueError(f"密钥长度错误: 期望 {KEY_SIZE} 字节, 实际 {len(key)} 字节")
    return key


def save_key(key: bytes) -> None:
    ensure_key_dir()
    KEY_FILE.write_bytes(key)
    try:
        os.chmod(str(KEY_FILE), 0o600)
    except Exception:
        pass


def has_key() -> bool:
    return KEY_FILE.exists() and KEY_FILE.stat().st_size == KEY_SIZE


def encrypt_token(plaintext: str, aad: Optional[str] = None) -> Tuple[str, str, str]:
    key = load_key()
    if key is None:
        raise ValueError("密钥不存在，请先运行 auth.py setup")

    nonce = os.urandom(NONCE_SIZE)
    aad_bytes = aad.encode() if aad else None

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), aad_bytes)

    return (
        base64.b64encode(ciphertext).decode(),
        base64.b64encode(nonce).decode(),
        base64.b64encode(aad_bytes).decode() if aad_bytes else ""
    )


def decrypt_token(ciphertext_b64: str, nonce_b64: str, aad: Optional[str] = None) -> str:
    key = load_key()
    if key is None:
        raise ValueError("密钥不存在")

    ciphertext = base64.b64decode(ciphertext_b64)
    nonce = base64.b64decode(nonce_b64)
    
    # 处理 AAD：如果是 base64 编码则先解码
    if aad:
        # 检查是否看起来像 base64 编码（包含 = 或特殊字符）
        if '=' in aad or len(aad) > 20:
            try:
                aad_bytes = base64.b64decode(aad)
            except Exception:
                aad_bytes = aad.encode()
        else:
            aad_bytes = aad.encode()
    else:
        aad_bytes = None

    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)

    return plaintext.decode()


def load_secrets() -> dict:
    if not SECRETS_FILE.exists():
        return {}
    return json.loads(SECRETS_FILE.read_text(encoding="utf-8"))


def save_secrets(secrets: dict) -> None:
    ensure_key_dir()
    SECRETS_FILE.write_text(json.dumps(secrets, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(str(SECRETS_FILE), 0o600)
    except Exception:
        pass


def set_token(token_type: str, token: str, aad: Optional[str] = None) -> None:
    ciphertext, nonce, aad_b64 = encrypt_token(token, aad)

    secrets = load_secrets()
    secrets.setdefault("tokens", {})
    secrets["tokens"][token_type] = {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "aad": aad_b64,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

    save_secrets(secrets)


def get_token(token_type: str) -> Optional[str]:
    secrets = load_secrets()
    token_data = secrets.get("tokens", {}).get(token_type)
    if not token_data:
        return None

    try:
        return decrypt_token(
            token_data["ciphertext"],
            token_data["nonce"],
            token_data.get("aad") or None
        )
    except Exception as e:
        raise ValueError(f"解密 token 失败: {e}")


def set_app_config(app_id: str, app_secret: str) -> None:
    secrets = load_secrets()
    secrets["app_id"] = app_id
    secrets["app_secret"] = app_secret
    secrets["version"] = 1
    save_secrets(secrets)


def set_app_config(app_id: str, app_secret: str) -> None:
    """Set app config with app_secret encrypted"""
    ciphertext, nonce, aad_b64 = encrypt_token(app_secret, app_id)

    secrets = load_secrets()
    secrets["version"] = 1
    secrets["app_id"] = app_id
    secrets["app_secret"] = {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "aad": aad_b64
    }
    save_secrets(secrets)


def get_app_config() -> Tuple[Optional[str], Optional[str]]:
    """Get app config with app_secret decrypted"""
    secrets = load_secrets()
    app_id = secrets.get("app_id")
    
    app_secret_data = secrets.get("app_secret")
    if isinstance(app_secret_data, dict) and app_secret_data.get("ciphertext"):
        try:
            app_secret = decrypt_token(
                app_secret_data["ciphertext"],
                app_secret_data["nonce"],
                app_secret_data.get("aad") or None
            )
        except Exception:
            app_secret = None
    else:
        app_secret = None
    
    return app_id, app_secret


def rotate_key() -> bytes:
    old_key = load_key()
    new_key = generate_key()
    save_key(new_key)

    secrets = load_secrets()
    if "tokens" in secrets:
        for token_type, token_data in list(secrets["tokens"].items()):
            if old_key and token_data.get("ciphertext"):
                try:
                    old_plaintext = decrypt_token(
                        token_data["ciphertext"],
                        token_data["nonce"],
                        token_data.get("aad") or None
                    )
                    new_ciphertext, new_nonce, new_aad = encrypt_token(old_plaintext, token_data.get("aad"))
                    secrets["tokens"][token_type] = {
                        "ciphertext": new_ciphertext,
                        "nonce": new_nonce,
                        "aad": new_aad,
                        "timestamp": __import__("datetime").datetime.now().isoformat()
                    }
                except Exception:
                    pass
        save_secrets(secrets)

    return new_key


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        ensure_key_dir()
        if not has_key():
            key = generate_key()
            save_key(key)
            print(f"密钥已生成: {KEY_FILE}")
        else:
            print("密钥已存在")

        secrets = load_secrets()
        if not secrets:
            save_secrets({"version": 1, "tokens": {}})
            print(f"密文文件已初始化: {SECRETS_FILE}")
        else:
            print("密文文件已存在")