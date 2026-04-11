"""
通过 git credential manager 获取 GitHub token，然后用 API 创建 Release
"""
import subprocess
import json
import urllib.request
import urllib.error
import sys

# 1. 从 git credential 获取 token
proc = subprocess.run(
    ["git", "credential", "fill"],
    input="protocol=https\nhost=github.com\n",
    capture_output=True, text=True, encoding="utf-8"
)
token = None
for line in proc.stdout.splitlines():
    if line.startswith("password="):
        token = line.split("=", 1)[1].strip()
        break

if not token:
    print("❌ 无法从 git credential 获取 token")
    print("请先运行: gh auth login")
    print("或者访问 https://github.com/sdenilson212/ai-memory-system/releases/new")
    sys.exit(1)

print(f"✅ 获取到 token（长度: {len(token)}）")

# 2. 读取 release notes
with open("release_notes_v1.3.0.md", encoding="utf-8") as f:
    body = f.read()

# 3. 调用 GitHub API 创建 Release
payload = {
    "tag_name": "v1.3.0",
    "name": "v1.3.0 - 文件分片存储 + 并发安全 + Passphrase管理",
    "body": body,
    "draft": False,
    "prerelease": False
}

req = urllib.request.Request(
    "https://api.github.com/repos/sdenilson212/ai-memory-system/releases",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Python-Release-Creator"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print(f"✅ Release 创建成功！")
        print(f"   URL: {data['html_url']}")
        print(f"   ID:  {data['id']}")
except urllib.error.HTTPError as e:
    err = json.loads(e.read())
    print(f"❌ API 错误 {e.code}: {err.get('message', '')}")
    if "errors" in err:
        for error in err["errors"]:
            print(f"   - {error}")
    sys.exit(1)
