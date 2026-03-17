"""
api/server.py — FastAPI Application
FastAPI 应用主文件

职责:
    组装 FastAPI app，注册所有路由，提供依赖注入，启动服务。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MEMORY_DIR, SECURE_DIR
from core.ltm import LTMManager
from core.kb import KBManager
from core.stm import STMManager
from security.encryptor import Encryptor
from security.detector import SensitiveDetector

# ── 单例实例（应用生命周期内共享）────────────────────────────────────────────

_encryptor = Encryptor(SECURE_DIR)
_detector  = SensitiveDetector()
_ltm       = LTMManager(MEMORY_DIR, encryptor=_encryptor, detector=_detector)
_kb        = KBManager(MEMORY_DIR)
_stm       = STMManager()


def get_ltm() -> LTMManager:
    return _ltm

def get_kb() -> KBManager:
    return _kb

def get_stm() -> STMManager:
    return _stm

def get_encryptor() -> Encryptor:
    return _encryptor


# ── App Factory ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子 / App startup/shutdown hooks."""
    print("[AI Memory Engine] starting...")
    print(f"   Memory dir : {MEMORY_DIR}")
    print(f"   Secure dir : {SECURE_DIR}")
    yield
    print("[AI Memory Engine] shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Memory Engine",
        description=(
            "Persistent memory system for AI assistants. "
            "Provides Long-Term Memory (LTM), Knowledge Base (KB), "
            "and Short-Term Memory (STM) via REST API.\n\n"
            "AI 记忆引擎 — 为 AI 助手提供持久记忆系统。"
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS（允许本地前端访问）
    # Note: allow_origins 不支持通配符端口，需逐一列举或用 allow_origin_regex
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    from api.routes import memory as memory_router
    from api.routes import kb as kb_router
    from api.routes import session as session_router

    app.include_router(memory_router.router, prefix="/memory", tags=["Memory (LTM)"])
    app.include_router(kb_router.router, prefix="/kb", tags=["Knowledge Base"])
    app.include_router(session_router.router, prefix="/session", tags=["Session (STM)"])

    # 全局异常处理
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @app.exception_handler(Exception)
    async def generic_error_handler(request, exc):
        return JSONResponse(status_code=500, content={"error": f"Internal error: {exc}"})

    # 健康检查端点
    @app.get("/health", tags=["System"])
    async def health():
        profile = _ltm.load_profile()
        kb_index = _kb.get_index()
        return {
            "status": "ok",
            "memory_entries": profile.get("total_entries", 0),
            "kb_entries": len(kb_index),
            "active_sessions": len(_stm.list_active_sessions()),
        }

    return app


app = create_app()
