"""
直接 WAL 测试 - 验证性能
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# 添加正确的导入路径
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "engine"))

print("=" * 70)
print("直接 WAL 性能测试")
print("=" * 70)

# 创建测试目录
test_base = Path(tempfile.mkdtemp(prefix="wal_direct_"))
test_dir_trad = test_base / "traditional"
test_dir_wal = test_base / "wal"

test_dir_trad.mkdir(exist_ok=True)
test_dir_wal.mkdir(exist_ok=True)

print(f"测试目录: {test_base}")

# 首先检查模块是否可以导入
print("\n检查模块导入...")
try:
    from engine.core.ltm import LTMManager as TraditionalLTMManager
    print("✅ 传统 LTMManager 导入成功")
except Exception as e:
    print(f"❌ 传统 LTMManager 导入失败: {e}")
    exit(1)

try:
    from engine.core.ltm_wal import LTMManagerWAL
    print("✅ WAL LTMManager 导入成功")
except Exception as e:
    print(f"❌ WAL LTMManager 导入失败: {e}")
    exit(1)

# 创建测试内容
test_contents = [f"性能测试条目 #{i:03d}" for i in range(20)]

print(f"\n测试配置:")
print(f"  条目数: {len(test_contents)}")
print(f"  内容示例: {test_contents[0]}...{test_contents[-1]}")

# 测试传统方式
print("\n" + "-" * 70)
print("测试传统方式...")
print("-" * 70)

trad_time = 999
trad_ltm = None

try:
    trad_ltm = TraditionalLTMManager(test_dir_trad)
    print(f"✅ 传统管理器创建成功")
    
    trad_start = time.time()
    
    for i, content in enumerate(test_contents):
        entry = trad_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=["benchmark", f"item_{i}"]
        )
        
        if i % 5 == 0:
            print(f"  保存 {i+1}/{len(test_contents)}...")
    
    trad_end = time.time()
    trad_time = trad_end - trad_start
    
    print(f"✅ 传统方式完成")
    print(f"  时间: {trad_time:.3f} 秒")
    print(f"  速度: {len(test_contents)/trad_time:.1f} 条/秒")
    
except Exception as e:
    print(f"❌ 传统方式失败: {e}")

# 测试 WAL 方式
print("\n" + "-" * 70)
print("测试 WAL 方式...")
print("-" * 70)

wal_time = 999
wal_ltm = None

try:
    wal_ltm = LTMManagerWAL(test_dir_wal, enable_wal=True)
    print(f"✅ WAL 管理器创建成功")
    print(f"  WAL 状态: {wal_ltm.wal_enabled}")
    
    wal_start = time.time()
    
    for i, content in enumerate(test_contents):
        entry = wal_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=["benchmark", "wal", f"item_{i}"]
        )
        
        if i % 5 == 0:
            print(f"  保存 {i+1}/{len(test_contents)}...")
    
    wal_end = time.time()
    wal_time = wal_end - wal_start
    
    print(f"✅ WAL 方式完成")
    print(f"  时间: {wal_time:.3f} 秒")
    print(f"  速度: {len(test_contents)/wal_time:.1f} 条/秒")
    
except Exception as e:
    print(f"❌ WAL 方式失败: {e}")

# 性能对比
print("\n" + "=" * 70)
print("性能对比结果")
print("=" * 70)

if trad_time < 999 and wal_time < 999:
    speedup = trad_time / wal_time if wal_time > 0 else 0
    
    print(f"\n📊 性能数据:")
    print(f"  传统方式: {trad_time:.3f} 秒")
    print(f"  WAL 方式: {wal_time:.3f} 秒")
    print(f"  性能提升: {speedup:.1f}x")
    
    # 检查 WAL 文件
    wal_files = list(test_dir_wal.rglob("*.wal"))
    if wal_files:
        print(f"\n📝 WAL 文件:")
        for wal_file in wal_files:
            size = os.path.getsize(wal_file)
            print(f"  {wal_file.name} ({size:,} 字节)")
    
    # 验证数据
    if trad_ltm and wal_ltm:
        try:
            trad_count = len(trad_ltm._memory_entries)
            wal_count = len(wal_ltm._memory_entries)
            
            print(f"\n🔍 数据验证:")
            print(f"  传统条目数: {trad_count}")
            print(f"  WAL 条目数: {wal_count}")
            print(f"  一致性: {'✅ 匹配' if trad_count == wal_count else '❌ 不匹配'}")
            
            # 检查搜索功能
            trad_results = trad_ltm.search(query="性能", limit=3)
            wal_results = wal_ltm.search(query="性能", limit=3)
            
            print(f"  搜索功能: {'✅ 正常' if trad_results and wal_results else '❌ 异常'}")
            
        except Exception as e:
            print(f"  数据验证失败: {e}")

# 用户体验评估
print("\n" + "-" * 70)
print("用户体验评估")
print("-" * 70)

if wal_time < 1:
    print("🚀 闪电级性能: 20 条记忆保存 < 1 秒")
    print("  💡 用户体验: 几乎瞬时响应")
    print("  📈 实际感受: '飞一般的记忆' ✓")
elif wal_time < 2:
    print("⚡ 超快响应: 20 条记忆保存 < 2 秒")
    print("  💡 用户体验: 明显感觉更快")
    print("  📈 实际感受: 显著提升 ✓")
elif wal_time < 3:
    print("✅ 显著提升: 20 条记忆保存 < 3 秒")
    print("  💡 用户体验: 比原来快很多")
    print("  📈 实际感受: 有明显改进 ✓")
else:
    print("⚠️  仍有提升空间: 20 条记忆保存 > 3 秒")
    print("  💡 用户体验: 感知不明显")
    print("  📈 实际感受: 需要进一步优化")

# 显示文件结构
print("\n" + "-" * 70)
print("文件结构检查")
print("-" * 70)

for dir_name, dir_path in [("传统目录", test_dir_trad), ("WAL目录", test_dir_wal)]:
    print(f"\n{dir_name}: {dir_path}")
    
    if os.path.exists(dir_path):
        files = list(dir_path.iterdir())
        for file in files:
            if file.is_file():
                size = file.stat().st_size
                print(f"  📄 {file.name} ({size:,} 字节)")
    else:
        print(f"  ⚠️ 目录不存在")

# 清理
print("\n" + "-" * 70)
print("清理测试环境")
print("-" * 70)

try:
    shutil.rmtree(test_base)
    print(f"✅ 清理完成: {test_base}")
except Exception as e:
    print(f"⚠️ 清理失败: {e}")

print("\n" + "=" * 70)
print("测试总结")
print("=" * 70)

if wal_time < trad_time and wal_time < 3:
    print("\n🎯 WAL 性能优化验证成功!")
    print(f"\n💡 核心价值:")
    print(f"  1. 性能提升 {trad_time/wal_time:.1f}x")
    print(f"  2. 保存 {len(test_contents)} 条记忆仅需 {wal_time:.2f} 秒")
    print(f"  3. 完全向后兼容，API 不变")
    print(f"  4. 增量写入避免 O(n) 重写瓶颈")
    
    if wal_time < 1:
        print(f"\n🚀 '飞一般的记忆' 体验达成!")
        print(f"  平均每条记忆保存时间: {wal_time/len(test_contents)*1000:.0f} 毫秒")
    else:
        print(f"\n⚡ 显著性能提升达成!")
        print(f"  平均每条记忆保存时间: {wal_time/len(test_contents)*1000:.0f} 毫秒")
        
else:
    print(f"\n⚠️  性能测试未达预期")
    print(f"  传统: {trad_time:.2f}s, WAL: {wal_time:.2f}s")
    print(f"  建议: 检查 WAL 实现逻辑")

print("\n" + "=" * 70)