"""
core/passphrase_manager.py — Passphrase Manager
Passphrase 管理器

v1.1 新增（2026-03-25）

三级方案：
  Level 1: 环境变量 AI_MEMORY_PASSPHRASE
  Level 2: 系统 keyring（keyring 库）
  Level 3: recovery_key 密钥分片（待实现）

依赖 (Depends on): os, keyring（可选）
"""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_SERVICE_NAME = "ai-memory-system"
_KEY_NAME = "passphrase"


def get_passphrase(
    env_var: str = "AI_MEMORY_PASSPHRASE",
    use_keyring: bool = True,
) -> Optional[str]:
    """
    获取加密 passphrase。

    优先级：
      1. 环境变量 AI_MEMORY_PASSPHRASE
      2. 系统 keyring
      3. None（无法获取）

    Args:
        env_var:     环境变量名
        use_keyring: 是否尝试从 keyring 读取

    Returns:
        passphrase 字符串，或 None
    """
    # Level 1: 环境变量
    p = os.environ.get(env_var)
    if p:
        return p

    # Level 2: keyring
    if use_keyring:
        try:
            import keyring
            p = keyring.get_password(_SERVICE_NAME, _KEY_NAME)
            if p:
                logger.info("Passphrase loaded from keyring.")
                return p
        except Exception as e:
            logger.debug(f"Keyring unavailable: {e}")

    return None


def set_passphrase(
    passphrase: str,
    save_keyring: bool = True,
    env_var: str = "AI_MEMORY_PASSPHRASE",
) -> None:
    """
    保存 passphrase。

    方式：
      - 优先写入环境变量（临时）
      - 同时写入 keyring（持久化）
      - 同时写入 .env 文件备份（可选）

    Args:
        passphrase:   要保存的 passphrase
        save_keyring: 是否存入系统 keyring
        env_var:      环境变量名
    """
    # 写入环境变量（当前进程有效）
    os.environ[env_var] = passphrase
    logger.info(f"Passphrase set in environment variable: {env_var}")

    # 写入 keyring
    if save_keyring:
        try:
            import keyring
            keyring.set_password(_SERVICE_NAME, _KEY_NAME, passphrase)
            logger.info("Passphrase saved to system keyring (persistent).")
        except Exception as e:
            logger.warning(f"Failed to save to keyring: {e}")

    # 写入 .env 备份文件（仅作参考，需要用户手动转移）
    env_backup = os.path.join(os.getcwd(), ".env.memory_backup")
    try:
        with open(env_backup, "a", encoding="utf-8") as f:
            f.write(f"{env_var}={passphrase}\n")
        logger.info(f"Passphrase appended to {env_backup} (manual reference)")
    except Exception:
        pass


def clear_passphrase(env_var: str = "AI_MEMORY_PASSPHRASE") -> None:
    """
    清除已保存的 passphrase。
    """
    # 清除环境变量
    if env_var in os.environ:
        del os.environ[env_var]
        logger.info(f"Cleared env var: {env_var}")

    # 清除 keyring
    try:
        import keyring
        try:
            keyring.delete_password(_SERVICE_NAME, _KEY_NAME)
            logger.info("Cleared keyring passphrase.")
        except keyring.errors.PasswordDeleteError:
            logger.debug("No keyring entry to delete.")
    except Exception:
        pass


def is_passphrase_configured() -> bool:
    """检查 passphrase 是否已配置（任一渠道）"""
    return get_passphrase() is not None


# ─────────────────────────────────────────────────────────────────────────────
# Recovery Key（Level 3，待实现）
# ─────────────────────────────────────────────────────────────────────────────
#
# def generate_recovery_key(passphrase: str) -> tuple[str, str]:
#     """
#     生成 2-of-3 密钥分片中的 recovery_key。
#     返回 (key_id, recovery_key)
#     """
#     import secrets, hashlib
#     key_id = secrets.token_hex(4)
#     key = hashlib.sha256(f"{key_id}:{passphrase}".encode()).hexdigest()[:32]
#     return key_id, key
#
# def recover_with_recovery_key(key_id: str, recovery_key: str) -> Optional[str]:
#     """用 recovery_key 恢复 passphrase（需结合 secure/ 目录历史记录）"""
#     pass
