import sys, subprocess
from pathlib import Path

ENGINE = Path(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
RESULT_FILE = Path(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\full_test_result.txt")
PYTHON = r"C:\Python314\python.exe"

test_files = ["verify.py", "verify_fix.py", "verify_mcp_tools.py"]
results = []
passes = 0
fails = 0

env = {"PYTHONUTF8": "1", "PYTHONPATH": str(ENGINE)}
import os
env.update(os.environ)

for fname in test_files:
    results.append(f"\n{'='*50}")
    results.append(f"Running: {fname}")
    results.append("="*50)
    r = subprocess.run(
        [PYTHON, str(ENGINE / fname)],
        capture_output=True, text=True,
        cwd=str(ENGINE),
        env=env, timeout=60, encoding="utf-8"
    )
    if r.stdout:
        results.append(r.stdout)
    if r.stderr:
        results.append("[STDERR]\n" + r.stderr)
    status = "PASS" if r.returncode == 0 else "FAIL"
    results.append(f"RESULT: {status} (exit={r.returncode})")
    if r.returncode == 0:
        passes += 1
    else:
        fails += 1

results.append(f"\n{'='*50}")
results.append(f"SUMMARY: {passes}/{len(test_files)} PASS")
results.append("="*50)

RESULT_FILE.write_text("\n".join(results), encoding="utf-8")
