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

## [未来计划 / Future Plans]

### 1.2.0 - 计划中
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

*最后更新: 2026-03-17*
