"""
security/detector.py — Sensitive Data Detector
敏感信息检测器

职责 (Responsibility):
    识别文本中的敏感信息模式，如 API Key、密码、身份证号、银行卡号等。

暴露接口 (Exposes):
    SensitiveDetector.scan(text) -> ScanResult
    SensitiveDetector.is_sensitive(text) -> bool
    SensitiveDetector.redact(text) -> str

依赖 (Depends on):
    re (stdlib only)

禁止 (Must NOT):
    - 记录检测到的敏感值到任何日志
    - 依赖网络或文件 I/O
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

class SensitiveCategory(str, Enum):
    API_KEY       = "api_key"
    PASSWORD      = "password"    # nosec B105 - This is a category label, not a credential
    NATIONAL_ID   = "national_id"     # 身份证号
    BANK_CARD     = "bank_card"       # 银行卡号
    PRIVATE_KEY   = "private_key"     # PEM 私钥
    ACCESS_TOKEN  = "access_token"    # Bearer token 等


@dataclass
class DetectedItem:
    """单条敏感信息检测结果 / A single detected sensitive item."""
    category: SensitiveCategory
    pattern_name: str               # 匹配到的规则名称
    matched_text: str               # 原始匹配文本（用于重定位，内部使用）
    start: int                      # 在原文中的起始位置
    end: int                        # 在原文中的结束位置
    redacted: str                   # 脱敏后的展示文本


@dataclass
class ScanResult:
    """scan() 方法的返回值 / Return type for scan()."""
    is_sensitive: bool
    items: list[DetectedItem] = field(default_factory=list)
    categories: list[SensitiveCategory] = field(default_factory=list)
    redacted_text: str = ""         # 将所有敏感信息替换后的文本


# ─────────────────────────────────────────────────────────────────────────────
# Pattern Definitions
# ─────────────────────────────────────────────────────────────────────────────

_PATTERNS: list[dict] = [
    {
        "name": "openai_api_key",
        "category": SensitiveCategory.API_KEY,
        "regex": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
        "redact_template": "[API_KEY:sk-***]",
    },
    {
        "name": "generic_api_key",
        "category": SensitiveCategory.API_KEY,
        # 匹配 key=VALUE 或 api_key: VALUE 等形式，VALUE 至少 16 个非空白字符
        "regex": re.compile(
            r"(?i)(?:api[_\-]?key|access[_\-]?key|secret[_\-]?key)"
            r"\s*[:=]\s*([a-zA-Z0-9._\-]{16,})"
        ),
        "redact_template": "[API_KEY:***]",
    },
    {
        "name": "bearer_token",
        "category": SensitiveCategory.ACCESS_TOKEN,
        "regex": re.compile(r"(?i)Bearer\s+[a-zA-Z0-9._\-]{20,}"),
        "redact_template": "[TOKEN:Bearer ***]",
    },
    {
        "name": "password_assignment",
        "category": SensitiveCategory.PASSWORD,
        # 匹配 password: VALUE 或 密码: VALUE
        "regex": re.compile(
            r"(?i)(?:password|passwd|密码|口令)\s*[:：=]\s*(\S{4,})"
        ),
        "redact_template": "[PASSWORD:***]",
    },
    {
        "name": "chinese_national_id",
        "category": SensitiveCategory.NATIONAL_ID,
        # 18 位中国大陆居民身份证号
        "regex": re.compile(
            r"\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])\d{2}\d{3}[\dXx]\b"
        ),
        "redact_template": "[ID:***]",
    },
    {
        "name": "bank_card",
        "category": SensitiveCategory.BANK_CARD,
        # 16~19 位连续数字（排除纯年份等误报，要求前后无其他数字）
        "regex": re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
        "redact_template": "[BANK_CARD:****]",
    },
    {
        "name": "pem_private_key",
        "category": SensitiveCategory.PRIVATE_KEY,
        "regex": re.compile(
            r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE KEY-----"
        ),
        "redact_template": "[PRIVATE_KEY:***]",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SensitiveDetector
# ─────────────────────────────────────────────────────────────────────────────

class SensitiveDetector:
    """
    Detect and redact sensitive information in plain text.
    检测并脱敏文本中的敏感信息。

    Usage / 使用示例:
        detector = SensitiveDetector()

        result = detector.scan("My API key is sk-abc123XYZ789abcABC456")
        if result.is_sensitive:
            print(result.redacted_text)      # "My API key is [API_KEY:sk-***]"
            print(result.categories)         # [SensitiveCategory.API_KEY]

        safe_text = detector.redact("password: mySecret123")
        # → "password: [PASSWORD:***]"
    """

    def __init__(self, patterns: list[dict] | None = None) -> None:
        """
        Args:
            patterns: 自定义检测规则列表。不传则使用内置规则。
                      Custom pattern list. Uses built-in patterns if None.
        """
        self._patterns = patterns if patterns is not None else _PATTERNS

    # ── Public Interface ──────────────────────────────────────────────────────

    def scan(self, text: str) -> ScanResult:
        """
        Scan text for sensitive information and return a detailed result.
        扫描文本中的敏感信息，返回详细的检测结果。

        Args:
            text: 待检测的文本 / Text to scan.

        Returns:
            ScanResult 包含：是否敏感、检测到的条目列表、脱敏后文本。
        """
        if not text or not isinstance(text, str):
            return ScanResult(is_sensitive=False, redacted_text=text or "")

        items: list[DetectedItem] = []
        redacted = text

        for pattern_def in self._patterns:
            try:
                for match in pattern_def["regex"].finditer(text):
                    item = DetectedItem(
                        category=pattern_def["category"],
                        pattern_name=pattern_def["name"],
                        matched_text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        redacted=pattern_def["redact_template"],
                    )
                    items.append(item)
            except Exception:
                # 永远不因为单个规则失败而中断整个扫描
                # Never let a single pattern failure abort the whole scan
                continue

        if items:
            redacted = self._apply_redactions(text, items)

        categories = list({item.category for item in items})

        return ScanResult(
            is_sensitive=bool(items),
            items=items,
            categories=categories,
            redacted_text=redacted,
        )

    def is_sensitive(self, text: str) -> bool:
        """
        Quick check: does this text contain any sensitive information?
        快速检查：文本是否包含敏感信息？

        Args:
            text: 待检测的文本。

        Returns:
            True 如果检测到任何敏感信息，否则 False。
        """
        if not text or not isinstance(text, str):
            return False
        return any(
            pattern_def["regex"].search(text)
            for pattern_def in self._patterns
        )

    def redact(self, text: str) -> str:
        """
        Return a copy of text with all sensitive values replaced by placeholders.
        返回将所有敏感值替换为占位符的文本副本。

        Args:
            text: 原始文本。

        Returns:
            脱敏后的文本，不含任何敏感值。
        """
        result = self.scan(text)
        return result.redacted_text

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _apply_redactions(self, text: str, items: list[DetectedItem]) -> str:
        """
        Replace matched spans with redaction placeholders.
        将匹配到的文本片段替换为脱敏占位符。

        处理重叠匹配：按位置排序，跳过与已处理区间重叠的匹配。
        Handles overlapping matches by processing in order and skipping overlaps.
        """
        # 按起始位置排序，起始位置相同时优先处理较长的匹配
        sorted_items = sorted(items, key=lambda i: (i.start, -(i.end - i.start)))

        result_parts: list[str] = []
        last_end = 0

        for item in sorted_items:
            if item.start < last_end:
                # 跳过与已处理区间重叠的匹配 / Skip overlapping match
                continue
            result_parts.append(text[last_end:item.start])
            result_parts.append(item.redacted)
            last_end = item.end

        result_parts.append(text[last_end:])
        return "".join(result_parts)
