#!/usr/bin/env python3
"""
四级标题体系验证脚本（增强版）

功能：
1. 验证文档中的标题是否符合四级标题体系
2. 检查标题编号格式是否正确
3. 检查标题层级关系是否正确（包括越级使用）
4. 检查编号顺序是否混乱
5. 检查是否存在空标题
6. 返回验证结果和详细错误报告

四级标题体系规范：
- Level 1 (章): ## {n}. {content} （阿拉伯数字递增）
- Level 2 (节): ### {n}.{m} {content} （父级.子级递增）
- Level 3 (小节): #### ({k}) {content} （圆括号阿拉伯数字递增）
- Level 4 (段落条目): ##### {circled_n} {content} （带圈数字递增）

P0 检测（必须通过）：
- P0-1 格式问题：前缀、编号、空格、内容是否符合规范
- P0-2 越级使用：标题是否跳跃层级（如 Level 1 → Level 3）
- 编号递增错误：各级编号是否正确递增
- 超出四级：是否使用了 Level 5+
- 父子关系错误：Level 2 的父级编号是否匹配

P1 检测（建议通过）：
- P1-3 编号顺序混乱：编号出现顺序是否正确
- P1-4 空标题：标签后是否有内容

使用方式：
    python validate_titles.py <markdown_file_path>

返回 JSON 格式的验证结果：
{
    "valid": true/false,
    "errors": [
        {
            "line": int,
            "type": str,           # "format" | "skip_level" | "increment" | "overflow" | "parent_mismatch"
            "level": str,          # "Level 1" | "Level 2" | ...
            "message": str,
            "severity": str        # "error"
        }
    ],
    "warnings": [
        {
            "line": int,
            "type": str,           # "order" | "empty"
            "level": str,          # "Level 2" | "Level 3" | ...
            "message": str,
            "severity": str        # "warning"
        }
    ],
    "title_count": {...},
    "summary": {...}
}
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


# 四级标题体系的正则表达式（更严格，检测格式问题）
TITLE_PATTERNS = {
    "level_1": re.compile(r'^## (\d+)\. (.+)$'),
    "level_2": re.compile(r'^### (\d+)\.(\d+) (.+)$'),
    "level_3": re.compile(r'^#### \((\d+)\) (.+)$'),
    "level_4": re.compile(r'^##### ([①-⑳]) (.+)$')
}

# 宽松的正则表达式（用于识别可能的标题，即使格式不完全正确）
LOOSE_PATTERNS = {
    "level_1": re.compile(r'^## (\d+)\.?\s*(.*)$'),
    "level_2": re.compile(r'^### (\d+)[.:-](\d+)\s*(.*)$'),
    "level_3": re.compile(r'^#### \(?(\d+)\)?\s*(.*)$'),
    "level_4": re.compile(r'^##### ([①-⑳])\s*(.*)$')
}

# 允许的带圈数字
CIRCLED_NUMBERS = {
    '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
    '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
    '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
    '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20
}


class TitleInfo:
    """标题信息"""
    def __init__(self, line_num: int, level: int, raw_line: str,
                 prefix: str, numbering: str, content: str, is_valid_format: bool):
        self.line_num = line_num
        self.level = level
        self.raw_line = raw_line
        self.prefix = prefix
        self.numbering = numbering
        self.content = content
        self.is_valid_format = is_valid_format

    def __repr__(self):
        return f"TitleInfo(line={self.line_num}, level={self.level}, numbering={self.numbering}, content='{self.content}')"


def validate_titles(file_path: str) -> Dict:
    """
    验证文档的标题体系（增强版）

    Args:
        file_path: Markdown 文件路径

    Returns:
        验证结果字典
    """
    if not os.path.exists(file_path):
        return {
            "valid": False,
            "errors": [{
                "line": 0,
                "type": "file_not_found",
                "level": "N/A",
                "message": f"文件不存在: {file_path}",
                "severity": "error"
            }],
            "warnings": [],
            "title_count": {},
            "summary": {"total_errors": 1, "total_warnings": 0, "error_by_type": {}}
        }

    errors: List[Dict] = []
    warnings: List[Dict] = []
    title_count = {"level_1": 0, "level_2": 0, "level_3": 0, "level_4": 0}
    error_by_type = {}

    # Step 1: 解析所有标题
    titles = parse_all_titles(file_path)

    # Step 2: 统计标题数量
    for title in titles:
        if title.level <= 4:
            title_count[f"level_{title.level}"] += 1

    # Step 3: 检查 P0-1 格式问题
    format_errors = check_format_issues(titles)
    errors.extend(format_errors)

    # Step 4: 检查 P0-2 越级使用
    skip_level_errors = check_skip_level(titles)
    errors.extend(skip_level_errors)

    # Step 5: 检查编号递增（复用现有逻辑，增强）
    increment_errors = check_numbering_increment(titles)
    errors.extend(increment_errors['errors'])
    warnings.extend(increment_errors['warnings'])

    # Step 6: 检查超出四级
    overflow_errors = check_level_overflow(file_path)
    errors.extend(overflow_errors)

    # Step 7: 检查父子关系（复用现有逻辑，增强）
    parent_errors = check_parent_relationship(titles)
    errors.extend(parent_errors)

    # Step 8: 检查 P1-3 编号顺序混乱
    order_warnings = check_numbering_order(titles)
    warnings.extend(order_warnings)

    # Step 9: 检查 P1-4 空标题
    empty_warnings = check_empty_titles(titles)
    warnings.extend(empty_warnings)

    # 统计错误类型
    for error in errors:
        error_type = error['type']
        error_by_type[error_type] = error_by_type.get(error_type, 0) + 1

    for warning in warnings:
        warning_type = warning['type']
        error_by_type[warning_type] = error_by_type.get(warning_type, 0) + 1

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "title_count": title_count,
        "summary": {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "error_by_type": error_by_type
        }
    }


def parse_all_titles(file_path: str) -> List[TitleInfo]:
    """
    解析所有标题，提取基本信息

    Returns:
        标题信息列表
    """
    titles = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip()

            # 尝试用严格模式匹配
            for level, pattern in TITLE_PATTERNS.items():
                match = pattern.match(line)
                if match:
                    level_num = int(level.split('_')[1])
                    if level_num == 1:
                        numbering = match.group(1)
                        content = match.group(2)
                        prefix = "##"
                    elif level_num == 2:
                        numbering = f"{match.group(1)}.{match.group(2)}"
                        content = match.group(3)
                        prefix = "###"
                    elif level_num == 3:
                        numbering = f"({match.group(1)})"
                        content = match.group(2)
                        prefix = "####"
                    else:  # level 4
                        numbering = match.group(1)
                        content = match.group(2)
                        prefix = "#####"

                    titles.append(TitleInfo(
                        line_num=line_num,
                        level=level_num,
                        raw_line=line,
                        prefix=prefix,
                        numbering=numbering,
                        content=content,
                        is_valid_format=True
                    ))
                    break

            # 如果严格模式不匹配，尝试宽松模式（用于检测格式错误）
            if not any(t.line_num == line_num for t in titles):
                for level, pattern in LOOSE_PATTERNS.items():
                    match = pattern.match(line)
                    if match:
                        level_num = int(level.split('_')[1])
                        if level_num == 1:
                            numbering = match.group(1)
                            content = match.group(2)
                            prefix = "##"
                        elif level_num == 2:
                            numbering = f"{match.group(1)}.{match.group(2)}"
                            content = match.group(3)
                            prefix = "###"
                        elif level_num == 3:
                            numbering = f"({match.group(1)})"
                            content = match.group(2)
                            prefix = "####"
                        else:  # level 4
                            numbering = match.group(1)
                            content = match.group(2)
                            prefix = "#####"

                        titles.append(TitleInfo(
                            line_num=line_num,
                            level=level_num,
                            raw_line=line,
                            prefix=prefix,
                            numbering=numbering,
                            content=content,
                            is_valid_format=False
                        ))
                        break

    return titles


def check_format_issues(titles: List[TitleInfo]) -> List[Dict]:
    """
    检查 P0-1 格式问题

    Returns:
        错误列表
    """
    errors = []

    for title in titles:
        if title.is_valid_format:
            continue

        # 检查格式问题
        if title.level == 1:
            expected_format = "## {n}. {content}"
            errors.append({
                "line": title.line_num,
                "type": "format",
                "level": "Level 1",
                "message": f"Level 1 标题格式错误：当前为 '{title.raw_line}'，期望格式 '{expected_format}'（编号后需要点和空格）",
                "severity": "error"
            })
        elif title.level == 2:
            expected_format = "### {n}.{m} {content}"
            errors.append({
                "line": title.line_num,
                "type": "format",
                "level": "Level 2",
                "message": f"Level 2 标题格式错误：当前为 '{title.raw_line}'，期望格式 '{expected_format}'（使用点分隔父级和子级，后跟空格）",
                "severity": "error"
            })
        elif title.level == 3:
            expected_format = "#### ({k}) {content}"
            errors.append({
                "line": title.line_num,
                "type": "format",
                "level": "Level 3",
                "message": f"Level 3 标题格式错误：当前为 '{title.raw_line}'，期望格式 '{expected_format}'（使用圆括号包裹数字，后跟空格）",
                "severity": "error"
            })
        elif title.level == 4:
            expected_format = "##### {circled_n} {content}"
            errors.append({
                "line": title.line_num,
                "type": "format",
                "level": "Level 4",
                "message": f"Level 4 标题格式错误：当前为 '{title.raw_line}'，期望格式 '{expected_format}'（使用带圈数字 ①-⑳，后跟空格）",
                "severity": "error"
            })

    return errors


def check_skip_level(titles: List[TitleInfo]) -> List[Dict]:
    """
    检查 P0-2 越级使用

    Returns:
        错误列表
    """
    errors = []
    if not titles:
        return errors

    for i, title in enumerate(titles):
        if i == 0:
            continue

        prev_title = titles[i - 1]

        # 检查是否越级
        # 规则：下一个层级只能是当前层级或当前层级 +1
        # 例外：如果回到更高层级（如从 Level 3 回到 Level 1），需要检查是否有合适的父级
        if title.level > prev_title.level + 1:
            errors.append({
                "line": title.line_num,
                "type": "skip_level",
                "level": f"Level {prev_title.level} → Level {title.level}",
                "message": f"标题越级使用：第 {prev_title.line_num} 行是 Level {prev_title.level}，第 {title.line_num} 行直接跳到 Level {title.level}，违反层级递进规则",
                "severity": "error"
            })

    return errors


def check_numbering_increment(titles: List[TitleInfo]) -> Dict:
    """
    检查编号递增（复用现有逻辑）

    Returns:
        {"errors": [...], "warnings": [...]}
    """
    errors = []
    warnings = []

    # 跟踪各级标题的编号状态
    level_1_last = 0
    level_2_last = {}  # {父级编号: 最后的子级编号}
    level_3_last = 0
    level_4_last = 0

    current_level_1 = None  # 当前所在的章

    for title in titles:
        if title.level == 1:
            level_1_last += 1
            num = int(title.numbering)
            if num != level_1_last:
                errors.append({
                    "line": title.line_num,
                    "type": "increment",
                    "level": "Level 1",
                    "message": f"Level 1 标题编号错误：期望 {level_1_last}，实际 {num}",
                    "severity": "error"
                })
            current_level_1 = num
            level_2_last = {}  # 重置 Level 2 编号

        elif title.level == 2:
            if current_level_1 is None:
                errors.append({
                    "line": title.line_num,
                    "type": "parent_mismatch",
                    "level": "Level 2",
                    "message": f"Level 2 标题没有父级 Level 1 标题",
                    "severity": "error"
                })
                continue

            # 解析父级和子级编号
            parts = title.numbering.split('.')
            parent_num = int(parts[0])
            child_num = int(parts[1])

            if parent_num != current_level_1:
                errors.append({
                    "line": title.line_num,
                    "type": "parent_mismatch",
                    "level": "Level 2",
                    "message": f"Level 2 标题父级编号错误：当前在 Level 1 编号 {current_level_1} 下，但此标题父级为 {parent_num}",
                    "severity": "error"
                })

            # 更新该父级下的子级编号
            if parent_num not in level_2_last:
                level_2_last[parent_num] = 0
            level_2_last[parent_num] += 1

            if child_num != level_2_last[parent_num]:
                errors.append({
                    "line": title.line_num,
                    "type": "increment",
                    "level": "Level 2",
                    "message": f"Level 2 标题子级编号错误：期望 {level_2_last[parent_num]}，实际 {child_num}",
                    "severity": "error"
                })

        elif title.level == 3:
            level_3_last += 1
            # 提取圆括号中的数字
            num = int(title.numbering.strip('()'))
            if num != level_3_last:
                warnings.append({
                    "line": title.line_num,
                    "type": "increment",
                    "level": "Level 3",
                    "message": f"Level 3 标题编号错误：期望 {level_3_last}，实际 {num}",
                    "severity": "warning"
                })

        elif title.level == 4:
            level_4_last += 1
            circled = title.numbering

            if circled not in CIRCLED_NUMBERS:
                errors.append({
                    "line": title.line_num,
                    "type": "format",
                    "level": "Level 4",
                    "message": f"Level 4 标题使用了无效的带圈数字 '{circled}'，有效范围为 ①-⑳",
                    "severity": "error"
                })
                continue

            expected_circled = get_circled_number(level_4_last)
            if circled != expected_circled:
                warnings.append({
                    "line": title.line_num,
                    "type": "increment",
                    "level": "Level 4",
                    "message": f"Level 4 标题编号错误：期望 {expected_circled}，实际 {circled}",
                    "severity": "warning"
                })

    return {"errors": errors, "warnings": warnings}


def check_level_overflow(file_path: str) -> List[Dict]:
    """
    检查超出四级的标题

    Returns:
        错误列表
    """
    errors = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip()
            # 检查是否有超出四级体系的标题（Level 5+）
            if line.startswith("######"):
                errors.append({
                    "line": line_num,
                    "type": "overflow",
                    "level": "Level 5+",
                    "message": f"发现超过四级的标题（Level 5+），违反四级标题体系规范",
                    "severity": "error"
                })

    return errors


def check_parent_relationship(titles: List[TitleInfo]) -> List[Dict]:
    """
    检查父子关系（增强版）

    注意：这个功能已经在 check_numbering_increment 中实现
    这里保留是为了未来可能需要更复杂的父子关系检查

    Args:
        titles: 标题列表（当前未使用，保留以维持接口一致）

    Returns:
        错误列表
    """
    errors = []

    # 父子关系检查已在 check_numbering_increment 中实现
    # 如果未来需要更复杂的检查（如跨级检查），可以在这里添加

    return errors


def check_numbering_order(titles: List[TitleInfo]) -> List[Dict]:
    """
    检查 P1-3 编号顺序混乱

    Returns:
        警告列表
    """
    warnings = []

    # 按层级分组
    level_2_titles = [t for t in titles if t.level == 2]
    level_3_titles = [t for t in titles if t.level == 3]
    level_4_titles = [t for t in titles if t.level == 4]

    # 检查 Level 2 编号顺序
    for i in range(1, len(level_2_titles)):
        current = level_2_titles[i]
        prev = level_2_titles[i - 1]

        # 解析编号
        current_parts = current.numbering.split('.')
        prev_parts = prev.numbering.split('.')

        current_parent = int(current_parts[0])
        current_child = int(current_parts[1])
        prev_parent = int(prev_parts[0])
        prev_child = int(prev_parts[1])

        # 如果父级相同，检查子级顺序
        if current_parent == prev_parent:
            if current_child < prev_child:
                warnings.append({
                    "line": current.line_num,
                    "type": "order",
                    "level": "Level 2",
                    "message": f"Level 2 标题编号顺序混乱：{current.numbering} 出现在 {prev.numbering} 之前（第 {prev.line_num} 行）",
                    "severity": "warning"
                })

    # 检查 Level 3 编号顺序
    for i in range(1, len(level_3_titles)):
        current = level_3_titles[i]
        prev = level_3_titles[i - 1]

        current_num = int(current.numbering.strip('()'))
        prev_num = int(prev.numbering.strip('()'))

        if current_num < prev_num:
            warnings.append({
                "line": current.line_num,
                "type": "order",
                "level": "Level 3",
                "message": f"Level 3 标题编号顺序混乱：{current.numbering} 出现在 {prev.numbering} 之前（第 {prev.line_num} 行）",
                "severity": "warning"
            })

    # 检查 Level 4 编号顺序
    for i in range(1, len(level_4_titles)):
        current = level_4_titles[i]
        prev = level_4_titles[i - 1]

        current_num = CIRCLED_NUMBERS.get(current.numbering, 0)
        prev_num = CIRCLED_NUMBERS.get(prev.numbering, 0)

        if current_num < prev_num:
            warnings.append({
                "line": current.line_num,
                "type": "order",
                "level": "Level 4",
                "message": f"Level 4 标题编号顺序混乱：{current.numbering} 出现在 {prev.numbering} 之前（第 {prev.line_num} 行）",
                "severity": "warning"
            })

    return warnings


def check_empty_titles(titles: List[TitleInfo]) -> List[Dict]:
    """
    检查 P1-4 空标题

    Returns:
        警告列表
    """
    warnings = []

    for title in titles:
        # 检查内容是否为空
        if not title.content or title.content.strip() == '':
            warnings.append({
                "line": title.line_num,
                "type": "empty",
                "level": f"Level {title.level}",
                "message": f"Level {title.level} 标题为空：{title.raw_line}",
                "severity": "warning"
            })

    return warnings


def get_circled_number(n: int) -> str:
    """获取带圈数字"""
    circled_map = {
        1: '①', 2: '②', 3: '③', 4: '④', 5: '⑤',
        6: '⑥', 7: '⑦', 8: '⑧', 9: '⑨', 10: '⑩',
        11: '⑪', 12: '⑫', 13: '⑬', 14: '⑭', 15: '⑮',
        16: '⑯', 17: '⑰', 18: '⑱', 19: '⑲', 20: '⑳'
    }
    return circled_map.get(n, '?')


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_titles.py <markdown_file_path>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    result = validate_titles(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 返回退出码
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
