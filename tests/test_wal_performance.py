#!/usr/bin/env python3
"""
test_wal_performance.py - WAL Performance Comparison Tests
"""

import time
import uuid
import threading
import statistics
from pathlib import Path

# Test configuration
TEST_MEMORY_DIR = Path("test_wal_performance_memory")
TEST_ITERATIONS = 3
CONCURRENT_THREADS = 32


def cleanup_test_dir():
    """Clean up test directory"""
    import shutil
    if TEST_MEMORY_DIR.exists():
        shutil.rmtree(TEST_MEMORY_DIR)
    TEST_MEMORY_DIR.mkdir(parents=True)


def generate_test_content(count: int) -> list[str]:
    """Generate test content"""
    return [f"Test content {i}: UUID={uuid.uuid4().hex[:8]}"
            for i in range(count)]


# Traditional LTM Tests
def test_traditional_single_save():
    """Test traditional single save"""
    from core.ltm import LTMManager

    cleanup_test_dir()
    ltm = LTMManager(TEST_MEMORY_DIR)

    times = []
    for i in range(TEST_ITERATIONS):
        content = f"Traditional save {i}: {uuid.uuid4().hex[:8]}"
        start = time.time()
        ltm.save(content=content, category="other", source="test")
        end = time.time()
        times.append(end - start)

    avg_time = statistics.mean(times)
    print(f"Traditional single save: {avg_time:.4f}s (avg of {TEST_ITERATIONS})")
    return avg_time


def test_traditional_batch_save():
    """Test traditional batch save"""
    from core.ltm import LTMManager

    cleanup_test_dir()
    ltm = LTMManager(TEST_MEMORY_DIR)
    count = 10
    contents = generate_test_content(count)

    times = []
    for _ in range(TEST_ITERATIONS):
        start = time.time()
        for content in contents:
            ltm.save(content=content, category="other", source="test")
        end = time.time()
        times.append(end - start)

    avg_time = statistics.mean(times)
    print(f"Traditional batch save ({count} items): {avg_time:.4f}s (avg of {TEST_ITERATIONS})")
    return avg_time


# WAL LTM Tests
def test_wal_single_save():
    """Test WAL single save"""
    from core.ltm_wal import LTMManagerWAL

    cleanup_test_dir()
    ltm = LTMManagerWAL(TEST_MEMORY_DIR, enable_wal=True)

    times = []
    for i in range(TEST_ITERATIONS):
        content = f"WAL save {i}: {uuid.uuid4().hex[:8]}"
        start = time.time()
        ltm.save(content=content, category="other", source="test")
        end = time.time()
        times.append(end - start)

    avg_time = statistics.mean(times)
    print(f"WAL single save: {avg_time:.4f}s (avg of {TEST_ITERATIONS})")
    return avg_time


def test_wal_batch_save():
    """Test WAL batch save"""
    from core.ltm_wal import LTMManagerWAL

    cleanup_test_dir()
    ltm = LTMManagerWAL(TEST_MEMORY_DIR, enable_wal=True)
    count = 10
    contents = generate_test_content(count)

    times = []
    for _ in range(TEST_ITERATIONS):
        start = time.time()
        for content in contents:
            ltm.save(content=content, category="other", source="test")
        end = time.time()
        times.append(end - start)

    avg_time = statistics.mean(times)
    print(f"WAL batch save ({count} items): {avg_time:.4f}s (avg of {TEST_ITERATIONS})")
    return avg_time


# Concurrent Tests
def test_concurrent_traditional():
    """Test concurrent traditional saves"""
    from core.ltm import LTMManager

    cleanup_test_dir()
    ltm = LTMManager(TEST_MEMORY_DIR)

    results = {"errors": [], "times": []}

    def save_task(i):
        try:
            content = f"Concurrent save {i}: {uuid.uuid4().hex[:8]}"
            start = time.time()
            ltm.save(content=content, category="other", source="test")
            return time.time() - start
        except Exception as e:
            results["errors"].append(e)
            return None

    start_all = time.time()
    threads = []
    for i in range(CONCURRENT_THREADS):
        t = threading.Thread(target=lambda idx: results["times"].append(save_task(idx)), args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.time() - start_all
    print(f"Traditional concurrent ({CONCURRENT_THREADS} threads): {total_time:.4f}s")
    if results["errors"]:
        print(f"  Errors: {len(results['errors'])}")
    return total_time


def test_concurrent_wal():
    """Test concurrent WAL saves"""
    from core.ltm_wal import LTMManagerWAL

    cleanup_test_dir()
    ltm = LTMManagerWAL(TEST_MEMORY_DIR, enable_wal=True)

    results = {"errors": [], "times": []}

    def save_task(i):
        try:
            content = f"WAL concurrent save {i}: {uuid.uuid4().hex[:8]}"
            start = time.time()
            ltm.save(content=content, category="other", source="test")
            return time.time() - start
        except Exception as e:
            results["errors"].append(e)
            return None

    start_all = time.time()
    threads = []
    for i in range(CONCURRENT_THREADS):
        t = threading.Thread(target=lambda idx: results["times"].append(save_task(idx)), args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.time() - start_all
    print(f"WAL concurrent ({CONCURRENT_THREADS} threads): {total_time:.4f}s")
    if results["errors"]:
        print(f"  Errors: {len(results['errors'])}")
    return total_time


# Read Performance
def test_read_performance():
    """Test read performance"""
    from core.ltm_wal import LTMManagerWAL

    cleanup_test_dir()
    ltm = LTMManagerWAL(TEST_MEMORY_DIR, enable_wal=True)

    # Insert entries
    count = 50
    for i in range(count):
        ltm.save(content=f"Read test {i}", category="other", source="test")

    # Force WAL merge
    ltm.force_wal_merge()

    # Test read performance
    times = []
    for _ in range(10):
        start = time.time()
        results = ltm.search(query="test", max_results=20)
        times.append(time.time() - start)

    avg_time = statistics.mean(times)
    print(f"Read performance ({count} entries): {avg_time:.4f}s (avg of 10)")
    return avg_time


# Stats Test
def test_wal_stats():
    """Test WAL statistics"""
    from core.ltm_wal import LTMManagerWAL

    cleanup_test_dir()
    ltm = LTMManagerWAL(TEST_MEMORY_DIR, enable_wal=True)

    # Insert some entries
    for i in range(50):
        ltm.save(content=f"Stats test {i}", category="other", source="test")

    # Force merge
    merge_result = ltm.force_wal_merge(category="other")

    print(f"WAL stats: merge_result={merge_result}")
    return True
