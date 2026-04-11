"""
Final WAL Test - Verify Performance Difference
Test both small scale (20 items) and large scale (500 items)
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Set up path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "engine"))

# Force UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

print("=" * 70)
print("FINAL WAL PERFORMANCE TEST")
print("=" * 70)

# Import modules
try:
    from engine.core.ltm import LTMManager as TraditionalLTMManager
    from engine.core.ltm_wal import LTMManagerWAL
    print("[OK] Modules imported")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    exit(1)

def test_performance(test_size, test_name):
    """Run performance test with given size"""
    
    # Create temp dirs
    test_base = Path(tempfile.mkdtemp(prefix=f"wal_{test_name}_"))
    test_dir_trad = test_base / "traditional"
    test_dir_wal = test_base / "wal"
    
    test_dir_trad.mkdir(exist_ok=True)
    test_dir_wal.mkdir(exist_ok=True)
    
    # Create test content
    test_contents = [f"Test item #{i} for {test_name}" for i in range(test_size)]
    
    print(f"\n{test_name.upper()} TEST ({test_size} items)")
    print("-" * 50)
    
    # Test Traditional
    trad_time = None
    try:
        trad_ltm = TraditionalLTMManager(test_dir_trad)
        
        trad_start = time.time()
        for i, content in enumerate(test_contents):
            trad_ltm.save(
                content=content,
                category="other",
                source="ai-detected",
                tags=["test", f"size_{test_size}"]
            )
        trad_end = time.time()
        trad_time = trad_end - trad_start
        
        print(f"Traditional: {trad_time:.3f}s ({test_size/trad_time:.1f} items/sec)")
    except Exception as e:
        print(f"Traditional failed: {e}")
        trad_time = None
    
    # Test WAL
    wal_time = None
    try:
        wal_ltm = LTMManagerWAL(test_dir_wal, enable_wal=True)
        
        wal_start = time.time()
        for i, content in enumerate(test_contents):
            wal_ltm.save(
                content=content,
                category="other",
                source="ai-detected",
                tags=["test", "wal", f"size_{test_size}"]
            )
        wal_end = time.time()
        wal_time = wal_end - wal_start
        
        print(f"WAL:        {wal_time:.3f}s ({test_size/wal_time:.1f} items/sec)")
    except Exception as e:
        print(f"WAL failed: {e}")
        wal_time = None
    
    # Compare
    if trad_time and wal_time:
        speedup = trad_time / wal_time if wal_time > 0 else 0
        print(f"Speedup:    {speedup:.1f}x ({trad_time-wal_time:.3f}s saved)")
        
        # Check file sizes
        trad_files = list(test_dir_trad.rglob("*.md"))
        wal_files = list(test_dir_wal.rglob("*.md"))
        wal_logs = list(test_dir_wal.rglob("*.wal"))
        
        trad_size = sum(f.stat().st_size for f in trad_files) if trad_files else 0
        wal_size = sum(f.stat().st_size for f in wal_files) if wal_files else 0
        
        print(f"Files: Trad {len(trad_files)} files, {trad_size:,} bytes")
        print(f"       WAL  {len(wal_files)} files + {len(wal_logs)} logs, {wal_size:,} bytes")
    
    # Cleanup
    try:
        shutil.rmtree(test_base)
    except:
        pass
    
    return trad_time, wal_time

# Run tests
print("\nRUNNING PERFORMANCE TESTS")
print("=" * 50)

# Test 1: Small scale (20 items)
trad_small, wal_small = test_performance(20, "small")

# Test 2: Medium scale (100 items)
trad_medium, wal_medium = test_performance(100, "medium")

# Test 3: Large scale (500 items - simulate heavy usage)
print("\nWARNING: Large test may take time...")
trad_large, wal_large = test_performance(500, "large")

# Summary
print("\n" + "=" * 70)
print("FINAL ANALYSIS")
print("=" * 70)

print("\nPerformance Summary:")
print("Size      | Traditional | WAL       | Speedup | Status")
print("-" * 60)

def format_row(size, trad, wal):
    if trad and wal:
        speedup = trad / wal if wal > 0 else 0
        if speedup > 1:
            status = "FASTER"
        elif speedup > 0.8:
            status = "SIMILAR"
        else:
            status = "SLOWER"
        
        return f"{size:<9} | {trad:.3f}s    | {wal:.3f}s    | {speedup:.1f}x   | {status}"
    elif trad:
        return f"{size:<9} | {trad:.3f}s    | FAILED   | N/A     | WAL FAILED"
    else:
        return f"{size:<9} | FAILED    | N/A      | N/A     | BOTH FAILED"

print(format_row("20 items", trad_small, wal_small))
print(format_row("100 items", trad_medium, wal_medium))
print(format_row("500 items", trad_large, wal_large))

# Expert analysis
print("\n" + "-" * 70)
print("EXPERT ANALYSIS")
print("-" * 70)

print("\nKey Insights:")
print("1. Small scale (20 items): Traditional already fast (<0.2s)")
print("   - WAL benefit minimal at small scale")
print("   - Overhead may make WAL slower for tiny datasets")

print("\n2. Medium scale (100 items): Where WAL should start shining")
print("   - Traditional: ~O(n) performance")
print("   - WAL: O(1) append + async merge")
print("   - Should see speedup if WAL working")

print("\n3. Large scale (500 items): Real-world scenario")
print("   - Traditional: Could be 2-5 seconds")
print("   - WAL: Should be <1 second if working")
print("   - This is where 'flying memory' matters")

print("\n" + "-" * 70)
print("RECOMMENDATIONS")
print("-" * 70)

if wal_small and wal_medium and wal_large:
    # All tests passed
    if trad_large and wal_large and trad_large > wal_large:
        print("\n🎉 CONGRATULATIONS! WAL OPTIMIZATION SUCCESSFUL!")
        print(f"\nLarge scale speedup: {trad_large/wal_large:.1f}x")
        print(f"Time saved: {trad_large-wal_large:.2f} seconds")
        print("\n💡 'Flying Memory' verified!")
        print("   WAL provides real performance benefit at scale")
        
    elif wal_small and trad_small and wal_small > trad_small * 1.5:
        print("\n⚠️ WARNING: WAL SLOWER THAN TRADITIONAL")
        print("\n💡 Insight: WAL overhead too high for current implementation")
        print("   Consider:")
        print("   1. Increase WAL merge threshold")
        print("   2. Reduce WAL overhead")
        print("   3. Only enable WAL for >100 items")
        
    else:
        print("\n📊 MIXED RESULTS")
        print("\n💡 Recommendations:")
        print("   1. Profile WAL overhead vs benefit")
        print("   2. Consider adaptive WAL (enable only for large datasets)")
        print("   3. Optimize WAL merge algorithm")
        
else:
    print("\n❌ WAL IMPLEMENTATION ISSUES DETECTED")
    print("\n💡 Debug steps:")
    print("   1. Check WAL module imports and dependencies")
    print("   2. Verify WAL file creation")
    print("   3. Test with different dataset sizes")
    print("   4. Check error logs")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)

print("\nThe 'Flying Memory' promise depends on:")
print("✅ WAL implementation correctness")
print("✅ Real performance benefit at scale (>100 items)")
print("✅ Backward compatibility and data safety")
print("✅ User-perceivable speed improvement")

print("\nRecommendation:")
print("1. Fix any WAL implementation issues found")
print("2. Test with real production data sizes")
print("3. Enable WAL only when beneficial")
print("4. Monitor performance in production")

print("\n" + "=" * 70)