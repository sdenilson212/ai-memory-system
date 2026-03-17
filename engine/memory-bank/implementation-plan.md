# Implementation Plan — AI Memory Engine
# 实施计划 — AI 记忆引擎

**版本 / Version**: 1.0  
**原则**: 一次只做一步，每步完成后更新 progress.md 并提交 Git

---

## Phase 0 — 项目基础设施 (完成)
- [x] 创建目录结构
- [x] 生成 memory-bank 规划文档

---

## Phase 1 — 安全层 (security/)
> 先做安全层，因为 ltm.py 依赖它

### Step 1: `security/detector.py`
- 实现 `SensitiveDetector` 类
- 定义 6 种敏感数据正则模式
- 实现 `scan()`, `is_sensitive()`, `redact()` 方法
- 编写 `tests/test_detector.py`（至少 10 个测试用例）

### Step 2: `security/encryptor.py`
- 实现 `Encryptor` 类
- 使用 `cryptography` 库实现 AES-256-GCM
- 用 PBKDF2 从 passphrase 派生密钥
- 实现 `encrypt()`, `decrypt()`, `delete()`, `list_keys()`
- 读写 `secure/encrypted.json`
- 编写 `tests/test_encryptor.py`

---

## Phase 2 — 核心层 (core/)
> 依赖 security/ 完成

### Step 3: `core/ltm.py`
- 实现 `LTMManager` 类
- 使用 `python-frontmatter` 解析/写入 `long-term-memory.md`
- 实现 CRUD + `load_profile()` + 关键词搜索
- 编写 `tests/test_ltm.py`

### Step 4: `core/kb.py`
- 实现 `KBManager` 类
- 使用 `python-frontmatter` 管理 `knowledge-base.md`
- 实现 add / search / update / delete / import_text
- 编写 `tests/test_kb.py`

### Step 5: `core/stm.py`
- 实现 `STMManager` 类
- 纯内存操作（dict + list）
- 实现 start/end session、上下文更新、事件日志、pending_saves 队列
- 编写 `tests/test_stm.py`

---

## Phase 3 — API 层 (api/)
> 依赖 core/ 完成

### Step 6: `config.py` + `api/models.py`
- 定义所有路径配置（memory_dir, secure_dir）
- 定义所有 Pydantic 请求/响应模型

### Step 7: `api/routes/memory.py` + `api/routes/session.py`
- 实现 /memory/* 和 /session/* 路由
- 注入 LTMManager 和 STMManager 依赖

### Step 8: `api/routes/kb.py`
- 实现 /kb/* 路由
- 注入 KBManager 依赖

### Step 9: `api/server.py` + `main.py`
- 组装 FastAPI app
- 注册所有路由
- 添加全局异常处理
- 编写 `tests/test_api.py`（集成测试）

---

## Phase 4 — 打包与文档

### Step 10: `requirements.txt` + `README_ENGINE.md`
- 最终 requirements.txt
- 启动说明、API 文档链接
- 与 system-prompt.md 的集成说明

---

## 每步执行规范 / Per-Step Protocol

执行每步前必须确认：
1. 上一步的测试全部通过
2. `progress.md` 已更新
3. 只修改本步骤涉及的文件，不提前写其他模块

执行每步后必须做：
1. 运行 `pytest tests/test_[module].py`
2. 更新 `progress.md`
3. 提交 Git（如适用）
