# Tech Stack — AI Memory Engine
# 技术选型 — AI 记忆引擎

**版本 / Version**: 1.0  
**原则 / Principle**: 最简可靠 — Choose the simplest option that is robust enough

---

## 语言 / Language

| 选项 | 选择 | 原因 |
|---|---|---|
| Python 3.11+ | ✅ **选用** | 生态最成熟，cryptography / FastAPI / frontmatter 库都是一流的 |
| Node.js | ❌ | 项目已有 Python 环境，保持一致 |

---

## 文件解析 / File Parsing

| 库 | 用途 | 版本 |
|---|---|---|
| `python-frontmatter` | 解析/写入带 YAML front matter 的 Markdown 文件 | `^1.1.0` |
| `pathlib` (stdlib) | 文件路径操作 | 内置 |
| `json` (stdlib) | encrypted.json 读写 | 内置 |

**选择理由**：记忆文件是人类可读的 Markdown，`python-frontmatter` 让我们既能读 YAML 元数据，又能保留 Markdown 正文，无需引入数据库。

---

## 加密 / Encryption

| 库 | 用途 | 版本 |
|---|---|---|
| `cryptography` | AES-256-GCM 加密/解密 | `^42.0.0` |

**选择理由**：
- Python 官方推荐的加密库，维护活跃
- AES-256-GCM 提供认证加密（防篡改 + 防窃取）
- 比 `pycryptodome` 更现代，API 更清晰

**不选用**：
- ❌ `hashlib` — 只能单向哈希，无法解密
- ❌ `Fernet`（cryptography 内置）— 密钥长度固定 32 bytes，不够灵活

---

## 搜索 / Search

### 阶段 1（本 milestone）
| 库 | 用途 |
|---|---|
| Python 内置 `re` + 字符串匹配 | 关键词全文检索 |

**选择理由**：简单高效，满足 MVP 需求。知识库在早期不会超过几千条，线性扫描足够。

### 阶段 2（可选升级）
| 库 | 用途 |
|---|---|
| `chromadb` | 本地向量数据库 |
| `sentence-transformers` | 文本向量化（语义搜索） |

**升级条件**：当知识库超过 500 条或需要语义搜索时引入。**本 milestone 不实现。**

---

## API 层 / API Layer

| 库 | 用途 | 版本 |
|---|---|---|
| `fastapi` | REST API 框架 | `^0.115.0` |
| `uvicorn` | ASGI 服务器 | `^0.30.0` |
| `pydantic` | 请求/响应数据验证 | `^2.7.0`（FastAPI 内置） |

**选择理由**：
- FastAPI 自动生成 OpenAPI 文档，方便调试
- Pydantic v2 提供强类型验证，防止非法输入
- Uvicorn 轻量，单命令启动

---

## 测试 / Testing

| 库 | 用途 |
|---|---|
| `pytest` | 测试框架 |
| `pytest-asyncio` | 异步测试支持 |
| `httpx` | FastAPI 集成测试客户端 |

---

## 依赖汇总 / requirements.txt

```
# Core
python-frontmatter==1.1.0
cryptography==42.0.8

# API
fastapi==0.115.5
uvicorn[standard]==0.30.6
pydantic==2.7.4

# Testing
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0
```

---

## 项目结构 / Project Structure

```
engine/
├── core/
│   ├── __init__.py
│   ├── ltm.py          # Long-Term Memory manager
│   ├── kb.py           # Knowledge Base manager
│   └── stm.py          # Short-Term Memory (session tracker)
├── security/
│   ├── __init__.py
│   ├── encryptor.py    # AES-256-GCM encrypt/decrypt
│   └── detector.py     # Sensitive data pattern detection
├── api/
│   ├── __init__.py
│   ├── server.py       # FastAPI app + route registration
│   ├── routes/
│   │   ├── memory.py   # /memory/* routes
│   │   ├── kb.py       # /kb/* routes
│   │   └── session.py  # /session/* routes
│   └── models.py       # Pydantic request/response models
├── memory-bank/        # Runtime data directory (git-ignored)
│   ├── long-term-memory.md
│   ├── knowledge-base.md
│   ├── projects/
│   └── secure/
│       └── encrypted.json
├── tests/
│   ├── test_ltm.py
│   ├── test_kb.py
│   ├── test_stm.py
│   ├── test_encryptor.py
│   ├── test_detector.py
│   └── test_api.py
├── requirements.txt
├── config.py           # Path config, env vars
└── main.py             # Entry point: uvicorn main:app
```
