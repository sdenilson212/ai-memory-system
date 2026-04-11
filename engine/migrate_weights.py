"""
migrate_weights.py — Memory Weight 迁移工具 (v1.5.0)
=====================================================

为现有记忆条目自动分配权重，基于 MemoryWeight.auto_suggest_weight() 规则。

功能：
  1. 扫描所有现有 LTM 条目
  2. 用 auto_suggest_weight() 对每条内容建议权重
  3. 批量写入 weights.json（已有手动权重的条目不覆盖）
  4. 输出统计报告

使用方式:
  python migrate_weights.py                    # 默认 MEMORY_DIR
  python migrate_weights.py --dry-run          # 只预览，不写入
  python migrate_weights.py --force            # 强制覆盖已有权重
  python migrate_weights.py --show-stats       # 迁移后显示权重统计

示例:
  python engine/migrate_weights.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# ── Path bootstrap ──────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config import MEMORY_DIR
from core.ltm import LTMManager, VALID_CATEGORIES
from core.weight import MemoryWeight


def run_migration(
    memory_dir: Path,
    dry_run: bool = False,
    force: bool = False,
    show_stats: bool = False,
) -> dict:
    """
    核心迁移逻辑。

    Args:
        memory_dir: 记忆库目录
        dry_run:    只预览，不写入
        force:      强制覆盖已有权重（默认跳过已设权重条目）
        show_stats: 迁移后打印统计信息

    Returns:
        迁移结果统计字典
    """
    ltm = LTMManager(memory_dir)
    mw = MemoryWeight(memory_dir)

    # 加载所有条目
    all_entries = ltm.list_all(limit=10000)
    total = len(all_entries)

    if total == 0:
        return {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "skipped_reason": "no_entries",
            "weight_distribution": {},
        }

    # 统计
    migrated = 0
    skipped_existing = 0
    weight_dist: Counter[int] = Counter()
    new_weight_map: dict[str, int] = {}

    for entry in all_entries:
        already_set = entry.id in mw.weights  # weights.json 中已有记录

        if already_set and not force:
            # 保留已有手动权重
            existing_w = mw.get_weight(entry.id)
            weight_dist[existing_w] += 1
            skipped_existing += 1
            continue

        # 根据内容 + 分类自动建议权重
        suggested = mw.auto_suggest_weight(entry.content, entry.category)
        new_weight_map[entry.id] = suggested
        weight_dist[suggested] += 1
        migrated += 1

    if not dry_run and new_weight_map:
        mw.bulk_set_weights(new_weight_map)

    result = {
        "total": total,
        "migrated": migrated,
        "skipped_existing": skipped_existing,
        "dry_run": dry_run,
        "force": force,
        "weight_distribution": {
            f"{k} ({MemoryWeight.WEIGHT_NAMES[k]})": v
            for k, v in sorted(weight_dist.items())
        },
    }

    if show_stats:
        full_stats = mw.get_statistics() if not dry_run else {}
        result["post_migration_stats"] = full_stats

    return result


def _print_result(result: dict) -> None:
    """格式化打印迁移结果"""
    print("\n" + "=" * 50)
    print("  Memory Weight 迁移报告")
    print("=" * 50)

    if result.get("dry_run"):
        print("  [DRY RUN 模式 — 未实际写入]")

    print(f"  总条目数     : {result['total']}")
    print(f"  已迁移       : {result['migrated']}")
    print(f"  跳过（已有权重）: {result.get('skipped_existing', 0)}")

    print("\n  权重分布：")
    for label, count in result.get("weight_distribution", {}).items():
        bar = "█" * min(count, 40)
        print(f"    {label:20s} | {bar} {count}")

    if result.get("post_migration_stats"):
        stats = result["post_migration_stats"]
        print(f"\n  迁移后统计：")
        print(f"    总权重条目   : {stats.get('total_entries', 0)}")
        print(f"    平均权重值   : {stats.get('average_weight', 0):.2f}")

    print("=" * 50)

    if result.get("dry_run"):
        print("  提示：加 --no-dry-run 或去掉 --dry-run 执行实际迁移")
    elif result["migrated"] > 0:
        print(f"  ✓ 成功为 {result['migrated']} 条记忆写入权重")
    else:
        print("  没有新条目需要迁移")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="为现有 LTM 条目批量分配权重（v1.5.0 迁移工具）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python migrate_weights.py                    # 迁移（跳过已有权重）
  python migrate_weights.py --dry-run          # 预览，不写入
  python migrate_weights.py --force            # 强制覆盖所有权重
  python migrate_weights.py --show-stats       # 显示迁移后统计
  python migrate_weights.py --memory-dir /custom/path
""",
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=Path(MEMORY_DIR),
        help=f"记忆库目录（默认: {MEMORY_DIR}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="预览模式：只显示将要做什么，不实际写入",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="强制模式：覆盖已有手动权重（谨慎使用）",
    )
    parser.add_argument(
        "--show-stats",
        action="store_true",
        default=False,
        help="迁移后显示完整统计信息",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="以 JSON 格式输出结果（适合脚本调用）",
    )

    args = parser.parse_args()

    memory_dir = args.memory_dir
    if not memory_dir.exists():
        print(f"错误：记忆库目录不存在：{memory_dir}", file=sys.stderr)
        sys.exit(1)

    result = run_migration(
        memory_dir=memory_dir,
        dry_run=args.dry_run,
        force=args.force,
        show_stats=args.show_stats,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_result(result)


if __name__ == "__main__":
    main()
