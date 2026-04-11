"""
简单 WAL 测试 - 验证性能
"""

import time
import tempfile
import sys
from pathlib import Path

# 添加路径
sys.path.append(".")

# 创建测试目录
test_base = Path(tempfile.mkdtemp(prefix="wal_test_"))
test_dir_trad = test_base / "traditional"
test_dir_wal = test_base / "wal"

test_dir_trad.mkdir(exist_ok=True)
test_dir_wal.mkdir(exist_ok=True)

print("=" * 60)
print("简单 WAL 性能测试")
print("=" * 60)

# 测试内容
test_contents = [f"测试内容 #{i}" for i in range(30)]

print(f"测试条目数: {len(test_contents)}")
print(f"测试目录: {test_base}")

# 测试传统方式
try:
    from engine.core.ltm import LTMManager as TraditionalLTMManager
    
    trad_start = time.time()
    trad_ltm = TraditionalLTMManager(test_dir_trad)
    
    for content in test_contents:
        trad_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=["test"]
        )
    
    trad_end = time.time()
    trad_time = trad_end - trad_start
    trad_speed = len(test_contents) / trad_time if trad_time > 0 else 0
    
    print(f"\n传统方式:")
    print(f"  时间: {trad_time:.3f} 秒")
    print(f"  速度: {trad_speed:.1f} 条/秒")
    
except Exception as e:
    print(f"传统方式失败: {e}")
    trad_time = 999

# 测试 WAL 方式
try:
    from engine.core.ltm_wal import LTMManagerWAL
    
    wal_start = time.time()
    wal_ltm = LTMManagerWAL(test_dir_wal, enable_wal=True)
    
    for content in test_contents:
        wal_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=["test", "wal"]
        )
    
    wal_end = time.time()
    wal_time = wal_end - wal_start
    wal_speed = len(test_contents) / wal_time if wal_time > 0 else 0
    
    print(f"\nWAL 方式:")
    print(f"  时间: {wal_time:.3f} 秒")
    print(f"  速度: {wal_speed:.1f} 条/秒")
    
    if trad_time < 999 and wal_time < 999:
        speedup = trad_time / wal_time if wal_time > 0 else 0
        print(f"\n性能对比:")
        print(f"  速度提升: {speedup:.1f}x")
        
        if wal_time < 1:
            print("  感受: 闪电速度 (<1秒)")
        elif wal_time < 2:
            print("  感受: 超快响应 (<2秒)")
        elif wal_time < 3:
            print("  感受: 明显提升 (<3秒)")
        else:
            print("  感受: 仍有提升空间")
    
    # 验证数据
    trad_count = len(trad_ltm._memory_entries) if 'trad_ltm' in locals() else 0
    wal_count = len(wal_ltm._memory_entries) if 'wal_ltm' in locals() else 0
    
    print(f"\n数据验证:")
    print(f"  传统条目数: {trad_count}")
    print(f"  WAL 条目数: {wal_count}")
    print(f"  一致性: {'OK' if trad_count == wal_count else '不一致'}")
    
except Exception as e:
    print(f"WAL 方式失败: {e}")
    wal_time = 999

print("\n" + "=" * 60)
print("测试完成")

# 显示文件结构
import os

print(f"\n文件结构:")
for dir_name, dir_path in [("传统", test_dir_trad), ("WAL", test_dir_wal)]:
    print(f"\n{dir_name}:")
    if os.path.exists(dir_path):
        files = list(os.listdir(dir_path))
        for file in files:
            file_path = os.path.join(dir_path, file)
            size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
            print(f"  {file} ({size} bytes)")
    else:
        print(f"  目录不存在")

print("\n清理测试目录...")
import shutil
shutil.rmtree(test_base)
print("完成")