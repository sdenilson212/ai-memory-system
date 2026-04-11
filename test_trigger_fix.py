#!/usr/bin/env python3
"""测试触发规则修复效果"""

import sys
sys.path.insert(0, "engine")

from core.trigger import TriggerEngine

def test_preference_detection():
    """测试偏好检测的正确性"""
    engine = TriggerEngine(confidence_threshold=0.70)
    
    test_cases = [
        # (输入文本, 期望类别, 期望标签)
        ("我喜欢吃苹果", "preference", ["偏好", "正向"]),
        ("我不喜欢吃苹果", None, []),  # 期望不触发正向偏好
        ("我不太喜欢跑步", None, []),  # 期望不触发正向偏好  
        ("我有点不喜欢那个设计", None, []),  # 期望不触发正向偏好
        ("讨厌下雨天", "preference", ["偏好", "负向"]),
        ("我不喜欢下雨天", "preference", ["偏好", "负向"]),
        ("我的目标是学习 Python", "goal", ["目标"]),
        ("我叫张三", "profile", ["个人信息"]),
    ]
    
    print("测试触发规则修复效果")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for text, expected_category, expected_tags in test_cases:
        suggestions = engine.analyze_text(text)
        
        if expected_category is None:
            # 期望不触发任何规则
            if not suggestions:
                print(f"V '{text}' - 正确未触发")
                passed += 1
            else:
                print(f"X '{text}' - 错误触发: {suggestions}")
                failed += 1
        else:
            # 期望触发特定规则
            if suggestions and suggestions[0].category == expected_category:
                # 检查标签
                actual_tags = suggestions[0].tags
                if all(tag in actual_tags for tag in expected_tags):
                    print(f"V '{text}' - 正确触发 {expected_category} ({actual_tags})")
                    passed += 1
                else:
                    print(f"! '{text}' - 类别正确但标签不符: 期望 {expected_tags}, 实际 {actual_tags}")
                    passed += 0.5
                    failed += 0.5
            else:
                print(f"X '{text}' - 未触发或类别错误: {suggestions}")
                failed += 1
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("V 所有测试通过！触发规则修复有效。")
        return True
    else:
        print("! 有测试失败，需要进一步调整。")
        return False

if __name__ == "__main__":
    success = test_preference_detection()
    sys.exit(0 if success else 1)