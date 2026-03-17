## 🎉 AI Memory System v1.0.0

这是 AI Memory System 的首次公开发布！

### ✨ 主要功能

#### 长期记忆 (Long-Term Memory)
- 记忆保存、检索、更新、删除
- 用户档案管理
- 灵活的标签系统
- 敏感数据自动检测和加密

#### 知识库 (Knowledge Base)
- 知识条目添加、搜索、更新、删除
- 知识索引
- 批量导入支持

#### 会话管理 (Session Management)
- 会话开始和结束
- 会话上下文更新
- 事件记录
- 待保存队列管理

#### MCP 集成
- 17 个可用 MCP 工具
- 完整的 MCP 服务器实现
- 支持多平台（WorkBuddy、Claude、ChatGPT 等）

#### 安全功能
- AES-256 加密
- 密码短语保护
- 敏感数据自动检测

### 📦 技术栈

- Python 3.10+
- MCP (Model Context Protocol)
- React + TypeScript + Vite (Web UI)
- Docker 支持
- 跨平台支持（Windows、macOS、Linux）

### 📚 文档

- [快速开始指南](README.md)
- [贡献指南](CONTRIBUTING.md)
- [MCP 集成指南](engine/MCP_GUIDE.md)
- [安全策略](SECURITY.md)
- [更新日志](CHANGELOG.md)

### 🌟 特性

- ✅ 中英双语文档
- ✅ 完整的测试工具
- ✅ 轻量级设计（无外部依赖）
- ✅ MIT 开源许可证

### 🚀 快速开始

1. 部署系统提示词：将 `system-prompt.md` 中的内容复制到你的 AI 工具的 System Prompt 字段
2. 创建记忆库目录：按照 README.md 中的说明创建目录结构
3. 开始对话：直接开始使用，AI 会自动激活记忆系统

### 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

感谢使用 AI Memory System！🙏
