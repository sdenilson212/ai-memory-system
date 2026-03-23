# 更新日志 / Changelog

本文档记录 AI Memory System 的所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

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

### 新增 / Added

#### 自适应 Skill 系统（Adaptive Skill System）
- ✅ **三层递进机制** — Layer 1 直接调用 KB / Layer 2 组合 LTM / Layer 3 自动生成
- ✅ **Layer 2 组合引擎** (`engine/skill_composer.py`) — 从 LTM 搜索并组合出新 Skill
- ✅ **Layer 3 生成引擎** (`engine/skill_generator.py`) — 支持模板法、类比法、分解法、混合法四种生成策略
- ✅ **质量评估引擎** (`engine/quality_evaluator.py`) — 7 维度评分（完整性/清晰度/可行性/证据支持/泛化性/新颖性/风险缓解），通过阈值 ≥ 0.70 自动审批
- ✅ **系统集成** (`engine/adaptive_skill_system.py`) — Layer 1/2/3 完整数据流打通

#### AI 员工记忆体系
- ✅ **员工专属记忆标签** — 每位员工拥有独立的成长记录（`engine/memory-bank/employees/`）
- ✅ **员工成长积分系统** — 每次任务完成自动追加成长日志（`growth-logs/`）
- ✅ **员工会话启动协议** — 激活时自动 `kb_search` 历史经验，静默参考提升输出质量

#### 架构文档
- ✅ `ADAPTIVE_SKILL_SYSTEM.md` — 2000+ 行完整架构设计
- ✅ `IMPLEMENTATION_GUIDE.md` — 1200+ 行详细实现指南
- ✅ `DEEPENING_SUMMARY.md` — 阶段深化总结
- ✅ `DIRECTION_1_VERIFICATION_REPORT.md` — 方向验证报告

### 改进 / Improved
- 完善 `engine/core/deduplicator.py`，实现完整去重逻辑（相似度阈值 85%）
- 完善 `engine/core/vector_store.py`，实现轻量级向量存储（无需 ChromaDB 依赖）
- 完善 `engine/backup_restore.py`，完整备份管理器（增量/全量/自动调度）
- 更新 `README.md`，补充自适应 Skill 系统说明和员工记忆体系介绍

### 技术实现
- Python 3.10+，纯 OOP 设计，模块化高度可测试
- 自适应 Skill 系统：`skill_composer.py`（400+ 行）+ `skill_generator.py`（500+ 行）+ `quality_evaluator.py`（450+ 行）
- 总新增代码量：2000+ 行

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
