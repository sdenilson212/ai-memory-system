from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import time

from core.ltm import LTMManager


def test_ltm_concurrent_save_does_not_lose_entries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        total_writes = 32

        def writer(index: int) -> str:
            ltm = LTMManager(memory_dir)
            # 使用不同的内容，避免去重检查误判为重复内容
            entry = ltm.save(
                content=f"parallel integrity write {index} at timestamp {time.time()}",
                category="preference",
                source="test",
                tags=["parallel", "integrity", f"idx_{index}"],
            )
            return entry.id

        with ThreadPoolExecutor(max_workers=8) as pool:
            entry_ids = list(pool.map(writer, range(total_writes)))

        verifier = LTMManager(memory_dir)
        shard_entries = verifier._load_shard("preference")
        shard_ids = {entry.id for entry in shard_entries}

        assert len(set(entry_ids)) == total_writes, f"Expected {total_writes} unique IDs, got {len(set(entry_ids))}. Entry IDs: {entry_ids}"
        assert len(shard_entries) == total_writes, f"Expected {total_writes} entries in shard, got {len(shard_entries)}. Entry contents: {[e.content for e in shard_entries]}"
        assert set(entry_ids).issubset(shard_ids), f"Returned IDs not found in shard. Missing: {set(entry_ids) - shard_ids}"
