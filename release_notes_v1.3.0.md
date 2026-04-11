# AI Memory System v1.3.0

> 本版本聚焦于生产可用性修复：解决大数据量下的存储瓶颈、多客户端并发安全、以及密钥管理易用性问题。

---

## 🔧 修复 / Bug Fixes

### ⚡ 并发安全（Multi-Client Concurrency）
- 集成 [`filelock`](https://pypi.org/project/filelock/)（v3.13+），对每个记忆分片文件加读写锁，防止多客户端同时写入导致数据丢失
- 未安装 `filelock` 时自动降级为 `_NullLock`（单进程场景安全），不影响启动
- `requirements.txt` 新增 `filelock>=3.13.0` 依赖

### 🗂️ 存储分片（Storage Sharding）
- LTM 存储从单文件拆分为按 `category` 分片，共 7 个分片：
  - `long-term-memory-preference.md`
  - `long-term-memory-decision.md`
  - `long-term-memory-profile.md`
  - `long-term-memory-goal.md`
  - `long-term-memory-project.md`
  - `long-term-memory-habit.md`
  - `long-term-memory-other.md`
- `save()` / `search()` 指定 category 时只操作目标分片（O(k) → O(1)），全量操作才扫描所有分片
- `update()` 支持 category 变更时跨分片自动迁移
- 旧版 `long-term-memory.md` 首次启动时**自动迁移**到分片，迁移完成后重命名为 `.migrated.md`

### 🔑 Passphrase 管理（Passphrase Management）
- 新增 `Encryptor.get_passphrase()` 静态方法，优先级：**显式传入 > 环境变量 `MEMORY_PASSPHRASE` > 降级脱敏存储**
- `ltm.save()` 自动调用，无需每次手动传 passphrase
- 文档补充设置示例（Windows / Linux / macOS / `.env` 文件）

### 📋 Trigger 规则文档（Trigger Documentation）
- `trigger.py` 顶部新增完整触发规则参考表（LTM 规则 + KB 规则 + 置信度阈值说明 + 扩展方法）
- 新增 `analyze_text(text)` 接口说明

---

## ✨ 新增模块 / New Modules

### 自适应技能系统（Adaptive Skill System）
- **Layer 2 组合引擎** (`skill_composer.py`) — 从 LTM 中提取信息组合成新技能
- **Layer 3 生成引擎** (`skill_generator.py`) — 4 种生成策略：模板法、类比法、分解法、混合法
- **质量评估引擎** (`quality_evaluator.py`) — 7 维度评分（完整性、清晰度、可行性等），通过阈值 ≥ 0.70 自动审批
- 完整的 Layer 1→2→3 递进架构文档（`ADAPTIVE_SKILL_SYSTEM.md`、`IMPLEMENTATION_GUIDE.md`）

---

## 🚀 如何升级

```bash
pip install filelock>=3.13.0
```

设置加密密钥（可选，推荐）：
```bash
# Windows
setx MEMORY_PASSPHRASE "your-secret-key"

# Linux/macOS
export MEMORY_PASSPHRASE="your-secret-key"
```

---

## 📊 验证

本版本所有修复已通过 8 项自动化验证（`engine/verify_fix.py`）：

| # | 验证项 | 状态 |
|---|--------|------|
| 1 | 分片文件创建 | ✅ PASS |
| 2 | preference 分片写入 | ✅ PASS |
| 3 | filelock 可用（v3.25.2） | ✅ PASS |
| 4 | 分片删除 | ✅ PASS |
| 5 | 环境变量 passphrase 读取 | ✅ PASS |
| 6 | 显式传入优先级 | ✅ PASS |
| 7 | passphrase 降级 | ✅ PASS |
| 8 | Trigger 文档存在 | ✅ PASS |

---

**Full Changelog**: https://github.com/sdenilson212/ai-memory-system/compare/v1.2.0...v1.3.0
