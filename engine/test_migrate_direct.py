"""直接测试 migrate_weights 核心逻辑"""
import sys
import os
from pathlib import Path

sys.path.insert(0, r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
os.chdir(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")

out = open(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\migrate_result.txt", "w", encoding="utf-8")

try:
    out.write("Step 1: importing config\n")
    from config import MEMORY_DIR
    out.write(f"MEMORY_DIR = {MEMORY_DIR}\n")

    out.write("Step 2: importing ltm\n")
    from core.ltm import LTMManager, VALID_CATEGORIES
    out.write("LTMManager OK\n")

    out.write("Step 3: importing weight\n")
    from core.weight import MemoryWeight
    out.write("MemoryWeight OK\n")

    out.write("Step 4: loading entries\n")
    ltm = LTMManager(Path(MEMORY_DIR))
    entries = ltm.list_all(limit=10000)
    out.write(f"Found {len(entries)} entries\n")

    out.write("Step 5: running auto_suggest_weight\n")
    mw = MemoryWeight(Path(MEMORY_DIR))
    dist = {}
    for e in entries[:20]:  # 只测前20条
        w = mw.auto_suggest_weight(e.content, e.category)
        label = f"{w} ({MemoryWeight.WEIGHT_NAMES[w]})"
        dist[label] = dist.get(label, 0) + 1
        out.write(f"  [{e.category}] → weight={w}: {e.content[:50]}\n")

    out.write(f"\nDistribution (first 20): {dist}\n")
    out.write("PASS\n")

except Exception as e:
    import traceback
    out.write(f"ERROR: {e}\n{traceback.format_exc()}\n")

out.close()
print("done")
