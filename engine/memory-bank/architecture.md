# Architecture — AI Memory Engine
# 架构设计 — AI 记忆引擎

**版本 / Version**: 1.0  
**最后更新 / Last Updated**: 2026-03-16

---

## 模块依赖图 / Module Dependency Diagram

```
┌─────────────────────────────────────────────────┐
│                   API Layer                      │
│  server.py → routes/memory.py                   │
│           → routes/kb.py                        │
│           → routes/session.py                   │
└──────────────┬──────────────────────────────────┘
               │ calls
    ┌──────────▼──────────────────────┐
    │         Core Layer              │
    │  ltm.py   kb.py   stm.py        │
    └──────────┬──────────────────────┘
               │ uses
    ┌──────────▼──────────────────────┐
    │       Security Layer            │
    │  encryptor.py   detector.py     │
    └──────────┬──────────────────────┘
               │ reads/writes
    ┌──────────▼──────────────────────┐
    │       File System               │
    │  memory-bank/                   │
    │    long-term-memory.md          │
    │    knowledge-base.md            │
    │    projects/*.md                │
    │    secure/encrypted.json        │
    └─────────────────────────────────┘
```

---

## 模块接口定义 / Module Interface Contracts

### `core/ltm.py` — Long-Term Memory Manager

**职责 / Responsibility**: 读写 `long-term-memory.md`，提供 CRUD 操作

**暴露的接口 / Exposes**:
```python
class LTMManager:
    def __init__(self, memory_dir: Path) -> None

    def save(self, content: str, category: str, source: str,
             tags: list[str] = None, sensitive: bool = False) -> LTMEntry
    # 保存新条目。若 sensitive=True，调用 encryptor 并存引用

    def get(self, entry_id: str) -> LTMEntry | None
    # 按 ID 获取单条记忆

    def search(self, query: str, category: str = None) -> list[LTMEntry]
    # 关键词搜索，可按 category 过滤

    def update(self, entry_id: str, content: str = None,
               tags: list[str] = None) -> LTMEntry
    # 更新条目内容或标签

    def delete(self, entry_id: str, confirm: bool = False) -> bool
    # 删除条目，confirm=True 才执行

    def load_profile(self) -> dict
    # 返回用户档案摘要（name, preferences, active_projects）

    def list_all(self, category: str = None) -> list[LTMEntry]
    # 列出所有条目，可按 category 过滤
```

**依赖 / Depends on**: `security/encryptor.py`, `security/detector.py`, `pathlib`, `python-frontmatter`  
**禁止 / Must NOT**: 直接处理 HTTP 请求；调用 `kb.py` 或 `stm.py`

---

### `core/kb.py` — Knowledge Base Manager

**职责 / Responsibility**: 管理 `knowledge-base.md`，提供知识条目的增删改查

**暴露的接口 / Exposes**:
```python
class KBManager:
    def __init__(self, memory_dir: Path) -> None

    def add(self, title: str, content: str, category: str,
            tags: list[str] = None, source: str = "user-upload",
            confidence: str = "high") -> KBEntry
    # 添加新知识条目

    def search(self, query: str, category: str = None,
               top_k: int = 5) -> list[KBEntry]
    # 关键词检索，返回最相关的 top_k 条

    def update(self, entry_id: str, content: str = None,
               tags: list[str] = None) -> KBEntry
    # 更新现有条目

    def delete(self, entry_id: str, confirm: bool = False) -> bool
    # 删除条目

    def get_index(self) -> list[dict]
    # 返回 KB 索引摘要（id, title, category, tags）不含全文

    def import_text(self, text: str, category: str,
                    source: str = "user-upload") -> list[KBEntry]
    # 将大段文本拆分并批量导入知识库
```

**依赖 / Depends on**: `pathlib`, `python-frontmatter`, `re`  
**禁止 / Must NOT**: 处理加密；调用 `ltm.py` 或 `stm.py`

---

### `core/stm.py` — Short-Term Memory (Session Tracker)

**职责 / Responsibility**: 管理单次对话会话的内存状态，会话结束自动清除

**暴露的接口 / Exposes**:
```python
class STMManager:
    def __init__(self) -> None

    def start_session(self, task_type: str = "conversation") -> STMSession
    # 创建新会话，返回 session_id

    def get_session(self, session_id: str) -> STMSession | None
    # 获取会话对象

    def update_context(self, session_id: str, key: str, value: any) -> bool
    # 更新会话中的上下文变量（如当前项目名、用户意图等）

    def add_event(self, session_id: str, event_type: str,
                  content: str) -> bool
    # 记录会话事件（如"用户提到了项目名"、"触发了记忆保存"）

    def queue_save(self, session_id: str, item: dict) -> bool
    # 将待保存条目加入 pending_saves 队列

    def get_pending_saves(self, session_id: str) -> list[dict]
    # 获取待确认保存的条目列表

    def end_session(self, session_id: str) -> dict
    # 结束会话，返回 session_summary，清除内存中的会话数据
```

**依赖 / Depends on**: 纯内存操作，无文件 I/O  
**禁止 / Must NOT**: 直接写文件；依赖 `ltm.py`、`kb.py`、`security/`

---

### `security/encryptor.py` — AES-256-GCM Encryptor

**职责 / Responsibility**: 提供字符串的加密和解密，密文存储到 `secure/encrypted.json`

**暴露的接口 / Exposes**:
```python
class Encryptor:
    def __init__(self, secure_dir: Path) -> None

    def encrypt(self, key: str, plaintext: str,
                passphrase: str) -> str
    # 用 passphrase 派生密钥，加密 plaintext，存入 encrypted.json
    # 返回: entry_id（用于 LTM 引用）

    def decrypt(self, entry_id: str, passphrase: str) -> str
    # 用 passphrase 解密指定条目，返回明文

    def delete(self, entry_id: str, passphrase: str) -> bool
    # 验证 passphrase 后删除条目

    def list_keys(self) -> list[dict]
    # 返回所有加密条目的索引（id, key_name, category, created_at）不含密文
```

**依赖 / Depends on**: `cryptography`, `json`, `pathlib`  
**禁止 / Must NOT**: 记录明文到任何日志；存储 passphrase

---

### `security/detector.py` — Sensitive Data Detector

**职责 / Responsibility**: 识别文本中的敏感信息模式

**暴露的接口 / Exposes**:
```python
class SensitiveDetector:
    def scan(self, text: str) -> ScanResult
    # 扫描文本，返回检测到的敏感信息列表

    def is_sensitive(self, text: str) -> bool
    # 快速判断文本是否包含敏感信息

    def redact(self, text: str) -> str
    # 将敏感部分替换为 [REDACTED]
```

**识别模式 / Detection Patterns**:
- API Key / Token: `sk-[a-zA-Z0-9]{20,}`, `Bearer [a-zA-Z0-9._-]+`
- 密码上下文: `password\s*[:=]\s*\S+`, `密码\s*[:：]\s*\S+`
- 身份证号: `[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])\d{2}\d{3}[\dX]`
- 银行卡号: `\b\d{16,19}\b`
- 私钥标记: `-----BEGIN.*PRIVATE KEY-----`

---

### `api/server.py` + `routes/` — FastAPI Application

**职责 / Responsibility**: 暴露所有核心功能为 REST API

**API 端点 / Endpoints**:
```
POST   /session/start          → STM.start_session()
POST   /session/end            → STM.end_session() + LTM.save() batch
GET    /session/{id}/status    → STM.get_session()

POST   /memory/save            → LTM.save()
GET    /memory/recall          → LTM.search() + KB.search() + STM context
GET    /memory/profile         → LTM.load_profile()
PUT    /memory/{id}            → LTM.update()
DELETE /memory/{id}            → LTM.delete()

POST   /kb/add                 → KB.add()
GET    /kb/search              → KB.search()
GET    /kb/index               → KB.get_index()
PUT    /kb/{id}                → KB.update()
DELETE /kb/{id}                → KB.delete()
POST   /kb/import              → KB.import_text()

GET    /encrypt/list           → Encryptor.list_keys()
POST   /encrypt/decrypt        → Encryptor.decrypt()
DELETE /encrypt/{id}           → Encryptor.delete()
```

---

## 数据流 / Data Flow

### 保存记忆完整流程
```
POST /memory/save {content: "我的 API key 是 sk-abc123", category: "credential"}
  │
  ├─ detector.scan() → 检测到 API key 模式 → sensitive=True
  │
  ├─ encryptor.encrypt("openai_api_key", "sk-abc123", passphrase)
  │   └─ 写入 secure/encrypted.json → 返回 entry_id="enc_001"
  │
  └─ ltm.save(content="OpenAI API Key", sensitive=True, encrypted_ref="enc_001")
      └─ 写入 long-term-memory.md → {encrypted: true, ref: enc_001}
```

### 检索记忆完整流程
```
GET /memory/recall?query=fastapi&layer=all
  │
  ├─ stm.get_context(session_id) → 当前会话上下文
  ├─ ltm.search("fastapi") → [Entry: "用 FastAPI 做后端"]
  ├─ kb.search("fastapi") → [Entry: "FastAPI 官方文档摘要"]
  │
  └─ 合并 + 按相关性排序 → 返回结果列表
```
