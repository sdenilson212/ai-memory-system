# AI Memory System Benchmark v1

- 生成时间：2026-04-08T06:21:50+08:00
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
| engine.verify | 18 | 18 | 0 | 1771.35 | PASS |
| engine.verify_fix | 8 | 8 | 0 | 703.84 | PASS |
| engine.verify_mcp_tools | 22 | 22 | 0 | 2663.96 | PASS |
| run_full_test | 20 | 20 | 0 | 2435.66 | PASS |

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
| ltm-dark-mode-keyword | dark mode | 960a2103-faa5-4fe9-8e18-43e50dc5e089 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-python-backend | Python backend | c9be6839-093e-4fa2-927f-43e3a26992ce<br>780ab00e-deb0-4b7f-a804-8b97f3dbbbef | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-shanghai-half-marathon | 上海 半马 | 3c11e091-e080-44e2-bc3d-fd27b0d222ec | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-accent-folding-cafe | cafe brainstorming | d5aff047-dcf6-4f0f-be4d-8c57c852a058 | 1 | 0.3333 | 1.0 | 1.0 |
| ltm-fullwidth-python | Ｐｙｔｈｏｎ | c9be6839-093e-4fa2-927f-43e3a26992ce<br>780ab00e-deb0-4b7f-a804-8b97f3dbbbef | 1 | 0.6667 | 1.0 | 1.0 |

### KB aggregate

- cases=5 | hit_rate=1.0 | avg_precision@k=0.3333 | avg_recall@k=1.0 | MRR=1.0

| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |
|---|---|---|---:|---:|---:|---:|
| kb-fastapi-di | fastapi dependency injection | 8a5e3269-0da7-454e-ae69-24dd3ee57b75 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-rag-hybrid-retrieval | BM25 向量 检索 | f11ff245-4268-4145-aa86-65053843682e | 1 | 0.3333 | 1.0 | 1.0 |
| kb-wechat-map | 微信 地图 定位 | 2cafdc42-7f43-479a-bfc2-c078002b6044 | 1 | 0.3333 | 1.0 | 1.0 |
| kb-resume-accent-query | résumé impact | 977ed076-2f57-45a5-a35b-68bbac856dcf | 1 | 0.3333 | 1.0 | 1.0 |
| kb-unicode-cafe | café fullwidth normalize | 384fda9d-bf41-4a26-9b27-7a529e27463b | 1 | 0.3333 | 1.0 | 1.0 |

## Layer 3 — Performance & Integrity

- performance 目前仅记录本机观测值，不作为 release gate。
- integrity 关注 filelock 场景下的并发写入与重启后可读性。

### Performance

| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |
|---|---:|---:|---:|---:|---:|
| ltm_save | 15.559 | 15.74 | 17.751 | 19.056 | 25 |
| ltm_get | 16.255 | 16.048 | 20.745 | 31.773 | 60 |
| ltm_search | 22.118 | 21.426 | 26.54 | 32.068 | 60 |
| kb_add | 40.116 | 39.621 | 45.362 | 49.663 | 25 |
| kb_search | 19.992 | 19.8 | 24.4 | 32.407 | 60 |
| kb_index | 10.945 | 10.566 | 13.395 | 18.748 | 30 |

### Integrity

- concurrent_write_count=32 | unique_ids_written=32 | entries_loaded_from_shard=10 | search_hits_after_restart=10 | elapsed_ms=569.256

- PASS — all_ids_unique
- FAIL — all_entries_persisted_in_shard
- FAIL — entries_searchable_after_restart

## 下一步建议

- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。
- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。
- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。
- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。

