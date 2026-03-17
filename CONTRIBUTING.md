# 贡献指南 / Contributing Guide

感谢你对 AI Memory System 的关注！我们欢迎各种形式的贡献。

---

## 🤝 如何贡献 / How to Contribute

### 报告 Bug / Bug Reports

如果你发现了 bug，请：

1. 检查 [Issues](../../issues) 中是否已有相同问题
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤
   - 预期行为 vs 实际行为
   - 环境信息（操作系统、Python 版本等）
   - 相关日志或截图

### 提出新功能 / Feature Requests

我们欢迎功能建议！请在创建 Issue 时：

1. 说明功能的用途和场景
2. 描述预期的行为
3. 如果有实现想法，也欢迎分享
4. 讨论该功能的适用性和优先级

### 提交代码 / Code Contributions

#### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/ai-memory-system.git
cd ai-memory-system

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
cd engine
pip install -r requirements.txt
```

#### 代码规范

1. **遵循 PEP 8** Python 代码风格
2. **添加注释** 解释复杂逻辑
3. **编写测试** 为新功能添加测试用例
4. **更新文档** 修改功能时同步更新相关文档
5. **提交前自检** 运行测试确保通过

#### Pull Request 流程

1. **Fork 仓库** 到你的 GitHub
2. **创建分支**：`git checkout -b feature/your-feature-name`
3. **提交更改**：
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
4. **推送分支**：`git push origin feature/your-feature-name`
5. **创建 Pull Request** 到主仓库

#### Commit 消息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整（不影响功能）
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

示例：
```
feat: add memory encryption support
fix: resolve memory search encoding issue
docs: update README with new commands
```

---

## 📝 项目结构 / Project Structure

```
ai-memory-system/
├── engine/           # 核心 MCP 服务器和 API
│   ├── core/        # 核心逻辑（记忆、知识库、会话）
│   ├── api/         # API 接口
│   ├── security/    # 加密模块
│   └── mcp_server.py # MCP 服务器入口
├── memory-bank/     # 记忆存储目录（不提交）
├── templates/       # 记忆模板
└── ui/              # 可选：管理界面（如果有的话）
```

---

## 🧪 测试 / Testing

运行测试：

```bash
cd engine
python verify.py          # 验证系统完整性
python test_api.py        # 测试 API
python run_full_test.py   # 完整测试套件
```

---

## 📖 文档 / Documentation

- **README.md** - 快速开始指南
- **README_EN.md** - 英文版 README
- **engine/MCP_GUIDE.md** - MCP 集成指南
- **system-prompt.md** - System Prompt 模板

---

## 🌍 语言 / Language

- 主要使用中文进行讨论
- 代码注释可以使用中文或英文
- Issue 和 PR 可以使用中英文

---

## 📜 行为准则 / Code of Conduct

1. **尊重他人** - 保持礼貌和专业
2. **建设性反馈** - 提出有价值的建议
3. **欢迎新手** - 耐心回答问题
4. **开源精神** - 分享知识和经验

---

## 💬 联系方式 / Contact

如有问题，可以通过以下方式联系：

- GitHub Issues: [提交问题](../../issues)
- Discussions: [参与讨论](../../discussions)

---

**感谢你的贡献！🎉**
