import sys
sys.path.insert(0, '.')
from core.trigger import TriggerEngine

e = TriggerEngine()

tests = [
    "我喜欢深色主题界面，我不喜欢太亮的颜色",
    "My goal is to learn Python and build a memory system",
    "I usually wake up at 6am and go for a run",
    "Python 是一种高级编程语言，是指用于通用目的的解释型语言",
    "根据最新研究表明，每天运动30分钟可以提升记忆力",
]

for text in tests:
    suggestions = e.analyze_text(text)
    print(f"\n输入: {text[:50]}")
    if suggestions:
        for s in suggestions:
            print(f"  [{s.confidence:.2f}] {s.destination}/{s.category}: {s.content[:60]}")
            print(f"    原因: {s.reason}")
    else:
        print("  (无建议)")

print("\nTriggerEngine test done")
