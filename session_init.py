import sys, os
sys.path.insert(0, r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')
os.chdir(r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')

from config import MEMORY_DIR
from core.stm import STMManager
from core.ltm import LTMManager
from core.kb import KBManager

ltm = LTMManager(memory_dir=MEMORY_DIR)
kb = KBManager(memory_dir=MEMORY_DIR)
stm = STMManager()

# STEP 1: session_start
session = stm.start_session(task_type='general')
print(f"[session_start] session_id: {session.session_id}, task_type: {session.task_type}")

# STEP 2: memory_profile
profile = ltm.load_profile()
print(f"[memory_profile] total_entries: {profile.get('total_entries', 0)}")
cats = profile.get('categories', {})
if cats:
    print(f"[memory_profile] categories: {cats}")
else:
    print("[memory_profile] no memories yet — clean slate")

# STEP 3: memory_recall (ltm.search uses max_results)
results = ltm.search(query="user preferences goals background project", max_results=5)
print(f"[memory_recall] found: {len(results)} entries")
for r in results[:5]:
    print(f"  - [{r.category}] {r.content[:80]}")

# STEP 4: kb_search (kb.search uses top_k)
kb_results = kb.search(query="user preferences goals project", top_k=3, confirmed_only=False)
print(f"[kb_search] found: {len(kb_results)} entries")
for r in kb_results[:3]:
    print(f"  - [{r.category}] {r.title}: {r.content[:60]}")

print(f"\n[READY] Session active: {session.session_id}")
