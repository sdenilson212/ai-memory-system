# 🚀 快速开始指南 - 创建 GitHub 仓库并推送代码

## 方法一：使用 GitHub 网页界面（推荐，最简单）

### 步骤 1：创建 GitHub 仓库

1. 打开浏览器，访问：https://github.com/new

2. 填写仓库信息：
   - **Repository name**（仓库名称）：`ai-memory-system`
   - **Description**（描述）：`AI Memory System - 持久化长期记忆、知识库和会话追踪系统`
   - **Public**（公开）：✅ 选中（公开仓库）
   - **不要勾选**以下选项：
     - ❌ Add a README file
     - ❌ Add .gitignore
     - ❌ Choose a license

3. 点击绿色的 **"Create repository"** 按钮

4. 创建成功后，你会看到类似这样的页面：
   ```
   …or create a new repository on the command line
   echo "# ai-memory-system" >> README.md
   git init
   git add README.md
   git commit -m "first commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ai-memory-system.git
   git push -u origin main
   ```

### 步骤 2：推送代码到 GitHub

打开 **PowerShell** 或 **命令提示符**，执行以下命令：

```powershell
# 进入项目目录
cd C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system

# 添加远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/ai-memory-system.git

# 推送代码到 GitHub
git push -u origin main
```

**注意：** 如果提示需要认证，GitHub 会让你输入 Personal Access Token（PAT）或使用 GitHub 认证。

### 步骤 3：创建第一个 Release

1. 访问你新创建的仓库页面：
   ```
   https://github.com/YOUR_USERNAME/ai-memory-system
   ```

2. 点击右侧的 **Releases** 链接

3. 点击 **Create a new release** 按钮

4. 填写 Release 信息：
   - **Choose a tag**：输入 `v1.0.0`（会自动创建新标签）
   - **Release title**：`v1.0.0 - Initial Release`
   - **Description**：复制以下内容：

```markdown
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
```

5. 点击 **Publish release** 按钮

### 步骤 4：配置仓库设置（可选）

#### 添加 Topics（标签）

1. 在仓库页面，点击 **Settings** 标签
2. 向下滚动找到 **Topics** 部分
3. 添加以下标签（用回车分隔）：
   - ai
   - memory
   - mcp
   - model-context-protocol
   - knowledge-base
   - session-management
   - python
   - workbuddy
   - claude
   - chatgpt

#### 启用功能

在 **Settings** → **Features** 中启用：
- ✅ Issues（用于 Bug 报告和功能请求）
- ✅ Discussions（用于一般讨论和问答）
- ✅ Projects（可选，用于项目管理）
- ✅ Wiki（可选，用于扩展文档）

---

## 方法二：使用 GitHub CLI（高级）

如果你刚安装了 GitHub CLI，需要先刷新环境变量：

### 刷新环境变量

1. **关闭当前的 PowerShell 窗口**
2. **重新打开一个新的 PowerShell 窗口**
3. 验证安装：
   ```powershell
   gh --version
   ```

### 登录 GitHub

```powershell
# 进入项目目录
cd C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system

# 登录 GitHub（会在浏览器中打开认证页面）
gh auth login

# 选择：
# GitHub.com
# HTTPS
# Yes（上传 SSH keys）
# Login with a web browser
```

### 创建仓库并推送

```powershell
# 创建远程仓库
gh repo create ai-memory-system --public --source=. --remote=origin --description "AI Memory System - 持久化长期记忆、知识库和会话追踪系统"

# 推送代码
git push -u origin main
```

### 创建 Release

```powershell
# 创建 v1.0.0 Release
gh release create v1.0.0 --title "v1.0.0 - Initial Release" --notes-file CHANGELOG.md
```

---

## 🎉 完成后的验证

推送成功后，你应该能够：

1. ✅ 在浏览器中访问你的仓库：
   ```
   https://github.com/YOUR_USERNAME/ai-memory-system
   ```

2. ✅ 看到所有文件和文件夹

3. ✅ 查看提交历史（2 个提交）

4. ✅ 看到 Releases 页面有 v1.0.0 版本

5. ✅ 可以克隆你的仓库：
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-memory-system.git
   ```

---

## ❓ 常见问题

### Q1: 推送时提示认证失败怎么办？

**A:** GitHub 已不再支持密码认证，你需要：

1. 生成 Personal Access Token (PAT)：
   - 访问：https://github.com/settings/tokens
   - 点击 **Generate new token (classic)**
   - 勾选 `repo` 权限
   - 点击生成并复制 token

2. 推送时使用 token：
   ```powershell
   git push -u origin main
   # 用户名：输入你的 GitHub 用户名
   # 密码：粘贴生成的 token（不是你的 GitHub 密码）
   ```

### Q2: 如何更新代码？

```powershell
# 添加更改
git add .

# 提交
git commit -m "feat: add new feature"

# 推送
git push
```

### Q3: 如何创建新的版本？

```powershell
# 更新 CHANGELOG.md

# 创建标签
git tag -a v1.1.0 -m "Release v1.1.0"

# 推送标签
git push origin v1.1.0

# 在 GitHub 上创建 Release
```

---

## 📞 需要帮助？

如果遇到问题，可以：
- 查看详细指南：`GITHUB_SETUP.md`
- 查看 GitHub 文档：https://docs.github.com
- 提交 Issue 到你的仓库

---

**祝你开源顺利！🎉**
