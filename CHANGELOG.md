# 更新日志 / Changelog

本文档记录 AI Memory System 的所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [1.4.0] - 2026-03-26

### 新增 / Added

#### 自适应 Skill 系统（Adaptive Skill System）核心功能实装
- ✅ `_try_layer_1()`：接通真实 KB 搜索 + 本地缓存，支持中文字符 2-gram 分词匹配
- ✅ `_compute_skill_relevance()`：Skill 与问题的关联度计算（0-1 分）
- ✅ `_skill_from_kb_entry()`：将 KB 条目包装为轻量 Skill 壳，可直接执行
- ✅ `_execute_framework_step()`：框架步骤真实处理，传递自定义说明与上下文
- ✅ `_execute_memory_step()`：记忆步骤应用问题关键词，生成个性化建议
- ✅ `_execute_generated_step()`：自动生成步骤整合前序输出，附置信度标注
- ✅ `_analyze_feedback()`：情感三态（positive / negative / neutral）+ 6 类方面词提取（步骤/内容/数量/方向/数据/格式）
- ✅ `_try_layer_2/3` 导入兼容：相对导入失败时自动动态加载，支持包外直接运行

### 测试 / Tests
- ✅ `tests/test_adaptive_skill_system.py`：新建 23 个单元测试，全部通过（23 passed / 0.16s）
  - 覆盖：Skill 序列化、执行器三类步骤、反馈分析、Layer 1 缓存命中/未命中/废弃跳过、Solve 端到端、KB 条目转 Skill

### 修复 / Fixed
- ✅ `confidence=0` 修正为 `0.0`（类型一致性）
- ✅ 情感分析正面词全改为整词匹配，避免中文子串误命中（如"请"被误判为正面）
- ✅ Layer 1 匹配阈值调整为 0.40，适应中文分词粒度

---

## [1.3.0] - 2026-03-25

### 修复 / Fixed

#### 并发安全
- ✅ 集成 `filelock`（v3.13+）对每个记忆分片文件加读写锁，防止多客户端同时读写丢数据
- ✅ 未安装 `filelock` 时自动降级为 `_NullLock`（单进程场景安全），不影响启动
- ✅ `requirements.txt` 新增 `filelock>=3.13.0` 依赖

#### 存储分片（解决单文件天花板）
- ✅ LTM 存储从单文件拆分为按 category 分片（`long-term-memory-preference.md` 等 7 个分片）
- ✅ `save()` / `search()` 有 category 时只操作目标分片，全量操作才扫描所有分片
- ✅ `update()` 支持 category 变更时跨分片迁移
- ✅ 旧版 `long-term-memory.md` 首次启动时自动迁移到分片，迁移完成后重命名为 `.migrated.md`

#### Passphrase 管理
- ✅ `Encryptor.get_passphrase()` 静态方法：优先级 显式传入 > 环境变量 `MEMORY_PASSPHRASE` > 降级脱敏存储
- ✅ `ltm.save()` 自动调用，无需每次手动传 passphrase
- ✅ 文档补充设置示例（Windows/Linux/Mac/.env 文件）

#### Trigger 规则文档
- ✅ `trigger.py` 顶部新增完整触发规则参考表（LTM 规则 + KB 规则 + 置信度说明 + 扩展方法）
- ✅ 新增 `analyze_text(text)` 接口说明

---

## [1.2.0] - 2026-03-17

## [1.0.0] - 2026-03-17

### 新增 / Added

#### 核心功能
- ✅ 长期记忆（Long-Term Memory）系统
- ✅ 知识库（Knowledge Base）管理
- ✅ 会话追踪（Session Tracking）
- ✅ 项目记忆（Project Memory）
- ✅ 记忆加密（Memory Encryption）

#### MCP 集成
- ✅ 完整的 MCP 服务器实现
- ✅ 17 个可用工具：
  - `memory_save` - 保存记忆
  - `memory_recall` - 检索记忆
  - `memory_get` - 获取单条记忆
  - `memory_update` - 更新记忆
  - `memory_delete` - 删除记忆
  - `memory_profile` - 用户档案
  - `memory_list` - 列出记忆
  - `kb_add` - 添加知识
  - `kb_search` - 搜索知识
  - `kb_update` - 更新知识
  - `kb_delete` - 删除知识
  - `kb_index` - 知识索引
  - `kb_import` - 批量导入
  - `session_start` - 开始会话
  - `session_update` - 更新会话
  - `session_event` - 记录事件
  - `session_queue` - 队列操作
  - `session_pending` - 待处理项
  - `session_end` - 结束会话
  - `memory_status` - 系统状态
  - `trigger_analyze` - 触发分析

#### API 接口
- ✅ RESTful API 支持
- ✅ JSON 数据格式
- ✅ 错误处理机制

#### 安全功能
- ✅ AES-256 加密敏感数据
- ✅ 密码短语保护
- ✅ 敏感数据自动检测
- ✅ 环境变量配置

#### 文档
- ✅ 完整的 README（中英双语）
- ✅ MCP 集成指南
- ✅ System Prompt 模板
- ✅ 项目记忆模板
- ✅ MIT 开源许可证

#### 测试工具
- ✅ 系统验证脚本
- ✅ API 测试套件
- ✅ MCP 工具验证
- ✅ 环境检查工具

### 技术实现
- Python 3.10+
- 标准库（无外部依赖）
- 支持 WorkBuddy、Claude、ChatGPT 等平台
- 跨平台支持（Windows、macOS、Linux）

### 优化 / Optimized
- 快速检索算法（支持模糊匹配）
- 灵活的标签系统
- 可扩展的架构设计
- 轻量级部署（~500KB 代码）

---

## [1.1.0] - 2026-03-17

### 新增 / Added
- ✅ **向量检索** - 基于 ChromaDB + sentence-transformers 的语义搜索
- ✅ **自动去重** - 检测相似内容，避免重复记忆
- ✅ **记忆权重** - 重要性评分（1-5级），影响检索排序
- ✅ **备份恢复** - 自动化备份和一键恢复工具

### 技术实现
- `engine/core/vector_store.py` - 向量存储模块
- `engine/core/deduplicator.py` - 去重检测模块
- `engine/core/weight.py` - 权重管理系统
- `engine/backup_restore.py` - 备份恢复工具

---

## [1.2.0] - 2026-03-17

### 改进 / Improved

#### 记忆系统触发机制优化
- ✅ **项目产出自动检测** — 完成新项目/系统/文件时，AI 主动将产出物写入知识库，无需用户手动触发
- ✅ **路径索引强制记录** — 知识库条目必须包含完整绝对路径，确保下次对话可精确定位文件
- ✅ **会话收尾强制扫描** — 对话结束前自动回顾本次产出物，列出未记录内容清单供用户确认
- ✅ **保存触发率提升** — 从"被动等触发"改为"主动扫描兜底"，防止重要成果丢失

#### 知识库补全
- ✅ 补录 AI 员工体系（ai-workforce-system）完整档案，包含组织架构、员工名单、路径索引、CEO使用指南

### 问题修复 / Fixed
- 修复新对话无法通过关键词找到已完成项目的问题（根因：项目构建完成时未写入记忆系统）

### 技术实现
- 更新 `ai-memory-system.mdc` 规则文件，新增项目产出自动检测规则和会话收尾强制扫描机制

---

## [1.3.0] - 2026-03-23

### 改进 / Improved

#### 核心模块完善
- ✅ **`engine/core/deduplicator.py`** — 完整去重逻辑，基于文本相似度（阈值 85%）自动检测并跳过重复记忆
- ✅ **`engine/core/vector_store.py`** — 轻量级向量存储，纯 Python 实现，无需 ChromaDB 等外部依赖
- ✅ **`engine/backup_restore.py`** — 完整备份管理器，支持增量备份、全量备份、自动调度与一键恢复

### 问题修复 / Fixed
- 修复 `deduplicator.py` 仅有接口无实现的问题
- 修复 `vector_store.py` 缺少实际存储逻辑的问题
- 修复 `backup_restore.py` 备份恢复流程不完整的问题

### 文档更新 / Docs
- 更新 `README.md`，补充 v1.3.0 核心模块说明
- 更新 `CHANGELOG.md`

---

## [未来计划 / Future Plans]

### 1.3.0 - 计划中
- [ ] 记忆压缩（AI 自动摘要）
- [ ] 多语言自然语言处理
- [ ] 分布式记忆存储
- [ ] 团队协作功能
- [ ] 插件系统

### 1.2.0 - 长期规划
- [ ] 分布式记忆存储
- [ ] 团队协作功能
- [ ] AI 自动记忆建议优化
- [ ] 插件系统
- [ ] 移动端支持

---

## 版本说明

- **[Unreleased]** - 尚未发布的变更
- **[X.Y.Z]** - 已发布版本
  - X: 主版本号（重大变更）
  - Y: 次版本号（新增功能）
  - Z: 修订号（Bug 修复）

---

*最后更新: 2026-03-23 | v1.3.0*
