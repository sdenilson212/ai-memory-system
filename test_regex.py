"""
测试正则表达式
"""

import re

# 测试中文正向偏好模式
pattern1 = r"(?<!不)(我比较喜欢|我很喜欢|我喜欢|我爱|我偏好|我倾向).{2,}"
regex1 = re.compile(pattern1, re.IGNORECASE | re.DOTALL)

test_strings = [
    "我喜欢吃苹果",
    "我不喜欢吃苹果",
    "我比较喜欢跑步",
    "我不比较喜欢跑步",  # 这个有点奇怪但测试否定
    "我爱编程",
    "我不爱编程",
]

print("Testing pattern:", pattern1)
print("=" * 60)

for text in test_strings:
    match = regex1.search(text)
    if match:
        print(f"'{text}' -> MATCH: {match.group()}")
    else:
        print(f"'{text}' -> NO MATCH")

print("\n" + "=" * 60)
print("Testing English pattern...")

# 测试英文模式
pattern2 = r"(?<!don't\s)(?<!dont\s)(?<!not\s)(I\s+(like|prefer|love|enjoy))\s+.{4,}"
regex2 = re.compile(pattern2, re.IGNORECASE | re.DOTALL)

test_en = [
    "I like coffee",
    "I don't like coffee",
    "I dont like coffee",
    "I do not like coffee",
    "I prefer tea",
    "I don't prefer tea",
]

for text in test_en:
    match = regex2.search(text)
    if match:
        print(f"'{text}' -> MATCH: {match.group()}")
    else:
        print(f"'{text}' -> NO MATCH")