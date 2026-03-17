import sys
print("Python:", sys.version)
try:
    import mcp
    print("mcp: OK (installed)")
except ImportError as e:
    print("mcp NOT installed:", e)

try:
    import frontmatter
    print("frontmatter: OK")
except ImportError as e:
    print("frontmatter NOT installed:", e)
