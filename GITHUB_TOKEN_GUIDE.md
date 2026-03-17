# 🔐 GitHub Token 获取指南

## 📋 步骤 1: 生成 Personal Access Token

### 方法一：通过 GitHub 网页（推荐）

1. **访问 Settings 页面**
   - 打开：https://github.com/settings/tokens

2. **创建新 Token**
   - 点击右上角的 **"Generate new token"**
   - 选择 **"Generate new token (classic)"**

3. **配置 Token**
   - **Note（备注）**：输入 `AI Memory System Release`
   - **Expiration（过期时间）**：选择 `No expiration`（永不过期）或 `90 days`
   - **Scopes（权限范围）**：
     - ✅ 勾选 `repo`（这个权限可以访问所有仓库操作）
     - 或者更精细的选择：
       - ✅ `public_repo`（如果只需要操作公开仓库）
       - ✅ `repo:status`（如果需要访问 commit status）
       - ✅ `repo_deployment`（如果需要创建 deployments）

4. **生成并复制 Token**
   - 点击底部的绿色按钮 **"Generate token"**
   - **重要**：立即复制显示的 Token（以 `ghp_` 开头）
   - ⚠️ Token 只显示一次，关闭页面后无法再次查看

---

## 📋 步骤 2: 运行自动化脚本

### 方式一：命令行直接输入 Token（推荐）

打开 **PowerShell** 或 **命令提示符**，执行：

```powershell
cd C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system
python create_release.py
```

然后：
1. 脚本会提示你输入 Token
2. 粘贴刚才复制的 Token
3. 脚本会自动创建 Tag 和 Release

### 方式二：作为命令行参数

```powershell
cd C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system
python create_release.py YOUR_TOKEN_HERE
```

将 `YOUR_TOKEN_HERE` 替换为你的实际 Token。

---

## 🔍 验证 Token 权限

如果你的 Token 权限不足，脚本会报错。请确保：

### 必需权限
- ✅ `repo` - 完整的仓库访问权限

### 或者使用更精细的权限
- ✅ `public_repo` - 访问公开仓库
- ✅ `repo:status` - 读取 commit status
- ✅ `repo_deployment` - 管理部署

---

## 🚀 脚本执行流程

当你运行 `create_release.py` 时，它会：

1. **创建 Git Tag**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

2. **调用 GitHub API 创建 Release**
   - URL: `https://api.github.com/repos/sdenilson212/ai-memory-system/releases`
   - 方法: `POST`
   - 数据: 包含 tag、title、description 等

3. **显示结果**
   - 成功：显示 Release URL 和信息
   - 失败：显示错误信息

---

## ❓ 常见问题

### Q1: 提示 "Bad credentials"
**A:** Token 无效或已过期。请重新生成一个新的 Token。

### Q2: 提示 "Resource not found"
**A:** 仓库不存在或 Token 没有访问权限。检查：
- 仓库名称是否正确（`sdenilson212/ai-memory-system`）
- Token 是否有 `repo` 或 `public_repo` 权限

### Q3: 提示 "Tag already exists"
**A:** Tag 已存在。可以：
- 选项 1：删除现有 tag，重新创建
- 选项 2：直接创建 Release（跳过 tag 步骤）

### Q4: 脚本运行时提示 "module 'requests' not found"
**A:** 需要安装 requests 库：
```powershell
pip install requests
```

### Q5: Token 安全吗？
**A:** Token 只会保存在内存中，不会被写入文件。脚本运行结束后，Token 会被清除。

---

## 🔐 安全注意事项

1. **不要分享你的 Token**
   - Token 相当于你的密码，拥有完整的仓库访问权限
   - 不要在公开场合（Issues、Discussions 等）泄露 Token

2. **定期更换 Token**
   - 如果怀疑 Token 泄露，立即撤销
   - 在 Settings → Tokens 中可以删除或管理 Token

3. **使用最小权限原则**
   - 只授予必要的权限（如 `public_repo` 而不是 `repo`）
   - 设置合理的过期时间

---

## 📊 预期输出

### 成功示例：

```
============================================================
🚀 AI Memory System - 自动创建 Release v1.0.0
============================================================

✅ 已从命令行参数获取 token

📌 正在创建标签: v1.0.0
✅ 本地 tag 创建成功
✅ Tag 已推送到 GitHub

🚀 正在创建 GitHub Release...
✅ Release 创建成功！

📋 Release 信息:
  - 标题: v1.0.0 - Initial Release
  - 标签: v1.0.0
  - URL: https://github.com/sdenilson212/ai-memory-system/releases/tag/v1.0.0

🎉 恭喜！Release 已发布！

============================================================
🎊 完成！
============================================================

📝 下一步建议:
  1. 访问你的仓库: https://github.com/sdenilson212/ai-memory-system
  2. 查看 Releases 页面: https://github.com/sdenilson212/ai-memory-system/releases
  3. 添加仓库 Topics: Settings -> Topics
  4. 分享到社交媒体: 知乎、Twitter 等
```

### 失败示例：

```
============================================================
🚀 AI Memory System - 自动创建 Release v1.0.0
============================================================

请输入你的 GitHub Personal Access Token:
(从 https://github.com/settings/tokens 生成，需要 'repo' 权限)
> ghp_xxxxxxxxxxxxxxxx

📌 正在创建标签: v1.0.0
✅ 本地 tag 创建成功
✅ Tag 已推送到 GitHub

🚀 正在创建 GitHub Release...
❌ Release 创建失败
状态码: 404
响应: {"message": "Not Found"}

❌ Release 创建失败，请检查:
  1. Token 是否有效且具有 'repo' 权限
  2. 网络连接是否正常
  3. 仓库是否存在且可访问
```

---

## 💪 准备好了吗？

按照上面的步骤：

1. ✅ 访问 https://github.com/settings/tokens
2. ✅ 生成 Personal Access Token（勾选 `repo` 权限）
3. ✅ 复制 Token
4. ✅ 运行脚本：`python create_release.py`
5. ✅ 粘贴 Token
6. ✅ 等待 Release 创建成功！

需要帮助随时告诉我！🚀
