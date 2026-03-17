"""
core/trigger.py — Memory Trigger Suggestion Engine
记忆触发建议引擎

职责:
    分析会话事件列表，识别值得保存到 LTM 或 KB 的内容，
    输出"建议保存"列表（不自动写入）。

设计原则:
    - 只给建议，不自动写入 — 防止误判污染记忆库
    - 规则驱动 + 置信度评分 — 分数低于阈值不输出
    - 向后兼容 — 不依赖任何外部 AI API

暴露接口:
    TriggerEngine.analyze(events) -> list[SaveSuggestion]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SaveSuggestion:
    """一条建议保存的记忆项 / A suggested memory save item."""
    content: str
    destination: Literal["ltm", "kb"]      # ltm = 长期记忆, kb = 知识库
    category: str                           # ltm/kb 的分类
    confidence: float                       # 0.0 ~ 1.0
    reason: str                             # 触发原因说明（中文）
    source: str = "ai-detected"
    tags: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Rule Patterns
# ─────────────────────────────────────────────────────────────────────────────

# 每条规则: (pattern, category, destination, confidence_boost, reason, tags)
_LTM_RULES: list[tuple[str, str, float, str, list[str]]] = [
    # 偏好类 — 中文不需要 \s+，直接跟随内容
    (r"(我比较喜欢|我很喜欢|我喜欢|我爱|我偏好|我倾向).{2,}",
     "preference", 0.85, "检测到用户偏好表达", ["偏好"]),
    (r"(I\s+(like|prefer|love|enjoy))\s+.{4,}",
     "preference", 0.85, "检测到用户偏好表达（英文）", ["偏好"]),
    (r"(不喜欢|讨厌|我不想|我不喜欢).{2,}",
     "preference", 0.80, "检测到用户负向偏好", ["偏好", "负向"]),
    (r"(hate|don'?t\s+like|dislike)\s+.{4,}",
     "preference", 0.80, "检测到用户负向偏好（英文）", ["偏好", "负向"]),
    # 目标类
    (r"(我的目标|我想要|我计划|我打算|我希望|我要).{3,}",
     "goal", 0.82, "检测到用户目标/计划", ["目标"]),
    (r"(My goal|I want to|I plan to|I aim)\s+.{4,}",
     "goal", 0.82, "检测到用户目标/计划（英文）", ["目标"]),
    # 个人信息类
    (r"(我叫|我的名字是|我是)[A-Za-z\u4e00-\u9fff]{2,}",
     "profile", 0.90, "检测到用户身份信息", ["个人信息"]),
    (r"(I'm|I am|My name is)\s+[A-Za-z\u4e00-\u9fff]{2,}",
     "profile", 0.90, "检测到用户身份信息（英文）", ["个人信息"]),
    (r"(我住在|我在|我来自|我工作在).{3,}",
     "profile", 0.85, "检测到用户地理/工作信息", ["个人信息"]),
    (r"(I live in|I'm from|I work at)\s+.{3,}",
     "profile", 0.85, "检测到用户地理/工作信息（英文）", ["个人信息"]),
    # 习惯类
    (r"(我每天|我通常|我习惯|我一般|我经常).{3,}",
     "habit", 0.78, "检测到用户习惯描述", ["习惯"]),
    (r"(I usually|I always|I tend to|I often)\s+.{4,}",
     "habit", 0.78, "检测到用户习惯描述（英文）", ["习惯"]),
]

_KB_RULES: list[tuple[str, str, float, str, list[str]]] = [
    # 技术/知识定义
    (r"(是指|是一种|的意思是).{5,}",
     "technical", 0.75, "检测到概念定义或解释", ["知识", "定义"]),
    (r"(defined as|means that|refers to|is a)\s+.{10,}",
     "technical", 0.75, "检测到概念定义或解释（英文）", ["知识", "定义"]),
    # 明确的事实陈述
    (r"(研究表明|数据显示|事实上|实际上|根据.*表明).{5,}",
     "reference", 0.72, "检测到事实性陈述", ["事实"]),
    (r"(according to|studies show|in fact|the truth is)\s+.{10,}",
     "reference", 0.72, "检测到事实性陈述（英文）", ["事实"]),
    # 操作步骤
    (r"(步骤|第一步|首先).{5,}",
     "technical", 0.70, "检测到操作步骤描述", ["操作", "指南"]),
    (r"(how to|step\s+\d|first.*then)\s+.{10,}",
     "technical", 0.70, "检测到操作步骤描述（英文）", ["操作", "指南"]),
]

# 最低置信度阈值
_CONFIDENCE_THRESHOLD = 0.70
# 单条内容最大字符数（太长的不建议整段保存）
_MAX_CONTENT_LEN = 300


# ─────────────────────────────────────────────────────────────────────────────
# TriggerEngine
# ─────────────────────────────────────────────────────────────────────────────

class TriggerEngine:
    """
    Analyzes session events and returns save suggestions.
    分析会话事件，返回建议保存的记忆列表。

    Usage:
        engine = TriggerEngine()
        suggestions = engine.analyze(session.events)
        # suggestions is a list of SaveSuggestion, sorted by confidence desc
    """

    def __init__(self, confidence_threshold: float = _CONFIDENCE_THRESHOLD) -> None:
        self._threshold = confidence_threshold
        self._ltm_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), cat, conf, reason, tags)
            for pattern, cat, conf, reason, tags in _LTM_RULES
        ]
        self._kb_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), cat, conf, reason, tags)
            for pattern, cat, conf, reason, tags in _KB_RULES
        ]

    def analyze(self, events: list[dict]) -> list[SaveSuggestion]:
        """
        Analyze a list of session events and return save suggestions.
        分析会话事件列表，返回建议保存列表。

        Args:
            events: STM session events list, each item has:
                    {"event_type": str, "content": str, "timestamp": str}

        Returns:
            List of SaveSuggestion, sorted by confidence descending.
            Duplicates (same content snippet) are deduplicated.
        """
        suggestions: list[SaveSuggestion] = []
        seen_snippets: set[str] = set()

        for event in events:
            content = str(event.get("content", "")).strip()
            if not content or len(content) < 8:
                continue

            # Only analyze user-typed content
            event_type = event.get("event_type", "")
            if event_type not in ("user_message", "user_input", "message", ""):
                continue

            # Truncate very long content
            analysis_content = content[:_MAX_CONTENT_LEN]

            # Try LTM rules
            for pattern, category, conf, reason, tags in self._ltm_patterns:
                m = pattern.search(analysis_content)
                if m:
                    snippet = _extract_snippet(analysis_content, m)
                    key = snippet[:60].lower()
                    if key in seen_snippets:
                        continue
                    if conf >= self._threshold:
                        suggestions.append(SaveSuggestion(
                            content=snippet,
                            destination="ltm",
                            category=category,
                            confidence=conf,
                            reason=reason,
                            tags=tags[:],
                        ))
                        seen_snippets.add(key)
                    break  # one rule per event is enough for LTM

            # Try KB rules
            for pattern, category, conf, reason, tags in self._kb_patterns:
                m = pattern.search(analysis_content)
                if m:
                    snippet = _extract_snippet(analysis_content, m)
                    key = snippet[:60].lower()
                    if key in seen_snippets:
                        continue
                    if conf >= self._threshold:
                        suggestions.append(SaveSuggestion(
                            content=snippet,
                            destination="kb",
                            category=category,
                            confidence=conf,
                            reason=reason,
                            tags=tags[:],
                        ))
                        seen_snippets.add(key)
                    break

        # Sort by confidence desc
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    def analyze_text(self, text: str) -> list[SaveSuggestion]:
        """
        Convenience method: analyze a single text string directly.
        便捷方法：直接分析单条文本。
        """
        return self.analyze([{"event_type": "user_message", "content": text}])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_snippet(content: str, match: re.Match) -> str:
    """
    Extract a meaningful snippet around the match.
    提取匹配位置附近的有意义片段。
    """
    start = max(0, match.start() - 10)
    end = min(len(content), match.end() + 80)
    snippet = content[start:end].strip()
    # Clean up leading/trailing partial words
    if start > 0 and not content[start - 1].isspace():
        # Find first space
        sp = snippet.find(" ")
        if sp > 0:
            snippet = snippet[sp:].strip()
    return snippet[:_MAX_CONTENT_LEN]
