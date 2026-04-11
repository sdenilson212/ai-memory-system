#!/usr/bin/env python3
"""
test_wal_quick_fixed.py — WAL 功能快速验证 (Windows 兼容版)

快速验证 WAL 增强版功能是否正常工作。
Windows PowerShell 兼容版本，避免 Unicode 编码问题。
"""

import sys
from pathlib import Path

# 添加 engine 目录到路径
engine_dir = Path(__file__).parent / "engine"
sys.path.insert(0, str(engine_dir))

def test_basic_functionality():
    """测试基本功能"""
    print("[TEST] 测试 WAL 基本功能...")
    
    try:
        from core.ltm_wal import LTMManagerWAL
        
        # 创建测试目录
        test_dir = Path("test_wal_quick")
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
        test_dir.mkdir(parents=True)
        
        # 创建 WAL 增强版管理器
        ltm = LTMManagerWAL(test_dir, enable_wal=True)
        print("  [OK] LTMManagerWAL 初始化成功")
        
        # 测试保存
        entry = ltm.save(
            content="WAL 功能测试内容",
            category="other",  # 使用有效分类
            source="ai-detected",
            tags=["test", "wal"]
        )
        print(f"  [OK] 保存成功: ID={entry.id}")
        
        # 测试搜索
        results = ltm.search(query="WAL", category="other")
        print(f"  [OK] 搜索成功: 找到 {len(results)} 条结果")
        
        # 测试获取
        retrieved = ltm.get(entry.id)
        if retrieved and retrieved.id == entry.id:
            print(f"  [OK] 获取成功: ID={retrieved.id}")
        else:
            print(f"  [FAIL] 获取失败")
            return False
        
        # 测试 WAL 统计
        stats = ltm.get_wal_stats()
        print(f"  [OK] WAL 统计: {stats}")
        
        # 清理
        import shutil
        shutil.rmtree(test_dir)
        
        print("[SUCCESS] 所有基本功能测试通过!")
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_improvement():
    """测试性能改进"""
    print("\n[TEST] 测试性能改进...")
    
    try:
        from core.ltm import LTMManager as TraditionalLTMManager
        from core.ltm_wal import LTMManagerWAL
        
        # 创建测试目录
        test_dir_trad = Path("test_traditional")
        test_dir_wal = Path("test_wal")
        
        for d in [test_dir_trad, test_dir_wal]:
            if d.exists():
                import shutil
                shutil.rmtree(d)
            d.mkdir(parents=True)
        
        # 创建大量数据测试
        print("  创建测试数据 (100条)...")
        test_contents = [f"性能测试内容 {i}" for i in range(100)]
        
        # 传统方式
        import time
        trad_ltm = TraditionalLTMManager(test_dir_trad)
        
        trad_start = time.time()
        for content in test_contents:
            trad_ltm.save(content=content, category="other", source="ai-detected")
        trad_end = time.time()
        trad_time = trad_end - trad_start
        
        # WAL 方式
        wal_ltm = LTMManagerWAL(test_dir_wal, enable_wal=True)
        
        wal_start = time.time()
        for content in test_contents:
            wal_ltm.save(content=content, category="other", source="ai-detected")
        wal_end = time.time()
        wal_time = wal_end - wal_start
        
        print(f"  传统方式: {trad_time:.2f}s")
        print(f"  WAL 方式: {wal_time:.2f}s")
        
        if wal_time < trad_time:
            speedup = trad_time / wal_time
            print(f"  [OK] 性能提升: {speedup:.1f}x 更快")
        else:
            print(f"  [WARN] WAL 没有更快 (可能数据量太小)")
        
        # 清理
        import shutil
        shutil.rmtree(test_dir_trad)
        shutil.rmtree(test_dir_wal)
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 性能测试失败: {e}")
        return False

def test_mcp_compatibility():
    """测试 MCP 兼容性"""
    print("\n[TEST] 测试 MCP 兼容性...")
    
    try:
        # 检查 MCP 服务器文件
        mcp_file = Path(__file__).parent / "engine" / "mcp_server_wal.py"
        if not mcp_file.exists():
            print(f"  [FAIL] MCP 服务器文件不存在: {mcp_file}")
            return False
        
        print(f"  [OK] MCP 服务器文件存在: {mcp_file}")
        
        # 检查文件内容
        content = mcp_file.read_text(encoding="utf-8")
        if "LTMManagerWAL" in content:
            print("  [OK] 文件中包含 LTMManagerWAL")
        else:
            print("  [FAIL] 文件中未找到 LTMManagerWAL")
            return False
        
        if "WAL-enhanced" in content:
            print("  [OK] 文件中包含 WAL-enhanced 标识")
        else:
            print("  [WARN] 文件中未找到 WAL-enhanced 标识")
        
        # 检查环境变量配置
        if "AI_MEMORY_WAL_ENABLED" in content:
            print("  [OK] 文件中包含 WAL 环境变量配置")
        else:
            print("  [WARN] 文件中未找到 WAL 环境变量配置")
        
        print("  [OK] MCP 兼容性检查通过")
        return True
        
    except Exception as e:
        print(f"[FAIL] MCP 兼容性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("WAL 增强版快速验证 (Windows 兼容版)")
    print("=" * 60)
    
    success = True
    
    # 运行测试
    if not test_basic_functionality():
        success = False
    
    if not test_performance_improvement():
        success = False
    
    if not test_mcp_compatibility():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] 所有测试通过! WAL 增强版功能正常。")
        print("\n下一步:")
        print("1. 重启 WorkBuddy 以加载新的 MCP 配置")
        print("2. 观察 memory_save 性能是否提升")
        print("3. 使用 memory_status 查看 WAL 统计信息")
    else:
        print("[FAIL] 部分测试失败，请检查错误信息。")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)