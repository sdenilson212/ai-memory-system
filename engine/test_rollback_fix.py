"""测试回滚修复"""
import sys
# 重定向输出到文件
sys.stdout = open('test_rollback_fix.log', 'w', encoding='utf-8')

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

# 测试完整回滚流程
skill = TestSkill(skill_id='test', version='1.0', name='test')
rm = create_rollback_manager()

# 创建 checkpoint1
cp1 = rm.create_checkpoint(skill, '初始版本')
print(f'创建 cp1: version={cp1.skill_snapshot["version"]}')

# 修改 skill
skill.version = '1.1'
skill.steps.append({'step': 1})
print(f'修改后: skill.version={skill.version}')

# 创建 checkpoint2
cp2 = rm.create_checkpoint(skill, '修改后')
print(f'创建 cp2: version={cp2.skill_snapshot["version"]}')

# 检查 cp1 的 snapshot
print(f'回滚前 cp1 snapshot: version={cp1.skill_snapshot["version"]}, steps={cp1.skill_snapshot["steps"]}')

# 回滚到 cp1
result = rm.rollback(skill, target_checkpoint_id=cp1.checkpoint_id)
print(f'回滚结果: {result}')
print(f'回滚后: skill.version={skill.version}')
print(f'回滚后 cp1 snapshot: version={cp1.skill_snapshot["version"]}, steps={cp1.skill_snapshot["steps"]}')

# 验证
assert skill.version == '1.0', f'版本应为1.0，实际是{skill.version}'
print('SUCCESS: 回滚测试通过')
