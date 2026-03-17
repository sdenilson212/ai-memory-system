"""
config.py — Path & Environment Configuration
路径与环境配置

所有模块通过此文件获取路径配置，不硬编码路径。
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Base Directory ─────────────────────────────────────────────────────────

# MEMORY_DIR 可通过环境变量覆盖，默认为 engine 目录下的 memory-bank
_ENGINE_ROOT = Path(__file__).parent

MEMORY_DIR: Path = Path(
    os.environ.get("MEMORY_DIR", str(_ENGINE_ROOT / "memory-bank"))
)

SECURE_DIR: Path = MEMORY_DIR / "secure"
PROJECTS_DIR: Path = MEMORY_DIR / "projects"

# ── Server Config ──────────────────────────────────────────────────────────

API_HOST: str = os.environ.get("API_HOST", "127.0.0.1")
API_PORT: int = int(os.environ.get("API_PORT", "8765"))

# ── Auto-create directories on import ─────────────────────────────────────

def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    for d in [MEMORY_DIR, SECURE_DIR, PROJECTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

ensure_dirs()
