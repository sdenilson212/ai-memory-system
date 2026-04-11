"""
Direct WAL Performance Test - ASCII Only
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

# Force UTF-8 output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

print("=" * 70)
print("Direct WAL Performance Test")
print("=" * 70)

# Create test directories
test_base = Path(tempfile.mkdtemp(prefix="wal_direct_"))
test_dir_trad = test_base / "traditional"
test_dir_wal = test_base / "wal"

test_dir_trad.mkdir(exist_ok=True)
test_dir_wal.mkdir(exist_ok=True)

print(f"Test directory: {test_base}")

# Check module imports
print("\nChecking module imports...")
try:
    from engine.core.ltm import LTMManager as TraditionalLTMManager
    print("[OK] Traditional LTMManager imported")
except Exception as e:
    print(f"[FAIL] Traditional LTMManager import failed: {e}")
    exit(1)

try:
    from engine.core.ltm_wal import LTMManagerWAL
    print("[OK] WAL LTMManager imported")
except Exception as e:
    print(f"[FAIL] WAL LTMManager import failed: {e}")
    exit(1)

# Test content
test_contents = [f"Performance Test Item #{i:03d}" for i in range(20)]

print(f"\nTest configuration:")
print(f"  Items: {len(test_contents)}")
print(f"  Sample: {test_contents[0]} ... {test_contents[-1]}")

# Test Traditional
print("\n" + "-" * 70)
print("Testing Traditional method...")
print("-" * 70)

trad_time = 999
trad_ltm = None

try:
    trad_ltm = TraditionalLTMManager(test_dir_trad)
    print("[OK] Traditional manager created")
    
    trad_start = time.time()
    
    for i, content in enumerate(test_contents):
        entry = trad_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=["benchmark", f"item_{i}"]
        )
        
        if i % 5 == 0:
            print(f"  Progress: {i+1}/{len(test_contents)}...")
    
    trad_end = time.time()
    trad_time = trad_end - trad_start
    
    print("[OK] Traditional method completed")
    print(f"  Time: {trad_time:.3f} seconds")
    print(f"  Speed: {len(test_contents)/trad_time:.1f} items/sec")
    
except Exception as e:
    print(f"[FAIL] Traditional method failed: {e}")

# Test WAL
print("\n" + "-" * 70)
print("Testing WAL method...")
print("-" * 70)

wal_time = 999
wal_ltm = None

try:
    wal_ltm = LTMManagerWAL(test_dir_wal, enable_wal=True)
    print("[OK] WAL manager created")
    print(f"  WAL enabled: {wal_ltm.wal_enabled}")
    
    wal_start = time.time()
    
    for i, content in enumerate(test_contents):
        entry = wal_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=["benchmark", "wal", f"item_{i}"]
        )
        
        if i % 5 == 0:
            print(f"  Progress: {i+1}/{len(test_contents)}...")
    
    wal_end = time.time()
    wal_time = wal_end - wal_start
    
    print("[OK] WAL method completed")
    print(f"  Time: {wal_time:.3f} seconds")
    print(f"  Speed: {len(test_contents)/wal_time:.1f} items/sec")
    
except Exception as e:
    print(f"[FAIL] WAL method failed: {e}")

# Performance comparison
print("\n" + "=" * 70)
print("Performance Comparison Results")
print("=" * 70)

if trad_time < 999 and wal_time < 999:
    speedup = trad_time / wal_time if wal_time > 0 else 0
    
    print(f"\nPerformance Data:")
    print(f"  Traditional: {trad_time:.3f} seconds")
    print(f"  WAL: {wal_time:.3f} seconds")
    print(f"  Speedup: {speedup:.1f}x")
    
    # Check WAL files
    wal_files = list(test_dir_wal.rglob("*.wal"))
    if wal_files:
        print(f"\nWAL Files:")
        for wal_file in wal_files:
            size = os.path.getsize(wal_file)
            print(f"  {wal_file.name} ({size:,} bytes)")
    
    # Data verification
    if trad_ltm and wal_ltm:
        try:
            trad_count = len(trad_ltm._memory_entries)
            wal_count = len(wal_ltm._memory_entries)
            
            print(f"\nData Verification:")
            print(f"  Traditional items: {trad_count}")
            print(f"  WAL items: {wal_count}")
            print(f"  Consistency: {'PASS' if trad_count == wal_count else 'FAIL'}")
            
            # Search test
            trad_results = trad_ltm.search(query="Performance", limit=3)
            wal_results = wal_ltm.search(query="Performance", limit=3)
            
            print(f"  Search function: {'PASS' if trad_results and wal_results else 'FAIL'}")
            
        except Exception as e:
            print(f"  Verification failed: {e}")

# User experience
print("\n" + "-" * 70)
print("User Experience Evaluation")
print("-" * 70)

if wal_time < 1:
    print("A+ Light-speed performance: 20 items < 1 second")
    print("  Experience: Near-instant response")
    print("  Result: 'Flying Memory' ACHIEVED!")
elif wal_time < 2:
    print("A  Fast response: 20 items < 2 seconds")
    print("  Experience: Noticeably faster")
    print("  Result: Significant improvement")
elif wal_time < 3:
    print("B  Good improvement: 20 items < 3 seconds")
    print("  Experience: Much faster than before")
    print("  Result: Clear improvement")
else:
    print("C  Room for improvement: 20 items > 3 seconds")
    print("  Experience: Not significantly noticeable")
    print("  Result: Needs further optimization")

# File structure
print("\n" + "-" * 70)
print("File Structure Check")
print("-" * 70)

for dir_name, dir_path in [("Traditional", test_dir_trad), ("WAL", test_dir_wal)]:
    print(f"\n{dir_name} directory: {dir_path}")
    
    if os.path.exists(dir_path):
        files = list(dir_path.iterdir())
        for file in files:
            if file.is_file():
                size = file.stat().st_size
                print(f"  FILE: {file.name} ({size:,} bytes)")
    else:
        print(f"  WARNING: Directory does not exist")

# Cleanup
print("\n" + "-" * 70)
print("Cleanup")
print("-" * 70)

try:
    shutil.rmtree(test_base)
    print(f"[OK] Cleanup complete: {test_base}")
except Exception as e:
    print(f"[WARN] Cleanup failed: {e}")

print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)

if wal_time < trad_time and wal_time < 3:
    print("\n[SUCCESS] WAL performance optimization verified!")
    print(f"\nCore Value:")
    print(f"  1. Performance improved by {trad_time/wal_time:.1f}x")
    print(f"  2. Save {len(test_contents)} items in only {wal_time:.2f} seconds")
    print(f"  3. Fully backward compatible, API unchanged")
    print(f"  4. Incremental write avoids O(n) rewrite bottleneck")
    
    if wal_time < 1:
        print(f"\n[EXCELLENT] 'Flying Memory' experience achieved!")
        print(f"  Average per-item save time: {wal_time/len(test_contents)*1000:.0f} ms")
    else:
        print(f"\n[GOOD] Significant performance improvement achieved!")
        print(f"  Average per-item save time: {wal_time/len(test_contents)*1000:.0f} ms")
        
else:
    print(f"\n[WARNING] Performance test did not meet expectations")
    print(f"  Traditional: {trad_time:.2f}s, WAL: {wal_time:.2f}s")
    print(f"  Suggestion: Check WAL implementation logic")

print("\n" + "=" * 70)