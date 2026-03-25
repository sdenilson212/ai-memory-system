"""
security/encryptor.py — AES-256-GCM Encryptor
加密器

职责 (Responsibility):
    用 AES-256-GCM 对敏感字符串进行加密和解密，密文存储在 secure/encrypted.json。
    使用 PBKDF2-HMAC-SHA256 从用户提供的 passphrase 派生加密密钥。

passphrase 管理方式（优先级从高到低）：
    1. 调用方显式传入 passphrase 参数（最高优先级，适合程序内部调用）
    2. 环境变量 MEMORY_PASSPHRASE（推荐生产环境，如：export MEMORY_PASSPHRASE="your-strong-pass"）
    3. 未提供且内容被检测为敏感：存储脱敏版本而不加密（降级安全模式）

设置环境变量示例：
    Windows:  $env:MEMORY_PASSPHRASE = "your-strong-passphrase"
    Linux/Mac: export MEMORY_PASSPHRASE="your-strong-passphrase"
    .env 文件（推荐）: MEMORY_PASSPHRASE=your-strong-passphrase（配合 python-dotenv）

注意：
    - passphrase 不会被记录到任何日志或存储文件中
    - 忘记 passphrase 将永久无法解密（无后门），请务必备份

暴露接口 (Exposes):
    Encryptor.encrypt(key, plaintext, passphrase) -> entry_id
    Encryptor.decrypt(entry_id, passphrase) -> plaintext
    Encryptor.delete(entry_id, passphrase) -> bool
    Encryptor.list_keys() -> list[dict]
    Encryptor.get_passphrase(explicit=None) -> str | None  # 新增：统一获取 passphrase

依赖 (Depends on):
    cryptography, json, pathlib, os, hashlib (stdlib)

禁止 (Must NOT):
    - 在日志中记录明文或 passphrase
    - 存储 passphrase 到任何地方
    - 在返回值中包含密文或 IV
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_PBKDF2_ITERATIONS = 600_000    # OWASP 2023 推荐值
_SALT_SIZE        = 32          # bytes
_NONCE_SIZE       = 12          # bytes — GCM 标准 96-bit nonce
_KEY_SIZE         = 32          # bytes — AES-256


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EncryptedEntry:
    """加密条目的存储格式 / Storage format for an encrypted entry."""
    id: str
    key_name: str           # 人类可读的键名，如 "openai_api_key"
    category: str           # password | api_key | personal_id | financial | other
    ciphertext_hex: str     # 密文（hex 编码）
    nonce_hex: str          # GCM nonce（hex 编码）
    salt_hex: str           # PBKDF2 salt（hex 编码）
    hint: str               # 可选的非敏感提示信息
    created_at: str         # ISO 8601
    last_accessed: str      # ISO 8601


class DecryptionError(Exception):
    """Raised when decryption fails (wrong passphrase or corrupted data)."""
    pass


class EntryNotFoundError(Exception):
    """Raised when the requested entry_id does not exist."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Encryptor
# ─────────────────────────────────────────────────────────────────────────────

class Encryptor:
    """
    AES-256-GCM encryptor with PBKDF2 key derivation.
    Stores ciphertext in a JSON file at secure_dir/encrypted.json.

    Usage / 使用示例:
        enc = Encryptor(Path("memory-bank/secure"))

        entry_id = enc.encrypt(
            key="openai_api_key",
            plaintext="sk-abc123",
            passphrase="my-strong-passphrase",
            category="api_key",
        )

        plaintext = enc.decrypt(entry_id, passphrase="my-strong-passphrase")
        # → "sk-abc123"

        keys = enc.list_keys()
        # → [{"id": "...", "key_name": "openai_api_key", "category": "api_key", ...}]
    """

    def __init__(self, secure_dir: Path) -> None:
        """
        Args:
            secure_dir: 存储 encrypted.json 的目录路径。
                        Directory where encrypted.json will be stored.
        Raises:
            OSError: 如果目录无法创建。
        """
        self._secure_dir = Path(secure_dir)
        self._store_path = self._secure_dir / "encrypted.json"
        self._secure_dir.mkdir(parents=True, exist_ok=True)

    # ── Public Interface ──────────────────────────────────────────────────────

    @staticmethod
    def get_passphrase(explicit: str | None = None) -> str | None:
        """
        统一获取 passphrase 的入口，优先级：显式传入 > 环境变量 > None。

        Args:
            explicit: 调用方显式传入的 passphrase（None 表示未提供）。

        Returns:
            passphrase 字符串，或 None（表示无可用 passphrase）。

        使用示例：
            passphrase = Encryptor.get_passphrase(explicit=user_input)
            if passphrase:
                entry_id = enc.encrypt("my_key", secret, passphrase)
            else:
                # 无 passphrase，降级为脱敏存储
                ...
        """
        if explicit:
            return explicit
        env_pass = os.environ.get("MEMORY_PASSPHRASE", "").strip()
        return env_pass if env_pass else None

    def encrypt(
        self,
        key: str,
        plaintext: str,
        passphrase: str,
        category: str = "other",
        hint: str = "",
    ) -> str:
        """
        Encrypt plaintext and store the ciphertext. Returns the entry_id.
        加密明文并存储密文，返回 entry_id 供 LTM 引用。

        Args:
            key:        人类可读键名，如 "openai_api_key"。
            plaintext:  要加密的明文字符串。
            passphrase: 用于派生加密密钥的密码短语。
            category:   分类标签（password / api_key / personal_id / financial / other）。
            hint:       可选的非敏感提示（不含任何敏感信息！）。

        Returns:
            entry_id: 字符串 UUID，用于后续解密/删除操作。

        Raises:
            ValueError: 如果 key、plaintext 或 passphrase 为空。
        """
        if not key or not plaintext or not passphrase:
            raise ValueError("key, plaintext, and passphrase must all be non-empty.")

        salt   = os.urandom(_SALT_SIZE)
        nonce  = os.urandom(_NONCE_SIZE)
        dk     = self._derive_key(passphrase, salt)
        aesgcm = AESGCM(dk)

        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        entry = EncryptedEntry(
            id=str(uuid.uuid4()),
            key_name=key,
            category=category,
            ciphertext_hex=ciphertext.hex(),
            nonce_hex=nonce.hex(),
            salt_hex=salt.hex(),
            hint=hint,
            created_at=_now_iso(),
            last_accessed=_now_iso(),
        )

        store = self._load_store()
        store.append(asdict(entry))
        self._save_store(store)

        return entry.id

    def decrypt(self, entry_id: str, passphrase: str) -> str:
        """
        Decrypt and return the plaintext for the given entry_id.
        解密并返回指定条目的明文。

        Args:
            entry_id:   encrypt() 返回的 UUID 字符串。
            passphrase: 加密时使用的密码短语。

        Returns:
            解密后的明文字符串。

        Raises:
            EntryNotFoundError: 如果 entry_id 不存在。
            DecryptionError:    如果 passphrase 错误或数据已损坏。
        """
        if not entry_id or not passphrase:
            raise ValueError("entry_id and passphrase must be non-empty.")

        store = self._load_store()
        raw = next((e for e in store if e["id"] == entry_id), None)
        if raw is None:
            raise EntryNotFoundError(f"Entry '{entry_id}' not found.")

        try:
            salt       = bytes.fromhex(raw["salt_hex"])
            nonce      = bytes.fromhex(raw["nonce_hex"])
            ciphertext = bytes.fromhex(raw["ciphertext_hex"])
            dk         = self._derive_key(passphrase, salt)
            aesgcm     = AESGCM(dk)
            plaintext  = aesgcm.decrypt(nonce, ciphertext, None)
        except InvalidTag:
            raise DecryptionError(
                "Decryption failed: incorrect passphrase or corrupted data."
            )
        except Exception as exc:
            raise DecryptionError(f"Decryption error: {exc}") from exc

        # 更新 last_accessed（不暴露明文）
        self._touch_entry(store, entry_id)

        return plaintext.decode("utf-8")

    def delete(self, entry_id: str, passphrase: str) -> bool:
        """
        Delete an encrypted entry after verifying the passphrase.
        验证 passphrase 后删除加密条目。

        Args:
            entry_id:   要删除的条目 ID。
            passphrase: 用于验证身份的密码短语（必须能成功解密才允许删除）。

        Returns:
            True 如果成功删除，False 如果条目不存在。

        Raises:
            DecryptionError: 如果 passphrase 错误（拒绝删除）。
        """
        # 验证 passphrase — 如果解密失败会抛出异常，阻止删除
        self.decrypt(entry_id, passphrase)

        store = self._load_store()
        original_len = len(store)
        store = [e for e in store if e["id"] != entry_id]

        if len(store) == original_len:
            return False

        self._save_store(store)
        return True

    def list_keys(self) -> list[dict]:
        """
        Return index of all encrypted entries WITHOUT exposing ciphertext.
        返回所有加密条目的索引，不含密文或任何敏感字段。

        Returns:
            List of dicts with: id, key_name, category, hint, created_at, last_accessed.
        """
        store = self._load_store()
        return [
            {
                "id":            e["id"],
                "key_name":      e["key_name"],
                "category":      e["category"],
                "hint":          e.get("hint", ""),
                "created_at":    e["created_at"],
                "last_accessed": e["last_accessed"],
            }
            for e in store
        ]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """PBKDF2-HMAC-SHA256 key derivation."""
        return hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=passphrase.encode("utf-8"),
            salt=salt,
            iterations=_PBKDF2_ITERATIONS,
            dklen=_KEY_SIZE,
        )

    def _load_store(self) -> list[dict]:
        """Load the encrypted store from disk."""
        if not self._store_path.exists():
            return []
        try:
            raw = self._store_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            # 兼容旧格式（dict with "entries" key）
            return data.get("entries", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_store(self, store: list[dict]) -> None:
        """Persist the encrypted store to disk."""
        self._store_path.write_text(
            json.dumps(store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _touch_entry(self, store: list[dict], entry_id: str) -> None:
        """Update last_accessed timestamp for an entry and save."""
        for entry in store:
            if entry["id"] == entry_id:
                entry["last_accessed"] = _now_iso()
                break
        self._save_store(store)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
