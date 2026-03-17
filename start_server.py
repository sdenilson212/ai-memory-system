import subprocess, time, sys, os

engine_dir = r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine'
p = subprocess.Popen(
    [sys.executable, 'main.py'],
    cwd=engine_dir,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
time.sleep(3)
print(f'Server PID: {p.pid}')
print('OK')
