# AI Memory System Benchmark v1

- 生成时间：2026-04-08T16:24:13+08:00
- 总体状态：needs_attention

## Scope 声明

- 目标系统：AI Memory System (pure scope)
- 纳入脚本：
  - `engine/verify.py`
  - `engine/verify_fix.py`
  - `engine/verify_mcp_tools.py`
  - `run_full_test.py`
- 排除脚本：
  - `tests/test_adaptive_skill_system.py`
  - `any adaptive-skill-system related tests`

## 结论摘要

- Correctness scope locked to pure AI Memory System: 68/68
- Retrieval seeded benchmark hit@k=1.0, MRR=1.0
- Integrity concurrent write checks: FAIL
- Known limitation remains: vector search is still TF-IDF placeholder, not embedding-grade semantic retrieval.

## Layer 1 — Correctness

- 纯系统 correctness 基线：**68/68**

| Check | Expected | Observed | Return Code | Elapsed ms | Status |
|---|---:|---:|---:|---:|---|
| engine.verify | 18 | 18 | 0 | 2116.49 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 868.83 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2819.92 | PASS |
| run_full_test | 20 | 20 | 0 | 3442.69 | PASS |

## Layer 2 — Retrieval Quality

- 数据集：`seeded-synthetic-v1`
- 这是首版种子集 benchmark，不代表真实线上分布。
- 目标是把 correctness 之外的 retrieval 能力显式量化。
- 案例刻意覆盖英文、中文、全角字符、accent folding。

### Overall

- cases=10 | hit_rate=1.0 | avg_precision@k=0.3666 | avg_recall@k=1.0 | MRR=1.0

### LTM aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.4 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| ltm-dark-mode-keyword | dark mode | 9ec16230-5061-4838-a4e3-3ca186656d50 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | b7c21932-1b73-4b8b-b062-bf09d16bdebe<br>bd5156b2-ce6b-44b9-859f-24f6563d585e | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | ac9dadcf-b9cc-4843-b42d-4ededa1ab509 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | f2ef96b3-df5d-496c-a510-560fddbfea14 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | b7c21932-1b73-4b8b-b062-bf09d16bdebe<br>bd5156b2-ce6b-44b9-859f-24f6563d585e | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 89d875f8-3aba-4e07-9c5c-46640ec21343 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | 06b6384b-13e3-4fe4-a30f-24b93eb4a7ae | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 9515f449-6d4d-46bf-bddb-683472d1457c | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | c5c807e9-da20-4bc4-b241-1fec316714b5 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | b53d9948-53cf-401c-9f90-88c2f1d1d3c4 | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 3.581 | 2.968 | 9.249 | 12.284 | 25 |
| ltm_get | 6.63 | 6.572 | 7.846 | 8.696 | 60 |
| ltm_search | 6.781 | 6.749 | 7.922 | 8.031 | 60 |
| kb_add | 45.045 | 44.42 | 53.18 | 54.022 | 25 |
| kb_search | 21.764 | 21.557 | 26.164 | 29.385 | 60 |
| kb_index | 13.018 | 12.785 | 16.144 | 18.007 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=23 | entries_loaded_from_shard=23 | search_hits_after_restart=23 | elapsed_ms=500.192

- FAIL — all_ids_unique
- PASS — all_entries_persisted_in_shard
- PASS — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

