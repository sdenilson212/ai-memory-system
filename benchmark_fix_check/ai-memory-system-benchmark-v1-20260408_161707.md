# AI Memory System Benchmark v1

- 生成时间：2026-04-08T16:17:21+08:00
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
| engine.verify | 18 | 18 | 0 | 1855.4 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 717.65 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2613.18 | PASS |
| run_full_test | 20 | 20 | 0 | 2440.81 | PASS |

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
| ltm-dark-mode-keyword | dark mode | 10d913b3-6ca8-4869-bfaf-a65a46525e75 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | f6c330ab-e3d7-409f-bacc-6097ba60ca8a<br>a17cd3c5-ca6f-4449-a29e-5c3e5b9e5fc2 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | 0941ae86-fac1-4040-bd23-80a20398c863 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | 9f75ed13-bb8c-4e08-98e2-3a9f5b69b92b | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | f6c330ab-e3d7-409f-bacc-6097ba60ca8a<br>a17cd3c5-ca6f-4449-a29e-5c3e5b9e5fc2 | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 28a8c971-4f75-4b26-94dd-0f6c3b4b8625 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | 96ad962c-2163-4eef-8d80-9e93ebe8e33a | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 2c881b5f-fa27-4133-8c8b-c87b30282099 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | 2c77cc05-012e-4623-a4d9-ac6caaa59828 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | 2c57e889-c33a-4ef7-b42f-3e6fc6061086 | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 3.358 | 2.708 | 9.084 | 13.62 | 25 |
| ltm_get | 5.049 | 5.044 | 5.891 | 6.545 | 60 |
| ltm_search | 6.727 | 6.683 | 8.491 | 8.889 | 60 |
| kb_add | 42.005 | 41.014 | 50.121 | 55.625 | 25 |
| kb_search | 21.033 | 20.546 | 26.587 | 30.729 | 60 |
| kb_index | 11.661 | 11.529 | 14.28 | 16.548 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=1 | entries_loaded_from_shard=1 | search_hits_after_restart=1 | elapsed_ms=180.68

- FAIL — all_ids_unique
- PASS — all_entries_persisted_in_shard
- PASS — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

