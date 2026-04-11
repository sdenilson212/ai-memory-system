"""
调试 RollbackManager
"""
import sys
sys.path.insert(0, r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')

from dataclasses import dataclass, field
from typing import List, Dict
from core.rollback_manager import create_rollback_manager, SideEffect, SideEffectType, RollbackPriority


@dataclass
class TestSkill:
    skill_id: str
    version: str
    name: str
    description: str = ""
    steps: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "steps": self.steps
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            skill_id=data["skill_id"],
            version=data["version"],
            name=data["name"],
            description=data.get("description", ""),
            steps=data.get("steps", [])
        )


# 创建 Skill
skill = TestSkill(
    skill_id="test_skill",
    version="1.0",
    name="测试 Skill",
    steps=[]
)

print("初始状态:")
print(f"  version: {skill.version}")
print(f"  steps: {skill.steps}")
print(f"  id(skill): {id(skill)}")
print(f"  id(skill.steps): {id(skill.steps)}")

# 创建 RollbackManager
rm = create_rollback_manager()

# 创建 checkpoint
cp1 = rm.create_checkpoint(skill, "初始版本")
print(f"\n创建 checkpoint1: {cp1.checkpoint_id}")
print(f"  snapshot version: {cp1.skill_snapshot.get('version')}")
print(f"  snapshot steps: {cp1.skill_snapshot.get('steps')}")
print(f"  id(snapshot.steps): {id(cp1.skill_snapshot.get('steps'))}")

# 修改 Skill
skill.version = "1.1"
skill.steps.append({"step": 1, "name": "添加功能1"})

print("\n修改后状态:")
print(f"  version: {skill.version}")
print(f"  steps: {skill.steps}")
print(f"  id(skill): {id(skill)}")

# 创建新 checkpoint
cp2 = rm.create_checkpoint(skill, "添加功能1")
print(f"\n创建 checkpoint2: {cp2.checkpoint_id}")

# 回滚前状态
print(f"\n回滚前状态:")
print(f"  version: {skill.version}")
print(f"  steps: {skill.steps}")
print(f"  id(skill): {id(skill)}")

# 打开日志文件
log = open("rollback_debug.log", "w", encoding="utf-8")

# 检查 rollback_manager 的代码
log.write(f"检查 rollback_manager 模块路径:\n")
import core.rollback_manager as rm_module
log.write(f"  模块文件: {rm_module.__file__}\n")

# 回滚
log.write(f"\n回滚到 checkpoint1...\n")
log.write(f"  cp1.checkpoint_id: {cp1.checkpoint_id}\n")
log.write(f"  rm.checkpoints keys: {list(rm.checkpoints.keys())}\n")
log.flush()

result = rm.rollback(skill, target_checkpoint_id=cp1.checkpoint_id)
log.write(f"\n回滚完成\n")
log.write(f"  result: {result}\n")
log.flush()
log.close()

print(f"\n回滚结果: {result}")
print(f"  result['success']: {result.get('success')}")
print(f"  result['p0_rolled_back']: {result.get('p0_rolled_back')}")
print(f"\n回滚后状态:")
print(f"  version: {skill.version}")
print(f"  steps: {skill.steps}")
print(f"  id(skill): {id(skill)}")

# 验证
assert skill.version == "1.0", f"版本应为1.0，实际是{skill.version}"
assert skill.steps == [], f"步骤应为空，实际是{skill.steps}"
print("\n验证通过!")
