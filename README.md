# 🧠 AI Memory System

> 让 AI 拥有长期记忆、知识积累和持续学习能力

[![GitHub Stars](https://img.shields.io/github/stars/sdenilson212/ai-memory-system)](https://github.com/sdenilson212/ai-memory-system/stargazers)
[![License](https://img.shields.io/github/license/sdenilson212/ai-memory-system)](https://github.com/sdenilson212/ai-memory-system/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io/)

---

## 🎯 解决的问题

**AI 的痛点：记不住**

| 场景 | 没有记忆系统 | 有记忆系统 |
|---|---|---|
| 第1次问偏好 | 记住需重复N次 | 自动存入长期记忆 |
| 第10次相同问题 | 每次重新回答 | 直接调取记忆 |
| 项目背景 | 每次从头解释 | 自动关联上下文 |
| 团队协作 | 信息孤岛 | 共享知识库 |

**AI Memory System 让 AI 从"金鱼脑"变成"终身学习者"。**

---

## ✨ 核心功能

### 🔋 三层记忆架构

```
┌─────────────────────────────────────┐
│          Short-Term Memory          │
│         (会话级，临时缓存)            │
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│         Long-Term Memory            │
│      (持久化，长期记忆存储)           │
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│          Knowledge Base              │
│        (结构化知识库)                │
└─────────────────────────────────────┘
```

### 🛠️ 完整工具链

| 模块 | 功能 |
|---|---|
| **LTM Manager** | 长期记忆 CRUD、搜索、加密存储 |
| **KB Manager** | 知识库批量导入、结构化检索 |
| **STM Manager** | 会话追踪、上下文保持 |
| **Trigger Engine** | 自动识别值得保存的内容 |
| **Vector Store** | 语义搜索（TF-IDF / OpenAI / 通义） |
| **Sensitive Detector** | 自动识别并加密敏感信息 |

### 🔌 多种接入方式

```bash
# 1. MCP Server（推荐）
python engine/mcp_server.py

# 2. FastAPI
python engine/api/server.py

# 3. 直接 import
from core.ltm import LTMManager
```

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/sdenilson212/ai-memory-system.git
cd ai-memory-system
pip install -r requirements.txt
```

### 使用 MCP（推荐）

```bash
# STDIO 模式（WorkBuddy / Claude Desktop）
python engine/mcp_server.py

# SSE 模式（网络调用）
python engine/mcp_server.py --sse --port 8766
```

### 17 个 MCP 工具

```
Memory (LTM):    save / recall / get / update / delete / profile / list
Knowledge Base: add / search / update / delete / index / import
Session (STM):  start / update / event / queue / pending / end
Status:         memory_status
```

---

## 📖 使用场景

| 场景 | 效果 |
|---|---|
| **个人 AI 助手** | 记住你的偏好、习惯、项目背景，每次对话都是连续的 |
| **团队知识库** | 多人共享项目文档、技术方案、决策记录 |
| **客服机器人** | 记住客户历史对话，提供个性化服务 |
| **AI Agent 记忆** | 给任何 AI Agent 加上记忆能力，不丢失上下文 |
| **代码助手** | 记住项目架构、代码规范、技术债务 |

---

## 🏷️ 版本对比

| 功能 | 免费版 | Pro 版 |
|---|---|---|
| 基础记忆存储 | ✅ | ✅ |
| 关键词搜索 | ✅ | ✅ |
| SQLite 索引加速 | - | ✅ |
| 语义向量搜索 | - | ✅ |
| 敏感信息自动加密 | ✅ | ✅ |
| MCP Server | ✅ | ✅ |
| 自定义触发规则 | - | ✅ |
| 技术支持 | - | ✅ |

> **Pro 版即将发布** — 关注 GitHub 动态获取更新

---

## 🏗️ 技术架构

```
engine/
├── core/                    # 核心模块
│   ├── ltm.py              # 长期记忆管理器
│   ├── kb.py               # 知识库管理器
│   ├── stm.py              # 会话管理器
│   ├── trigger.py          # 触发引擎
│   ├── vector_store.py     # 向量存储
│   ├── passphrase_manager.py  # 加密管理
│   └── ...
├── api/                    # FastAPI 接口
├── memory-bank/            # 数据存储
│   ├── long-term-memory.md
│   ├── knowledge-base.md
│   ├── index.db
│   └── secure/             # 加密数据
└── mcp_server.py           # MCP 协议服务
```

### 技术栈

- Python 3.10+
- FastAPI + MCP (Model Context Protocol)
- SQLite（索引）
- cryptography（AES-256-GCM）
- 支持 OpenAI / 阿里通义 / HuggingFace Embedding

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 打开 Pull Request

---

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 了解详情

---

## 🔗 相关链接

- 📖 [架构文档](./engine/memory-bank/architecture.md)
- 📖 [快速开始指南](./QUICK_START_GUIDE.md)
- 🐛 [问题反馈](https://github.com/sdenilson212/ai-memory-system/issues)
- 💬 [社区讨论](https://github.com/sdenilson212/ai-memory-system/discussions)

---

## ☕ 支持我们

如果你觉得这个项目有用，欢迎：

- ⭐ Star 本项目
- 📢 分享给更多需要的人

### 微信/支付宝打赏

如果你愿意资助我们继续开发，可以扫描下方二维码：

| 微信 | 支付宝 |
|---|---|
| ![微信支付](.github/wechat-pay.png) | ![支付宝](.github/alipay.png) |

*（二维码文件放在 `.github/` 目录下）*

---

*Built with ❤️ by AI, for AI.*
