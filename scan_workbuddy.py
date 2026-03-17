import os

root = r'C:\Users\sdenilson\AppData\Roaming\WorkBuddy'
print("=== Files containing 'mcp' in name ===")
for r, d, fs in os.walk(root):
    for f in fs:
        if 'mcp' in f.lower():
            print(os.path.join(r, f))

print("\n=== All JSON files in root level dirs ===")
for r, d, fs in os.walk(root):
    depth = r.replace(root, '').count(os.sep)
    if depth <= 2:
        for f in fs:
            if f.endswith('.json'):
                print(os.path.join(r, f))
