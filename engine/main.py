"""main.py — Application Entry Point"""
import os
from pathlib import Path
import uvicorn
from api.server import app, create_app
from config import API_HOST, API_PORT

# ── Optional: serve built UI as static files ──────────────────────────────────
# When running inside Docker, the UI is built into engine/static/
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    # Serve static assets (JS, CSS, etc.)
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")

    @app.get("/ui/{path:path}", include_in_schema=False)
    async def serve_ui(path: str = ""):
        index = _STATIC_DIR / "index.html"
        return FileResponse(str(index))

    @app.get("/ui", include_in_schema=False)
    async def serve_ui_root():
        return FileResponse(str(_STATIC_DIR / "index.html"))

    print(f"   UI served  : http://{API_HOST}:{API_PORT}/ui")

if __name__ == "__main__":
    reload = os.environ.get("APP_ENV", "production") == "development"
    uvicorn.run(
        "api.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=reload,
        log_level="info",
    )
