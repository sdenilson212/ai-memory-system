import subprocess
import sys
import os

engine_dir = r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine'
result = subprocess.run(
    [sys.executable, '-c', 'import api.server; print("Import OK")'],
    cwd=engine_dir,
    capture_output=True,
    text=True,
    timeout=15
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:2000])
