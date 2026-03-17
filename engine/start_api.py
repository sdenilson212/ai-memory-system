"""Quick start script for the FastAPI backend."""
import os
import sys

ENGINE_DIR = r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine"
sys.path.insert(0, ENGINE_DIR)
os.chdir(ENGINE_DIR)
os.environ.setdefault("MEMORY_DIR", ENGINE_DIR + r"\memory-bank")

import uvicorn

if __name__ == "__main__":
    print("Starting AI Memory System API on http://127.0.0.1:8765 ...")
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",
        port=8765,
        log_level="info",
        reload=False,
    )
