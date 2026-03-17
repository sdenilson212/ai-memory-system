import os

config_paths = [
    r'C:\Users\sdenilson\AppData\Roaming\WorkBuddy\User\globalStorage\tencent-cloud.coding-copilot',
    r'C:\Users\sdenilson\.workbuddy',
    r'C:\Users\sdenilson\.codebuddy',
    r'C:\Users\sdenilson\AppData\Roaming\WorkBuddy',
]
for p in config_paths:
    if os.path.exists(p):
        print(f'EXISTS: {p}')
        for r, d, f in os.walk(p):
            # skip deep node_modules
            d[:] = [x for x in d if x != 'node_modules']
            for fn in f:
                if any(k in fn.lower() for k in ['mcp', 'config', 'setting']):
                    print(f'  {os.path.join(r, fn)}')
    else:
        print(f'NOT FOUND: {p}')
