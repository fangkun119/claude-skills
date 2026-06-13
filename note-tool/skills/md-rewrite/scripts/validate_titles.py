#!/usr/bin/env python3
"""
四级标题体系验证脚本

功能：
1. 验证文档中的标题是否符合四级标题体系
2. 检查标题编号格式是否正确
3. 返回验证结果和错误报告

四级标题体系规范：
- Level 1 (章): ## {n}.  （阿拉伯数字递增）
- Level 2 (节): ### {n}.{m}  （父级.子级递增）
- Level 3 (小节): #### ({k})  （圆括号阿拉伯数字递增）
- Level 4 (段落条目): ##### {circled_n}  （带圈数字递增）

使用方式：
    python validate_titles.py <markdown_file_path>

返回 JSON 格式的验证结果：
{
    "valid": true/false,
    "errors": ["错误1", "错误2"],
    "warnings": ["警告1", "警告2"],
    "title_count": {
        "level_1": 5,
        "level_2": 12,
        "level_3": 8,
        "level_4": 3
    }
}
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


# 四级标题体系的正则表达式
TITLE_PATTERNS = {
    "level_1": re.compile(r'^## (\d+)\. '),
    "level_2": re.compile(r'^### (\d+)\.(\d+) '),
    "level_3": re.compile(r'^#### \((\d+)\) '),
    "level_4": re.compile(r'^##### ([①-⑩⑪-⑳]) ')
}

# 允许的带圈数字
CIRCLED_NUMBERS = {
    '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
    '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
    '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
    '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20
}


def validate_titles(file_path: str) -> Dict:
    """
    验证文档的标题体系

    Args:
        file_path: Markdown 文件路径

    Returns:
        验证结果字典
    """
    if not os.path.exists(file_path):
        return {
            "valid": False,
            "errors": [f"文件不存在: {file_path}"],
            "warnings": [],
            "title_count": {}
        }

    errors: List[str] = []
    warnings: List[str] = []
    title_count = {"level_1": 0, "level_2": 0, "level_3": 0, "level_4": 0}

    # 跟踪各级标题的编号状态
    level_1_last = 0
    level_2_last = {}  # {父级编号: 最后的子级编号}
    level_3_last = 0
    level_4_last = 0

    current_level_1 = None  # 当前所在的章

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip()

            # 检查 Level 1 标题
            match = TITLE_PATTERNS["level_1"].match(line)
            if match:
                level_1_last += 1
                title_count["level_1"] += 1
                num = int(match.group(1))

                if num != level_1_last:
                    errors.append(f"第 {line_num} 行: Level 1 标题编号错误，期望 {level_1_last}，实际 {num}")

                current_level_1 = num
                # 重置 Level 2 编号
                level_2_last = {}
                continue

            # 检查 Level 2 标题
            match = TITLE_PATTERNS["level_2"].match(line)
            if match:
                if current_level_1 is None:
                    errors.append(f"第 {line_num} 行: Level 2 标题没有父级 Level 1 标题")
                    title_count["level_2"] += 1
                    continue

                parent_num = int(match.group(1))
                child_num = int(match.group(2))

                if parent_num != current_level_1:
                    errors.append(f"第 {line_num} 行: Level 2 标题父级编号错误，期望 {current_level_1}，实际 {parent_num}")

                # 更新该父级下的子级编号
                if parent_num not in level_2_last:
                    level_2_last[parent_num] = 0
                level_2_last[parent_num] += 1

                if child_num != level_2_last[parent_num]:
                    errors.append(f"第 {line_num} 行: Level 2 标题子级编号错误，期望 {level_2_last[parent_num]}，实际 {child_num}")

                title_count["level_2"] += 1
                continue

            # 检查 Level 3 标题
            match = TITLE_PATTERNS["level_3"].match(line)
            if match:
                level_3_last += 1
                title_count["level_3"] += 1
                num = int(match.group(1))

                if num != level_3_last:
                    warnings.append(f"第 {line_num} 行: Level 3 标题编号错误，期望 {level_3_last}，实际 {num}")

                continue

            # 检查 Level 4 标题
            match = TITLE_PATTERNS["level_4"].match(line)
            if match:
                level_4_last += 1
                title_count["level_4"] += 1
                circled = match.group(1)

                if circled not in CIRCLED_NUMBERS:
                    errors.append(f"第 {line_num} 行: Level 4 标题使用了无效的带圈数字 '{circled}'")

                expected_circled = get_circled_number(level_4_last)
                if circled != expected_circled:
                    warnings.append(f"第 {line_num} 行: Level 4 标题编号错误，期望 {expected_circled}，实际 {circled}")

                continue

            # 检查是否有超出四级体系的标题
            if line.startswith("######"):
                errors.append(f"第 {line_num} 行: 发现超过四级的标题（Level 5+），违反四级标题体系规范")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "title_count": title_count
    }


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
