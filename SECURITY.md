# 安全策略 / Security Policy

## 支持的版本 / Supported Versions

| 版本 | 支持状态 |
|------|----------|
| 1.0.0 | ✅ 支持中 |

---

## 🛡️ 安全报告 / Reporting a Vulnerability

如果你发现了安全漏洞，**请不要公开提交 Issue**。请通过以下方式私下报告：

### 报告方式

1. **发送邮件** 至：[你的邮箱地址]
2. 或使用 GitHub 的 **私有安全公告** 功能

### 报告内容应包括

- 漏洞的详细描述
- 复现步骤（如有可能）
- 潜在的影响范围
- 建议的修复方案（可选）

### 响应流程

1. **确认收到** - 我们会在 48 小时内回复确认
2. **评估验证** - 验证漏洞的严重程度和影响范围
3. **制定方案** - 开发修复方案
4. **修复测试** - 在安全环境中测试修复
5. **发布更新** - 发布补丁版本
6. **公开披露** - 在修复发布后公开漏洞信息

### 响应时间承诺

| 严重程度 | 响应时间 | 修复时间 |
|----------|----------|----------|
| 严重 (Critical) | 48 小时 | 7 天 |
| 高危 (High) | 72 小时 | 14 天 |
| 中危 (Medium) | 5 天 | 30 天 |
| 低危 (Low) | 7 天 | 60 天 |

---

## 🔒 已知安全注意事项

### 1. 加密存储

- 敏感数据使用 AES-256 加密
- 密码短语由用户自行管理
- 加密密钥不存储在记忆文件中

**最佳实践：**
- 使用强密码短语（至少 16 字符）
- 定期更换密码短语
- 不要将密码短语提交到 Git

### 2. 文件权限

**生产环境建议：**
```bash
# 限制 memory-bank 目录访问权限
chmod 700 memory-bank/
chmod 600 memory-bank/secure/encrypted.json
```

### 3. Git 安全

**⚠️ 重要提醒：**
- `memory-bank/` 目录**不应**提交到 Git
- `encrypted.json` 已在 `.gitignore` 中排除
- 提交前检查是否有敏感数据意外包含

**检查命令：**
```bash
# 查看将要提交的内容
git diff --cached

# 搜索可能的敏感数据
git grep -i "password\|secret\|token\|key"
```

### 4. 环境变量

敏感配置应使用环境变量：

```bash
# 示例
export MEMORY_PASSPHRASE="your-secure-passphrase"
export MEMORY_DIR="/path/to/memory-bank"
```

### 5. 审计日志

建议启用日志记录并定期审查：

```python
# 在代码中启用详细日志
import logging
logging.basicConfig(level=logging.INFO)
```

---

## 🎯 安全最佳实践

### 对于用户

1. **定期备份** - 备份 `memory-bank/` 目录
2. **使用强密码** - 密码短语至少 16 字符
3. **隔离环境** - 生产环境使用独立的环境
4. **更新依赖** - 定期更新 Python 和相关库
5. **审查权限** - 检查文件和目录权限

### 对于开发者

1. **输入验证** - 所有用户输入都应验证
2. **输出编码** - 防止注入攻击
3. **最小权限** - 只请求必要的权限
4. **安全测试** - 在发布前进行安全测试
5. **依赖审计** - 定期检查依赖项的安全性

---

## 📋 常见安全问题

### Q1: 记忆文件会被公开吗？

**A:** 不会。`memory-bank/` 目录默认在 `.gitignore` 中，不会被提交到公开仓库。

### Q2: 加密数据安全吗？

**A:** 使用 AES-256 加密，这是工业级加密标准。安全性取决于你的密码短语强度。

### Q3: 如何备份我的记忆？

**A:** 定期备份 `memory-bank/` 整个目录到安全位置。

### Q4: 多人协作安全吗？

**A:** 每个用户应有独立的 `memory-bank/` 目录和密码短语。不要共享加密文件。

---

## 🔗 相关资源

- [OWASP Python Security](https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)
- [Python Cryptography Best Practices](https://docs.python.org/3/library/crypto.html)
- [MITRE CVE](https://cve.mitre.org/)

---

**感谢帮助保持 AI Memory System 安全！** 🙏
