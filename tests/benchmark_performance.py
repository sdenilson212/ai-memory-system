#!/usr/bin/env python3
"""
AI Memory System 性能基准测试
用于验证 v1.5.0 改进效果

测试场景:
1. 写入性能 (WAL 机制)
2. 并发写入 (锁竞争)
3. 检索性能 (索引优化)
4. 内存占用 (缓存管理)
"""

import os
import sys
import time
import json
import threading
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from engine.core.ltm import LTMManager
    from engine.core.kb import KBManager
    from engine.core.wal_manager import WALManager  # v1.5.0 新增
    from engine.core.weight_manager import WeightManager  # v1.5.0 新增
except ImportError as e:
    print(f"⚠️ 导入失败: {e}")
    print("请确保在项目根目录运行: cd output/ai-memory-system")
    sys.exit(1)

# 测试配置
TEST_DATA_DIR = Path("test_data") / "benchmark"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 测试数据
SAMPLE_CONTENTS = [
    "我喜欢用Python写后端代码，特别是FastAPI框架",
    "我不喜欢Java，觉得语法太啰嗦",
    "我的目标是成为一名全栈工程师",
    "记住要每周备份一次数据库",
    "我习惯早上6点起床跑步",
    "我的GitHub用户名是sdenilson",
    "我住在上海，喜欢这个城市的活力",
    "2026年我参加了上海半程马拉松，成绩1:51:23",
    "我使用Garmin手表记录跑步数据",
    "我的AI员工办公室项目有10名员工",
]

# 性能结果存储
PERFORMANCE_RESULTS = {
    "version": "1.4.0",  # 将在测试后更新
    "timestamp": datetime.now().isoformat(),
    "tests": {}
}


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, use_wal: bool = False):
        """初始化测试环境"""
        self.use_wal = use_wal
        
        # 清理旧测试数据
        self._cleanup_test_data()
        
        # 初始化管理器
        self.ltm = LTMManager(TEST_DATA_DIR / "memory-bank")
        self.kb = KBManager(TEST_DATA_DIR / "memory-bank")
        
        # v1.5.0 功能 (如果可用)
        self.wal = None
        self.weight = None
        if use_wal:
            try:
                self.wal = WALManager(TEST_DATA_DIR / "memory-bank" / "ltm_wal")
                self.weight = WeightManager(TEST_DATA_DIR / "memory-bank")
            except:
                print("⚠️ WAL 或 WeightManager 不可用，使用传统模式")
                self.use_wal = False
    
    def _cleanup_test_data(self):
        """清理测试数据"""
        import shutil
        
        if TEST_DATA_DIR.exists():
            shutil.rmtree(TEST_DATA_DIR)
        
        TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
        (TEST_DATA_DIR / "memory-bank").mkdir(exist_ok=True)
    
    def benchmark_write_performance(self, num_entries: int = 1000) -> Dict[str, Any]:
        """测试写入性能"""
        print(f"\n📝 测试写入性能 ({num_entries} 条记录)...")
        
        start_time = time.time()
        
        for i in range(num_entries):
            content = SAMPLE_CONTENTS[i % len(SAMPLE_CONTENTS)] + f" - {i}"
            category = "test"
            
            try:
                if self.use_wal and self.wal:
                    # WAL 快速写入
                    entry_data = {
                        "id": f"test-{i:06d}",
                        "content": content,
                        "category": category,
                        "op": "add",
                        "ts": datetime.now().isoformat(),
                        "weight": 2,
                        "tags": ["benchmark", "test"],
                    }
                    self.wal.append(category, entry_data)
                else:
                    # 传统全量写入
                    self.ltm.save(content, category)
                
                if i % 100 == 0 and i > 0:
                    print(f"  ... 已写入 {i} 条")
                    
            except Exception as e:
                print(f"⚠️ 写入失败 (i={i}): {e}")
                break
        
        elapsed = time.time() - start_time
        
        # 计算性能指标
        entries_per_second = num_entries / elapsed if elapsed > 0 else 0
        avg_latency_ms = (elapsed * 1000) / num_entries if num_entries > 0 else 0
        
        result = {
            "total_entries": num_entries,
            "total_time_seconds": round(elapsed, 3),
            "entries_per_second": round(entries_per_second, 1),
            "avg_latency_ms": round(avg_latency_ms, 1),
            "use_wal": self.use_wal,
        }
        
        print(f"✅ 写入完成: {result['total_time_seconds']}秒 "
              f"({result['entries_per_second']}条/秒)")
        
        return result
    
    def benchmark_concurrent_write(self, num_threads: int = 32, 
                                   entries_per_thread: int = 50) -> Dict[str, Any]:
        """测试并发写入性能"""
        print(f"\n⚡ 测试并发写入 ({num_threads} 线程，每线程 {entries_per_thread} 条)...")
        
        results = []
        lock_failures = 0
        write_errors = 0
        
        def worker(thread_id: int):
            nonlocal lock_failures, write_errors
            thread_results = []
            
            for i in range(entries_per_thread):
                content = f"线程{thread_id}-记录{i}"
                category = "concurrent_test"
                
                try:
                    if self.use_wal and self.wal:
                        entry_data = {
                            "id": f"thread-{thread_id:03d}-{i:03d}",
                            "content": content,
                            "category": category,
                            "op": "add",
                            "ts": datetime.now().isoformat(),
                        }
                        self.wal.append(category, entry_data)
                    else:
                        self.ltm.save(content, category)
                    
                    thread_results.append((thread_id, i, "success"))
                    
                except TimeoutError:
                    lock_failures += 1
                    thread_results.append((thread_id, i, "timeout"))
                except Exception as e:
                    write_errors += 1
                    thread_results.append((thread_id, i, f"error: {str(e)}"))
            
            return thread_results
        
        # 启动线程
        start_time = time.time()
        threads = []
        all_results = []
        
        for t in range(num_threads):
            thread = threading.Thread(target=lambda tid=t: all_results.extend(worker(tid)))
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        elapsed = time.time() - start_time
        
        # 统计结果
        total_entries = num_threads * entries_per_thread
        success_count = len([r for r in all_results if r[2] == "success"])
        
        result = {
            "num_threads": num_threads,
            "entries_per_thread": entries_per_thread,
            "total_entries": total_entries,
            "successful_entries": success_count,
            "lock_failures": lock_failures,
            "write_errors": write_errors,
            "total_time_seconds": round(elapsed, 3),
            "throughput_entries_per_second": round(success_count / elapsed, 1) if elapsed > 0 else 0,
            "use_wal": self.use_wal,
        }
        
        print(f"✅ 并发写入完成: {result['successful_entries']}/{result['total_entries']} "
              f"成功 ({result['lock_failures']}锁失败, {result['write_errors']}错误)")
        
        return result
    
    def benchmark_search_performance(self, num_searches: int = 100) -> Dict[str, Any]:
        """测试检索性能"""
        print(f"\n🔍 测试检索性能 ({num_searches} 次搜索)...")
        
        # 首先确保有数据
        if len(self.ltm._load_entries()) < 100:
            print("  创建测试数据...")
            for i in range(100):
                self.ltm.save(f"搜索测试数据 {i}", "search_test")
        
        search_queries = [
            "Python", "喜欢", "目标", "记住", "习惯",
            "GitHub", "上海", "跑步", "Garmin", "AI"
        ]
        
        latencies = []
        results_counts = []
        
        for i in range(num_searches):
            query = search_queries[i % len(search_queries)]
            
            start = time.perf_counter()
            
            try:
                # 测试权重排序
                if self.use_wal and self.weight:
                    results = self.ltm.search(query, use_weight=True, max_results=20)
                else:
                    results = self.ltm.search(query, max_results=20)
                
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies.append(elapsed_ms)
                results_counts.append(len(results))
                
            except Exception as e:
                print(f"⚠️ 搜索失败 (查询='{query}'): {e}")
                latencies.append(-1)  # 标记失败
        
        # 过滤掉失败的结果
        valid_latencies = [l for l in latencies if l >= 0]
        
        result = {
            "num_searches": num_searches,
            "avg_latency_ms": round(statistics.mean(valid_latencies), 1) if valid_latencies else -1,
            "p95_latency_ms": round(statistics.quantiles(valid_latencies, n=20)[18], 1) if len(valid_latencies) >= 20 else -1,
            "p99_latency_ms": round(statistics.quantiles(valid_latencies, n=100)[98], 1) if len(valid_latencies) >= 100 else -1,
            "min_latency_ms": round(min(valid_latencies), 1) if valid_latencies else -1,
            "max_latency_ms": round(max(valid_latencies), 1) if valid_latencies else -1,
            "avg_results_per_search": round(statistics.mean(results_counts), 1) if results_counts else 0,
            "use_weight": self.use_wal and self.weight is not None,
        }
        
        print(f"✅ 检索性能: 平均 {result['avg_latency_ms']}ms, "
              f"P95 {result['p95_latency_ms']}ms")
        
        return result
    
    def benchmark_memory_usage(self, operation: str = "write_1000") -> Dict[str, Any]:
        """测试内存占用"""
        print(f"\n🧠 测试内存占用 ({operation})...")
        
        import psutil
        import gc
        
        # 强制垃圾回收
        gc.collect()
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        if operation == "write_1000":
            # 写入 1000 条记录
            for i in range(1000):
                self.ltm.save(f"内存测试 {i}", "memory_test")
        
        elif operation == "search_100":
            # 执行 100 次搜索
            for i in range(100):
                self.ltm.search("测试", max_results=10)
        
        # 再次垃圾回收
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        result = {
            "operation": operation,
            "initial_memory_mb": round(initial_memory, 1),
            "final_memory_mb": round(final_memory, 1),
            "memory_increase_mb": round(memory_increase, 1),
            "peak_memory_mb": round(process.memory_info().vms / 1024 / 1024, 1),
        }
        
        print(f"✅ 内存占用: 初始 {result['initial_memory_mb']}MB, "
              f"最终 {result['final_memory_mb']}MB (+{result['memory_increase_mb']}MB)")
        
        return result
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        print("=" * 60)
        print("🚀 AI Memory System 性能基准测试")
        print("=" * 60)
        
        all_results = {}
        
        # 1. 写入性能
        write_result = self.benchmark_write_performance(1000)
        all_results["write_performance"] = write_result
        
        # 2. 并发写入
        concurrent_result = self.benchmark_concurrent_write(32, 50)
        all_results["concurrent_write"] = concurrent_result
        
        # 3. 检索性能
        search_result = self.benchmark_search_performance(100)
        all_results["search_performance"] = search_result
        
        # 4. 内存占用
        memory_result = self.benchmark_memory_usage("write_1000")
        all_results["memory_usage"] = memory_result
        
        # 5. 加权检索效果 (如果可用)
        if self.use_wal and self.weight:
            print("\n⚖️ 测试权重排序效果...")
            
            # 创建不同权重的测试数据
            test_entries = [
                ("重要记忆 (权重5)", "weight_test", 5),
                ("中等记忆 (权重3)", "weight_test", 3),
                ("普通记忆 (权重2)", "weight_test", 2),
                ("低权重记忆 (权重1)", "weight_test", 1),
            ]
            
            for content, category, weight in test_entries:
                self.ltm.save(content, category, weight=weight)
            
            # 搜索并检查排序
            results = self.ltm.search("记忆", category="weight_test", use_weight=True)
            
            weight_result = {
                "test_entries": len(test_entries),
                "retrieved_entries": len(results),
                "correct_order": all(r.weight >= results[i+1].weight 
                                     for i, r in enumerate(results[:-1])) if len(results) > 1 else True,
                "retrieved_weights": [r.weight for r in results],
            }
            all_results["weight_sorting"] = weight_result
            
            print(f"✅ 权重排序: {weight_result['correct_order']}")
        
        return all_results
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """保存测试结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode = "wal" if self.use_wal else "legacy"
            filename = f"benchmark_results_{mode}_{timestamp}.json"
        
        results_path = TEST_DATA_DIR.parent / "benchmark_results" / filename
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加元数据
        full_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.4.0" if not self.use_wal else "1.5.0-beta",
                "use_wal": self.use_wal,
                "use_weight": self.weight is not None,
                "python_version": sys.version,
                "platform": sys.platform,
            },
            "results": results,
        }
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(full_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 结果已保存到: {results_path}")
        return results_path


def compare_results(baseline_path: str, new_path: str) -> Dict[str, Any]:
    """比较两个测试结果"""
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    
    with open(new_path, 'r', encoding='utf-8') as f:
        new = json.load(f)
    
    comparison = {
        "baseline": baseline["metadata"]["version"],
        "new": new["metadata"]["version"],
        "improvements": {},
        "regressions": {},
        "summary": "",
    }
    
    # 比较关键指标
    metrics = [
        ("write_performance", "total_time_seconds", "写入时间", "越低越好", lambda x: -x),
        ("write_performance", "entries_per_second", "写入吞吐量", "越高越好", lambda x: x),
        ("search_performance", "avg_latency_ms", "搜索延迟", "越低越好", lambda x: -x),
        ("concurrent_write", "throughput_entries_per_second", "并发吞吐量", "越高越好", lambda x: x),
        ("memory_usage", "memory_increase_mb", "内存增量", "越低越好", lambda x: -x),
    ]
    
    for test_key, metric_key, name, better_direction, transform in metrics:
        if (test_key in baseline["results"] and test_key in new["results"] and
            metric_key in baseline["results"][test_key] and metric_key in new["results"][test_key]):
            
            baseline_val = baseline["results"][test_key][metric_key]
            new_val = new["results"][test_key][metric_key]
            
            if baseline_val > 0 and new_val > 0:
                improvement = (new_val - baseline_val) / baseline_val * 100
                improvement_transformed = transform(new_val) - transform(baseline_val)
                
                if improvement_transformed > 0:
                    comparison["improvements"][name] = {
                        "baseline": baseline_val,
                        "new": new_val,
                        "improvement_percent": round(improvement, 1),
                        "direction": better_direction,
                    }
                else:
                    comparison["regressions"][name] = {
                        "baseline": baseline_val,
                        "new": new_val,
                        "regression_percent": round(-improvement, 1),
                        "direction": better_direction,
                    }
    
    # 生成摘要
    if comparison["improvements"]:
        best_improvement = max(
            comparison["improvements"].items(),
            key=lambda x: abs(x[1]["improvement_percent"])
        )
        comparison["summary"] += f"最佳改进: {best_improvement[0]} {best_improvement[1]['improvement_percent']}%"
    
    if comparison["regressions"]:
        worst_regression = max(
            comparison["regressions"].items(),
            key=lambda x: abs(x[1]["regression_percent"])
        )
        comparison["summary"] += f" | 最差回归: {worst_regression[0]} {worst_regression[1]['regression_percent']}%"
    
    return comparison


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Memory System 性能基准测试")
    parser.add_argument("--mode", choices=["legacy", "wal", "compare"], 
                       default="legacy", help="测试模式")
    parser.add_argument("--baseline", help="基准结果文件路径 (用于比较)")
    parser.add_argument("--new", help="新结果文件路径 (用于比较)")
    parser.add_argument("--output", help="输出结果文件路径")
    
    args = parser.parse_args()
    
    if args.mode == "compare":
        if not args.baseline or not args.new:
            print("❌ 比较模式需要 --baseline 和 --new 参数")
            return
        
        comparison = compare_results(args.baseline, args.new)
        
        print("\n" + "=" * 60)
        print("📊 性能比较结果")
        print("=" * 60)
        
        print(f"基准版本: {comparison['baseline']}")
        print(f"新版本: {comparison['new']}")
        
        if comparison["improvements"]:
            print("\n✅ 改进项:")
            for name, data in comparison["improvements"].items():
                print(f"  {name}: {data['baseline']} → {data['new']} "
                      f"(改进 {data['improvement_percent']}%)")
        
        if comparison["regressions"]:
            print("\n⚠️ 回归项:")
            for name, data in comparison["regressions"].items():
                print(f"  {name}: {data['baseline']} → {data['new']} "
                      f"(回归 {data['regression_percent']}%)")
        
        print(f"\n📋 摘要: {comparison['summary']}")
        
        # 保存比较结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            print(f"💾 比较结果已保存到: {args.output}")
        
        return
    
    # 运行基准测试
    use_wal = (args.mode == "wal")
    
    print(f"🚀 启动 {args.mode.upper()} 模式性能测试...")
    
    benchmark = PerformanceBenchmark(use_wal=use_wal)
    results = benchmark.run_all_benchmarks()
    
    # 保存结果
    results_path = benchmark.save_results(results, args.output)
    
    print("\n" + "=" * 60)
    print("🎉 基准测试完成!")
    print("=" * 60)
    
    # 显示关键指标
    key_metrics = [
        ("写入性能", results.get("write_performance", {}).get("total_time_seconds"), "秒 (1000条)"),
        ("写入吞吐量", results.get("write_performance", {}).get("entries_per_second"), "条/秒"),
        ("搜索延迟", results.get("search_performance", {}).get("avg_latency_ms"), "毫秒"),
        ("并发成功率", 
         f"{results.get('concurrent_write', {}).get('successful_entries', 0)}/"
         f"{results.get('concurrent_write', {}).get('total_entries', 0)}", 
         "成功/总数"),
        ("内存增量", results.get("memory_usage", {}).get("memory_increase_mb"), "MB"),
    ]
    
    for name, value, unit in key_metrics:
        if value is not None:
            print(f"  {name}: {value} {unit}")
    
    print(f"\n📊 详细结果: {results_path}")
    
    if use_wal:
        print("\n💡 提示: 运行以下命令比较 WAL 与传统模式性能:")
        print(f"  python {__file__} --mode compare --baseline legacy_result.json --new wal_result.json")


if __name__ == "__main__":
    main()