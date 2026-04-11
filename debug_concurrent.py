#!/usr/bin/env python3
"""调试并发写入问题：为什么 32 个线程只有 23 个成功"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import time
import traceback

import sys
sys.path.insert(0, str(Path(__file__).parent))

from engine.core.ltm import LTMManager


def test_concurrent_debug():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        total_writes = 32
        results = []
        errors = []

        def writer(index: int):
            try:
                ltm = LTMManager(memory_dir)
                entry = ltm.save(
                    content=f"parallel integrity write {index} at timestamp {time.time()}",
                    category="preference",
                    source="test",
                    tags=["parallel", "integrity", f"idx_{index}"],
                )
                results.append((index, "success", entry.id))
                return entry.id
            except Exception as e:
                errors.append((index, str(e), traceback.format_exc()))
                raise

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(writer, i) for i in range(total_writes)]
            
            successful = 0
            failed = 0
            for i, future in enumerate(futures):
                try:
                    future.result(timeout=10)
                    successful += 1
                except Exception as e:
                    failed += 1
                    print(f"Thread {i} failed: {e}")

        print(f"\n=== 并发写入调试结果 ===")
        print(f"Total threads: {total_writes}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        if errors:
            print(f"\n=== 错误详情（前 3 个）===")
            for i, (idx, err, tb) in enumerate(errors[:3]):
                print(f"Thread {idx}: {err}")
                # print(f"Traceback: {tb}")
        
        # 验证实际写入的条目数
        verifier = LTMManager(memory_dir)
        shard_entries = verifier._load_shard("preference")
        print(f"\n=== 实际写入的条目 ===")
        print(f"Entries in shard: {len(shard_entries)}")
        for i, entry in enumerate(shard_entries[:5]):
            print(f"  {i}: {entry.id} - {entry.content[:50]}...")
        
        return successful == total_writes


if __name__ == "__main__":
    success = test_concurrent_debug()
    print(f"\n测试 {'通过' if success else '失败'}")