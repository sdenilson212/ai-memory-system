"""
全量测试运行器 — AI Memory System v1.5.0
运行所有 verify*.py 测试文件，收集结果
"""
import sys
import os
import importlib
import traceback
from pathlib import Path

ENGINE = Path(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
RESULT_FILE = Path(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\full_test_result.txt")

sys.path.insert(0, str(ENGINE))
os.chdir(str(ENGINE))

results = []
test_files = [
    "verify.py",
    "verify_fix.py",
    "verify_mcp_tools.py",
]

total_pass = 0
total_fail = 0

for fname in test_files:
    fpath = ENGINE / fname
    if not fpath.exists():
        results.append(f"SKIP {fname}: file not found")
        continue

    results.append(f"\n{'='*50}")
    results.append(f"Running: {fname}")
    results.append("="*50)

    try:
        # Re-import fresh each time
        spec = importlib.util.spec_from_file_location("test_module", fpath)
        mod = importlib.util.module_from_spec(spec)
        # Capture the test's output
        import io
        old_stdout = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            spec.loader.exec_module(mod)
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0
        except Exception as e:
            exit_code = 1
            buf.write(f"\nFATAL ERROR: {e}\n{traceback.format_exc()}")
        finally:
            sys.stdout = old_stdout

        output = buf.getvalue()
        results.append(output)

        if exit_code == 0:
            results.append(f"RESULT: PASS (exit_code={exit_code})")
            total_pass += 1
        else:
            results.append(f"RESULT: FAIL (exit_code={exit_code})")
            total_fail += 1

    except Exception as e:
        results.append(f"ERROR loading {fname}: {e}\n{traceback.format_exc()}")
        total_fail += 1

results.append(f"\n{'='*50}")
results.append(f"SUMMARY: {total_pass} PASS / {total_fail} FAIL / {len(test_files)} total")
results.append("="*50)

RESULT_FILE.write_text("\n".join(results), encoding="utf-8")
