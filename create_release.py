#!/usr/bin/env python3
"""
创建 GitHub Release v1.0.0 的自动化脚本

使用方法:
1. 生成 GitHub Personal Access Token:
   - 访问 https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 勾选 "repo" 权限
   - 点击生成并复制 token

2. 运行脚本:
   python create_release.py YOUR_TOKEN_HERE

3. 输入你的 GitHub token

注意: token 会被保存在内存中，不会被写入文件
"""

import requests
import sys
from typing import Optional

# GitHub API 配置
REPO_OWNER = "sdenilson212"
REPO_NAME = "ai-memory-system"
TAG_NAME = "v1.0.0"
RELEASE_TITLE = "v1.0.0 - Initial Release"

RELEASE_DESCRIPTION = """## 🎉 AI Memory System v1.0.0

这是 AI Memory System 的首次公开发布！为 AI 助手提供持久化长期记忆、知识库和会话追踪功能。

### ✨ 核心特性

#### 🧠 长期记忆 (Long-Term Memory)
- ✅ 记忆保存、检索、更新、删除
- ✅ 用户档案管理
- ✅ 灵活的标签系统
- ✅ 敏感数据自动检测和 AES-256 加密

#### 📚 知识库 (Knowledge Base)
- ✅ 知识条目添加、搜索、更新、删除
- ✅ 知识索引浏览
- ✅ 批量导入支持
- ✅ 确信度管理

#### 💬 会话管理 (Session Management)
- ✅ 会话开始和结束
- ✅ 会话上下文更新
- ✅ 事件时间线记录
- ✅ 待保存队列管理

#### 🔌 MCP 集成
- ✅ **17 个完整的 MCP 工具**
- ✅ 标准 stdio + SSE 双模式支持
- ✅ 兼容 WorkBuddy、Claude Desktop、ChatGPT 等平台

#### 🔐 安全功能
- ✅ **AES-256 加密**敏感数据
- ✅ **自动检测**密码、API 密钥、个人信息
- ✅ 密码短语保护
- ✅ 本地优先设计，数据完全自主控制

### 📦 技术栈

- **后端**: Python 3.10+
- **MCP 协议**: Model Context Protocol (Anthropic)
- **前端**: React + TypeScript + Vite
- **部署**: Docker + Docker Compose
- **平台**: Windows, macOS, Linux

### 🌟 项目亮点

- ✅ **中英双语文档** - 降低中文开发者使用门槛
- ✅ **轻量级设计** - 核心代码仅 ~500KB，无外部依赖
- ✅ **开箱即用** - 一键启动，完整 MCP 工具集
- ✅ **安全优先** - 敏感数据加密，隐私保护
- ✅ **三层记忆架构** - LTM + KB + STM 完整生命周期
- ✅ **智能触发** - 自动识别值得保存的内容

### 📚 完整文档

- [📖 README.md](https://github.com/sdenilson212/ai-memory-system/blob/main/README.md) - 快速参考卡片
- [🤝 CONTRIBUTING.md](https://github.com/sdenilson212/ai-memory-system/blob/main/CONTRIBUTING.md) - 贡献指南
- [🧠 MCP_GUIDE.md](https://github.com/sdenilson212/ai-memory-system/blob/main/engine/MCP_GUIDE.md) - MCP 集成指南
- [🔒 SECURITY.md](https://github.com/sdenilson212/ai-memory-system/blob/main/SECURITY.md) - 安全策略
- [📋 CHANGELOG.md](https://github.com/sdenilson212/ai-memory-system/blob/main/CHANGELOG.md) - 更新日志
- [🚀 QUICK_START_GUIDE.md](https://github.com/sdenilson212/ai-memory-system/blob/main/QUICK_START_GUIDE.md) - 快速开始指南

### 🚀 快速开始

#### 方式一：使用 MCP（推荐）

1. **部署系统提示词**
   - 将 `system-prompt.md` 中的内容复制到你的 AI 工具的 System Prompt 字段

2. **创建记忆库目录**
   ```bash
   ai-memory-system/
   └── memory-bank/
       ├── long-term-memory.md
       ├── knowledge-base.md
       ├── projects/
       └── secure/
   ```

3. **启动 MCP 服务器**
   ```bash
   cd engine
   python mcp_server.py
   ```

4. **开始使用**
   - 在 WorkBuddy/Claude Desktop 中直接调用 MCP 工具
   - AI 会自动激活记忆系统

#### 方式二：使用 Docker

```bash
# 克隆仓库
git clone https://github.com/sdenilson212/ai-memory-system.git
cd ai-memory-system

# 使用 Docker Compose 启动
docker-compose up -d

# 访问 Web UI
open http://localhost:3000
```

### 📊 项目统计

- **代码行数**: ~16,600 行
- **文件数量**: 104 个
- **MCP 工具**: 17 个
- **文档文件**: 11 个（中英双语）
- **测试脚本**: 6 个

### 🎯 适用场景

- ✅ **WorkBuddy 集成** - 为 AI 助手添加持久化记忆
- ✅ **Claude Desktop 集成** - 提升对话连续性
- ✅ **ChatGPT Custom GPTs** - 构建 AI 应用
- ✅ **AI 研究者** - 学习记忆系统架构设计
- ✅ **企业内部助手** - 本地部署，数据自主可控

### 🌍 社区与支持

- 📝 **Issues**: [提交问题](https://github.com/sdenilson212/ai-memory-system/issues)
- 💬 **Discussions**: [参与讨论](https://github.com/sdenilson212/ai-memory-system/discussions)
- 🤝 **Contributing**: [贡献指南](https://github.com/sdenilson212/ai-memory-system/blob/main/CONTRIBUTING.md)

### 📜 许可证

[MIT License](https://github.com/sdenilson212/ai-memory-system/blob/main/LICENSE)

---

## 🎊 感谢使用！

感谢关注 AI Memory System v1.0.0！

这是一个安全优先、中英双语的本地 AI 记忆系统，具备完整的 MCP 集成和三层记忆架构。

欢迎：
- ⭐ **Star** - 关注项目更新
- 🔱 **Fork** - 自定义和改进
- 🐛 **Issues** - 报告问题和提出建议
- 🔀 **Pull Requests** - 贡献代码

---

**快速链接**:
- 🏠 [GitHub 仓库](https://github.com/sdenilson212/ai-memory-system)
- 📖 [完整文档](https://github.com/sdenilson212/ai-memory-system#readme)
- 🚀 [快速开始](https://github.com/sdenilson212/ai-memory-system/blob/main/QUICK_START_GUIDE.md)"""


def create_tag(token: str) -> bool:
    """创建 Git tag"""
    import subprocess

    print(f"📌 正在创建标签: {TAG_NAME}")

    try:
        # 创建本地 tag
        result = subprocess.run(
            ["git", "tag", "-a", TAG_NAME, "-m", "Release v1.0.0"],
            cwd="C:/Users/sdenilson/WorkBuddy/Claw/output/ai-memory-system",
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ 本地 tag 创建成功")

        # 推送 tag 到远程
        result = subprocess.run(
            ["git", "push", "origin", TAG_NAME],
            cwd="C:/Users/sdenilson/WorkBuddy/Claw/output/ai-memory-system",
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Tag 已推送到 GitHub")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Tag 创建失败: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def create_github_release(token: str) -> bool:
    """在 GitHub 上创建 Release"""

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    data = {
        "tag_name": TAG_NAME,
        "name": RELEASE_TITLE,
        "body": RELEASE_DESCRIPTION,
        "draft": False,
        "prerelease": False,
        "target_commitish": "main"
    }

    print(f"🚀 正在创建 GitHub Release...")

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code == 201:
            print("✅ Release 创建成功！")
            result = response.json()
            print(f"\n📋 Release 信息:")
            print(f"  - 标题: {result['name']}")
            print(f"  - 标签: {result['tag_name']}")
            print(f"  - URL: {result['html_url']}")
            print(f"\n🎉 恭喜！Release 已发布！")
            return True
        else:
            print(f"❌ Release 创建失败")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 AI Memory System - 自动创建 Release v1.0.0")
    print("=" * 60)
    print()

    # 获取 GitHub token
    if len(sys.argv) > 1:
        token = sys.argv[1]
        print("✅ 已从命令行参数获取 token")
    else:
        print("请输入你的 GitHub Personal Access Token:")
        print("(从 https://github.com/settings/tokens 生成，需要 'repo' 权限)")
        token = input("> ").strip()

    if not token:
        print("❌ Token 不能为空")
        return

    print()

    # 步骤 1: 创建 tag
    if not create_tag(token):
        print("\n⚠️  Tag 创建失败，跳过...")
        print("   如果 tag 已存在，可以继续创建 Release")

    print()

    # 步骤 2: 创建 GitHub Release
    if create_github_release(token):
        print("\n" + "=" * 60)
        print("🎊 完成！")
        print("=" * 60)
        print()
        print("📝 下一步建议:")
        print("  1. 访问你的仓库: https://github.com/sdenilson212/ai-memory-system")
        print("  2. 查看 Releases 页面: https://github.com/sdenilson212/ai-memory-system/releases")
        print("  3. 添加仓库 Topics: Settings -> Topics")
        print("  4. 分享到社交媒体: 知乎、Twitter 等")
        print()
    else:
        print("\n❌ Release 创建失败，请检查:")
        print("  1. Token 是否有效且具有 'repo' 权限")
        print("  2. 网络连接是否正常")
        print("  3. 仓库是否存在且可访问")
        print()


if __name__ == "__main__":
    main()
