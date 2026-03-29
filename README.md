# AI Memory System

**持久化长期记忆、知识库和会话追踪系统 — 为 AI 应用提供跨会话记忆能力**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-21-brightgreen.svg)](#mcp-tools)

[English](#english) | 中文

---

## 核心能力

AI 默认没有记忆——每次对话结束，一切归零。

**AI Memory System** 解决这个问题，为任何 AI 应用提供三层持久化记忆：

```
长期记忆（LTM）    ←  跨会话保存用户偏好、决策、项目事实
知识库（KB）       ←  存储可复用的技术文档、方案、笔记
会话追踪（STM）    ←  当前对话上下文、事件记录、待保存队列
```

---

## 特性

- **21 个 MCP 工具**：开箱即用，直接接入任何支持 MCP 协议的 AI 框架
- **三层记忆架构**：LTM（长期）+ KB（知识库）+ STM（会话）
- **AES-256-GCM 加密**：敏感数据自动检测并加密存储
- **语义搜索**：基于向量相似度的记忆检索（可选，需 ChromaDB）
- **自动去重**：相似内容自动检测，避免冗余记忆（阈值 85%）
- **记忆权重**：1-5 级重要性评分，影响检索排序
- **备份恢复**：自动备份 + 一键恢复
- **Web UI**：内置可视化界面，浏览和管理所有记忆

---

## 快速开始

### 安装

```bash
git clone https://github.com/sdenilson212/ai-memory-system.git
cd ai-memory-system
pip install -r requirements.txt
```

### 启动 MCP 服务器

```bash
python engine/mcp_server.py
```

### 在 AI 对话中使用

```python
# 保存一条记忆
memory_save(
    content="用户偏好深色模式，不喜欢过多动画",
    category="preference",
    tags=["ui", "preference"]
)

# 检索相关记忆
results = memory_recall(query="用户界面偏好")

# 搜索知识库
docs = kb_search(query="React 组件最佳实践")
```

---

## MCP 工具列表（21 个）

### 长期记忆（LTM）

| 工具 | 说明 |
|------|------|
| `memory_save` | 保存新记忆条目 |
| `memory_recall` | 关键词搜索记忆 |
| `memory_get` | 按 ID 获取单条记忆 |
| `memory_update` | 更新现有记忆 |
| `memory_delete` | 删除记忆（需 confirm=true） |
| `memory_profile` | 获取用户档案摘要 |
| `memory_list` | 列出所有记忆（可按分类过滤） |

### 知识库（KB）

| 工具 | 说明 |
|------|------|
| `kb_add` | 添加知识库条目 |
| `kb_search` | 搜索知识库 |
| `kb_update` | 更新知识库条目 |
| `kb_delete` | 删除知识库条目 |
| `kb_index` | 查看知识库索引 |
| `kb_import` | 批量导入大段文本 |

### 会话追踪（STM）

| 工具 | 说明 |
|------|------|
| `session_start` | 开始新会话 |
| `session_update` | 更新会话上下文 |
| `session_event` | 记录会话事件 |
| `session_queue` | 将内容加入待保存队列 |
| `session_pending` | 查看待保存内容 |
| `session_end` | 结束会话并获取摘要 |
| `trigger_analyze` | 分析文本识别值得保存的内容 |
| `memory_status` | 获取系统整体状态 |

---

## 架构

```
ai-memory-system/
├── engine/
│   ├── mcp_server.py        # MCP 服务器（主入口）
│   ├── core/
│   │   ├── ltm.py           # 长期记忆引擎
│   │   ├── kb.py            # 知识库引擎
│   │   ├── stm.py           # 会话追踪引擎
│   │   ├── vector_store.py  # 向量检索（可选）
│   │   ├── deduplicator.py  # 自动去重
│   │   ├── weight.py        # 记忆权重
│   │   └── encryption.py    # AES-256-GCM 加密
│   └── memory-bank/         # 数据存储目录
├── ui/                      # Web UI（React + TypeScript）
└── backup_restore.py        # 备份恢复工具
```

---

## 与 Adaptive Skill System 的关系

本项目是 [Adaptive Skill System](https://github.com/sdenilson212/adaptive-skill-system) 的**记忆基础层**：

```
AI Memory System（记忆层）← 本项目
    ↕ 读写
Adaptive Skill System（执行层）
    ↕ 接口
你的 AI 应用
```

---

## License

MIT © [sdenilson212](https://github.com/sdenilson212)

---

<a name="english"></a>

## English

**AI Memory System** — A persistent long-term memory, knowledge base, and session tracking system that gives any AI application cross-session memory capabilities.

### The Problem

AI has no memory by default — every conversation ends with a blank slate.

**AI Memory System** solves this by providing a three-layer persistent memory backend for any AI application:

```
Long-Term Memory (LTM)  ←  Cross-session: user preferences, decisions, project facts
Knowledge Base (KB)     ←  Reusable: technical docs, solutions, notes
Session Tracking (STM)  ←  In-session: context, events, pending-save queue
```

---

### Features

- **21 MCP tools** — plug-and-play integration with any MCP-compatible AI framework
- **Three-layer memory architecture** — LTM + KB + STM working together
- **AES-256-GCM encryption** — sensitive data auto-detected and encrypted at rest
- **Semantic search** — vector similarity retrieval (optional, requires ChromaDB)
- **Auto-deduplication** — similar content detected automatically, threshold 85%
- **Memory weighting** — 1-5 importance scoring influences retrieval ranking
- **Backup & restore** — scheduled backups + one-click restore
- **Web UI** — built-in dashboard to browse and manage all memories

---

### Quick Start

```bash
git clone https://github.com/sdenilson212/ai-memory-system.git
cd ai-memory-system
pip install -r requirements.txt

# Start MCP server
python engine/mcp_server.py
```

```python
# Save a memory
memory_save(
    content="User prefers dark mode and minimal animations",
    category="preference",
    tags=["ui", "preference"]
)

# Recall related memories
results = memory_recall(query="user interface preferences")

# Search the knowledge base
docs = kb_search(query="React component best practices")
```

---

### MCP Tool Reference (21 tools)

**Long-Term Memory (LTM)**

| Tool | Description |
|------|-------------|
| `memory_save` | Save a new memory entry |
| `memory_recall` | Search memories by keyword |
| `memory_get` | Retrieve a single entry by ID |
| `memory_update` | Update an existing memory |
| `memory_delete` | Delete a memory (requires confirm=true) |
| `memory_profile` | Get a structured user profile summary |
| `memory_list` | List all memories (filterable by category) |

**Knowledge Base (KB)**

| Tool | Description |
|------|-------------|
| `kb_add` | Add a knowledge base entry |
| `kb_search` | Search the knowledge base |
| `kb_update` | Update a KB entry |
| `kb_delete` | Delete a KB entry |
| `kb_index` | Browse KB index (no full content) |
| `kb_import` | Bulk-import a large text document |

**Session Tracking (STM)**

| Tool | Description |
|------|-------------|
| `session_start` | Start a new session |
| `session_update` | Update a session context key-value |
| `session_event` | Log a notable session event |
| `session_queue` | Queue an item for pending save |
| `session_pending` | View all pending saves |
| `session_end` | End session and get summary |
| `trigger_analyze` | Analyze text for memory-worthy content |
| `memory_status` | Get overall system status and stats |

---

### Repository Structure

```
ai-memory-system/
├── engine/
│   ├── mcp_server.py        # MCP server (main entry point)
│   ├── core/
│   │   ├── ltm.py           # Long-term memory engine
│   │   ├── kb.py            # Knowledge base engine
│   │   ├── stm.py           # Session tracking engine
│   │   ├── vector_store.py  # Vector retrieval (optional)
│   │   ├── deduplicator.py  # Auto-deduplication
│   │   ├── weight.py        # Memory weighting
│   │   └── encryption.py    # AES-256-GCM encryption
│   └── memory-bank/         # Data storage directory
├── ui/                      # Web UI (React + TypeScript)
└── backup_restore.py        # Backup and restore tool
```

---

### Relationship with Adaptive Skill System

This project serves as the **memory foundation layer** for [Adaptive Skill System](https://github.com/sdenilson212/adaptive-skill-system):

```
AI Memory System  (memory layer — this project)
        ↕
Adaptive Skill System  (execution layer)
        ↕
Your AI application
```

Both systems can be used independently, or together for maximum effect.

---

### License

MIT © [sdenilson212](https://github.com/sdenilson212)
