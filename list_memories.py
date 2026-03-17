import sys, os
sys.path.insert(0, r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')
os.chdir(r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')
from config import MEMORY_DIR
from core.ltm import LTMManager
ltm = LTMManager(memory_dir=MEMORY_DIR)
entries = ltm.list_all()
print(f"Total entries: {len(entries)}")
for e in entries:
    print(f"  [{e.category}] {e.content[:100]}")
