# 自适应 Skill 系统 — 完整架构设计

**版本**: v1.0-alpha  
**创建时间**: 2026-03-18  
**状态**: 设计阶段

---

## 📋 目录

1. [核心概念](#核心概念)
2. [系统架构](#系统架构)
3. [三层递进机制](#三层递进机制)
4. [自动生成流程](#自动生成流程)
5. [实现方案](#实现方案)
6. [API 设计](#api-设计)

---

## 核心概念

### Skill 是什么？

**Skill** = 可复用的问题解决方案

```
特征：
- 有明确的输入和输出
- 有步骤化的解决过程
- 可以被版本控制
- 可以被评分和优化
- 包含元信息（生成过程、可信度、更新历史）
```

### 三个关键角色

| 角色 | 职责 | 存储位置 |
|------|------|--------|
| **Skill** | 可执行的解决方案 | KB（知识库） |
| **Memory** | 学习的过程和历史 | LTM（长期记忆） |
| **System** | 连接两者的逻辑 | 运行时 |

---

## 系统架构

### 整体流程

```
┌─────────────────────────────────────┐
│         用户提出问题                 │
└────────────────┬────────────────────┘
                 ↓
        【第一步：诊断】
                 ↓
    ┌─────────────┬──────────────┐
    ↓             ↓              ↓
【有现成Skill】【能组合】【需要生成】
    ↓             ↓              ↓
  快速返回  中等延迟    自动生成+验证
    ↓             ↓              ↓
  └─────────┬─────────────┘
            ↓
      返回解决方案
            ↓
    【用户反馈/质疑】
            ↓
    更新Skill + 记录到LTM
```

### 数据模型

#### Skill 的完整结构

```json
{
  "skill_id": "skill-marketing-budget-2026-03-18",
  "name": "营销预算分配",
  "version": "2.1",
  "status": "active",
  
  "metadata": {
    "created_at": "2026-03-17T10:00:00Z",
    "updated_at": "2026-03-18T14:30:00Z",
    "created_by": "user|ai-generated",
    "update_reason": "用户反馈：缺少社交媒体预算考量"
  },
  
  "generation_info": {
    "type": "manual|composed|auto-generated",
    "base_skills": ["预算框架", "渠道优化"],
    "ltm_references": ["memory-id-001", "memory-id-002"],
    "confidence": 0.85
  },
  
  "content": {
    "description": "用于分配营销预算到不同渠道",
    "steps": [
      {
        "step": 1,
        "name": "明确营销目标",
        "description": "...",
        "source": "基础框架"
      },
      ...
    ],
    "required_inputs": ["总预算", "目标受众", "渠道列表"],
    "outputs": ["预算分配方案", "预期效果评估"],
    "parameters": {
      "industry": "string",
      "target_audience": "string",
      "channels": ["array"]
    }
  },
  
  "quality_metrics": {
    "usage_count": 127,
    "success_rate": 0.92,
    "user_satisfaction": 4.3,
    "failure_cases": 2,
    "last_challenged": "2026-03-18T09:15:00Z"
  },
  
  "versions": {
    "v2.0": {
      "timestamp": "2026-03-10",
      "changes": "Added social media budget consideration",
      "ltm_reference": "memory-id-456"
    },
    "v1.9": {...}
  }
}
```

---

## 三层递进机制

### 【第 1 层】直接调用已有 Skill

**触发条件**: 用户问题与已有 Skill 匹配度 > 90%

```python
def handle_layer_1(user_problem):
    # 搜索 KB
    skills = kb_search(user_problem, top_k=3)
    
    if skills and skills[0].match_score > 0.9:
        # 找到高度匹配的 Skill
        skill = skills[0]
        
        # 执行 Skill
        result = execute_skill(skill, user_problem)
        
        # 记录使用
        log_skill_usage(skill.id, user_problem)
        
        return result
    
    # 没有匹配的，进入第二层
    return None
```

**成本**: ⚡️ 最低  
**速度**: ⚡️⚡️⚡️ 最快 (< 1 秒)  
**可靠性**: ⭐️⭐️⭐️⭐️⭐️ 最高

---

### 【第 2 层】从记忆中组合新 Skill

**触发条件**: 找不到直接匹配，但找到相关信息可以组合

```python
def handle_layer_2(user_problem):
    # 第一步：分析问题
    problem_analysis = analyze_problem(user_problem)
    # 提取关键概念、领域、方法论等
    
    # 第二步：从 LTM 搜索相关信息
    memory_chunks = memory_recall(
        query=problem_analysis["keywords"],
        max_results=10
    )
    
    # 第三步：评估是否能组合
    if can_compose_skill(memory_chunks, problem_analysis):
        # 从记忆中提取关键步骤
        steps = extract_steps_from_memory(memory_chunks)
        
        # 组合成临时 Skill
        temp_skill = compose_skill(
            name=f"临时 Skill: {problem_analysis['title']}",
            steps=steps,
            ltm_references=memory_chunks,
            version="1.0-temp",
            status="composed"
        )
        
        # 执行这个临时 Skill
        result = execute_skill(temp_skill, user_problem)
        
        # 记录组合过程
        memory_save({
            "content": f"组合了新 Skill: {temp_skill.name}",
            "category": "project",
            "tags": ["skill-composition", user_problem.domain]
        })
        
        return result, temp_skill
    
    # 无法组合，进入第三层
    return None, None
```

**成本**: 💰 中等  
**速度**: ⚡️⚡️ 中等 (10-30 秒)  
**可靠性**: ⭐️⭐️⭐️⭐️ 较高

---

### 【第 3 层】自动生成新 Skill

**触发条件**: 前两层都失败，且问题有足够的信息可以推理

```python
def handle_layer_3(user_problem):
    # 第一步：问题诊断
    diagnosis = diagnose_problem(user_problem)
    
    # 检查是否有足够的信息来生成
    if not diagnosis.can_generate:
        return None, None, {
            "status": "cannot_handle",
            "reason": diagnosis.reason,
            "suggestion": "这个问题超出了我的能力范围。让我们一起思考..."
        }
    
    # 第二步：设计 Skill 结构
    skill_blueprint = design_skill_blueprint(
        problem_analysis=diagnosis,
        base_frameworks=find_applicable_frameworks(diagnosis),
        ltm_knowledge=extract_relevant_knowledge(diagnosis)
    )
    
    # 第三步：生成 Skill（标记为试验版）
    generated_skill = generate_skill(
        blueprint=skill_blueprint,
        name=diagnosis.title,
        version="1.0-beta",
        status="auto-generated",
        confidence=diagnosis.confidence_score,
        generation_info={
            "generated_at": now(),
            "base_frameworks": skill_blueprint.frameworks,
            "ltm_references": skill_blueprint.memory_sources,
            "needs_verification": True
        }
    )
    
    # 第四步：试用这个 Skill
    result = execute_skill(generated_skill, user_problem)
    
    # 第五步：评估结果质量
    quality = evaluate_result_quality(result, user_problem)
    
    if quality.score >= 0.75:
        # 效果不错，标记为可用
        generated_skill.status = "verified"
        
        # 保存到 KB
        kb_add(
            title=generated_skill.name,
            content=skill_to_json(generated_skill),
            category="auto-generated",
            tags=[diagnosis.domain, "auto-generated", diagnosis.keywords],
            confidence="medium",
            confirmed=False  # 等待用户确认
        )
    else:
        # 效果一般，标记为试验版，请用户反馈
        generated_skill.status = "experimental"
    
    # 记录生成过程
    memory_save({
        "content": f"自动生成了新 Skill: {generated_skill.name}",
        "category": "project",
        "tags": ["skill-generation", diagnosis.domain]
    })
    
    return result, generated_skill, {
        "status": "generated",
        "quality": quality.score,
        "needs_user_feedback": quality.score < 0.85
    }
```

**成本**: 💰💰💰 最高  
**速度**: ⚡️ 最慢 (1-5 分钟)  
**可靠性**: ⭐️⭐️⭐️ 中等（需要用户验证）

---

## 自动生成流程

### 流程 1：问题诊断

```python
def diagnose_problem(problem):
    """
    分析问题的特征，判断是否可以生成 Skill
    """
    analysis = {
        "title": extract_problem_title(problem),
        "domain": classify_domain(problem),
        "complexity": assess_complexity(problem),
        "keywords": extract_keywords(problem),
        "required_knowledge": identify_required_knowledge(problem),
        "applicable_frameworks": find_frameworks(problem),
        "confidence_score": calculate_confidence(problem),
        "can_generate": False,
        "reason": ""
    }
    
    # 判断是否可以生成
    if analysis["confidence_score"] >= 0.6:
        analysis["can_generate"] = True
    else:
        analysis["reason"] = "信息不足，无法生成可靠的 Skill"
    
    return analysis
```

### 流程 2：框架选择

```python
def find_applicable_frameworks(diagnosis):
    """
    从已有的框架中选择适用的
    """
    frameworks = []
    
    # 搜索 KB 中所有可用的框架
    all_frameworks = kb_search("framework", category="framework")
    
    for framework in all_frameworks:
        # 评估这个框架是否适用
        applicability = evaluate_applicability(
            framework=framework,
            diagnosis=diagnosis
        )
        
        if applicability > 0.5:
            frameworks.append({
                "framework": framework,
                "applicability": applicability
            })
    
    # 排序，返回最适用的
    return sorted(frameworks, key=lambda x: x["applicability"], reverse=True)
```

### 流程 3：从 LTM 提取知识

```python
def extract_relevant_knowledge(diagnosis):
    """
    从 LTM 中提取与问题相关的知识片段
    """
    knowledge_sources = []
    
    # 搜索相关的讨论记录
    memories = memory_recall(
        query=diagnosis["keywords"],
        max_results=20
    )
    
    for memory in memories:
        # 评估这条记忆的相关性
        relevance = evaluate_relevance(memory, diagnosis)
        
        if relevance > 0.5:
            knowledge_sources.append({
                "memory": memory,
                "relevance": relevance,
                "applicable_parts": extract_applicable_parts(memory, diagnosis)
            })
    
    return sorted(knowledge_sources, key=lambda x: x["relevance"], reverse=True)
```

### 流程 4：Skill 设计

```python
def design_skill_blueprint(problem_analysis, base_frameworks, ltm_knowledge):
    """
    基于分析结果设计 Skill 的蓝图
    """
    blueprint = {
        "name": problem_analysis["title"],
        "domain": problem_analysis["domain"],
        "complexity": problem_analysis["complexity"],
        
        # 步骤设计
        "steps": design_steps(
            frameworks=base_frameworks,
            knowledge=ltm_knowledge,
            analysis=problem_analysis
        ),
        
        # 输入/输出定义
        "inputs": identify_inputs(problem_analysis),
        "outputs": identify_outputs(problem_analysis),
        
        # 元信息
        "frameworks": [f["framework"].name for f in base_frameworks],
        "memory_sources": [k["memory"].id for k in ltm_knowledge],
        
        # 质量指标
        "expected_quality": estimate_quality(base_frameworks, ltm_knowledge)
    }
    
    return blueprint
```

### 流程 5：结果评估

```python
def evaluate_result_quality(result, original_problem):
    """
    评估自动生成的 Skill 的效果质量
    """
    quality = {
        "score": 0,
        "reasons": [],
        "recommendations": []
    }
    
    # 评估维度 1：完整性
    completeness = evaluate_completeness(result, original_problem)
    quality["score"] += completeness * 0.3
    if completeness < 0.7:
        quality["reasons"].append("结果不够完整")
    
    # 评估维度 2：准确性
    accuracy = evaluate_accuracy(result, original_problem)
    quality["score"] += accuracy * 0.4
    if accuracy < 0.7:
        quality["reasons"].append("可能存在错误")
    
    # 评估维度 3：可解释性
    explainability = evaluate_explainability(result)
    quality["score"] += explainability * 0.3
    if explainability < 0.7:
        quality["reasons"].append("解释不清楚")
    
    return quality
```

---

## 实现方案

### 核心模块

```
adaptive_skill_system/
├── core/
│   ├── skill_executor.py      # Skill 执行引擎
│   ├── skill_composer.py      # Skill 组合引擎
│   ├── skill_generator.py     # Skill 自动生成引擎
│   ├── problem_analyzer.py    # 问题诊断引擎
│   └── quality_evaluator.py   # 质量评估引擎
│
├── integrations/
│   ├── kb_integration.py      # 与知识库的集成
│   ├── ltm_integration.py     # 与长期记忆的集成
│   └── api_client.py          # AI 服务客户端
│
├── models/
│   ├── skill_model.py         # Skill 数据模型
│   ├── result_model.py        # 结果数据模型
│   └── metadata_model.py      # 元数据模型
│
└── utils/
    ├── framework_loader.py    # 加载通用框架
    ├── keyword_extractor.py   # 关键词提取
    └── logger.py              # 日志记录
```

### 关键接口

```python
class AdaptiveSkillSystem:
    """
    自适应 Skill 系统的主类
    """
    
    def __init__(self, kb_client, ltm_client):
        self.kb = kb_client          # 知识库客户端
        self.ltm = ltm_client        # 长期记忆客户端
        self.executor = SkillExecutor()
        self.composer = SkillComposer()
        self.generator = SkillGenerator()
        self.analyzer = ProblemAnalyzer()
        self.evaluator = QualityEvaluator()
    
    def solve(self, problem, verbose=False):
        """
        主入口：尝试解决用户的问题
        
        Returns:
            {
                "result": 解决方案,
                "skill_used": 使用的 Skill 信息,
                "layer": 使用的层级 (1/2/3),
                "status": "success" | "partial" | "failed",
                "confidence": 置信度 (0-1),
                "metadata": 元数据
            }
        """
        
        # 第一层：直接调用
        result_1, skill_1 = self._try_layer_1(problem)
        if result_1:
            return self._format_response(
                result=result_1,
                skill=skill_1,
                layer=1,
                status="success"
            )
        
        # 第二层：组合
        result_2, skill_2 = self._try_layer_2(problem)
        if result_2:
            return self._format_response(
                result=result_2,
                skill=skill_2,
                layer=2,
                status="success"
            )
        
        # 第三层：自动生成
        result_3, skill_3, gen_info = self._try_layer_3(problem)
        if result_3:
            return self._format_response(
                result=result_3,
                skill=skill_3,
                layer=3,
                status="success" if gen_info["quality"] >= 0.75 else "partial",
                generation_info=gen_info
            )
        
        # 都失败了
        return self._format_response(
            result=None,
            skill=None,
            layer=0,
            status="failed",
            reason="无法解决这个问题"
        )
    
    def _try_layer_1(self, problem):
        """第一层：直接调用"""
        skills = self.kb.search(problem, top_k=3)
        if skills and skills[0].match_score > 0.9:
            result = self.executor.execute(skills[0], problem)
            return result, skills[0]
        return None, None
    
    def _try_layer_2(self, problem):
        """第二层：组合"""
        analysis = self.analyzer.analyze(problem)
        memories = self.ltm.recall(analysis.keywords, max_results=10)
        
        if self.composer.can_compose(memories, analysis):
            skill = self.composer.compose(memories, analysis)
            result = self.executor.execute(skill, problem)
            return result, skill
        return None, None
    
    def _try_layer_3(self, problem):
        """第三层：自动生成"""
        analysis = self.analyzer.analyze(problem)
        
        if not analysis.can_generate:
            return None, None, None
        
        frameworks = self._find_frameworks(analysis)
        knowledge = self._extract_knowledge(analysis)
        blueprint = self.generator.design_blueprint(
            analysis, frameworks, knowledge
        )
        
        skill = self.generator.generate(blueprint)
        result = self.executor.execute(skill, problem)
        
        quality = self.evaluator.evaluate(result, problem)
        
        if quality.score >= 0.75:
            self.kb.add(skill)  # 保存到知识库
        
        self.ltm.save({
            "content": f"Auto-generated skill: {skill.name}",
            "category": "project",
            "tags": ["skill-generation"]
        })
        
        return result, skill, {
            "status": "generated",
            "quality": quality.score,
            "needs_feedback": quality.score < 0.85
        }
    
    def update_skill_from_feedback(self, skill_id, user_feedback):
        """
        根据用户反馈更新 Skill
        """
        skill = self.kb.get(skill_id)
        
        # 理解反馈内容
        feedback_analysis = self.analyzer.analyze_feedback(user_feedback)
        
        # 更新 Skill
        updated_skill = self._update_skill(skill, feedback_analysis)
        
        # 保存到知识库
        self.kb.update(skill_id, updated_skill)
        
        # 记录到 LTM
        self.ltm.save({
            "content": f"Skill {skill.name} updated based on user feedback",
            "category": "project",
            "tags": ["skill-update", feedback_analysis.aspect]
        })
        
        return updated_skill
```

---

## API 设计

### REST API 端点

```
POST /api/solve
  Input: { "problem": "...", "verbose": true/false }
  Output: { "result": {...}, "layer": 1|2|3, "status": "success"|"partial"|"failed" }

POST /api/skills
  Input: { "name": "...", "content": "...", "version": "..." }
  Output: { "skill_id": "...", "status": "created" }

GET /api/skills/:skill_id
  Output: { Skill 对象 }

PUT /api/skills/:skill_id
  Input: { "updates": {...} }
  Output: { "status": "updated" }

POST /api/skills/:skill_id/feedback
  Input: { "feedback": "...", "rating": 1-5 }
  Output: { "status": "recorded", "updated_skill": {...} }

GET /api/skills?domain=marketing&top_k=10
  Output: [Skill 列表]

GET /api/stats
  Output: { "total_skills": 123, "avg_quality": 0.87, "recently_updated": [...] }
```

---

## 下一步

- [ ] 实现 `SkillExecutor` 执行引擎
- [ ] 实现 `SkillComposer` 组合引擎
- [ ] 实现 `SkillGenerator` 生成引擎
- [ ] 实现 `ProblemAnalyzer` 问题诊断
- [ ] 实现 `QualityEvaluator` 质量评估
- [ ] 建立通用框架库
- [ ] 编写单元测试
- [ ] 部署 API 服务
- [ ] 构建 Web UI
- [ ] 收集真实用户反馈

---

**这个文档将持续更新，记录系统的演进过程。**
