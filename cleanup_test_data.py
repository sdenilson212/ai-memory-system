import sys, os
sys.path.insert(0, r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')
os.chdir(r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')
from config import MEMORY_DIR
from core.ltm import LTMManager

ltm = LTMManager(memory_dir=MEMORY_DIR)
entries = ltm.list_all()
print(f"Before: {len(entries)} entries")

deleted = 0
for e in entries:
    if "dark mode UI" in e.content and e.category == "preference":
        ok = ltm.delete(e.id, confirm=True)
        if ok:
            deleted += 1
            print(f"  Deleted: {e.id} — {e.content[:60]}")

entries_after = ltm.list_all()
print(f"After: {len(entries_after)} entries | Deleted: {deleted}")
