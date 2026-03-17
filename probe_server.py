import subprocess
import sys
import time

engine_dir = r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine'

# Start server and capture output for 5 seconds
p = subprocess.Popen(
    [sys.executable, 'main.py'],
    cwd=engine_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(4)

if p.poll() is not None:
    # Process exited
    out, err = p.communicate()
    print("Process exited with code:", p.returncode)
    print("STDOUT:", out[:2000])
    print("STDERR:", err[:2000])
else:
    print(f"Server is running, PID: {p.pid}")
    # Try to read any output so far
    import select, os
    p.terminate()
