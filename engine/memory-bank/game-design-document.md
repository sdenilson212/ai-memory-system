# Game Design Document — AI Memory Engine
# 项目设计文档 — AI 记忆引擎

**版本 / Version**: 1.0  
**创建时间 / Created**: 2026-03-16  
**状态 / Status**: ✅ Approved — Ready to Build

---

## 🎯 一句话目标 / Goal

Build a Python backend engine that gives any AI assistant persistent, queryable, encrypted memory — stored as local files, accessible via a REST API.

构建一个 Python 后端引擎，让任何 AI 助手拥有持久化、可检索、可加密的记忆系统 — 以本地文件存储，通过 REST API 访问。

## ❌ 非目标 / Non-Goals

- 不做 Web UI（那是后续方向 B）
- 不做云端同步（本地优先）
- 不做多租户 SaaS（单用户本地部署）
- 不集成特定 AI 平台 SDK（API 层保持通用）

## ✅ 成功标准 / Definition of Done

1. `ltm.py` — 可以 CRUD 长期记忆条目，持久化到 Markdown 文件
2. `kb.py` — 可以 add / search / update 知识库，支持关键词检索
3. `stm.py` — 可以在单次会话中追踪上下文，会话结束后清除
4. `encryptor.py` — 可以 AES-256-GCM 加密/解密任意字符串
5. `detector.py` — 可以识别密码、API Key、身份证号等敏感模式
6. `server.py` — FastAPI 服务启动后，所有模块功能通过 HTTP 可访问
7. 全部模块有单元测试，覆盖 happy path + error cases

---

## 👤 用户故事 / User Stories

### Story 1 — 跨对话记住我
```
作为用户，我希望 AI 在下一次对话开始时知道我的名字、偏好和正在做的项目，
这样我不需要每次都重复介绍自己。

As a user, I want AI to know my name, preferences, and active projects
at the start of every new conversation, so I don't repeat myself.
```

### Story 2 — 自然语言触发记忆保存
```
作为用户，当我说"记住我用 FastAPI 做后端"，AI 能自动保存这条信息，
不需要我手动操作文件。

As a user, when I say "remember I use FastAPI for backend",
AI saves this automatically without me touching any files.
```

### Story 3 — 敏感信息安全保存
```
作为用户，当我让 AI 记住我的 API Key，我希望它被加密存储，
即使有人打开记忆文件也看不到实际的值。

As a user, when I ask AI to remember my API key,
I want it encrypted so the plaintext is never visible in any file.
```

### Story 4 — 知识库检索
```
作为用户，我可以上传技术文档或笔记，之后对 AI 说"查一下知识库里关于 X 的内容"，
AI 能找到并返回相关内容。

As a user, I can upload docs/notes, then ask AI to "look up X in the knowledge base",
and AI returns the relevant content.
```

### Story 5 — 项目上下文切换
```
作为用户，当我说"我们来继续 memory-engine 项目"，AI 能自动加载该项目的
架构、进度、待办事项等上下文。

As a user, when I say "let's continue the memory-engine project",
AI loads that project's architecture, progress, and tasks automatically.
```

---

## 📊 数据模型 / Data Model

### LTM Entry (长期记忆条目)
```python
@dataclass
class LTMEntry:
    id: str                    # UUID
    content: str               # 记忆内容
    category: str              # profile | preference | project | decision | habit
    source: str                # user-explicit | ai-detected | user-upload
    tags: list[str]            # 自由标签
    created_at: datetime
    updated_at: datetime
    sensitive: bool = False    # 是否加密存储
    encrypted_ref: str = None  # encrypted.json 中的 key（若 sensitive=True）
```

### KB Entry (知识库条目)
```python
@dataclass
class KBEntry:
    id: str
    title: str
    content: str
    category: str              # personal | technical | project | domain | reference | ai-learned
    tags: list[str]
    source: str
    confidence: str = "high"   # high | medium | low（AI学习内容用）
    confirmed: bool = True
    created_at: datetime
    updated_at: datetime
```

### STM Session (短期记忆会话)
```python
@dataclass
class STMSession:
    session_id: str
    started_at: datetime
    task_type: str             # conversation | coding | project | research
    context: dict              # 本次会话追踪的变量
    events: list[dict]         # 事件日志 [{time, type, content}]
    pending_saves: list[dict]  # 待用户确认保存的条目
```

---

## 🔄 核心用户流 / Core User Flows

### Flow A — 会话启动
```
API 调用 POST /session/start
  → STM 初始化新 session
  → LTM 读取并返回用户档案摘要
  → KB 读取并返回索引
  → 返回: {session_id, user_profile, kb_index, active_projects}
```

### Flow B — 保存记忆
```
API 调用 POST /memory/save
  Body: {content, category, source, sensitive}
  → detector.py 扫描敏感信息
  → 若 sensitive: encryptor.py 加密，存 encrypted.json，LTM 存引用
  → 若 not sensitive: LTM 直接存 long-term-memory.md
  → 返回: {success, entry_id, saved_to}
```

### Flow C — 检索记忆
```
API 调用 GET /memory/recall?query=xxx&layer=all
  → STM 检查当前会话上下文
  → LTM 关键词匹配
  → KB 关键词匹配
  → 合并结果，按相关性排序
  → 返回: {results: [{source, content, relevance_score}]}
```

### Flow D — 会话结束
```
API 调用 POST /session/end
  Body: {session_id, items_to_save: [...]}
  → 将 pending_saves 中确认的条目写入 LTM / KB
  → 清除 STM session
  → 返回: {saved_count, session_summary}
```
