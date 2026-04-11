"""
版本 DAG 功能测试
[P3-01 修复] 直接使用真实 AdaptiveSkillSystem，而非复制其内部逻辑，
确保测试路径与生产路径一致，主文件改动后测试自动跟进。
"""

import sys
import os
from datetime import datetime

# 直接 import 源文件（绕过包导入）
sys.path.insert(0, os.path.dirname(__file__))

from adaptive_skill_system import (
    AdaptiveSkillSystem,
    Skill,
    SkillStep,
    SkillMetadata,
    SkillStatus,
    SkillType,
    GenerationInfo,
    QualityMetrics,
    ExecutionResult,
    EvolutionType,
)


# ─────────────────────────────────────────────
# 使用真实 AdaptiveSkillSystem（kb=None, ltm=None）
# ─────────────────────────────────────────────

def make_system() -> AdaptiveSkillSystem:
    """
    [P3-01] 创建一个不依赖 KB/LTM 的系统实例，直接使用真实生产类。
    传入 kb_client/ltm_client 占位对象以绕过自动路径检测和相对导入。
    """
    # 用一个最简 Stub 对象代替真实客户端，避免相对导入和网络依赖
    class _NullClient:
        def search(self, *a, **kw): return []
        def get(self, *a, **kw): return None
        def save(self, *a, **kw): return None
        def update(self, *a, **kw): return None

    sys = AdaptiveSkillSystem(kb_client=_NullClient(), ltm_client=_NullClient())
    return sys




# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def make_skill(skill_id="test-001", name="测试Skill", version="1.0") -> Skill:
    return Skill(
        skill_id=skill_id, name=name,
        description="用于单元测试的 Skill",
        version=version, status=SkillStatus.ACTIVE,
        steps=[
            SkillStep(1, "步骤A", "分析问题", "框架"),
            SkillStep(2, "步骤B", "制定方案", "记忆"),
            SkillStep(3, "步骤C", "执行方案", "框架"),
        ],
        required_inputs=["问题描述"], outputs=["解决方案"], parameters={},
        metadata=SkillMetadata(created_at=datetime.now(),
                               updated_at=datetime.now(), created_by="test"),
        generation_info=GenerationInfo(skill_type=SkillType.MANUAL),
        quality_metrics=QualityMetrics(usage_count=2, success_rate=0.60),
    )


PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def test(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    if not condition:
        print(f"  {status}  {name}" + (f"\n         → {detail}" if detail else ""))
    else:
        print(f"  {status}  {name}")


# ─────────────────────────────────────────────
# TEST 1: FIX 进化
# ─────────────────────────────────────────────
print("\n=== TEST 1: FIX 进化 ===")
skill = make_skill()
sys1 = make_system()
sys1.skills_cache["test-001"] = skill

updated = sys1.evolve_fix("test-001", "步骤B超时", "拆分步骤B为B1和B2")

test("FIX: 返回非空", updated is not None)
test("FIX: 版本号递增到 1.1", updated.version == "1.1", f"实际: {updated.version}")
test("FIX: derived_from == 1.0", updated.derived_from == "1.0", f"实际: {updated.derived_from}")
test("FIX: version_dag 含新节点 1.1", "1.1" in updated.version_dag)
test("FIX: version_dag 含根节点 1.0", "1.0" in updated.version_dag)
test("FIX: 进化类型 == fix",
     updated.version_dag["1.1"]["evolution_type"] == "fix",
     f"实际: {updated.version_dag['1.1'].get('evolution_type')}")
test("FIX: versions 旧格式含步骤快照",
     "1.0" in updated.versions and "steps_snapshot" in updated.versions["1.0"])

# ─────────────────────────────────────────────
# TEST 2: DERIVED 进化
# ─────────────────────────────────────────────
print("\n=== TEST 2: DERIVED 进化 ===")
skill2 = make_skill("test-002", version="2.0")
skill2.quality_metrics.success_rate = 0.80
sys2 = make_system()
sys2.skills_cache["test-002"] = skill2

derived = sys2.evolve_derived("test-002", "新增英文问题支持")

test("DERIVED: 返回非空", derived is not None)
test("DERIVED: 版本 2.1", derived.version == "2.1")
test("DERIVED: 进化类型 == derived",
     derived.version_dag["2.1"]["evolution_type"] == "derived")
test("DERIVED: derived_from == 2.0", derived.derived_from == "2.0")

# ─────────────────────────────────────────────
# TEST 3: CAPTURED 进化
# ─────────────────────────────────────────────
print("\n=== TEST 3: CAPTURED 进化 ===")
skill3 = make_skill("test-003")
skill3.quality_metrics.success_rate = 0.90
sys3 = make_system()
sys3.skills_cache["test-003"] = skill3

captured = sys3.evolve_captured("test-003", "三步法在营销问题稳定有效", quality_score=0.90)

test("CAPTURED: 返回非空", captured is not None)
test("CAPTURED: 版本 1.1", captured.version == "1.1")
test("CAPTURED: 进化类型 == captured",
     captured.version_dag["1.1"]["evolution_type"] == "captured")
test("CAPTURED: quality_after == 0.90",
     captured.version_dag["1.1"]["quality_after"] == 0.90)

# ─────────────────────────────────────────────
# TEST 4: 多次进化链 1.0 → 1.1 → 1.2
# ─────────────────────────────────────────────
print("\n=== TEST 4: 多次进化链 ===")
skill4 = make_skill("test-004")
sys4 = make_system()
sys4.skills_cache["test-004"] = skill4

v1 = sys4.evolve_fix("test-004", "err", "fix step A")
sys4.skills_cache["test-004"] = v1
v2 = sys4.evolve_derived("test-004", "extend EN")
sys4.skills_cache["test-004"] = v2

chain = v2.get_evolution_chain()
test("链长度 == 3", len(chain) == 3, f"实际: {chain}")
test("链顺序 1.0→1.1→1.2", chain == ["1.0", "1.1", "1.2"], f"实际: {chain}")
test("当前 derived_from == 1.1", v2.derived_from == "1.1")

# ─────────────────────────────────────────────
# TEST 5: rollback_to
# ─────────────────────────────────────────────
print("\n=== TEST 5: rollback_to ===")
skill5 = make_skill("test-005")
sys5 = make_system()
sys5.skills_cache["test-005"] = skill5
v1r = sys5.evolve_fix("test-005", "err", "fix")
sys5.skills_cache["test-005"] = v1r

ok = v1r.rollback_to("1.0")
test("rollback 已存在版本 → True", ok)
test("rollback 后 version == 1.0", v1r.version == "1.0")

ok_fail = v1r.rollback_to("9.9")
test("rollback 不存在版本 → False", not ok_fail)

# ─────────────────────────────────────────────
# TEST 6: diff_summary 字段类型
# ─────────────────────────────────────────────
print("\n=== TEST 6: diff_summary ===")
skill6 = make_skill("test-006")
sys6 = make_system()
sys6.skills_cache["test-006"] = skill6

v1d = sys6.evolve_fix("test-006", "step err", "fix step")
diff = v1d.version_dag["1.1"].get("diff_summary", None)
test("diff_summary 字段存在", diff is not None)
test("diff_summary 是 list", isinstance(diff, list))

# ─────────────────────────────────────────────
# TEST 7: post_execution_analyze
# ─────────────────────────────────────────────
print("\n=== TEST 7: post_execution_analyze ===")
skill7 = make_skill("test-007")
skill7.quality_metrics.success_rate = 0.55
skill7.quality_metrics.usage_count = 1
sys7 = make_system()

# A: 执行失败 → fix
fail_result = ExecutionResult(
    success=False, output=None,
    duration_seconds=1.0, steps_completed=1, total_steps=3,
    error_message="step B timeout"
)
s_fail = sys7.post_execution_analyze(skill7, fail_result, "分析营销策略")
test("失败 → action=fix", s_fail["action"] == "fix", f"实际: {s_fail}")
test("FIX 不自动应用", s_fail["auto_apply"] == False)

# B: 高质量多次 → captured
skill7.quality_metrics.success_rate = 0.88
skill7.quality_metrics.usage_count = 4
ok_result = ExecutionResult(
    success=True, output={"r": "ok"},
    duration_seconds=1.0, steps_completed=3, total_steps=3
)
s_cap = sys7.post_execution_analyze(skill7, ok_result, "分析营销策略")
test("高质量 → action=captured", s_cap["action"] == "captured", f"实际: {s_cap}")
test("CAPTURED 自动应用", s_cap.get("auto_apply") == True)

# C: 成熟 → derived
skill7.quality_metrics.usage_count = 7
skill7.quality_metrics.success_rate = 0.75
s_der = sys7.post_execution_analyze(skill7, ok_result, "营销策略扩展")
test("成熟 → derived 或 captured",
     s_der["action"] in ("derived", "captured"),
     f"实际: {s_der}")

# ─────────────────────────────────────────────
# TEST 8: get_skill_evolution_report
# ─────────────────────────────────────────────
print("\n=== TEST 8: 进化报告 ===")
skill8 = make_skill("test-008")
sys8 = make_system()
sys8.skills_cache["test-008"] = skill8

va = sys8.evolve_fix("test-008", "err", "fix1")
sys8.skills_cache["test-008"] = va
vb = sys8.evolve_derived("test-008", "enhance")
sys8.skills_cache["test-008"] = vb

report = sys8.get_skill_evolution_report("test-008")
test("报告非空", report is not None)
test("含 evolution_chain", "evolution_chain" in report)
test("stats.total_evolutions == 2",
     report["stats"]["total_evolutions"] == 2, f"实际: {report['stats']}")
test("stats.fix == 1", report["stats"]["fix"] == 1)
test("stats.derived == 1", report["stats"]["derived"] == 1)

# ─────────────────────────────────────────────
# 汇总
# ─────────────────────────────────────────────
print("\n" + "=" * 50)
passed = sum(1 for _, s, _ in results if s == PASS)
total = len(results)
print(f"测试结果：{passed}/{total} 通过")
if passed == total:
    print("ALL PASSED! Version DAG works correctly.")
else:
    print(f"⚠️ {total - passed} 项失败：")
    for name, status, detail in results:
        if status == FAIL:
            print(f"  {FAIL}  {name}" + (f"  [{detail}]" if detail else ""))
