# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-03-25

### 🚀 Features
- **并发安全**: 添加 SafeFileWriter 文件锁 + WAL 操作日志，防止多进程写冲突
- **SQLite 索引**: 新增 LTMIndex 类，搜索从 O(n) → O(log n)
- **语义搜索**: VectorStore 支持多后端 Embedding（TF-IDF / OpenAI / 通义 / HuggingFace）
- **混合搜索**: hybrid_search() 支持关键词 + 向量结果融合
- **Passphrase 管理**: 新增 passphrase_manager.py，支持环境变量 / keyring 双通道
- **触发规则自定义**: 支持 YAML 规则文件加载 + 运行时动态添加规则

### 🔧 Improvements
- 重写 README 为产品化版本
- 添加 GitHub Sponsors 支持说明
- 完善许可证和贡献指南

---

## [1.0.0] - 2026-03-17

### 🎉 Initial Release
- LTM 长期记忆管理器
- KB 知识库管理器
- STM 会话追踪
- Trigger 触发引擎
- 向量存储（基础版）
- MCP Server 17个工具
- FastAPI 接口
- 敏感信息自动加密

---

## 📅 Planned

### v1.2.0 (Q2 2026)
- [ ] Web Dashboard（可视化记忆管理）
- [ ] 多用户支持
- [ ] 云端同步
- [ ] Pro 版发布

### v2.0.0 (Q3 2026)
- [ ] 分布式部署
- [ ] 向量数据库集成（Milvus / Qdrant）
- [ ] 企业版功能
