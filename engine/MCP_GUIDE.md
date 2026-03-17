# AI Memory System — MCP 接入指南

## 快速接入（5分钟完成）

### 前置条件
- Python 3.10+
- 依赖已安装：`pip install -r requirements.txt`（如未安装，先执行）

---

## 方式 1：WorkBuddy 接入（推荐）

### 步骤 1 — 打开 MCP 设置
在 WorkBuddy 中打开设置 → MCP → 编辑配置文件

### 步骤 2 — 添加配置
将以下内容合并到你的 MCP 配置文件中：

```json
{
  "mcpServers": {
    "ai-memory-system": {
      "command": "python",
      "args": [
        "C:/Users/sdenilson/WorkBuddy/Claw/output/ai-memory-system/engine/mcp_server.py"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

> 配置文件已生成：`mcp_config/workbuddy_mcp.json`，可直接复制使用。

### 步骤 3 — 重启 WorkBuddy
重启后，你会在工具列表中看到以下 21 个工具全部出现。

---

## 方式 2：Claude Desktop 接入

### 配置文件位置
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`
- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`

### 添加配置
```json
{
  "mcpServers": {
    "ai-memory-system": {
      "command": "python",
      "args": [
        "C:/Users/sdenilson/WorkBuddy/Claw/output/ai-memory-system/engine/mcp_server.py"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

---

## 方式 3：SSE 模式（网络客户端）

适用于需要通过 HTTP 连接的客户端（如自定义 Web 应用）：

```bash
python mcp_server.py --sse --port 8766
# 连接地址：http://127.0.0.1:8766/sse
```

---

## 完整工具清单（21个）

### 长期记忆 (LTM) — 7个

| 工具名 | 作用 | 何时使用 |
|---|---|---|
| `memory_save` | 保存新的长期记忆条目 | 用户分享个人信息、偏好、项目 |
| `memory_recall` | 关键词搜索长期记忆 | **每次对话开始时** 加载上下文 |
| `memory_get` | 按 ID 获取单条记忆 | 查看具体条目详情 |
| `memory_update` | 更新条目内容/标签/分类 | 用户纠正或更新信息 |
| `memory_delete` | 删除条目（需 confirm=true） | 用户要求遗忘某内容 |
| `memory_profile` | 获取用户档案摘要 | **每次新对话** 个性化响应 |
| `memory_list` | 列出所有条目 | 用户查看记忆列表 |

### 知识库 (KB) — 6个

| 工具名 | 作用 | 何时使用 |
|---|---|---|
| `kb_add` | 添加知识库条目 | 用户上传文档/笔记 |
| `kb_search` | 搜索知识库 | 回答问题前查阅背景知识 |
| `kb_update` | 更新知识库条目 | 修改已有知识 |
| `kb_delete` | 删除知识库条目 | 清理过时内容 |
| `kb_index` | 获取知识库索引 | 浏览可用知识 |
| `kb_import` | 批量导入大段文本 | 用户粘贴大型文档 |

### 会话追踪 (STM) — 7个

| 工具名 | 作用 | 何时使用 |
|---|---|---|
| `session_start` | 开始新会话 | **每次对话最开始** |
| `session_update` | 更新会话上下文 | 追踪当前任务状态 |
| `session_event` | 记录会话事件 | 记录重要节点 |
| `session_queue` | 加入待保存队列 | AI 检测到值得记住的内容 |
| `session_pending` | 查看待保存列表 | 对话结束前确认 |
| `session_end` | 结束会话 | 每次对话结束时 |

### 状态 — 1个

| 工具名 | 作用 |
|---|---|
| `memory_status` | 系统状态、条目统计 |

---

## AI 的标准工作流程

### 对话开始时（每次必做）
```
1. session_start           → 开始追踪本次对话
2. memory_profile          → 了解用户是谁
3. memory_recall(主题词)   → 加载相关历史上下文
```

### 对话过程中（自动触发）
```
当用户分享个人信息     → memory_save (category=profile)
当用户提到偏好         → memory_save (category=preference)
当用户分享文档/知识    → kb_import 或 kb_add
当 AI 学到新知识       → session_queue + 对话结束时保存
当用户纠正 AI          → memory_update 或 memory_save
```

### 对话结束时（建议）
```
1. session_pending     → 查看本次对话积累的待保存内容
2. memory_save × N    → 将重要内容保存到 LTM
3. session_end         → 清理会话
```

---

## 命令词触发速查

| 用户说 | AI 应调用 |
|---|---|
| `/remember [内容]`、`记住 [内容]` | `memory_save` |
| `/recall [话题]`、`回忆 [话题]` | `memory_recall` |
| `/forget [内容]`、`忘记 [内容]` | `memory_delete (confirm=true)` |
| `/kb add [内容]`、`加入知识库` | `kb_add` 或 `kb_import` |
| `/kb search [词]` | `kb_search` |
| `/memory status`、`记忆状态` | `memory_status` |
| `我叫 [名字]`、`我是 [职业]` | `memory_save (category=profile)` |
| `我喜欢/不喜欢 [某事]` | `memory_save (category=preference)` |

---

## 敏感数据处理

系统会自动检测以下模式并脱敏：
- API Key（`sk-`、`Bearer `、`token` 等前缀）
- 密码（`password=`、`pwd=`）
- 信用卡号（16位数字）
- 证件号（身份证）
- JWT Token（`eyJ` 开头）
- 私钥（`-----BEGIN`）

**加密保存**：提供 `passphrase` 参数时，敏感值用 AES-256-GCM 加密存入 `memory-bank/secure/encrypted.json`，记忆文件中只保存 `[ENCRYPTED: key_name]` 引用。

---

## 常见问题

**Q: 工具不出现在工具列表？**
检查 Python 路径是否正确，以及 `mcp` 库是否已安装（`pip install mcp`）。

**Q: 记忆文件在哪里？**
`engine/memory-bank/long-term-memory.md` 和 `knowledge-base.md`，人类可读的 Markdown 格式，可以直接编辑。

**Q: 多台设备同步？**
把 `memory-bank/` 目录放到 OneDrive / Dropbox / Git 里即可。注意：`secure/encrypted.json` 不要提交到公开仓库。

**Q: 知识库太大会慢吗？**
目前是关键词搜索，条目数 < 1000 时基本无感。如果需要语义搜索，可以后续接入 ChromaDB（已预留接口）。
