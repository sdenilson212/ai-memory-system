import sys, os
sys.path.insert(0, r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
os.chdir(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
result_path = r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\migrate_result.txt"
lines = []
try:
    lines.append("importing config...")
    import importlib
    config = importlib.import_module("config")
    MEMORY_DIR = config.MEMORY_DIR
    lines.append(f"MEMORY_DIR={MEMORY_DIR}")
    lines.append("importing ltm...")
    ltm_mod = importlib.import_module("core.ltm")
    LTMManager = ltm_mod.LTMManager
    lines.append("LTMManager OK")
    lines.append("importing weight...")
    weight_mod = importlib.import_module("core.weight")
    MemoryWeight = weight_mod.MemoryWeight
    lines.append("MemoryWeight OK")
    from pathlib import Path
    ltm = LTMManager(Path(MEMORY_DIR))
    entries = ltm.list_all(limit=50)
    lines.append(f"entries count={len(entries)}")
    mw = MemoryWeight(Path(MEMORY_DIR))
    sample = entries[:5]
    for e in sample:
        w = mw.auto_suggest_weight(e.content, e.category)
        lines.append(f"  cat={e.category} w={w} content={e.content[:40]!r}")
    lines.append("PASS")
except Exception as ex:
    import traceback
    lines.append(f"ERROR: {ex}")
    lines.append(traceback.format_exc())
with open(result_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
