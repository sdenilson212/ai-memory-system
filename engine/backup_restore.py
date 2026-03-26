#!/usr/bin/env python3
"""
Backup & Restore — 备份恢复工具
自动化备份和一键恢复功能
版本: 1.0
"""

import shutil
import json
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """备份管理器"""
    
    def __init__(self, memory_dir: str, backup_dir: Optional[str] = None):
        self.memory_dir = Path(memory_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else self.memory_dir.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 排除模式
        self.exclude_patterns = ["encrypted.json", "*.pyc", "__pycache__", ".git", "*.log", "*.tmp"]
    
    def _should_exclude(self, path: Path) -> bool:
        """检查文件/目录是否应被排除"""
        for pattern in self.exclude_patterns:
            if pattern.startswith("*."):
                if path.name.endswith(pattern[1:]):
                    return True
            elif path.name == pattern:
                return True
            elif pattern in str(path):
                return True
        return False
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        创建备份
        
        Args:
            backup_name: 备份名称，如果为 None 则使用时间戳
            
        Returns:
            备份路径
        """
        if not self.memory_dir.exists():
            raise FileNotFoundError(f"源目录不存在: {self.memory_dir}")
        
        # 生成备份文件名
        if backup_name:
            backup_folder_name = backup_name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder_name = f"backup_{timestamp}"
        
        backup_path = self.backup_dir / backup_folder_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始备份: {self.memory_dir} -> {backup_path}")
        
        # 复制文件
        copied_files = []
        for item in self.memory_dir.rglob("*"):
            # 检查排除
            if self._should_exclude(item):
                continue
            
            # 计算相对路径
            rel_path = item.relative_to(self.memory_dir)
            dest_path = backup_path / rel_path
            
            try:
                if item.is_dir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                else:
                    # 确保父目录存在
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
                    copied_files.append(rel_path.as_posix())
            except Exception as e:
                logger.warning(f"复制失败 {item}: {e}")
        
        # 保存备份元数据
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "source": str(self.memory_dir),
            "backup_name": backup_folder_name,
            "files": copied_files,
            "file_count": len(copied_files),
            "total_size": sum((backup_path / f).stat().st_size for f in copied_files if (backup_path / f).exists()),
            "created_by": "ai-memory-system-backup"
        }
        
        meta_file = backup_path / "backup_meta.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"备份完成: {backup_path} (文件数: {len(copied_files)})")
        return str(backup_path)
    
    def restore_backup(self, backup_name: str, target_dir: Optional[str] = None, confirm: bool = True) -> bool:
        """
        恢复备份
        
        Args:
            backup_name: 备份名称
            target_dir: 目标目录，如果为 None 则恢复到源目录
            confirm: 是否需要用户确认
            
        Returns:
            是否恢复成功
        """
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"备份不存在: {backup_path}")
        
        target_path = Path(target_dir) if target_dir else self.memory_dir
        
        # 读取备份元数据
        meta_file = backup_path / "backup_meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"备份元数据不存在: {meta_file}")
        
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"备份信息:")
        print(f"  名称: {metadata['backup_name']}")
        print(f"  时间: {metadata['timestamp']}")
        print(f"  文件数: {metadata['file_count']}")
        print(f"  大小: {metadata.get('total_size', 0) / 1024:.1f} KB")
        
        if confirm:
            response = input(f"\n确认恢复到 {target_path}? (yes/no): ").strip().lower()
            if response != 'yes':
                print("恢复已取消")
                return False
        
        # 备份当前数据（如果目标目录存在）
        if target_path.exists():
            current_backup_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            current_backup_path = self.backup_dir / current_backup_name
            
            logger.info(f"备份当前数据到: {current_backup_path}")
            try:
                current_backup_path.mkdir(exist_ok=True)
                for item in target_path.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, current_backup_path / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, current_backup_path / item.name)
                print(f"当前数据已备份到: {current_backup_path}")
            except Exception as e:
                logger.error(f"备份当前数据失败: {e}")
                print(f"警告: 无法备份当前数据，但将继续恢复...")
        
        # 执行恢复
        logger.info(f"开始恢复: {backup_path} -> {target_path}")
        
        try:
            # 先清空目标目录（排除备份元数据）
            for item in target_path.iterdir():
                if item.name == "backup_meta.json":
                    continue
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    logger.warning(f"删除 {item} 失败: {e}")
            
            # 复制备份文件
            restored_files = 0
            for rel_path_str in metadata["files"]:
                rel_path = Path(rel_path_str)
                src_file = backup_path / rel_path
                dest_file = target_path / rel_path
                
                if not src_file.exists():
                    logger.warning(f"源文件不存在: {src_file}")
                    continue
                
                # 确保目标目录存在
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                shutil.copy2(src_file, dest_file)
                restored_files += 1
            
            logger.info(f"恢复完成: {restored_files} 个文件已恢复")
            print(f"恢复成功！恢复了 {restored_files} 个文件到 {target_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"恢复失败: {e}")
            print(f"恢复失败: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for folder in sorted(self.backup_dir.iterdir(), reverse=True):
            if not folder.is_dir():
                continue
            
            meta_file = folder / "backup_meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    # 计算文件夹大小
                    total_size = 0
                    try:
                        total_size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
                    except Exception as e:
                        logger.debug(f"计算备份文件夹大小失败 {folder.name}: {e}")
                    
                    backups.append({
                        "name": folder.name,
                        "timestamp": meta.get("timestamp", "未知"),
                        "file_count": meta.get("file_count", 0),
                        "total_size": total_size,
                        "source": meta.get("source", "未知"),
                        "path": str(folder)
                    })
                except Exception as e:
                    logger.warning(f"读取备份元数据失败 {folder}: {e}")
        
        return backups
    
    def delete_backup(self, backup_name: str, confirm: bool = True) -> bool:
        """删除备份"""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"备份不存在: {backup_path}")
        
        if confirm:
            response = input(f"确认删除备份 '{backup_name}'? (yes/no): ").strip().lower()
            if response != 'yes':
                print("删除已取消")
                return False
        
        try:
            shutil.rmtree(backup_path)
            logger.info(f"已删除备份: {backup_path}")
            print(f"备份 '{backup_name}' 已删除")
            return True
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            print(f"删除失败: {e}")
            return False
    
    def cleanup_old_backups(self, keep_days: int = 30, keep_count: int = 10) -> int:
        """
        清理旧备份
        
        Args:
            keep_days: 保留天数
            keep_count: 至少保留的数量
            
        Returns:
            删除的备份数量
        """
        backups = self.list_backups()
        if len(backups) <= keep_count:
            return 0
        
        # 按时间排序
        backups_sorted = sorted(backups, key=lambda x: x["timestamp"], reverse=True)
        
        # 保留最新的 keep_count 个
        to_keep = backups_sorted[:keep_count]
        
        # 再按时间筛选（保留指定天数内的）
        current_time = datetime.now()
        cutoff_time = None
        
        if keep_days > 0:
            cutoff_time = current_time.timestamp() - (keep_days * 24 * 3600)
        
        deleted_count = 0
        
        for backup in backups_sorted[keep_count:]:
            # 检查是否在保留天数内
            if cutoff_time:
                try:
                    backup_time = datetime.fromisoformat(backup["timestamp"]).timestamp()
                    if backup_time > cutoff_time:
                        continue  # 还在保留期内
                except Exception as e:
                    logger.debug(f"解析备份时间戳失败 {backup.get('name', '?')}: {e}")
            
            # 删除
            try:
                backup_path = Path(backup["path"])
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                    logger.info(f"清理旧备份: {backup['name']}")
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"删除旧备份失败 {backup['name']}: {e}")
        
        logger.info(f"清理完成: 删除了 {deleted_count} 个旧备份")
        return deleted_count


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="AI Memory System 备份恢复工具")
    parser.add_argument("--memory-dir", default="./memory-bank", help="记忆库目录")
    parser.add_argument("--backup-dir", default="./backups", help="备份存储目录")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # backup 命令
    backup_parser = subparsers.add_parser("backup", help="创建备份")
    backup_parser.add_argument("--name", help="备份名称（默认使用时间戳）")
    
    # restore 命令
    restore_parser = subparsers.add_parser("restore", help="恢复备份")
    restore_parser.add_argument("--name", required=True, help="要恢复的备份名称")
    restore_parser.add_argument("--target-dir", help="目标恢复目录")
    restore_parser.add_argument("--yes", action="store_true", help="跳过确认")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出备份")
    
    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除备份")
    delete_parser.add_argument("--name", required=True, help="要删除的备份名称")
    delete_parser.add_argument("--yes", action="store_true", help="跳过确认")
    
    # cleanup 命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理旧备份")
    cleanup_parser.add_argument("--keep-days", type=int, default=30, help="保留天数")
    cleanup_parser.add_argument("--keep-count", type=int, default=10, help="至少保留数量")
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    try:
        manager = BackupManager(args.memory_dir, args.backup_dir)
        
        if args.command == "backup":
            backup_path = manager.create_backup(args.name)
            print(f"备份创建成功: {backup_path}")
        
        elif args.command == "restore":
            success = manager.restore_backup(
                backup_name=args.name,
                target_dir=args.target_dir,
                confirm=not args.yes
            )
            if not success:
                sys.exit(1)
        
        elif args.command == "list":
            backups = manager.list_backups()
            if not backups:
                print("暂无备份")
            else:
                print(f"备份列表 (共 {len(backups)} 个):")
                print("-" * 80)
                for i, backup in enumerate(backups, 1):
                    size_mb = backup.get("total_size", 0) / (1024 * 1024)
                    print(f"{i:2d}. {backup['name']}")
                    print(f"    时间: {backup['timestamp']}")
                    print(f"    文件数: {backup['file_count']}")
                    print(f"    大小: {size_mb:.2f} MB")
                    print(f"    源目录: {backup.get('source', '未知')}")
                    print()
        
        elif args.command == "delete":
            success = manager.delete_backup(
                backup_name=args.name,
                confirm=not args.yes
            )
            if not success:
                sys.exit(1)
        
        elif args.command == "cleanup":
            deleted = manager.cleanup_old_backups(
                keep_days=args.keep_days,
                keep_count=args.keep_count
            )
            print(f"清理完成: 删除了 {deleted} 个旧备份")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
