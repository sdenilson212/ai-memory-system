# AI Memory System Benchmark v1

- 生成时间：2026-04-08T16:20:51+08:00
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
| engine.verify | 18 | 18 | 0 | 1806.28 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 772.38 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2508.72 | PASS |
| run_full_test | 20 | 20 | 0 | 2444.88 | PASS |

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
| ltm-dark-mode-keyword | dark mode | b720627c-ca80-43f7-858a-07156f963842 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | 82fdb63a-89fc-4aa4-a20e-074b7204fe6a<br>8264c65c-3e59-43d4-8039-ea17295d7911 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | 9d75dd82-8853-4169-87b0-8221ec6e6d7a | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | 19f36cdb-7bdf-4b3d-acd1-535113308da0 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | 82fdb63a-89fc-4aa4-a20e-074b7204fe6a<br>8264c65c-3e59-43d4-8039-ea17295d7911 | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 214fe54b-8bf5-4d12-b0ce-55a8d42a79b7 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | 759e003e-1d1c-4203-98a7-11ce536d3419 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 1944f2ec-c8cc-46fd-80ff-0b9e4860682a | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | 06a453f7-a811-4051-8d6b-aef864de7b35 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | afdc7cb6-3cda-42aa-8704-8ed641be7e42 | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 3.614 | 2.907 | 9.816 | 11.325 | 25 |
| ltm_get | 5.802 | 5.744 | 6.806 | 6.926 | 60 |
| ltm_search | 6.003 | 6.017 | 6.908 | 7.067 | 60 |
| kb_add | 40.458 | 39.489 | 45.697 | 46.533 | 25 |
| kb_search | 19.484 | 19.243 | 24.681 | 30.124 | 60 |
| kb_index | 12.981 | 12.179 | 17.496 | 22.834 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=23 | entries_loaded_from_shard=23 | search_hits_after_restart=23 | elapsed_ms=655.32

- FAIL — all_ids_unique
- PASS — all_entries_persisted_in_shard
- PASS — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

