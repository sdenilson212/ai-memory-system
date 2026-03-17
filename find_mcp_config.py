import os

# Search for MCP-related config files in common locations
search_roots = [
    r'C:\Users\sdenilson\AppData\Roaming\WorkBuddy',
    r'C:\Users\sdenilson\AppData\Local\WorkBuddy',
    r'C:\Users\sdenilson\.workbuddy',
    r'C:\Users\sdenilson\.codebuddy',
    r'C:\Users\sdenilson\AppData\Roaming\Code',
]

print("=== Searching for MCP config files ===")
for root in search_roots:
    if not os.path.exists(root):
        print(f"  [not found] {root}")
        continue
    for r, d, fs in os.walk(root):
        for f in fs:
            if any(k in f.lower() for k in ['mcp', 'server', 'config']):
                fp = os.path.join(r, f)
                print(fp)

# Also look for workbuddy dotdir
print("\n=== .workbuddy dirs ===")
for r, d, fs in os.walk(r'C:\Users\sdenilson\WorkBuddy\Claw'):
    for dd in d:
        if 'workbuddy' in dd.lower() or dd.startswith('.'):
            print(os.path.join(r, dd))
    break  # only top level
