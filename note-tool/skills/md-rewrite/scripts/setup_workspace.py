#!/usr/bin/env python3
"""
Phase 1 工作环境准备脚本

功能：
1. 验证源文件存在且可读
2. 创建工作目录
3. 创建改写副本和备份
4. 返回路径变量供后续阶段使用

使用方式：
    python setup_workspace.py <source_file_path>

返回 JSON 格式的路径变量：
{
    "source_file_path": "源文件路径",
    "source_file_dir": "源文件所在目录",
    "source_file_name": "源文件名（不含扩展名）",
    "workspace_directory": "工作区目录",
    "rewritten_file_path": "改写文件路径",
    "backup_file_path": "备份文件路径"
}
"""

import os
import sys
import json
import shutil
from pathlib import Path


def setup_workspace(source_file_path: str) -> dict:
    """
    设置工作环境

    Args:
        source_file_path: 用户提供的源 Markdown 文件路径

    Returns:
        包含所有路径变量的字典
    """
    # 转换为绝对路径
    source_path = Path(source_file_path).resolve()

    # 验证源文件存在
    if not source_path.exists():
        raise FileNotFoundError(f"源文件不存在: {source_path}")

    # 验证源文件可读
    if not os.access(source_path, os.R_OK):
        raise PermissionError(f"源文件不可读: {source_path}")

    # 提取路径变量
    source_file_dir = source_path.parent
    source_file_name = source_path.stem

    # 构建路径
    workspace_directory = source_file_dir / "workspace" / source_file_name
    rewritten_file_path = source_file_dir / f"{source_file_name}_rewritten.md"
    backup_file_path = workspace_directory / f"{source_file_name}_backup.md"

    # 创建工作目录
    workspace_directory.mkdir(parents=True, exist_ok=True)

    # 创建改写副本
    shutil.copy2(source_path, rewritten_file_path)

    # 创建备份
    shutil.copy2(source_path, backup_file_path)

    return {
        "source_file_path": str(source_path),
        "source_file_dir": str(source_file_dir),
        "source_file_name": source_file_name,
        "workspace_directory": str(workspace_directory),
        "rewritten_file_path": str(rewritten_file_path),
        "backup_file_path": str(backup_file_path)
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_workspace.py <source_file_path>", file=sys.stderr)
        sys.exit(1)

    source_file_path = sys.argv[1]

    try:
        result = setup_workspace(source_file_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
