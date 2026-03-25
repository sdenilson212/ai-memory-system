"""Quick start script for the FastAPI backend."""
import os
import sys
from pathlib import Path

# 动态计算路径
ENGINE_DIR = Path(__file__).parent
sys.path.insert(0, str(ENGINE_DIR))
os.chdir(ENGINE_DIR)

# 设置 memory-bank 路径
memory_bank_path = ENGINE_DIR / "memory-bank"
if memory_bank_path.exists():
    os.environ.setdefault("MEMORY_DIR", str(memory_bank_path))
else:
    # 向上搜索 memory-bank
    possible_paths = [
        ENGINE_DIR.parent / "memory-bank",
        Path.cwd() / "memory-bank",
    ]
    for path in possible_paths:
        if path.exists():
            os.environ.setdefault("MEMORY_DIR", str(path))
            print(f"Using memory bank at: {path}")
            break

import uvicorn

if __name__ == "__main__":
    print("Starting AI Memory System API on http://127.0.0.1:8765 ...")
    print(f"Engine directory: {ENGINE_DIR}")
    print(f"Memory dir: {os.environ.get('MEMORY_DIR', '未设置')}")
    
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",
        port=8765,
        log_level="info",
        reload=False,
    )
