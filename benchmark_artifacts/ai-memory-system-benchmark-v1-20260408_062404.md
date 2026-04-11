# AI Memory System Benchmark v1

- 生成时间：2026-04-08T06:24:20+08:00
- 总体状态：passed

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
- Integrity concurrent write checks: PASS
- Known limitation remains: vector search is still TF-IDF placeholder, not embedding-grade semantic retrieval.

## Layer 1 — Correctness

- 纯系统 correctness 基线：**68/68**

| Check | Expected | Observed | Return Code | Elapsed ms | Status |
|---|---:|---:|---:|---:|---|
| engine.verify | 18 | 18 | 0 | 1719.0 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 689.74 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2402.49 | PASS |
| run_full_test | 20 | 20 | 0 | 2533.76 | PASS |

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
| ltm-dark-mode-keyword | dark mode | 2fbdbde9-ffc7-4c09-aa98-14c7679296fa | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | 4c8b20c9-8154-4846-a5c8-45b1e666be3d<br>6b5dcf02-3143-42e6-8726-08455682e87b | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | 2cdf4ed4-879f-42de-a46a-2bc10a842cca | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | d53a1329-5f1e-4cc6-a71a-15348078cb1b | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | 4c8b20c9-8154-4846-a5c8-45b1e666be3d<br>6b5dcf02-3143-42e6-8726-08455682e87b | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 94110431-a535-4ae3-9fe9-1cfb1d1be9dd | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | aff25eea-b86c-4f34-9aa4-a39927fd6f5e | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 08d543db-8216-439e-8bf6-7a443dd131ba | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | 4ee86d72-ff2d-4c76-997c-f2d8744f00c1 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | 9a93e4b7-439b-43d1-80b8-3a241ee5848b | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 14.047 | 13.997 | 16.442 | 17.554 | 25 |
| ltm_get | 16.357 | 15.517 | 19.529 | 33.344 | 60 |
| ltm_search | 22.107 | 21.624 | 25.416 | 30.101 | 60 |
| kb_add | 38.647 | 38.526 | 44.083 | 47.759 | 25 |
| kb_search | 18.179 | 17.434 | 21.885 | 25.308 | 60 |
| kb_index | 12.376 | 12.155 | 16.636 | 18.197 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=32 | entries_loaded_from_shard=32 | search_hits_after_restart=32 | elapsed_ms=674.856

- PASS — all_ids_unique
- PASS — all_entries_persisted_in_shard
- PASS — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

