from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ENGINE_DIR = ROOT / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from core.kb import KBManager
from core.ltm import LTMManager


@dataclass
class CorrectnessTarget:
    name: str
    script_path: Path
    cwd: Path
    token: str
    expected_passes: int
    description: str


def now_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def short(text: str, limit: int = 800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_subprocess(script_path: Path, cwd: Path, timeout: int = 180) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    combined = (completed.stdout or "")
    if completed.stderr:
        combined += "\n[stderr]\n" + completed.stderr
    return {
        "returncode": completed.returncode,
        "elapsed_ms": round(elapsed_ms, 2),
        "output": combined,
    }


def run_correctness_layer() -> dict[str, Any]:
    scope = {
        "target_system": "AI Memory System (pure scope)",
        "included": [
            "engine/verify.py",
            "engine/verify_fix.py",
            "engine/verify_mcp_tools.py",
            "run_full_test.py",
        ],
        "excluded": [
            "tests/test_adaptive_skill_system.py",
            "any adaptive-skill-system related tests",
        ],
    }

    targets = [
        CorrectnessTarget(
            name="engine.verify",
            script_path=ENGINE_DIR / "verify.py",
            cwd=ENGINE_DIR,
            token="[OK]",
            expected_passes=18,
            description="核心引擎 smoke：LTM / KB / STM / 安全模块",
        ),
        CorrectnessTarget(
            name="engine.verify_fix",
            script_path=ENGINE_DIR / "verify_fix.py",
            cwd=ENGINE_DIR,
            token="[PASS]",
            expected_passes=8,
            description="历史修复点复核：分片 / filelock / passphrase / trigger / vector_store 声明",
        ),
        CorrectnessTarget(
            name="engine.verify_mcp_tools",
            script_path=ENGINE_DIR / "verify_mcp_tools.py",
            cwd=ENGINE_DIR,
            token="[PASS]",
            expected_passes=22,
            description="MCP 21+ 工具链端到端验证",
        ),
        CorrectnessTarget(
            name="run_full_test",
            script_path=ROOT / "run_full_test.py",
            cwd=ROOT,
            token="[PASS]",
            expected_passes=20,
            description="REST API 全链路验证（启动服务 -> 调接口 -> 清理）",
        ),
    ]

    checks: list[dict[str, Any]] = []
    total_expected = 0
    total_observed = 0
    all_passed = True

    for target in targets:
        result = run_subprocess(target.script_path, target.cwd)
        observed_passes = result["output"].count(target.token)
        passed = result["returncode"] == 0 and observed_passes == target.expected_passes
        total_expected += target.expected_passes
        total_observed += observed_passes
        if not passed:
            all_passed = False
        checks.append(
            {
                "name": target.name,
                "description": target.description,
                "script": str(target.script_path),
                "cwd": str(target.cwd),
                "token": target.token,
                "expected_passes": target.expected_passes,
                "observed_passes": observed_passes,
                "returncode": result["returncode"],
                "elapsed_ms": result["elapsed_ms"],
                "passed": passed,
                "output_excerpt": short(result["output"]),
            }
        )

    return {
        "scope": scope,
        "score": {
            "observed": total_observed,
            "expected": total_expected,
        },
        "checks": checks,
        "passed": all_passed,
    }


def seed_retrieval_data(memory_dir: Path) -> dict[str, Any]:
    ltm = LTMManager(memory_dir)
    kb = KBManager(memory_dir)

    ltm_entries = {
        "dark_mode": ltm.save(
            content="User prefers dark mode UI for dashboards and tools.",
            category="preference",
            source="benchmark",
            tags=["ui", "theme", "dark-mode"],
        ),
        "python_backend": ltm.save(
            content="I prefer Python over Java for backend APIs and automation.",
            category="preference",
            source="benchmark",
            tags=["python", "backend", "coding"],
        ),
        "shanghai_half": ltm.save(
            content="2026年3月参加了上海黄浦区半马，成绩 1:51:23，平均配速 5:12/km。",
            category="project",
            source="benchmark",
            tags=["running", "half-marathon", "上海", "黄浦"],
        ),
        "cafe_note": ltm.save(
            content="I like café meetings for product brainstorming and roadmap reviews.",
            category="habit",
            source="benchmark",
            tags=["cafe", "brainstorming"],
        ),
        "fullwidth_python": ltm.save(
            content="全角字符测试：Ｐｙｔｈｏｎ 工程记录与检索兼容性。",
            category="other",
            source="benchmark",
            tags=["python", "fullwidth", "unicode"],
        ),
    }

    kb_entries = {
        "fastapi": kb.add(
            title="FastAPI Best Practices",
            content="Use dependency injection for database sessions and structured routers.",
            category="technical",
            tags=["python", "fastapi", "backend"],
        ),
        "rag": kb.add(
            title="RAG 检索实践",
            content="混合检索应结合 BM25、向量召回与重排，避免只靠单一召回通道。",
            category="technical",
            tags=["rag", "bm25", "vector", "retrieval"],
        ),
        "wechat_map": kb.add(
            title="微信小程序地图方案",
            content="使用腾讯地图小程序 SDK 处理定位、逆地理编码与路线展示。",
            category="technical",
            tags=["微信小程序", "腾讯地图", "location"],
        ),
        "resume": kb.add(
            title="Resume Writing Guide",
            content="A concise resume should highlight impact, ownership, and measurable results.",
            category="domain",
            tags=["resume", "writing", "career"],
        ),
        "unicode": kb.add(
            title="Unicode Normalization Note",
            content="Normalize fullwidth characters before search and treat cafe and café consistently.",
            category="technical",
            tags=["unicode", "normalization", "café"],
        ),
    }

    cases = [
        {
            "group": "ltm",
            "name": "ltm-dark-mode-keyword",
            "query": "dark mode",
            "expected_ids": [ltm_entries["dark_mode"].id],
            "k": 3,
        },
        {
            "group": "ltm",
            "name": "ltm-python-backend",
            "query": "Python backend",
            "expected_ids": [ltm_entries["python_backend"].id],
            "k": 3,
        },
        {
            "group": "ltm",
            "name": "ltm-shanghai-half-marathon",
            "query": "上海 半马",
            "expected_ids": [ltm_entries["shanghai_half"].id],
            "k": 3,
        },
        {
            "group": "ltm",
            "name": "ltm-accent-folding-cafe",
            "query": "cafe brainstorming",
            "expected_ids": [ltm_entries["cafe_note"].id],
            "k": 3,
        },
        {
            "group": "ltm",
            "name": "ltm-fullwidth-python",
            "query": "Ｐｙｔｈｏｎ",
            "expected_ids": [ltm_entries["python_backend"].id, ltm_entries["fullwidth_python"].id],
            "k": 3,
        },
        {
            "group": "kb",
            "name": "kb-fastapi-di",
            "query": "fastapi dependency injection",
            "expected_ids": [kb_entries["fastapi"].id],
            "k": 3,
        },
        {
            "group": "kb",
            "name": "kb-rag-hybrid-retrieval",
            "query": "BM25 向量 检索",
            "expected_ids": [kb_entries["rag"].id],
            "k": 3,
        },
        {
            "group": "kb",
            "name": "kb-wechat-map",
            "query": "微信 地图 定位",
            "expected_ids": [kb_entries["wechat_map"].id],
            "k": 3,
        },
        {
            "group": "kb",
            "name": "kb-resume-accent-query",
            "query": "résumé impact",
            "expected_ids": [kb_entries["resume"].id],
            "k": 3,
        },
        {
            "group": "kb",
            "name": "kb-unicode-cafe",
            "query": "café fullwidth normalize",
            "expected_ids": [kb_entries["unicode"].id],
            "k": 3,
        },
    ]

    return {
        "ltm": ltm,
        "kb": kb,
        "cases": cases,
    }


def evaluate_retrieval_case(group: str, manager: Any, query: str, expected_ids: list[str], k: int) -> dict[str, Any]:
    if group == "ltm":
        results = manager.search(query, max_results=k)
        found_ids = [item.id for item in results[:k]]
    elif group == "kb":
        results = manager.search(query, top_k=k, confirmed_only=True)
        found_ids = [item.id for item in results[:k]]
    else:
        raise ValueError(f"Unknown retrieval group: {group}")

    expected_set = set(expected_ids)
    retrieved_relevant = sum(1 for item_id in found_ids if item_id in expected_set)
    hit = 1 if retrieved_relevant > 0 else 0
    precision_at_k = retrieved_relevant / k if k else 0.0
    recall_at_k = retrieved_relevant / len(expected_set) if expected_set else 0.0

    first_relevant_rank = None
    reciprocal_rank = 0.0
    for index, item_id in enumerate(found_ids, start=1):
        if item_id in expected_set:
            first_relevant_rank = index
            reciprocal_rank = 1.0 / index
            break

    return {
        "query": query,
        "expected_ids": expected_ids,
        "found_ids": found_ids,
        "hit_at_k": hit,
        "precision_at_k": round(precision_at_k, 4),
        "recall_at_k": round(recall_at_k, 4),
        "mrr": round(reciprocal_rank, 4),
        "first_relevant_rank": first_relevant_rank,
    }


def run_retrieval_layer() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        seeded = seed_retrieval_data(Path(tmpdir))
        ltm = seeded["ltm"]
        kb = seeded["kb"]
        cases = seeded["cases"]

        per_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for case in cases:
            manager = ltm if case["group"] == "ltm" else kb
            metrics = evaluate_retrieval_case(
                group=case["group"],
                manager=manager,
                query=case["query"],
                expected_ids=case["expected_ids"],
                k=case["k"],
            )
            per_group[case["group"]].append({
                "name": case["name"],
                "k": case["k"],
                **metrics,
            })

    aggregates: dict[str, Any] = {}
    overall_hits: list[float] = []
    overall_precision: list[float] = []
    overall_recall: list[float] = []
    overall_mrr: list[float] = []

    for group, rows in per_group.items():
        hits = [row["hit_at_k"] for row in rows]
        precisions = [row["precision_at_k"] for row in rows]
        recalls = [row["recall_at_k"] for row in rows]
        mrrs = [row["mrr"] for row in rows]
        overall_hits.extend(hits)
        overall_precision.extend(precisions)
        overall_recall.extend(recalls)
        overall_mrr.extend(mrrs)
        aggregates[group] = {
            "case_count": len(rows),
            "hit_rate": round(sum(hits) / len(hits), 4) if hits else 0.0,
            "avg_precision_at_k": round(sum(precisions) / len(precisions), 4) if precisions else 0.0,
            "avg_recall_at_k": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
            "mrr": round(sum(mrrs) / len(mrrs), 4) if mrrs else 0.0,
        }

    overall = {
        "case_count": len(overall_hits),
        "hit_rate": round(sum(overall_hits) / len(overall_hits), 4) if overall_hits else 0.0,
        "avg_precision_at_k": round(sum(overall_precision) / len(overall_precision), 4) if overall_precision else 0.0,
        "avg_recall_at_k": round(sum(overall_recall) / len(overall_recall), 4) if overall_recall else 0.0,
        "mrr": round(sum(overall_mrr) / len(overall_mrr), 4) if overall_mrr else 0.0,
    }

    return {
        "dataset": "seeded-synthetic-v1",
        "notes": [
            "这是首版种子集 benchmark，不代表真实线上分布。",
            "目标是把 correctness 之外的 retrieval 能力显式量化。",
            "案例刻意覆盖英文、中文、全角字符、accent folding。",
        ],
        "aggregates": aggregates,
        "overall": overall,
        "cases": dict(per_group),
    }


def time_operation(fn, iterations: int) -> list[float]:
    durations: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        durations.append((time.perf_counter() - started) * 1000)
    return durations


def summarize_latency(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "mean_ms": round(sum(values) / len(values), 3) if values else 0.0,
        "p50_ms": round(percentile(values, 0.50), 3) if values else 0.0,
        "p95_ms": round(percentile(values, 0.95), 3) if values else 0.0,
        "max_ms": round(max(values), 3) if values else 0.0,
    }


def run_performance_integrity_layer() -> dict[str, Any]:
    performance: dict[str, Any] = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        ltm = LTMManager(memory_dir)
        kb = KBManager(memory_dir)

        save_counter = {"value": 0}
        def ltm_save_once() -> None:
            idx = save_counter["value"]
            save_counter["value"] += 1
            ltm.save(
                content=f"benchmark save {idx} python fastapi retrieval",
                category="preference",
                source="benchmark",
                tags=["python", "benchmark"],
            )

        search_anchor = ltm.save(
            content="Performance anchor for python search benchmark.",
            category="preference",
            source="benchmark",
            tags=["python", "performance"],
        )
        for idx in range(80):
            ltm.save(
                content=f"seed {idx} python benchmark retrieval latency",
                category="other",
                source="benchmark",
                tags=["python", "seed"],
            )

        kb_counter = {"value": 0}
        def kb_add_once() -> None:
            idx = kb_counter["value"]
            kb_counter["value"] += 1
            kb.add(
                title=f"Benchmark Doc {idx}",
                content=f"FastAPI retrieval benchmark document {idx} with dependency injection guidance.",
                category="technical",
                tags=["fastapi", "benchmark"],
            )

        kb_anchor = kb.add(
            title="FastAPI Anchor",
            content="FastAPI anchor entry for repeated search benchmark.",
            category="technical",
            tags=["fastapi", "anchor"],
        )
        for idx in range(80):
            kb.add(
                title=f"Seed KB {idx}",
                content=f"RAG retrieval seed {idx} uses BM25 and reranking.",
                category="technical",
                tags=["rag", "seed"],
            )

        performance["ltm_save"] = summarize_latency(time_operation(ltm_save_once, iterations=25))
        performance["ltm_get"] = summarize_latency(time_operation(lambda: ltm.get(search_anchor.id), iterations=60))
        performance["ltm_search"] = summarize_latency(time_operation(lambda: ltm.search("python benchmark", max_results=5), iterations=60))
        performance["kb_add"] = summarize_latency(time_operation(kb_add_once, iterations=25))
        performance["kb_search"] = summarize_latency(time_operation(lambda: kb.search("fastapi benchmark", top_k=5), iterations=60))
        performance["kb_index"] = summarize_latency(time_operation(lambda: kb.get_index(), iterations=30))

    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        total_writes = 32

        def concurrent_writer(index: int) -> str:
            writer = LTMManager(memory_dir)
            # 使用时间戳确保每个写入内容唯一，避免去重检查误判
            entry = writer.save(
                content=f"parallel integrity write {index} at timestamp {time.time()}",
                category="preference",
                source="benchmark",
                tags=["parallel", "integrity", "benchmark", f"idx_{index}"],
            )
            return entry.id

        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            entry_ids = list(pool.map(concurrent_writer, range(total_writes)))
        elapsed_ms = (time.perf_counter() - started) * 1000

        verifier = LTMManager(memory_dir)
        shard_entries = verifier._load_shard("preference")
        shard_ids = {entry.id for entry in shard_entries}
        parallel_hits = verifier.search("parallel integrity", max_results=100)
        parallel_hit_ids = {entry.id for entry in parallel_hits}

        integrity = {
            "concurrent_write_count": total_writes,
            "elapsed_ms": round(elapsed_ms, 3),
            "unique_ids_written": len(set(entry_ids)),
            "entries_loaded_from_shard": len(shard_entries),
            "search_hits_after_restart": len(parallel_hits),
            "checks": [
                {
                    "name": "all_ids_unique",
                    "passed": len(set(entry_ids)) == total_writes,
                },
                {
                    "name": "all_entries_persisted_in_shard",
                    "passed": set(entry_ids).issubset(shard_ids),
                },
                {
                    "name": "entries_searchable_after_restart",
                    "passed": set(entry_ids).issubset(parallel_hit_ids),
                },
            ],
        }

    integrity["passed"] = all(check["passed"] for check in integrity["checks"])
    return {
        "performance": performance,
        "integrity": integrity,
        "notes": [
            "performance 目前仅记录本机观测值，不作为 release gate。",
            "integrity 关注 filelock 场景下的并发写入与重启后可读性。",
        ],
    }


def build_summary(correctness: dict[str, Any], retrieval: dict[str, Any], perf_integrity: dict[str, Any]) -> dict[str, Any]:
    overall_status = "passed" if correctness["passed"] and perf_integrity["integrity"]["passed"] else "needs_attention"
    return {
        "benchmark": "AI Memory System Benchmark v1",
        "generated_at": iso_now(),
        "overall_status": overall_status,
        "key_findings": [
            f"Correctness scope locked to pure AI Memory System: {correctness['score']['observed']}/{correctness['score']['expected']}",
            f"Retrieval seeded benchmark hit@k={retrieval['overall']['hit_rate']}, MRR={retrieval['overall']['mrr']}",
            f"Integrity concurrent write checks: {'PASS' if perf_integrity['integrity']['passed'] else 'FAIL'}",
            "Known limitation remains: vector search is still TF-IDF placeholder, not embedding-grade semantic retrieval.",
        ],
        "layers": {
            "correctness": correctness,
            "retrieval_quality": retrieval,
            "performance_integrity": perf_integrity,
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    correctness = summary["layers"]["correctness"]
    retrieval = summary["layers"]["retrieval_quality"]
    perf_integrity = summary["layers"]["performance_integrity"]

    lines: list[str] = []
    lines.append("# AI Memory System Benchmark v1")
    lines.append("")
    lines.append(f"- 生成时间：{summary['generated_at']}")
    lines.append(f"- 总体状态：{summary['overall_status']}")
    lines.append("")
    lines.append("## Scope 声明")
    lines.append("")
    lines.append(f"- 目标系统：{correctness['scope']['target_system']}")
    lines.append("- 纳入脚本：")
    for item in correctness["scope"]["included"]:
        lines.append(f"  - `{item}`")
    lines.append("- 排除脚本：")
    for item in correctness["scope"]["excluded"]:
        lines.append(f"  - `{item}`")
    lines.append("")
    lines.append("## 结论摘要")
    lines.append("")
    for item in summary["key_findings"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Layer 1 — Correctness")
    lines.append("")
    lines.append(f"- 纯系统 correctness 基线：**{correctness['score']['observed']}/{correctness['score']['expected']}**")
    lines.append("")
    lines.append("| Check | Expected | Observed | Return Code | Elapsed ms | Status |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for check in correctness["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(
            f"| {check['name']} | {check['expected_passes']} | {check['observed_passes']} | {check['returncode']} | {check['elapsed_ms']} | {status} |"
        )
    lines.append("")
    lines.append("## Layer 2 — Retrieval Quality")
    lines.append("")
    lines.append(f"- 数据集：`{retrieval['dataset']}`")
    for note in retrieval["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    overall = retrieval["overall"]
    lines.append("### Overall")
    lines.append("")
    lines.append(
        f"- cases={overall['case_count']} | hit_rate={overall['hit_rate']} | avg_precision@k={overall['avg_precision_at_k']} | avg_recall@k={overall['avg_recall_at_k']} | MRR={overall['mrr']}"
    )
    lines.append("")
    for group in ("ltm", "kb"):
        aggregate = retrieval["aggregates"][group]
        lines.append(f"### {group.upper()} aggregate")
        lines.append("")
        lines.append(
            f"- cases={aggregate['case_count']} | hit_rate={aggregate['hit_rate']} | avg_precision@k={aggregate['avg_precision_at_k']} | avg_recall@k={aggregate['avg_recall_at_k']} | MRR={aggregate['mrr']}"
        )
        lines.append("")
        lines.append("| Case | Query | Found Top-K | Hit@K | Precision@K | Recall@K | MRR |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for row in retrieval["cases"][group]:
            found_ids = "<br>".join(row["found_ids"]) if row["found_ids"] else "-"
            query = row["query"].replace("|", "\\|")
            lines.append(
                f"| {row['name']} | {query} | {found_ids} | {row['hit_at_k']} | {row['precision_at_k']} | {row['recall_at_k']} | {row['mrr']} |"
            )
        lines.append("")
    lines.append("## Layer 3 — Performance & Integrity")
    lines.append("")
    for note in perf_integrity["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("### Performance")
    lines.append("")
    lines.append("| Operation | Mean ms | P50 ms | P95 ms | Max ms | Count |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for operation, metrics in perf_integrity["performance"].items():
        lines.append(
            f"| {operation} | {metrics['mean_ms']} | {metrics['p50_ms']} | {metrics['p95_ms']} | {metrics['max_ms']} | {metrics['count']} |"
        )
    lines.append("")
    integrity = perf_integrity["integrity"]
    lines.append("### Integrity")
    lines.append("")
    lines.append(
        f"- concurrent_write_count={integrity['concurrent_write_count']} | unique_ids_written={integrity['unique_ids_written']} | entries_loaded_from_shard={integrity['entries_loaded_from_shard']} | search_hits_after_restart={integrity['search_hits_after_restart']} | elapsed_ms={integrity['elapsed_ms']}"
    )
    lines.append("")
    for check in integrity["checks"]:
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'} — {check['name']}")
    lines.append("")
    lines.append("## 下一步建议")
    lines.append("")
    lines.append("- correctness 已和 pure-scope 绑定，可继续作为 release smoke gate。")
    lines.append("- retrieval 当前只是 seeded synthetic baseline，下一步应补真实用户语料和更难的 negative cases。")
    lines.append("- performance 已有本机观测值，但仍缺跨数据量规模曲线（10 / 100 / 1000 / 10000 条）。")
    lines.append("- vector_store 仍是 TF-IDF 占位实现；如果要对外声称 semantic retrieval，需要独立补 embedding-grade benchmark。")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI Memory System Benchmark v1")
    parser.add_argument(
        "--report-dir",
        default=str(ROOT / "benchmark_artifacts"),
        help="Directory to write JSON and Markdown outputs.",
    )
    args = parser.parse_args()

    report_dir = ensure_dir(Path(args.report_dir))
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    correctness = run_correctness_layer()
    retrieval = run_retrieval_layer()
    perf_integrity = run_performance_integrity_layer()
    summary = build_summary(correctness, retrieval, perf_integrity)

    json_path = report_dir / f"ai-memory-system-benchmark-v1-{timestamp}.json"
    md_path = report_dir / f"ai-memory-system-benchmark-v1-{timestamp}.md"

    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")

    print(f"Benchmark complete at {now_local()}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(f"Overall status: {summary['overall_status']}")
    print(f"Correctness: {correctness['score']['observed']}/{correctness['score']['expected']}")
    print(
        "Retrieval: hit_rate={hit_rate}, mrr={mrr}".format(
            hit_rate=retrieval["overall"]["hit_rate"],
            mrr=retrieval["overall"]["mrr"],
        )
    )
    print(f"Integrity: {'PASS' if perf_integrity['integrity']['passed'] else 'FAIL'}")
    return 0 if summary["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
