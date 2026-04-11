"""
Feature List 模块 - Phase 1 实现

功能：
1. 使用 LLM Prompt 将用户需求拆解为 Feature List
2. 质量检查层验证 Feature 的完整性
3. 支持依赖排序和验收标准定义

遵循张大胖建议：LLM Prompt + 质量检查层
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re


class FeatureStatus(Enum):
    """Feature 状态"""
    PENDING = "pending"      # 待实现
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


class Complexity(Enum):
    """复杂度评估"""
    SIMPLE = "simple"      # 简单：1-2小时
    MEDIUM = "medium"      # 中等：半天-1天
    COMPLEX = "complex"    # 复杂：1天以上


@dataclass
class Feature:
    """
    单个 Feature 定义
    
    模板：
    - 描述：用一句用户能懂的话
    - 验收标准：至少2-3个可测试条件
    - 依赖项：依赖哪些其他 Feature
    - 预估复杂度：simple/medium/complex
    """
    feature_id: str
    description: str                    # Feature 描述
    acceptance_criteria: List[str]      # 验收标准（2-3个可测试条件）
    dependencies: List[str]             # 依赖的其他 Feature ID
    complexity: Complexity              # 预估复杂度
    status: FeatureStatus = FeatureStatus.PENDING
    
    # 执行信息
    implementation_notes: Optional[str] = None
    test_results: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "dependencies": self.dependencies,
            "complexity": self.complexity.value,
            "status": self.status.value,
            "implementation_notes": self.implementation_notes,
            "test_results": self.test_results,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Feature":
        return cls(
            feature_id=data["feature_id"],
            description=data["description"],
            acceptance_criteria=data.get("acceptance_criteria", []),
            dependencies=data.get("dependencies", []),
            complexity=Complexity(data.get("complexity", "medium")),
            status=FeatureStatus(data.get("status", "pending")),
            implementation_notes=data.get("implementation_notes"),
            test_results=data.get("test_results"),
        )


@dataclass
class FeatureList:
    """
    Feature List 容器
    
    包含：
    - 原始用户需求
    - 拆解后的 Feature 列表
    - 实现顺序（按依赖排序）
    """
    original_request: str               # 原始用户需求
    features: List[Feature]             # Feature 列表
    core_objective: Optional[str] = None  # 核心目标（一句话）
    
    def to_dict(self) -> Dict:
        return {
            "original_request": self.original_request,
            "core_objective": self.core_objective,
            "features": [f.to_dict() for f in self.features],
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FeatureList":
        return cls(
            original_request=data["original_request"],
            core_objective=data.get("core_objective"),
            features=[Feature.from_dict(f) for f in data.get("features", [])],
        )
    
    def get_implementation_order(self) -> List[Feature]:
        """
        按依赖排序返回实现顺序
        
        使用拓扑排序确保依赖先实现
        """
        # 构建依赖图
        feature_map = {f.feature_id: f for f in self.features}
        in_degree = {f.feature_id: 0 for f in self.features}
        graph = {f.feature_id: [] for f in self.features}
        
        for f in self.features:
            for dep in f.dependencies:
                if dep in feature_map:
                    graph[dep].append(f.feature_id)
                    in_degree[f.feature_id] += 1
        
        # 拓扑排序
        queue = [fid for fid, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 按复杂度排序：simple 优先
            queue.sort(key=lambda x: {
                Complexity.SIMPLE: 0,
                Complexity.MEDIUM: 1,
                Complexity.COMPLEX: 2
            }.get(feature_map[x].complexity, 1))
            
            fid = queue.pop(0)
            result.append(feature_map[fid])
            
            for next_fid in graph[fid]:
                in_degree[next_fid] -= 1
                if in_degree[next_fid] == 0:
                    queue.append(next_fid)
        
        return result
    
    def get_feature_by_id(self, feature_id: str) -> Optional[Feature]:
        """按 ID 查找 Feature"""
        for f in self.features:
            if f.feature_id == feature_id:
                return f
        return None


class FeatureListGenerator:
    """
    Feature List 生成器
    
    流程：
    1. LLM Prompt 生成 Feature List
    2. 质量检查层验证
    3. 不通过则补充/修正
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        
    def generate(self, user_request: str, max_retries: int = 3) -> Tuple[FeatureList, Dict]:
        """
        生成 Feature List
        
        Args:
            user_request: 用户需求描述
            max_retries: 最大重试次数
            
        Returns:
            (FeatureList, 生成信息)
        """
        for attempt in range(max_retries):
            # Step 1: LLM 生成
            raw_features = self._llm_generate(user_request)
            
            # Step 2: 质量检查
            check_result = self._quality_check(raw_features)
            
            if check_result["passed"]:
                feature_list = self._parse_features(user_request, raw_features)
                return feature_list, {
                    "attempts": attempt + 1,
                    "quality_score": check_result["score"],
                    "issues": check_result.get("issues", [])
                }
            
            # 检查失败，准备重试
            if attempt < max_retries - 1:
                user_request = self._enhance_prompt(user_request, check_result["issues"])
        
        # 所有尝试失败，返回最佳尝试
        feature_list = self._parse_features(user_request, raw_features)
        return feature_list, {
            "attempts": max_retries,
            "quality_score": check_result["score"],
            "issues": check_result.get("issues", []),
            "warning": "质量检查未完全通过，请人工审查"
        }
    
    def _llm_generate(self, user_request: str) -> List[Dict]:
        """
        使用 LLM Prompt 生成 Feature List
        
        注意：这里是占位符实现
        实际应该调用 LLM API
        """
        # 构建 Prompt
        prompt = self._build_prompt(user_request)
        
        # 模拟 LLM 输出（实际应调用 API）
        return self._mock_llm_response(user_request)
    
    def _build_prompt(self, user_request: str) -> str:
        """
        构建 LLM Prompt
        
        使用 WBS + MECE 框架
        """
        return f"""请使用 WBS（工作分解结构）+ MECE（相互独立，完全穷尽）原则，将以下用户需求拆解为 Feature List。

用户需求：
{user_request}

请按以下格式输出：

核心目标：[一句话描述要解决的核心问题]

Feature 列表：
1. [Feature ID]: [描述]
   - 验收标准：
     * [标准1]
     * [标准2]
   - 依赖项：[依赖的 Feature ID，无则写"无"]
   - 预估复杂度：[simple/medium/complex]

要求：
1. 每个 Feature 足够小，小到"一次验证能通过"
2. 核心模块不超过3个
3. Feature 之间符合 MECE 原则
4. 明确依赖关系，避免循环依赖
5. 每个 Feature 必须有2-3个可测试的验收标准
"""
    
    def _mock_llm_response(self, user_request: str) -> List[Dict]:
        """
        模拟 LLM 响应（占位符）
        
        实际实现应调用真实 LLM API
        """
        # 简单的关键词匹配生成 Feature
        features = []
        
        # 分析请求类型
        if "记忆" in user_request or "memory" in user_request.lower():
            features = [
                {
                    "id": "F001",
                    "description": "实现 Feature 数据结构定义",
                    "acceptance_criteria": [
                        "Feature 类能正确序列化/反序列化",
                        "包含所有必要字段（id, description, criteria, dependencies, complexity）"
                    ],
                    "dependencies": [],
                    "complexity": "simple"
                },
                {
                    "id": "F002",
                    "description": "实现 Feature List 生成器",
                    "acceptance_criteria": [
                        "能解析用户需求并生成 Feature List",
                        "支持质量检查和重试机制",
                        "生成的 Feature 符合 MECE 原则"
                    ],
                    "dependencies": ["F001"],
                    "complexity": "medium"
                },
                {
                    "id": "F003",
                    "description": "实现质量检查层",
                    "acceptance_criteria": [
                        "检查每个 Feature 是否有验收标准",
                        "检查依赖项是否存在循环",
                        "复杂度评估是否合理"
                    ],
                    "dependencies": ["F001"],
                    "complexity": "simple"
                },
                {
                    "id": "F004",
                    "description": "实现依赖排序算法",
                    "acceptance_criteria": [
                        "使用拓扑排序确保依赖先实现",
                        "同层级按复杂度排序（simple优先）",
                        "能检测循环依赖并报错"
                    ],
                    "dependencies": ["F002", "F003"],
                    "complexity": "medium"
                }
            ]
        else:
            # 通用处理
            features = [
                {
                    "id": "F001",
                    "description": "分析用户需求，提取核心目标",
                    "acceptance_criteria": [
                        "核心目标能用一句话清晰描述",
                        "与原始需求一致，无歧义"
                    ],
                    "dependencies": [],
                    "complexity": "simple"
                },
                {
                    "id": "F002",
                    "description": "拆解核心功能模块",
                    "acceptance_criteria": [
                        "模块数不超过3个",
                        "符合 MECE 原则",
                        "每个模块有明确边界"
                    ],
                    "dependencies": ["F001"],
                    "complexity": "medium"
                },
                {
                    "id": "F003",
                    "description": "细化 Feature 并定义验收标准",
                    "acceptance_criteria": [
                        "每个 Feature 有2-3个可测试标准",
                        "Feature 足够小（一次验证能通过）",
                        "依赖关系明确"
                    ],
                    "dependencies": ["F002"],
                    "complexity": "medium"
                }
            ]
        
        return features
    
    def _quality_check(self, raw_features: List[Dict]) -> Dict:
        """
        质量检查层
        
        检查项：
        1. 每个 Feature 是否有验收标准？
        2. 依赖项是否存在循环？
        3. 复杂度评估是否合理？
        4. 是否有"一句话说不清楚"的 Feature？
        """
        issues = []
        score = 1.0
        critical_issues = 0
        
        # 检查1：验收标准（关键检查）
        for f in raw_features:
            criteria = f.get("acceptance_criteria", [])
            if len(criteria) < 2:
                issues.append(f"Feature {f.get('id', '?')} 验收标准不足（<2条）")
                score -= 0.2
                critical_issues += 1
        
        # 检查2：循环依赖（关键检查）
        feature_ids = {f.get("id") for f in raw_features}
        graph = {f.get("id"): f.get("dependencies", []) for f in raw_features}
        
        if self._has_cycle(graph):
            issues.append("存在循环依赖")
            score -= 0.3
            critical_issues += 1
        
        # 检查3：依赖存在性
        for f in raw_features:
            for dep in f.get("dependencies", []):
                if dep and dep != "无" and dep not in feature_ids:
                    issues.append(f"Feature {f.get('id')} 依赖不存在的 Feature: {dep}")
                    score -= 0.1
        
        # 检查4：描述清晰度
        for f in raw_features:
            desc = f.get("description", "")
            if len(desc) > 100:
                issues.append(f"Feature {f.get('id')} 描述过长，建议拆分")
                score -= 0.05
        
        score = max(0.0, score)
        # 有关键问题时不通过
        passed = score >= 0.8 and critical_issues == 0
        
        return {
            "passed": passed,
            "score": round(score, 2),
            "issues": issues,
            "critical_issues": critical_issues
        }
    
    def _has_cycle(self, graph: Dict[str, List[str]]) -> bool:
        """检测图中是否有环"""
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor == "无":
                    continue
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def _parse_features(self, user_request: str, raw_features: List[Dict]) -> FeatureList:
        """解析原始 Feature 数据为 FeatureList"""
        features = []
        for rf in raw_features:
            feature = Feature(
                feature_id=rf.get("id", f"F{len(features)+1:03d}"),
                description=rf.get("description", ""),
                acceptance_criteria=rf.get("acceptance_criteria", []),
                dependencies=[d for d in rf.get("dependencies", []) if d != "无"],
                complexity=Complexity(rf.get("complexity", "medium"))
            )
            features.append(feature)
        
        return FeatureList(
            original_request=user_request,
            features=features,
            core_objective=self._extract_core_objective(user_request)
        )
    
    def _extract_core_objective(self, user_request: str) -> str:
        """提取核心目标（简单实现）"""
        # 提取第一句话或前50字符
        first_sentence = user_request.split("。")[0].split("？")[0]
        return first_sentence[:50] + "..." if len(first_sentence) > 50 else first_sentence
    
    def _enhance_prompt(self, original_request: str, issues: List[str]) -> str:
        """根据问题增强 Prompt"""
        issues_text = "\n".join(f"- {issue}" for issue in issues)
        return f"""{original_request}

注意：之前的拆解存在以下问题，请修正：
{issues_text}

请重新拆解，确保：
1. 所有 Feature 都有至少2-3个明确的验收标准
2. 依赖关系正确，无循环
3. Feature 描述简洁清晰（20词以内）
"""


class QualityChecker:
    """
    独立的质量检查器
    
    用于 Feature 实现后的验收验证
    """
    
    def check_feature(self, feature: Feature, implementation_result: Any) -> Dict:
        """
        检查单个 Feature 是否通过验收
        
        Args:
            feature: 要检查的 Feature
            implementation_result: 实现结果
            
        Returns:
            检查结果
        """
        results = []
        passed_count = 0
        
        for criterion in feature.acceptance_criteria:
            # 简单的关键词匹配验证
            # 实际应根据具体验收标准设计验证逻辑
            passed = self._verify_criterion(criterion, implementation_result)
            results.append({
                "criterion": criterion,
                "passed": passed
            })
            if passed:
                passed_count += 1
        
        total = len(feature.acceptance_criteria)
        pass_rate = passed_count / total if total > 0 else 0
        
        return {
            "feature_id": feature.feature_id,
            "passed": pass_rate >= 0.8,  # 80%通过算整体通过
            "pass_rate": round(pass_rate, 2),
            "details": results
        }
    
    def _verify_criterion(self, criterion: str, result: Any) -> bool:
        """
        验证单个验收标准
        
        Phase 1 实现：宽松的验证逻辑
        - 如果有实现结果，就认为可能满足标准
        - 实际应根据标准类型设计更精确的验证
        """
        # Phase 1: 只要有实现结果就认为通过（宽松验证）
        if result is not None:
            # 简单的启发式：结果非空且看起来合理
            result_str = str(result).lower()
            # 排除明显的失败信号
            failure_signals = ["error", "fail", "exception", "none", "null"]
            if not any(signal in result_str for signal in failure_signals):
                return True
        return False


# 便捷函数
def generate_feature_list(user_request: str) -> Tuple[FeatureList, Dict]:
    """
    快速生成 Feature List 的便捷函数
    
    Args:
        user_request: 用户需求描述
        
    Returns:
        (FeatureList, 生成信息)
    """
    generator = FeatureListGenerator()
    return generator.generate(user_request)


if __name__ == "__main__":
    # 简单测试
    request = "实现一个 Feature List 生成器，用于将用户需求拆解为可追踪的功能点"
    feature_list, info = generate_feature_list(request)
    
    print("=" * 50)
    print(f"核心目标: {feature_list.core_objective}")
    print(f"生成信息: {info}")
    print("=" * 50)
    print("Feature 列表:")
    for f in feature_list.features:
        print(f"\n[{f.feature_id}] {f.description}")
        print(f"  复杂度: {f.complexity.value}")
        print(f"  依赖: {f.dependencies if f.dependencies else '无'}")
        print(f"  验收标准:")
        for ac in f.acceptance_criteria:
            print(f"    - {ac}")
    
    print("\n" + "=" * 50)
    print("实现顺序:")
    for i, f in enumerate(feature_list.get_implementation_order(), 1):
        print(f"{i}. [{f.feature_id}] {f.description[:30]}...")
