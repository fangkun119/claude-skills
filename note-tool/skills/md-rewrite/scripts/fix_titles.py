#!/usr/bin/env python3
"""
四级标题体系自动更正脚本

功能：
1. 读取 validate_titles.py 返回的验证结果
2. 根据错误类型自动更正标题
3. 保存更正后的文件

支持更正的错误类型：
- format: 格式问题（自动修正编号格式）
- empty: 空标题（可选择补充占位内容或删除）
- increment: 编号递增错误（自动重新编号）
- parent_mismatch: 父子关系错误（自动调整父级编号）
- order: 编号顺序混乱（半自动，需用户确认）
- skip_level: 越级使用（半自动，需插入中间层级）
- overflow: 超出四级（半自动，需降级或调整结构）

使用方式：
    python fix_titles.py <markdown_file_path> [--auto] [--dry-run]

参数：
    --auto: 自动更正所有可自动修复的错误（不询问用户）
    --dry-run: 预览更正结果，不实际修改文件
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple


# 四级标题体系的正则表达式
TITLE_PATTERNS = {
    "level_1": re.compile(r'^## (\d+)\.?\s*(.*)$'),
    "level_2": re.compile(r'^### (\d+)[.:-](\d+)\s*(.*)$'),
    "level_3": re.compile(r'^#### \(?(\d+)\)?\s*(.*)$'),
    "level_4": re.compile(r'^##### ([①-⑳])\s*(.*)$')
}

# 带圈数字映射
CIRCLED_NUMBERS = {
    1: '①', 2: '②', 3: '③', 4: '④', 5: '⑤',
    6: '⑥', 7: '⑦', 8: '⑧', 9: '⑨', 10: '⑩',
    11: '⑪', 12: '⑫', 13: '⑬', 14: '⑭', 15: '⑮',
    16: '⑯', 17: '⑰', 18: '⑱', 19: '⑲', 20: '⑳'
}

# 反向映射（带圈数字 → 阿拉伯数字）
CIRCLED_TO_ARABIC = {v: k for k, v in CIRCLED_NUMBERS.items()}


def fix_titles(file_path: str, auto_mode: bool = False, dry_run: bool = False) -> Dict:
    """
    自动更正标题体系

    Args:
        file_path: Markdown 文件路径
        auto_mode: 自动模式，不询问用户
        dry_run: 预览模式，不实际修改文件

    Returns:
        更正结果字典
    """
    # Step 1: 调用验证脚本获取错误列表
    validation_result = run_validation(file_path)

    if validation_result.get("valid", False):
        return {
            "success": True,
            "message": "文档已符合四级标题体系规范，无需更正",
            "fixes_applied": 0
        }

    # Step 2: 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Step 3: 按优先级处理错误
    fixes_applied = 0
    all_fixes = []

    # P0 级别错误（必须修复）
    p0_errors = [e for e in validation_result.get("errors", []) if e.get("severity") == "error"]
    p1_warnings = [w for w in validation_result.get("warnings", []) if w.get("severity") == "warning"]

    # 按错误类型分组
    format_errors = [e for e in p0_errors if e.get("type") == "format"]
    increment_errors = [e for e in p0_errors if e.get("type") == "increment"]
    parent_errors = [e for e in p0_errors if e.get("type") == "parent_mismatch"]
    skip_level_errors = [e for e in p0_errors if e.get("type") == "skip_level"]
    overflow_errors = [e for e in p0_errors if e.get("type") == "overflow"]

    order_warnings = [w for w in p1_warnings if w.get("type") == "order"]
    empty_warnings = [w for w in p1_warnings if w.get("type") == "empty"]

    # 处理格式错误
    if format_errors:
        fixes = fix_format_errors(lines, format_errors, auto_mode)
        fixes_applied += len(fixes)
        all_fixes.extend(fixes)

    # 处理空标题
    if empty_warnings:
        fixes = fix_empty_titles(lines, empty_warnings, auto_mode)
        fixes_applied += len(fixes)
        all_fixes.extend(fixes)

    # 处理编号递增错误（需要重新编号）
    if increment_errors or parent_errors:
        fixes = fix_numbering_errors(lines, increment_errors, parent_errors, auto_mode)
        fixes_applied += len(fixes)
        all_fixes.extend(fixes)

    # 处理编号顺序混乱
    if order_warnings:
        if auto_mode:
            fixes = fix_order_errors(lines, order_warnings)
            fixes_applied += len(fixes)
            all_fixes.extend(fixes)
        else:
            print("\n⚠️  检测到编号顺序混乱问题：")
            for warning in order_warnings:
                print(f"  - 行 {warning['line']}: {warning['message']}")
            print("\n建议手动调整标题顺序，或使用 --auto 参数自动处理。")

    # 处理越级使用（需要用户介入）
    if skip_level_errors:
        print("\n⚠️  检测到越级使用问题：")
        for error in skip_level_errors:
            print(f"  - 行 {error['line']}: {error['message']}")
        print("\n越级使用需要手动插入缺失的中间层级标题。")

    # 处理超出四级（需要用户介入）
    if overflow_errors:
        print("\n⚠️  检测到超出四级的标题：")
        for error in overflow_errors:
            print(f"  - 行 {error['line']}: {error['message']}")
        print("\n超出四级的标题需要手动降级或调整结构。")

    # Step 4: 保存更正后的文件
    if not dry_run and fixes_applied > 0:
        # 创建备份
        backup_path = create_backup(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"\n✅ 已应用 {fixes_applied} 处更正")
        print(f"📝 原文件已备份至: {backup_path}")
    elif dry_run:
        print(f"\n🔍 预览模式：将应用 {fixes_applied} 处更正（未实际修改文件）")

    return {
        "success": True,
        "fixes_applied": fixes_applied,
        "fixes": all_fixes,
        "dry_run": dry_run
    }


def run_validation(file_path: str) -> Dict:
    """运行验证脚本"""
    import subprocess

    validate_script = os.path.join(os.path.dirname(__file__), 'validate_titles.py')
    result = subprocess.run(
        ['python3', validate_script, file_path],
        capture_output=True,
        text=True
    )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"valid": False, "errors": [], "warnings": []}


def create_backup(file_path: str) -> str:
    """创建文件备份"""
    from datetime import datetime

    base_path = Path(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = base_path.parent / f"{base_path.stem}_backup_{timestamp}{base_path.suffix}"

    import shutil
    shutil.copy2(file_path, backup_path)

    return str(backup_path)


def fix_format_errors(lines: List[str], errors: List[Dict], auto_mode: bool) -> List[Dict]:
    """
    更正格式错误

    策略：
    - Level 1: 确保 `## {n}. ` 格式
    - Level 2: 确保 `### {n}.{m} ` 格式
    - Level 3: 确保 `#### ({k}) ` 格式
    - Level 4: 确保 `##### {circled} ` 格式
    """
    fixes = []

    for error in errors:
        line_num = error["line"] - 1  # 转换为 0-based 索引
        if line_num >= len(lines):
            continue

        line = lines[line_num].rstrip()

        # 根据当前行格式和错误类型进行更正
        if line.startswith("##") and not line.startswith("###"):
            # Level 1
            match = TITLE_PATTERNS["level_1"].match(line)
            if match:
                num = match.group(1)
                content = match.group(2).strip()
                new_line = f"## {num}. {content}\n"
                lines[line_num] = new_line
                fixes.append({"line": error["line"], "old": line, "new": new_line.strip()})

        elif line.startswith("###") and not line.startswith("####"):
            # Level 2
            match = TITLE_PATTERNS["level_2"].match(line)
            if match:
                parent = match.group(1)
                child = match.group(2)
                content = match.group(3).strip()
                new_line = f"### {parent}.{child} {content}\n"
                lines[line_num] = new_line
                fixes.append({"line": error["line"], "old": line, "new": new_line.strip()})

        elif line.startswith("####") and not line.startswith("#####"):
            # Level 3
            match = TITLE_PATTERNS["level_3"].match(line)
            if match:
                num = match.group(1)
                content = match.group(2).strip()
                new_line = f"#### ({num}) {content}\n"
                lines[line_num] = new_line
                fixes.append({"line": error["line"], "old": line, "new": new_line.strip()})

        elif line.startswith("#####"):
            # Level 4
            match = TITLE_PATTERNS["level_4"].match(line)
            if match:
                circled = match.group(1)
                content = match.group(2).strip()
                new_line = f"##### {circled} {content}\n"
                lines[line_num] = new_line
                fixes.append({"line": error["line"], "old": line, "new": new_line.strip()})

    return fixes


def fix_empty_titles(lines: List[str], warnings: List[Dict], auto_mode: bool) -> List[Dict]:
    """
    更正空标题

    策略：
    - 如果有占位内容（如"待补充"），使用占位内容
    - 否则，询问用户如何处理（补充内容或删除）
    """
    fixes = []

    for warning in warnings:
        line_num = warning["line"] - 1
        if line_num >= len(lines):
            continue

        line = lines[line_num].rstrip()

        # 询问用户如何处理
        if not auto_mode:
            print(f"\n⚠️  行 {warning['line']}: {line}")
            choice = input("选择处理方式: [1] 补充占位内容 '待补充' [2] 删除标题 [3] 跳过 ").strip()
            if choice == "1":
                # 补充占位内容
                if line.startswith("##") and not line.startswith("###"):
                    match = TITLE_PATTERNS["level_1"].match(line)
                    if match:
                        new_line = f"## {match.group(1)}. 待补充\n"
                        lines[line_num] = new_line
                        fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
                elif line.startswith("###") and not line.startswith("####"):
                    match = TITLE_PATTERNS["level_2"].match(line)
                    if match:
                        new_line = f"### {match.group(1)}.{match.group(2)} 待补充\n"
                        lines[line_num] = new_line
                        fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
                elif line.startswith("####") and not line.startswith("#####"):
                    match = TITLE_PATTERNS["level_3"].match(line)
                    if match:
                        new_line = f"#### ({match.group(1)}) 待补充\n"
                        lines[line_num] = new_line
                        fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
                elif line.startswith("#####"):
                    match = TITLE_PATTERNS["level_4"].match(line)
                    if match:
                        new_line = f"##### {match.group(1)} 待补充\n"
                        lines[line_num] = new_line
                        fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
            elif choice == "2":
                # 删除标题
                lines[line_num] = ""
                fixes.append({"line": warning["line"], "old": line, "new": "(已删除)"})
            else:
                # 跳过
                continue
        else:
            # 自动模式：补充占位内容
            if line.startswith("##") and not line.startswith("###"):
                match = TITLE_PATTERNS["level_1"].match(line)
                if match:
                    new_line = f"## {match.group(1)}. 待补充\n"
                    lines[line_num] = new_line
                    fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
            elif line.startswith("###") and not line.startswith("####"):
                match = TITLE_PATTERNS["level_2"].match(line)
                if match:
                    new_line = f"### {match.group(1)}.{match.group(2)} 待补充\n"
                    lines[line_num] = new_line
                    fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
            elif line.startswith("####") and not line.startswith("#####"):
                match = TITLE_PATTERNS["level_3"].match(line)
                if match:
                    new_line = f"#### ({match.group(1)}) 待补充\n"
                    lines[line_num] = new_line
                    fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})
            elif line.startswith("#####"):
                match = TITLE_PATTERNS["level_4"].match(line)
                if match:
                    new_line = f"##### {match.group(1)} 待补充\n"
                    lines[line_num] = new_line
                    fixes.append({"line": warning["line"], "old": line, "new": new_line.strip()})

    return fixes


def fix_numbering_errors(lines: List[str], increment_errors: List[Dict], parent_errors: List[Dict], auto_mode: bool) -> List[Dict]:
    """
    更正编号递增错误和父子关系错误

    策略：重新编号所有标题
    """
    fixes = []

    # 提取所有标题并记录其行号
    titles = []
    for i, line in enumerate(lines):
        line = line.rstrip()
        if line.startswith("##") and not line.startswith("###"):
            match = TITLE_PATTERNS["level_1"].match(line)
            if match:
                titles.append({"line_num": i, "level": 1, "original": line, "num": match.group(1), "content": match.group(2)})
        elif line.startswith("###") and not line.startswith("####"):
            match = TITLE_PATTERNS["level_2"].match(line)
            if match:
                titles.append({"line_num": i, "level": 2, "original": line, "parent": match.group(1), "child": match.group(2), "content": match.group(3)})
        elif line.startswith("####") and not line.startswith("#####"):
            match = TITLE_PATTERNS["level_3"].match(line)
            if match:
                titles.append({"line_num": i, "level": 3, "original": line, "num": match.group(1), "content": match.group(2)})
        elif line.startswith("#####"):
            match = TITLE_PATTERNS["level_4"].match(line)
            if match:
                titles.append({"line_num": i, "level": 4, "original": line, "num": match.group(1), "content": match.group(2)})

    # 重新编号
    level_1_counter = 0
    level_2_counter = {}
    level_3_counter = 0
    level_4_counter = 0
    current_level_1 = None

    for title in titles:
        if title["level"] == 1:
            level_1_counter += 1
            current_level_1 = level_1_counter
            level_2_counter = {}  # 重置 Level 2 计数器
            level_3_counter = 0  # 重置 Level 3 计数器
            level_4_counter = 0  # 重置 Level 4 计数器

            new_line = f"## {level_1_counter}. {title['content']}\n"
            if new_line.strip() != title["original"]:
                lines[title["line_num"]] = new_line
                fixes.append({"line": title["line_num"] + 1, "old": title["original"], "new": new_line.strip()})

        elif title["level"] == 2:
            if current_level_1 not in level_2_counter:
                level_2_counter[current_level_1] = 0
            level_2_counter[current_level_1] += 1

            new_line = f"### {current_level_1}.{level_2_counter[current_level_1]} {title['content']}\n"
            if new_line.strip() != title["original"]:
                lines[title["line_num"]] = new_line
                fixes.append({"line": title["line_num"] + 1, "old": title["original"], "new": new_line.strip()})

        elif title["level"] == 3:
            level_3_counter += 1
            level_4_counter = 0  # 重置 Level 4 计数器

            new_line = f"#### ({level_3_counter}) {title['content']}\n"
            if new_line.strip() != title["original"]:
                lines[title["line_num"]] = new_line
                fixes.append({"line": title["line_num"] + 1, "old": title["original"], "new": new_line.strip()})

        elif title["level"] == 4:
            level_4_counter += 1
            new_circled = CIRCLED_NUMBERS.get(level_4_counter, '①')

            new_line = f"##### {new_circled} {title['content']}\n"
            if new_line.strip() != title["original"]:
                lines[title["line_num"]] = new_line
                fixes.append({"line": title["line_num"] + 1, "old": title["original"], "new": new_line.strip()})

    return fixes


def fix_order_errors(lines: List[str], warnings: List[Dict]) -> List[Dict]:
    """
    更正编号顺序混乱

    策略：排序同级别的标题（实现较复杂，暂时只提供警告）
    """
    # 这个功能实现较复杂，需要重新排序标题行
    # 暂时只返回空列表，建议用户手动调整
    return []


def main():
    parser = argparse.ArgumentParser(description='四级标题体系自动更正脚本')
    parser.add_argument('file_path', help='Markdown 文件路径')
    parser.add_argument('--auto', action='store_true', help='自动模式，不询问用户')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际修改文件')

    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(f"错误：文件不存在: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    result = fix_titles(args.file_path, auto_mode=args.auto, dry_run=args.dry_run)

    if result.get("success"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
