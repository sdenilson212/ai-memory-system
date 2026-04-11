"""测试深拷贝"""
from dataclasses import dataclass, field
from typing import List, Dict
from core.rollback_manager import create_rollback_manager

@dataclass
class TestSkill:
    skill_id: str
    version: str
    name: str
    description: str = ''
    steps: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'skill_id': self.skill_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'steps': self.steps
        }

skill = TestSkill(skill_id='test', version='1.0', name='test')
rm = create_rollback_manager()
cp1 = rm.create_checkpoint(skill, '初始版本')
print(f'创建 cp1 后，cp1 snapshot version: {cp1.skill_snapshot["version"]}')
print(f'创建 cp1 后，cp1 snapshot steps: {cp1.skill_snapshot["steps"]}')

skill.version = '1.1'
skill.steps.append({'step': 1})
print(f'修改 skill 后，skill version: {skill.version}')
print(f'修改 skill 后，skill steps: {skill.steps}')
print(f'修改 skill 后，cp1 snapshot version: {cp1.skill_snapshot["version"]}')
print(f'修改 skill 后，cp1 snapshot steps: {cp1.skill_snapshot["steps"]}')

# 验证
if cp1.skill_snapshot["version"] == "1.0":
    print("SUCCESS: version 未被修改")
else:
    print("FAIL: version 被修改了")

if cp1.skill_snapshot["steps"] == []:
    print("SUCCESS: steps 未被修改")
else:
    print("FAIL: steps 被修改了")
