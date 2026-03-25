# 自适应 Skill 系统 — 实现指南

**状态**: 开发中  
**最后更新**: 2026-03-18

---

## 目录

1. [快速开始](#快速开始)
2. [核心模块实现](#核心模块实现)
3. [与记忆系统的集成](#与记忆系统的集成)
4. [数据流示例](#数据流示例)
5. [测试策略](#测试策略)
6. [部署指南](#部署指南)

---

## 快速开始

### 环境要求

```bash
Python 3.8+
pip install requests  # 用于调用 LTM/KB API
```

### 基础使用

```python
from adaptive_skill_system import AdaptiveSkillSystem

# 初始化系统
system = AdaptiveSkillSystem(
    kb_client=YourKBClient(),      # 你的知识库客户端
    ltm_client=YourLTMClient()     # 你的长期记忆客户端
)

# 解决问题
response = system.solve(
    problem="怎样制定营销预算？",
    verbose=True
)

print(response.to_dict())
```

### 输出示例

```json
{
  "result": {
    "budget_allocation": {
      "channels": {
        "social_media": 40,
        "content_marketing": 30,
        "paid_ads": 20,
        "events": 10
      },
      "notes": "Based on your target audience analysis"
    }
  },
  "layer": 2,
  "status": "success",
  "confidence": 0.85,
  "execution_time_ms": 2340,
  "metadata": {
    "layer_2_composed": true,
    "base_skills": ["Budget Framework", "Channel Analysis"]
  }
}
```

---

## 核心模块实现

### 1. 问题诊断模块 (`ProblemAnalyzer`)

```python
class ProblemAnalyzer:
    """
    分析问题的特征，判断应该使用哪个层级的解决方案
    """
    
    def analyze(self, problem: str) -> ProblemAnalysis:
        """
        分析问题
        
        Returns:
            ProblemAnalysis: 包含以下信息
              - title: 问题标题
              - domain: 问题所属领域
              - complexity: 问题复杂度 (1-10)
              - keywords: 关键词列表
              - required_knowledge: 需要的知识领域
              - can_generate: 是否可以自动生成 Skill
              - confidence_score: 分析的置信度
        """
        pass
    
    def analyze_feedback(self, feedback: str) -> FeedbackAnalysis:
        """
        分析用户反馈
        
        Returns:
            FeedbackAnalysis: 包含以下信息
              - aspect: 反馈涉及的方面
              - sentiment: 情感分析
              - suggestions: 具体建议
              - priority: 优先级
        """
        pass
```

**实现要点**：
- 使用 NLP 技术提取关键信息
- 与知识库对比找到相似的问题
- 评估问题复杂度

---

### 2. Skill 组合模块 (`SkillComposer`)

```python
class SkillComposer:
    """
    从记忆中提取信息，组合成新 Skill
    """
    
    def can_compose(self, memories: List[Memory], analysis: ProblemAnalysis) -> bool:
        """
        判断是否可以从现有记忆中组合 Skill
        """
        pass
    
    def compose(self, memories: List[Memory], analysis: ProblemAnalysis) -> Skill:
        """
        组合成新 Skill
        
        Process:
          1. 从 memories 中提取相关步骤
          2. 排序和链接这些步骤
          3. 创建新 Skill
          4. 标记为 "composed"
        """
        pass
    
    def extract_steps(self, memory: Memory) -> List[SkillStep]:
        """
        从单条记忆中提取可用的步骤
        """
        pass
    
    def link_steps(self, steps: List[SkillStep]) -> List[SkillStep]:
        """
        链接多个步骤，确保它们能够顺序执行
        """
        pass
```

**实现要点**：
- 分析记忆中的问题解决过程
- 提取关键步骤和决策逻辑
- 验证步骤之间的依赖关系

---

### 3. Skill 生成模块 (`SkillGenerator`)

```python
class SkillGenerator:
    """
    从零开始自动生成新 Skill
    """
    
    def design_blueprint(self, analysis: ProblemAnalysis, 
                        frameworks: List[Framework],
                        knowledge: List[KnowledgeSource]) -> SkillBlueprint:
        """
        设计 Skill 的蓝图
        
        Steps:
          1. 选择最适用的框架
          2. 从知识源中提取相关内容
          3. 定义输入输出
          4. 设计步骤流程
        """
        pass
    
    def generate(self, blueprint: SkillBlueprint) -> Skill:
        """
        根据蓝图生成 Skill
        
        Steps:
          1. 创建 Skill 对象
          2. 填充步骤信息
          3. 标记为 "auto-generated"
          4. 设置较低的初始置信度
        """
        pass
    
    def find_frameworks(self, analysis: ProblemAnalysis) -> List[Framework]:
        """
        找到适用的框架
        """
        pass
    
    def extract_knowledge(self, analysis: ProblemAnalysis) -> List[KnowledgeSource]:
        """
        从 LTM 中提取相关知识
        """
        pass
```

**实现要点**：
- 维护一个框架库（营销、编程、产品等）
- 从 LTM 中进行语义搜索
- 生成结构化的步骤

---

### 4. 质量评估模块 (`QualityEvaluator`)

```python
class QualityEvaluator:
    """
    评估 Skill 执行结果的质量
    """
    
    def evaluate(self, result: ExecutionResult, 
                problem: str) -> QualityScore:
        """
        评估结果质量
        
        Dimensions:
          - Completeness (30%): 结果是否完整
          - Accuracy (40%): 结果是否准确
          - Explainability (30%): 解释是否清晰
        
        Returns:
            QualityScore: 0-1 的评分
        """
        pass
    
    def evaluate_completeness(self, result: ExecutionResult, 
                            problem: str) -> float:
        """检查结果是否包含所有必要信息"""
        pass
    
    def evaluate_accuracy(self, result: ExecutionResult, 
                        problem: str) -> float:
        """检查结果的准确性（可能需要用户反馈）"""
        pass
    
    def evaluate_explainability(self, result: ExecutionResult) -> float:
        """检查结果的可解释性"""
        pass
```

**实现要点**：
- 定义清晰的评估标准
- 收集用户反馈来改进评估
- 考虑不同问题的特殊需求

---

## 与记忆系统的集成

### 集成点 1：搜索和回忆

```python
# 与 LTM 的集成
def query_ltm(keywords: List[str], max_results: int = 10):
    """
    查询长期记忆
    """
    memories = ltm_client.memory_recall(
        query=" ".join(keywords),
        max_results=max_results
    )
    return memories


# 与 KB 的集成
def query_kb(keywords: List[str], category: str = None):
    """
    查询知识库
    """
    skills = kb_client.kb_search(
        query=" ".join(keywords),
        category=category,
        top_k=5
    )
    return skills
```

### 集成点 2：保存和更新

```python
def save_new_skill_to_kb(skill: Skill):
    """
    将新生成的 Skill 保存到知识库
    """
    kb_client.kb_add(
        title=f"{skill.name} v{skill.version}",
        content=json.dumps(skill.to_dict()),
        category="auto-generated",
        tags=[skill.generation_info.domain, "skill"],
        confidence=skill.generation_info.confidence,
        confirmed=False  # 需要用户确认
    )


def record_skill_usage_to_ltm(skill: Skill, result: ExecutionResult):
    """
    记录 Skill 的使用情况到 LTM
    """
    ltm_client.memory_save(
        content=f"Used skill '{skill.name}' for problem. Success: {result.success}",
        category="project",
        tags=["skill-usage", skill.skill_id]
    )


def record_skill_update_to_ltm(skill_id: str, feedback: str):
    """
    记录 Skill 的更新到 LTM
    """
    ltm_client.memory_save(
        content=f"Skill '{skill_id}' updated based on feedback: {feedback}",
        category="project",
        tags=["skill-update", skill_id]
    )
```

---

## 数据流示例

### 场景 1：Layer 1 - 直接命中

```
用户: "制定营销预算方案"
  ↓
[分析] 搜索 KB: "营销预算"
  ↓
[匹配] 找到 "营销预算分配 Skill v2.1" (匹配度 95%)
  ↓
[执行] 调用这个 Skill
  ↓
[结果] 返回预算分配方案
  ↓
[记录] 记录使用到 Skill 的质量指标
```

### 场景 2：Layer 2 - 组合

```
用户: "针对 Z 世代制定营销策略"
  ↓
[分析] 分析问题:
  - 主题: 营销策略
  - 特殊: Z 世代
  - 复杂度: 中等
  ↓
[搜索 KB] 找不到直接匹配 ❌
  ↓
[搜索 LTM] 回忆相关讨论:
  - "Z 世代消费习惯分析" (相关度 0.8)
  - "营销策略通用框架" (相关度 0.9)
  - "数据分析方法论" (相关度 0.7)
  ↓
[组合] 组合成新 Skill:
  步骤 1: 分析 Z 世代特征 (来自 LTM)
  步骤 2: 应用营销框架 (来自 LTM)
  步骤 3: 验证数据 (来自 LTM)
  ↓
[执行] 用组合的 Skill 解决问题
  ↓
[评估] 质量评分: 0.82 (较好)
  ↓
[保存] 保存到 KB (标记为 composed)
  ↓
[记录] 记录组合过程到 LTM
```

### 场景 3：Layer 3 - 生成

```
用户: "进入火星采矿业，制定 5 年商业计划"
  ↓
[分析] 分析问题:
  - 主题: 商业计划
  - 领域: 火星采矿 (陌生领域)
  - 复杂度: 高
  - 置信度: 0.65 (信息不足)
  ↓
[搜索] Layer 1, 2 都失败 ❌
  ↓
[诊断] 可以尝试生成 ✓
  ↓
[框架] 找到适用的通用框架:
  - "商业计划制定框架"
  - "市场分析框架"
  - "风险管理框架"
  ↓
[知识] 从 LTM 提取相关知识:
  - 之前的商业计划讨论
  - 采矿业的相关知识
  - 太空探索的基本知识
  ↓
[生成] 生成新 Skill:
  - 名称: "火星采矿商业计划制定"
  - 版本: "1.0-beta"
  - 状态: "experimental"
  - 置信度: 0.65
  - 需要验证: True
  ↓
[执行] 用生成的 Skill 解决问题
  ↓
[评估] 质量评分: 0.72
  ↓
[反馈] 返回给用户，标记为需要验证
  返回消息: "这是基于现有知识生成的试验版，需要你的领域知识验证"
  ↓
[等待] 等待用户反馈...
  
【用户反馈后】
用户: "这个框架很好，但要加入火星特定的政策风险"
  ↓
[分析] 分析反馈
  ↓
[更新] 更新 Skill:
  - 添加"政策风险分析"步骤
  - 版本升到 "1.1"
  - 标记为 "verified"
  ↓
[保存] 保存到 KB (现在正式可用)
  ↓
[记录] 记录更新过程到 LTM
```

---

## 测试策略

### 单元测试

```python
# test_skill_executor.py
def test_skill_execution():
    """测试 Skill 执行"""
    skill = create_sample_skill()
    executor = SkillExecutor()
    result = executor.execute(skill, "test problem")
    
    assert result.success == True
    assert result.output is not None
    assert result.steps_completed == len(skill.steps)


# test_problem_analyzer.py
def test_problem_analysis():
    """测试问题分析"""
    analyzer = ProblemAnalyzer()
    analysis = analyzer.analyze("How to solve this?")
    
    assert analysis.title is not None
    assert 0 <= analysis.confidence_score <= 1


# test_quality_evaluator.py
def test_result_evaluation():
    """测试质量评估"""
    evaluator = QualityEvaluator()
    result = create_sample_result()
    quality = evaluator.evaluate(result, "test problem")
    
    assert 0 <= quality.score <= 1
    assert quality.completeness is not None
    assert quality.accuracy is not None
```

### 集成测试

```python
# test_system_integration.py
def test_layer_1_flow():
    """测试 Layer 1 流程"""
    system = AdaptiveSkillSystem(kb_mock, ltm_mock)
    response = system.solve("existing problem")
    
    assert response.layer == 1
    assert response.status == "success"


def test_layer_2_flow():
    """测试 Layer 2 流程"""
    system = AdaptiveSkillSystem(kb_mock, ltm_mock)
    response = system.solve("new problem that can be composed")
    
    assert response.layer == 2
    assert response.status == "success"


def test_layer_3_flow():
    """测试 Layer 3 流程"""
    system = AdaptiveSkillSystem(kb_mock, ltm_mock)
    response = system.solve("completely new problem")
    
    assert response.layer == 3
    assert response.status in ["success", "partial"]
```

### 用户验收测试

```
测试场景 1: 实际的营销问题
- 输入: 用户真实的营销预算问题
- 预期: Layer 1 直接命中，快速返回结果

测试场景 2: 新的领域组合
- 输入: 用户提出一个新的问题组合
- 预期: Layer 2 从记忆中组合出解决方案

测试场景 3: 完全陌生的问题
- 输入: 用户提出一个全新的问题
- 预期: Layer 3 生成试验版 Skill，请用户验证
```

---

## 部署指南

### 服务架构

```
┌─────────────────────┐
│   User Interface    │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   API Gateway       │
└──────────┬──────────┘
           │
┌──────────▼────────────────────────────────┐
│  Adaptive Skill System                     │
│  ├─ SkillExecutor                         │
│  ├─ SkillComposer                         │
│  ├─ SkillGenerator                        │
│  ├─ ProblemAnalyzer                       │
│  └─ QualityEvaluator                      │
└──────────┬─────────────┬────────────────┬─┘
           │             │                │
    ┌──────▼──┐  ┌──────▼──┐  ┌─────────▼─────┐
    │  KB     │  │  LTM    │  │  AI Model     │
    │ Service │  │ Service │  │  (for NLP)    │
    └─────────┘  └─────────┘  └───────────────┘
```

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0"]
```

### API 服务

```python
# api/main.py
from fastapi import FastAPI
from adaptive_skill_system import AdaptiveSkillSystem

app = FastAPI()
system = AdaptiveSkillSystem()

@app.post("/api/solve")
async def solve_problem(problem: str):
    response = system.solve(problem)
    return response.to_dict()

@app.get("/api/skills")
async def list_skills():
    # 返回所有可用的 Skill
    pass

@app.post("/api/skills/{skill_id}/feedback")
async def submit_feedback(skill_id: str, feedback: str):
    updated_skill = system.update_skill_from_feedback(skill_id, feedback)
    return updated_skill.to_dict()
```

---

## 下一步实现优先级

1. **高优先级**
   - [ ] 完成 `ProblemAnalyzer` 实现
   - [ ] 完成 `SkillExecutor` 的真实步骤执行
   - [ ] 与 KB/LTM 的完整集成

2. **中优先级**
   - [ ] 实现 `SkillComposer` 的组合逻辑
   - [ ] 建立通用框架库
   - [ ] API 服务部署

3. **低优先级**
   - [ ] 实现 `SkillGenerator` 的高级生成
   - [ ] Web UI 界面
   - [ ] 性能优化和缓存

---

**这个指南将根据实现过程持续更新。**
