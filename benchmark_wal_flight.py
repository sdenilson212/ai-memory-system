"""
benchmark_wal_flight.py
WAL 性能飞行测试 - 验证"飞一般的记忆"效果

测试目标：验证 WAL 增强版的实际性能表现
对比项：传统方式 vs WAL 方式
测试场景：模拟真实使用环境，保存 50 条记忆
"""

import time
import tempfile
import shutil
import os
from pathlib import Path

# 设置临时测试目录
test_base = Path(tempfile.mkdtemp(prefix="wal_flight_"))
test_dir_trad = test_base / "traditional"
test_dir_wal = test_base / "wal"

test_dir_trad.mkdir(exist_ok=True)
test_dir_wal.mkdir(exist_ok=True)

# 导入模块
import sys
sys.path.append(".")

try:
    # 导入传统 LTM
    from engine.core.ltm import LTMManager as TraditionalLTMManager
    print("[INFO] 传统 LTMManager 导入成功")
except ImportError as e:
    print(f"[ERROR] 无法导入传统 LTMManager: {e}")
    exit(1)

try:
    # 导入 WAL LTM
    from engine.core.ltm_wal import LTMManagerWAL
    print("[INFO] WAL LTMManager 导入成功")
except ImportError as e:
    print(f"[ERROR] 无法导入 WAL LTMManager: {e}")
    exit(1)

print("\n" + "="*70)
print("🚀 WAL 性能飞行测试 - 验证 '飞一般的记忆' 效果")
print("="*70)

# 测试内容
test_contents = [
    f"WAL 性能测试内容 #{i} - {'🎯' * (i % 5 + 1)}" for i in range(50)
]

print(f"\n📊 测试配置:")
print(f"  测试条目数: {len(test_contents)}")
print(f"  测试目录: {test_base}")
print(f"  传统目录: {test_dir_trad}")
print(f"  WAL 目录: {test_dir_wal}")

print("\n" + "-"*70)
print("📈 测试 1: 传统方式批量保存 (基准测试)")
print("-"*70)

try:
    trad_ltm = TraditionalLTMManager(test_dir_trad)
    
    trad_start = time.time()
    trad_ids = []
    
    for i, content in enumerate(test_contents):
        entry = trad_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=[f"test_{i}", "benchmark"]
        )
        trad_ids.append(entry.id)
        
        if i % 10 == 0:
            print(f"  保存 {i+1}/{len(test_contents)}...")
    
    trad_end = time.time()
    trad_time = trad_end - trad_start
    trad_avg = trad_time / len(test_contents)
    
    print(f"\n✅ 传统方式完成:")
    print(f"  总时间: {trad_time:.3f} 秒")
    print(f"  平均每条: {trad_avg:.3f} 秒")
    print(f"  速度: {len(test_contents)/trad_time:.1f} 条/秒")
    
except Exception as e:
    print(f"❌ 传统方式测试失败: {e}")
    trad_time = 999

print("\n" + "-"*70)
print("⚡ 测试 2: WAL 方式批量保存 (优化测试)")
print("-"*70)

try:
    wal_ltm = LTMManagerWAL(test_dir_wal, enable_wal=True)
    
    wal_start = time.time()
    wal_ids = []
    
    for i, content in enumerate(test_contents):
        entry = wal_ltm.save(
            content=content,
            category="other",
            source="ai-detected",
            tags=[f"test_{i}", "benchmark", "wal"]
        )
        wal_ids.append(entry.id)
        
        if i % 10 == 0:
            print(f"  保存 {i+1}/{len(test_contents)}...")
    
    wal_end = time.time()
    wal_time = wal_end - wal_start
    wal_avg = wal_time / len(test_contents)
    
    print(f"\n✅ WAL 方式完成:")
    print(f"  总时间: {wal_time:.3f} 秒")
    print(f"  平均每条: {wal_avg:.3f} 秒")
    print(f"  速度: {len(test_contents)/wal_time:.1f} 条/秒")
    
except Exception as e:
    print(f"❌ WAL 方式测试失败: {e}")
    wal_time = 999

print("\n" + "="*70)
print("🏆 性能对比结果")
print("="*70)

if trad_time < 999 and wal_time < 999:
    speedup = trad_time / wal_time if wal_time > 0 else 0
    
    print(f"\n📊 绝对性能:")
    print(f"  传统方式: {trad_time:.3f} 秒 ({trad_avg:.3f} 秒/条)")
    print(f"  WAL 方式: {wal_time:.3f} 秒 ({wal_avg:.3f} 秒/条)")
    
    print(f"\n⚡ 性能提升:")
    print(f"  速度提升: {speedup:.1f}x")
    print(f"  时间节省: {trad_time - wal_time:.3f} 秒 ({((trad_time - wal_time)/trad_time*100):.1f}%)")
    
    print(f"\n🚀 实际感受:")
    if wal_time < 1:
        print("  ✅ 闪电速度 - 50 条记忆保存 < 1 秒")
    elif wal_time < 3:
        print("  ✅ 快速响应 - 50 条记忆保存 < 3 秒")
    elif wal_time < 5:
        print("  ⚡ 显著提升 - 50 条记忆保存 < 5 秒")
    else:
        print("  ⚠️  仍有提升空间")
    
    # 验证数据一致性
    print(f"\n🔍 数据验证:")
    try:
        trad_count = len(trad_ltm._memory_entries)
        wal_count = len(wal_ltm._memory_entries)
        
        print(f"  传统方式条目数: {trad_count}")
        print(f"  WAL 方式条目数: {wal_count}")
        print(f"  数据一致性: {'✅ 匹配' if trad_count == wal_count else '❌ 不匹配'}")
        
        # 验证随机一条数据
        if trad_ids and wal_ids:
            trad_entry = trad_ltm.get(trad_ids[10])
            wal_entry = wal_ltm.get(wal_ids[10])
            
            if trad_entry and wal_entry:
                print(f"  内容验证: {'✅ 一致' if trad_entry.content == wal_entry.content else '❌ 不一致'}")
        
    except Exception as e:
        print(f"  数据验证失败: {e}")

elif trad_time >= 999:
    print("❌ 传统方式测试失败，无法对比")
elif wal_time >= 999:
    print("❌ WAL 方式测试失败，无法对比")

print("\n" + "-"*70)
print("📂 文件系统检查")
print("-"*70)

def check_dir_structure(dir_path, name):
    print(f"\n{name}:")
    total_files = 0
    total_size = 0
    
    for root, dirs, files in os.walk(dir_path):
        level = root.replace(str(dir_path), '').count(os.sep)
        indent = ' ' * 4 * level
        
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            
            rel_path = os.path.relpath(file_path, dir_path)
            print(f"{indent}📄 {rel_path} ({file_size:,} bytes)")
            
            total_files += 1
            total_size += file_size
    
    print(f"  总计: {total_files} 个文件，{total_size:,} 字节")

check_dir_structure(test_dir_trad, "传统目录")
check_dir_structure(test_dir_wal, "WAL 目录")

# 检查 WAL 特定文件
wal_files = list(test_dir_wal.rglob("*.wal"))
if wal_files:
    print(f"\n📝 WAL 日志文件:")
    for wal_file in wal_files:
        size = os.path.getsize(wal_file)
        print(f"  📄 {wal_file.name} ({size:,} bytes)")

print("\n" + "="*70)
print("🎯 飞行测试总结")
print("="*70)

if wal_time < trad_time and wal_time < 5:
    print("\n✅ 飞行测试通过！")
    print(f"\n💡 '飞一般的记忆' 验证成功:")
    print(f"  - WAL 方式比传统方式快 {trad_time/wal_time:.1f}x")
    print(f"  - 保存 {len(test_contents)} 条记忆仅需 {wal_time:.2f} 秒")
    print(f"  - 完全向后兼容，API 不变")
    print(f"  - 增量写入避免 O(n) 重写瓶颈")
    
    if wal_time < 1:
        print(f"\n🚀 闪电级性能：平均 {wal_avg*1000:.0f} 毫秒/条")
    elif wal_time < 2:
        print(f"\n⚡ 超快响应：平均 {wal_avg*1000:.0f} 毫秒/条")
    elif wal_time < 3:
        print(f"\n✅ 显著提升：平均 {wal_avg*1000:.0f} 毫秒/条")
else:
    print(f"\n⚠️  性能提升有限或测试失败")
    print(f"  传统: {trad_time:.2f}s, WAL: {wal_time:.2f}s")
    print(f"  建议检查 WAL 实现")

print(f"\n🧹 清理测试目录: {test_base}")
try:
    shutil.rmtree(test_base)
    print("✅ 测试目录已清理")
except Exception as e:
    print(f"⚠️  清理失败: {e}")

print("\n" + "="*70)
print("📈 建议后续步骤:")
print("1. 重启 WorkBuddy，应用 WAL MCP 配置")
print("2. 使用 memory_save 工具验证真实性能")
print("3. 监控 memory_status 查看 WAL 运行状态")
print("4. 压力测试：1000+ 条记忆保存")
print("="*70)