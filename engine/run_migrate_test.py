"""运行 migrate_weights 的 dry-run 测试，结果写入文件"""
import sys
import io
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 重定向输出到文件
output_file = Path(__file__).parent.parent / "migrate_test_output.txt"

# 捕获所有输出
old_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    from migrate_weights import run_migration, _print_result
    from config import MEMORY_DIR

    result = run_migration(
        memory_dir=Path(MEMORY_DIR),
        dry_run=True,
        force=False,
        show_stats=True,
    )
    _print_result(result)

    output = sys.stdout.getvalue()
except Exception as e:
    import traceback
    output = f"ERROR: {e}\n{traceback.format_exc()}"

sys.stdout = old_stdout

# 写文件
output_file.write_text(output, encoding="utf-8")
print(f"Output written to: {output_file}")
