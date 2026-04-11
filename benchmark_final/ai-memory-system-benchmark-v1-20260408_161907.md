# AI Memory System Benchmark v1

- 生成时间：2026-04-08T16:19:20+08:00
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
| engine.verify | 18 | 18 | 0 | 1863.62 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 741.17 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2560.91 | PASS |
| run_full_test | 20 | 20 | 0 | 2365.88 | PASS |

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
| ltm-dark-mode-keyword | dark mode | 52d6b818-00f0-4c61-9efa-66afed6fef4c | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | 978ebcee-3f37-4bfd-b832-5725aa828c5c<br>c8625f33-7a31-4142-ac87-98e0a73faefb | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | 95dc4ebc-a946-40e5-9084-6f24d22a3447 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | 426f0a01-889c-4e41-bd4c-e5c2114f44ad | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | 978ebcee-3f37-4bfd-b832-5725aa828c5c<br>c8625f33-7a31-4142-ac87-98e0a73faefb | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 91889cb7-16c7-41bd-b446-89b47d9451f5 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | 2b2c2096-8a67-46cf-b25c-209cb94b4aac | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 22aecd6f-ecd0-48b7-9132-4a88ebee4e8f | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | 4e844abd-1dfb-4863-8df7-01b05fa00055 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | 232a0a30-f9fe-40f1-bac3-85a80fb35870 | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 3.19 | 2.527 | 9.154 | 10.95 | 25 |
| ltm_get | 5.551 | 5.687 | 6.727 | 7.417 | 60 |
| ltm_search | 5.916 | 5.817 | 7.248 | 7.635 | 60 |
| kb_add | 41.837 | 41.186 | 48.788 | 54.496 | 25 |
| kb_search | 20.745 | 20.145 | 25.919 | 30.673 | 60 |
| kb_index | 11.931 | 11.619 | 15.186 | 16.778 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=1 | entries_loaded_from_shard=1 | search_hits_after_restart=1 | elapsed_ms=181.541

- FAIL — all_ids_unique
- PASS — all_entries_persisted_in_shard
- PASS — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

