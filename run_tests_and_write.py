"""run_tests_and_write.py - runs pytest and writes results to a file"""
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).parent / "pytest_results.txt"

result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        str(Path(__file__).parent / "engine" / "test_search_regressions.py"),
        str(Path(__file__).parent / "engine" / "test_integrity_regressions.py"),
        "-v", "--tb=short", "--no-header",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=str(Path(__file__).parent / "engine"),
    env={
        "PYTHONPATH": str(Path(__file__).parent / "engine"),
        "PYTHONUTF8": "1",
        "PATH": "C:\\Python314;C:\\Python314\\Scripts;C:\\Windows\\System32",
    }
)

output = result.stdout + ("\n--- STDERR ---\n" + result.stderr if result.stderr.strip() else "")
OUT.write_text(output, encoding="utf-8")
print(f"Exit code: {result.returncode}")
print(f"Results written to: {OUT}")
