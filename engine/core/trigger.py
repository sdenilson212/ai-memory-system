"""
core/trigger.py — Memory Trigger Suggestion Engine
记忆触发建议引擎

v1.1 改进（2026-03-25）：
  1. 补全文档注释，说明内置规则和自定义配置方法
  2. 增加规则可配置化：支持 YAML 规则文件加载

职责 (Responsibility):
    分析会话事件流，识别值得存入 LTM / KB 的内容，输出 SaveSuggestion 列表。
    LTM → 长期记忆（偏好、习惯、决策、项目信息）
    KB  → 知识库（技术术语、参考资料、引用信息）

暴露接口 (Exposes):
    TriggerEngine.analyze(events)  -> list[SaveSuggestion]
    TriggerEngine.analyze_text(text) -> list[SaveSuggestion]
    TriggerEngine.load_rules(yaml_path) -> None  # v1.1: 加载自定义规则

内置触发器:
    LTM:
      - "我的偏好..." → preference (置信度 0.85)
      - "我更喜欢..." → preference (置信度 0.85)
      - "我通常..." → habit (置信度 0.78)
      - "我的项目是..." → profile (置信度 0.90)
      - "我的目标是..." → goal (置信度 0.82)
    KB:
      - "定义/意味着..." → technical (置信度 0.75)
      - "根据/研究表明..." → reference (置信度 0.72)
      - "如何实现/步骤..." → howto (置信度 0.70)

依赖 (Depends on): re, dataclasses
禁止 (Must NOT): 直接写文件；依赖 ltm.py / kb.py
"""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from typing import Literal


# ─────────────────────────────────────────────────────────────────────────────
# Rule Patterns
# ─────────────────────────────────────────────────────────────────────────────

# LTM 触发规则列表
# 格式：(pattern, category, confidence_boost, reason, tags)
_LTM_RULES: list[tuple[str, str, float, str, list[str]]] = [
    # 偏好类
    (r"(?:我更喜欢?|I\s*(?:prefer|like|love|enjoy))\b.{0,60}", "preference", 0.85, "识别到偏好表达", ["偏好"]),
    (r"(?:我的偏好|I\s*prefer)\b.{0,60}", "preference", 0.85, "偏好明确表达", ["偏好"]),

    # 习惯类
    (r"(?:我通常?|I\s*(?:usually|always|often|tend\s+to))\b.{0,60}", "habit", 0.78, "识别到习惯性行为", ["习惯"]),
    (r"(?:我习惯于?|I\s*am\s+used\s+to)\b.{0,60}", "habit", 0.78, "习惯性行为", ["习惯"]),

    # 目标类
    (r"(?:我的目标|My\s*(?:goal|aim|plan))\s*(?:是|to\s*be|is)\b.{0,80}", "goal", 0.82, "目标设定", ["目标"]),
    (r"(?:I\s*want\s*to|I\s*plan\s*to|I\s*aim\s*to)\b.{0,80}", "goal", 0.82, "目标意图", ["目标"]),

    # Profile 类
    (r"(?:我的项目是?|My\s*project\s*(?:is|called))\b.{0,80}", "profile", 0.90, "项目信息", ["项目"]),
    (r"(?:I\s*live\s*in|I\s*work\s*at|I\s*am\s+a)\b.{0,80}", "profile", 0.85, "Profile信息", ["profile"]),

    # 决策类
    (r"(?:我决定|我选择|我决定用)\b.{0,80}", "decision", 0.80, "决策记录", ["决策"]),
    (r"(?:我最终选了?|I\s*(?:decided|chose|went\s+with))\b.{0,80}", "decision", 0.80, "决策表达", ["决策"]),
]

# KB 触发规则列表
_KB_RULES: list[tuple[str, str, float, str, list[str]]] = [
    # 技术术语
    (r"(?:定义|define|means?)\b.{0,80}", "technical", 0.75, "技术术语定义", ["术语", "定义"]),
    (r"(?:tech|API|SDK|protocol|framework)\b.{0,80}", "technical", 0.72, "技术关键词", ["技术"]),

    # 参考引用
    (r"(?:根据|依据|研究表明|from\s+.*research|according\s+to)\b.{0,100}", "reference", 0.72, "参考引用", ["引用"]),
    (r"(?:见|参考|refer\s+to|see\s+section)\b.{0,100}", "reference", 0.70, "参考资料", ["引用"]),

    # 操作步骤
    (r"(?:如何实现|how\s+to|步骤|steps?|实现方法)\b.{0,120}", "howto", 0.70, "操作步骤", ["教程"]),
    (r"(?:第一步|首先|then|next|finally)\b.{0,120}", "howto", 0.65, "分步说明", ["教程"]),
]

# 全局阈值
_CONFIDENCE_THRESHOLD = 0.70
_MAX_CONTENT_LENGTH = 300


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SaveSuggestion:
    """
    建议保存的记忆条目。
    """
    content: str
    destination: Literal["ltm", "kb"]   # ltm = 长期记忆, kb = 知识库
    category: str
    confidence: float                  # 0.0 ~ 1.0
    reason: str
    source: str = "ai-detected"
    tags: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# TriggerEngine
# ─────────────────────────────────────────────────────────────────────────────

class TriggerEngine:
    """
    Analyzes session events and returns save suggestions.
    分析会话事件流，返回值得保存的建议列表。

    v1.1 新增：
      - load_rules() 支持 YAML 自定义规则文件
      - add_rule() 动态添加规则
      - clear_rules() 清空规则（慎用）

    Usage:
        engine = TriggerEngine()
        suggestions = engine.analyze(session.events)
        for s in suggestions:
            if s.destination == "ltm":
                ltm.save(content=s.content, category=s.category, source=s.source)
            else:
                kb.add(title="...", content=s.content, category=s.category)
    """

    def __init__(self, confidence_threshold: float = _CONFIDENCE_THRESHOLD):
        self._threshold = confidence_threshold
        self._ltm_patterns = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), cat, conf, reason, tags)
            for p, cat, conf, reason, tags in _LTM_RULES
        ]
        self._kb_patterns = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), cat, conf, reason, tags)
            for p, cat, conf, reason, tags in _KB_RULES
        ]

    def analyze(self, events: list[dict]) -> list[SaveSuggestion]:
        """
        Analyze a list of session events and return save suggestions.

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

            # 只分析用户消息
            event_type = event.get("event_type", "")
            if event_type not in ("user_message", "user_input", "message", ""):
                continue

            # 截断超长内容
            analysis_content = content[:_MAX_CONTENT_LENGTH]

            # Try LTM rules
            for pattern, cat, conf, reason, tags in self._ltm_patterns:
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
                            category=cat,
                            confidence=conf,
                            reason=reason,
                            tags=tags,
                        ))
                        seen_snippets.add(key)
                        break  # one rule per event is enough for LTM

            # Try KB rules
            for pattern, cat, conf, reason, tags in self._kb_patterns:
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
                            category=cat,
                            confidence=conf,
                            reason=reason,
                            tags=tags,
                        ))
                        seen_snippets.add(key)
                        break

        # Sort by confidence descending
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    def analyze_text(self, text: str) -> list[SaveSuggestion]:
        """
        Convenience method: analyze a single text string directly.
        便捷方法：直接分析单段文本。
        """
        return self.analyze([{"event_type": "user_message", "content": text}])

    def load_rules(self, yaml_path: str) -> None:
        """
        v1.1: 从 YAML 文件加载自定义规则。

        YAML 格式示例:
        ```yaml
        ltm_rules:
          - pattern: "我的工作涉及..."
            category: project
            confidence: 0.80
            reason: "项目信息"
            tags: [工作]

        kb_rules:
          - pattern: "这种方法是..."
            category: technique
            confidence: 0.75
            reason: "技术方法"
            tags: [方法]
        ```
        """
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f) or {}

            for rule in rules.get("ltm_rules", []):
                p = re.compile(rule["pattern"], re.IGNORECASE | re.DOTALL)
                self._ltm_patterns.append((
                    p,
                    rule.get("category", "other"),
                    rule.get("confidence", 0.75),
                    rule.get("reason", ""),
                    rule.get("tags", []),
                ))

            for rule in rules.get("kb_rules", []):
                p = re.compile(rule["pattern"], re.IGNORECASE | re.DOTALL)
                self._kb_patterns.append((
                    p,
                    rule.get("category", "other"),
                    rule.get("confidence", 0.75),
                    rule.get("reason", ""),
                    rule.get("tags", []),
                ))
        except Exception as e:
            raise ValueError(f"Failed to load rules from {yaml_path}: {e}")

    def add_rule(
        self,
        pattern: str,
        destination: Literal["ltm", "kb"],
        category: str,
        confidence: float = 0.75,
        reason: str = "",
        tags: list[str] | None = None,
    ) -> None:
        """v1.1: 动态添加一条规则（运行时生效）"""
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        entry = (compiled, category, confidence, reason, tags or [])
        if destination == "ltm":
            self._ltm_patterns.append(entry)
        else:
            self._kb_patterns.append(entry)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_snippet(content: str, match: re.Match) -> str:
    """Extract a meaningful snippet around the match."""
    start = max(0, match.start() - 10)
    end = min(len(content), match.end() + 80)
    snippet = content[start:end].strip()
    # Clean up leading/trailing partial words
    if start > 0 and not content[start - 1].isspace():
        sp = snippet.find(" ")
        if sp > 0:
            snippet = snippet[sp + 1:]
    return snippet[:_MAX_CONTENT_LENGTH]
