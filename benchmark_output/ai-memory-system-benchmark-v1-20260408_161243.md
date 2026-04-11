# AI Memory System Benchmark v1

- 生成时间：2026-04-08T16:12:56+08:00
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
| engine.verify | 18 | 18 | 0 | 1775.8 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 686.36 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2458.01 | PASS |
| run_full_test | 20 | 20 | 0 | 2455.37 | PASS |

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
| ltm-dark-mode-keyword | dark mode | 647e8d85-4311-4fce-af41-dbccbabf4259 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | cbcb141b-fa66-4cfb-a010-ecc38a61433b<br>e93fd817-699a-4438-b8fd-36a7b428ab1f | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | ade0d060-dbe6-49ea-84bc-38286baeb126 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | 9479de17-b9ca-497e-b009-2334c2927466 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | cbcb141b-fa66-4cfb-a010-ecc38a61433b<br>e93fd817-699a-4438-b8fd-36a7b428ab1f | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 02640837-3693-4344-a913-44ca6f2756cc | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | 781876fc-eabb-42ef-b72d-c5daf6ae1210 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 4f18d27a-266d-48d5-8091-a741ed024578 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | e87e52f2-4b40-4f3d-a8c4-85cd55f7025c | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | 6fbf33df-c9de-4808-86f1-aee8966c45fe | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 3.043 | 2.277 | 8.599 | 13.591 | 25 |
| ltm_get | 4.687 | 4.573 | 5.321 | 5.535 | 60 |
| ltm_search | 5.782 | 5.396 | 8.19 | 10.867 | 60 |
| kb_add | 38.804 | 38.04 | 47.31 | 48.707 | 25 |
| kb_search | 18.023 | 17.164 | 21.602 | 26.46 | 60 |
| kb_index | 11.936 | 11.757 | 14.822 | 16.938 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=6 | entries_loaded_from_shard=6 | search_hits_after_restart=6 | elapsed_ms=343.604

- FAIL — all_ids_unique
- PASS — all_entries_persisted_in_shard
- PASS — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

