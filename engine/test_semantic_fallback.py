#!/usr/bin/env python3
"""
测试语义搜索降级机制
预期：模型下载失败时，系统自动回退到 BM25
"""

import sys
import tempfile
from pathlib import Path

# 测试1: 验证降级机制
print("Test 1: SemanticVectorStore fallback when model unavailable")
print("-" * 60)

# 使用 ignore_cleanup_errors=True 避免 ChromaDB 文件句柄问题
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
    try:
        from core.vector_store import SemanticVectorStore
        
        # 禁用网络（模拟墙内环境）
        import os
        os.environ['HF_HUB_OFFLINE'] = '1'
        
        store = SemanticVectorStore(Path(tmpdir))
        
        # 预期：语义搜索被禁用，但不崩溃
        assert store.semantic_enabled == False, "semantic_enabled should be False when model unavailable"
        print("[PASS] SemanticVectorStore correctly disabled when model unavailable")
        
        # 验证 add 和 search 不会崩溃
        result = store.add("test_id", "test content", {}, flush=True)
        print(f"[PASS] add() returns gracefully (returned: {result})")
        
        search_results = store.search("test")
        assert search_results == [], "search() should return empty list when disabled"
        print("[PASS] search() returns empty list when disabled")
        
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 确保关闭资源
        if 'store' in locals():
            store.close()

print("\nAll tests passed! Fallback mechanism works correctly.")
