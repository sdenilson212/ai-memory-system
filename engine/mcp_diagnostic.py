"""
MCP Server Diagnostic Script
==============================
This script helps diagnose why MCP server may not be working in WorkBuddy.
"""

import sys
import os
import json
import subprocess

print("=" * 70)
print("MCP SERVER DIAGNOSTIC TOOL")
print("=" * 70)

# 1. Check Python version
print("\n[1/8] Checking Python version...")
py_version = sys.version_info
print(f"  Python {py_version.major}.{py_version.minor}.{py_version.micro}")
if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
    print("  WARNING: Python 3.8+ is recommended")
else:
    print("  OK")

# 2. Check MCP package
print("\n[2/8] Checking MCP package installation...")
try:
    import mcp
    try:
        print(f"  OK - mcp version: {mcp.__version__}")
    except AttributeError:
        print(f"  OK - mcp package installed (version info not available)")
except ImportError:
    print("  ERROR: mcp package not installed")
    print("  Fix: pip install mcp")

# 3. Check dependencies
print("\n[3/8] Checking required dependencies...")
required = [
    ("mcp", "mcp"),
    ("starlette", "starlette"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
]

missing = []
for module_name, package_name in required:
    try:
        __import__(module_name)
        print(f"  OK - {package_name}")
    except ImportError:
        print(f"  MISSING - {package_name}")
        missing.append(package_name)

if missing:
    print(f"\n  Install missing: pip install {' '.join(missing)}")

# 4. Check mcp_server.py
print("\n[4/8] Checking mcp_server.py...")
server_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")
if os.path.exists(server_path):
    print(f"  OK - Found at: {server_path}")
    # Check if it's readable
    try:
        with open(server_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"  OK - File is readable ({len(content)} bytes)")
    except Exception as e:
        print(f"  ERROR - Cannot read file: {e}")
else:
    print(f"  ERROR - Not found at: {server_path}")

# 5. Check WorkBuddy config
print("\n[5/8] Checking WorkBuddy MCP configuration...")
workbuddy_config = r"C:\Users\sdenilson\.workbuddy\mcp.json"
if os.path.exists(workbuddy_config):
    print(f"  OK - Found at: {workbuddy_config}")
    try:
        with open(workbuddy_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if "mcpServers" in config:
            servers = config["mcpServers"]
            print(f"  OK - Found {len(servers)} MCP server(s)")

            if "ai-memory-system" in servers:
                server_config = servers["ai-memory-system"]
                print(f"  OK - ai-memory-system configured")

                # Check command
                command = server_config.get("command", "")
                args = server_config.get("args", [])
                print(f"    Command: {command}")
                print(f"    Args: {' '.join(args)}")

                # Check if file exists
                if args and len(args) > 0:
                    server_file = args[0]
                    if os.path.exists(server_file):
                        print(f"    OK - Server file exists")
                    else:
                        print(f"    ERROR - Server file not found: {server_file}")

                # Check environment variables
                env = server_config.get("env", {})
                if env:
                    print(f"    Environment variables: {list(env.keys())}")
                    memory_dir = env.get("MEMORY_DIR", "")
                    if memory_dir and os.path.exists(memory_dir):
                        print(f"    OK - MEMORY_DIR exists")
                    elif memory_dir:
                        print(f"    WARNING - MEMORY_DIR not found: {memory_dir}")
            else:
                print(f"  WARNING - ai-memory-system not in configuration")
        else:
            print("  ERROR - No mcpServers found in config")
    except Exception as e:
        print(f"  ERROR - Cannot read config: {e}")
else:
    print(f"  ERROR - Not found at: {workbuddy_config}")

# 6. Test mcp_server imports
print("\n[6/8] Testing mcp_server module imports...")
sys.path.insert(0, os.path.dirname(__file__))
try:
    from config import MEMORY_DIR
    print(f"  OK - config imported (MEMORY_DIR: {MEMORY_DIR})")
except Exception as e:
    print(f"  ERROR - config: {e}")

try:
    from core.ltm import LTMManager
    from core.kb import KBManager
    from core.stm import STMManager
    print("  OK - core modules imported")
except Exception as e:
    print(f"  ERROR - core: {e}")

try:
    import mcp_server
    print(f"  OK - mcp_server imported")
except Exception as e:
    print(f"  ERROR - mcp_server: {e}")
    import traceback
    traceback.print_exc()

# 7. Test server initialization
print("\n[7/8] Testing server initialization...")
try:
    import asyncio
    import mcp_server

    print(f"  OK - Server object created: {mcp_server.server.name}")

    # mcp >= 1.x: _tool_handlers 已移除，改用 list_tools() 异步函数来验证
    async def _check_tools():
        return await mcp_server.list_tools()

    tools = asyncio.run(_check_tools())
    print(f"  OK - {len(tools)} tool handlers registered")
    print(f"  OK - First 3 tools: {[t.name for t in tools[:3]]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 8. Recommendations
print("\n[8/8] Recommendations:")
print("\n  If tests pass but WorkBuddy times out:")
print("  1. Restart WorkBuddy application")
print("  2. Check WorkBuddy logs for MCP errors")
print("  3. Verify WorkBuddy is reading the correct mcp.json")
print("  4. Try running WorkBuddy from command line to see errors")

print("\n  If tests fail:")
print("  1. Install missing dependencies: pip install mcp starlette uvicorn pydantic")
print("  2. Check Python version (3.8+ required)")
print("  3. Verify file paths in mcp.json")
print("  4. Ensure MEMORY_DIR exists")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
