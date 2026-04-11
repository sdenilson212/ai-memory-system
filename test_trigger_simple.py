"""
简单测试正则触发修复
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "engine"))
from core.trigger import TriggerEngine

engine = TriggerEngine()

print("Testing trigger fix for negative preference misclassification...")
print("=" * 60)

# 测试中文
text1 = "我喜欢吃苹果"
s1 = engine.analyze_text(text1)
print(f"'{text1}' -> {len(s1)} suggestions")
if s1:
    print(f"  Category: {s1[0].category}, Confidence: {s1[0].confidence}")

text2 = "我不喜欢吃苹果"  
s2 = engine.analyze_text(text2)
print(f"'{text2}' -> {len(s2)} suggestions")
if s2:
    for sug in s2:
        print(f"  Category: {sug.category}, Tags: {sug.tags}, Confidence: {sug.confidence}")

# 检查是否被误判为正向偏好
misclassified = False
for sug in s2:
    if sug.category == "preference" and "负向" not in sug.tags:
        misclassified = True
        print("  [FAIL] Negative preference misclassified as positive!")
        break

if not misclassified and s2:
    print("  [OK] Negative preference correctly identified or not triggered")
elif not s2:
    print("  [OK] No trigger (acceptable for negative preference)")

print("\nTesting English...")
text3 = "I like coffee"
s3 = engine.analyze_text(text3)
print(f"'{text3}' -> {len(s3)} suggestions")
if s3:
    print(f"  Category: {s3[0].category}, Confidence: {s3[0].confidence}")

text4 = "I don't like coffee"
s4 = engine.analyze_text(text4)
print(f"'{text4}' -> {len(s4)} suggestions")
if s4:
    for sug in s4:
        print(f"  Category: {sug.category}, Tags: {sug.tags}, Confidence: {sug.confidence}")

# 检查英文误判
misclassified_en = False
for sug in s4:
    if sug.category == "preference" and "负向" not in sug.tags:
        misclassified_en = True
        print("  [FAIL] English negative preference misclassified as positive!")
        break

if not misclassified_en and s4:
    print("  [OK] English negative preference correctly identified")
elif not s4:
    print("  [OK] No trigger (acceptable for negative preference)")

print("\nTest complete.")