#!/usr/bin/env python3
"""
四级标题体系验证脚本（重构版）

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
"""

import os
import sys
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ============================================================================
# 数据结构和枚举定义
# ============================================================================

class Level(Enum):
    """标题层级枚举"""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4

    @classmethod
    def from_prefix(cls, prefix: str) -> Optional['Level']:
        """从标题前缀获取层级"""
        mapping = {
            '##': cls.LEVEL_1,
            '###': cls.LEVEL_2,
            '####': cls.LEVEL_3,
            '#####': cls.LEVEL_4,
        }
        return mapping.get(prefix)

    @classmethod
    def from_hash_count(cls, count: int) -> Optional['Level']:
        """从 # 数量获取层级"""
        mapping = {2: cls.LEVEL_1, 3: cls.LEVEL_2, 4: cls.LEVEL_3, 5: cls.LEVEL_4}
        return mapping.get(count)


class ErrorType(Enum):
    """错误类型枚举"""
    FORMAT = "format"
    SKIP_LEVEL = "skip_level"
    INCREMENT = "increment"
    OVERFLOW = "overflow"
    PARENT_MISMATCH = "parent_mismatch"
    ORDER = "order"
    EMPTY = "empty"
    FILE_NOT_FOUND = "file_not_found"


class Severity(Enum):
    """严重程度枚举"""
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class LevelConfig:
    """层级配置"""
    level: Level
    prefix: str
    pattern: str
    loose_pattern: str
    expected_format: str

    def get_regex(self) -> re.Pattern:
        """获取严格正则"""
        return re.compile(self.pattern)

    def get_loose_regex(self) -> re.Pattern:
        """获取宽松正则"""
        return re.compile(self.loose_pattern)


# 四级标题体系配置
LEVEL_CONFIGS: Dict[Level, LevelConfig] = {
    Level.LEVEL_1: LevelConfig(
        level=Level.LEVEL_1,
        prefix='##',
        pattern=r'^## (\d+)\. (.+)$',
        loose_pattern=r'^## (\d+)\.?\s*(.*)$',
        expected_format='## {n}. {content}'
    ),
    Level.LEVEL_2: LevelConfig(
        level=Level.LEVEL_2,
        prefix='###',
        pattern=r'^### (\d+)\.(\d+) (.+)$',
        loose_pattern=r'^### (\d+)[.:-](\d+)\s*(.*)$',
        expected_format='### {n}.{m} {content}'
    ),
    Level.LEVEL_3: LevelConfig(
        level=Level.LEVEL_3,
        prefix='####',
        pattern=r'^#### \((\d+)\) (.+)$',
        loose_pattern=r'^#### \(?(\d+)\)?\s*(.*)$',
        expected_format='#### ({k}) {content}'
    ),
    Level.LEVEL_4: LevelConfig(
        level=Level.LEVEL_4,
        prefix='#####',
        pattern=r'^##### ([①-⑳]) (.+)$',
        loose_pattern=r'^##### ([①-⑳])\s*(.*)$',
        expected_format='##### {circled_n} {content}'
    ),
}

# 带圈数字映射
CIRCLED_NUMBERS: Dict[str, int] = {
    '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
    '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
    '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
    '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20
}

# 反向映射
CIRCLED_NUMBER_MAP: Dict[int, str] = {v: k for k, v in CIRCLED_NUMBERS.items()}

# 代码围栏正则
FENCE_OPEN_RE = re.compile(r'^ {0,3}(`{3,})(.*)$')


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class TitleInfo:
    """标题信息"""
    line_num: int
    level: Level
    raw_line: str
    prefix: str
    numbering: str
    content: str
    is_valid_format: bool

    def __repr__(self) -> str:
        return f"TitleInfo(line={self.line_num}, level={self.level.name}, numbering='{self.numbering}', content='{self.content}')"


@dataclass
class ValidationError:
    """验证错误"""
    line: int
    error_type: ErrorType
    level: str
    message: str
    severity: Severity

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "line": self.line,
            "type": self.error_type.value,
            "level": self.level,
            "message": self.message,
            "severity": self.severity.value
        }


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    title_count: Dict[str, int] = field(default_factory=dict)
    summary: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "title_count": self.title_count,
            "summary": self.summary
        }


# ============================================================================
# 核心逻辑类
# ============================================================================

class TitleParser:
    """标题解析器"""

    def __init__(self):
        self.line_to_title: Dict[int, TitleInfo] = {}

    def parse_file(self, file_path: str) -> List[TitleInfo]:
        """解析文件中的所有标题"""
        titles = []
        for line_num, line in iter_code_aware_lines(file_path):
            title = self._parse_line(line_num, line)
            if title:
                titles.append(title)
                self.line_to_title[line_num] = title
        return titles

    def _parse_line(self, line_num: int, line: str) -> Optional[TitleInfo]:
        """解析单行标题"""
        # 尝试严格匹配
        title = self._try_match_strict(line_num, line)
        if title:
            return title

        # 尝试宽松匹配
        title = self._try_match_loose(line_num, line)
        if title:
            return title

        # 尝试无编号标题
        title = self._try_match_bare(line_num, line)
        if title:
            return title

        return None

    def _try_match_strict(self, line_num: int, line: str) -> Optional[TitleInfo]:
        """尝试严格模式匹配"""
        for config in LEVEL_CONFIGS.values():
            match = config.get_regex().match(line)
            if match:
                return self._build_title_from_match(
                    line_num, line, config, match, is_valid=True
                )
        return None

    def _try_match_loose(self, line_num: int, line: str) -> Optional[TitleInfo]:
        """尝试宽松模式匹配"""
        for config in LEVEL_CONFIGS.values():
            match = config.get_loose_regex().match(line)
            if match:
                return self._build_title_from_match(
                    line_num, line, config, match, is_valid=False
                )
        return None

    def _try_match_bare(self, line_num: int, line: str) -> Optional[TitleInfo]:
        """尝试无编号标题匹配"""
        match = re.match(r'^(#{2,5})\s+(\S.*)$', line)
        if not match:
            return None

        prefix = match.group(1)
        content = match.group(2)
        level = Level.from_prefix(prefix)

        if level is None:
            return None

        return TitleInfo(
            line_num=line_num,
            level=level,
            raw_line=line,
            prefix=prefix,
            numbering="(missing)",
            content=content,
            is_valid_format=False
        )

    def _build_title_from_match(
        self,
        line_num: int,
        line: str,
        config: LevelConfig,
        match: re.Match,
        is_valid: bool
    ) -> TitleInfo:
        """从正则匹配构建标题对象"""
        level = config.level
        prefix = config.prefix

        if level == Level.LEVEL_1:
            numbering = match.group(1)
            content = match.group(2)
        elif level == Level.LEVEL_2:
            numbering = f"{match.group(1)}.{match.group(2)}"
            content = match.group(3)
        elif level == Level.LEVEL_3:
            numbering = f"({match.group(1)})"
            content = match.group(2)
        else:  # LEVEL_4
            numbering = match.group(1)
            content = match.group(2)

        return TitleInfo(
            line_num=line_num,
            level=level,
            raw_line=line,
            prefix=prefix,
            numbering=numbering,
            content=content,
            is_valid_format=is_valid
        )


class TitleValidator:
    """标题验证器"""

    def __init__(self):
        self.parser = TitleParser()

    def validate(self, file_path: str) -> ValidationResult:
        """验证文件标题体系"""
        if not os.path.exists(file_path):
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    line=0,
                    error_type=ErrorType.FILE_NOT_FOUND,
                    level="N/A",
                    message=f"文件不存在: {file_path}",
                    severity=Severity.ERROR
                )],
                summary={"total_errors": 1, "total_warnings": 0, "error_by_type": {}}
            )

        # 解析标题
        titles = self.parser.parse_file(file_path)

        # 执行各类检查
        errors, warnings = self._run_all_checks(titles, file_path)

        # 统计信息
        title_count = self._count_titles(titles)
        summary = self._build_summary(errors, warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            title_count=title_count,
            summary=summary
        )

    def _run_all_checks(
        self,
        titles: List[TitleInfo],
        file_path: str
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """运行所有检查"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # P0 检查（必须通过）
        errors.extend(self._check_format_issues(titles))
        errors.extend(self._check_skip_level(titles))
        errors.extend(self._check_level_overflow(file_path))

        # 编号递增检查（包含错误和警告）
        inc_errors, inc_warnings = self._check_numbering_increment(titles)
        errors.extend(inc_errors)
        warnings.extend(inc_warnings)

        # P1 检查（建议通过）
        warnings.extend(self._check_numbering_order(titles))
        warnings.extend(self._check_empty_titles(titles))

        return errors, warnings

    def _count_titles(self, titles: List[TitleInfo]) -> Dict[str, int]:
        """统计各层级标题数量"""
        count = {f"level_{level.value}": 0 for level in Level}
        for title in titles:
            if title.level.value <= 4:
                count[f"level_{title.level.value}"] += 1
        return count

    def _build_summary(
        self,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> Dict:
        """构建汇总信息"""
        error_by_type: Dict[str, int] = {}

        for error in errors + warnings:
            error_type = error.error_type.value
            error_by_type[error_type] = error_by_type.get(error_type, 0) + 1

        return {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "error_by_type": error_by_type
        }

    def _check_format_issues(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 P0-1 格式问题"""
        errors = []

        for title in titles:
            if title.is_valid_format:
                continue

            # 区分"缺少编号"和"格式错误"
            if title.numbering == "(missing)":
                errors.append(self._create_missing_number_error(title))
            else:
                errors.append(self._create_format_error(title))

        return errors

    def _create_missing_number_error(self, title: TitleInfo) -> ValidationError:
        """创建缺少编号错误"""
        config = LEVEL_CONFIGS[title.level]
        hint = self._get_missing_number_hint(title.level)

        return ValidationError(
            line=title.line_num,
            error_type=ErrorType.FORMAT,
            level=f"Level {title.level.value}",
            message=(
                f"Level {title.level.value} 标题缺少编号："
                f"当前为 '{title.raw_line}'，"
                f"期望格式 '{config.expected_format}'（{hint}）"
            ),
            severity=Severity.ERROR
        )

    def _create_format_error(self, title: TitleInfo) -> ValidationError:
        """创建格式错误"""
        config = LEVEL_CONFIGS[title.level]
        hint = self._get_format_error_hint(title.level)

        return ValidationError(
            line=title.line_num,
            error_type=ErrorType.FORMAT,
            level=f"Level {title.level.value}",
            message=(
                f"Level {title.level.value} 标题格式错误："
                f"当前为 '{title.raw_line}'，"
                f"期望格式 '{config.expected_format}'（{hint}）"
            ),
            severity=Severity.ERROR
        )

    def _get_missing_number_hint(self, level: Level) -> str:
        """获取缺少编号的提示"""
        hints = {
            Level.LEVEL_1: "缺少编号，应在 ## 后添加形如 '1.' 的编号",
            Level.LEVEL_2: "缺少编号，应在 ### 后添加形如 '1.1' 的编号",
            Level.LEVEL_3: "缺少编号，应在 #### 后添加形如 '(1)' 的编号",
            Level.LEVEL_4: "缺少编号，应在 ##### 后添加形如 '①' 的带圈数字",
        }
        return hints[level]

    def _get_format_error_hint(self, level: Level) -> str:
        """获取格式错误的提示"""
        hints = {
            Level.LEVEL_1: "编号后需要点和空格",
            Level.LEVEL_2: "使用点分隔父级和子级，后跟空格",
            Level.LEVEL_3: "使用圆括号包裹数字，后跟空格",
            Level.LEVEL_4: "使用带圈数字 ①-⑳，后跟空格",
        }
        return hints[level]

    def _check_skip_level(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 P0-2 越级使用"""
        errors = []

        for i, title in enumerate(titles[1:], start=1):
            prev_title = titles[i - 1]

            if title.level.value > prev_title.level.value + 1:
                errors.append(ValidationError(
                    line=title.line_num,
                    error_type=ErrorType.SKIP_LEVEL,
                    level=f"Level {prev_title.level.value} → Level {title.level.value}",
                    message=(
                        f"标题越级使用："
                        f"第 {prev_title.line_num} 行是 Level {prev_title.level.value}，"
                        f"第 {title.line_num} 行直接跳到 Level {title.level.value}，"
                        f"违反层级递进规则"
                    ),
                    severity=Severity.ERROR
                ))

        return errors

    def _check_numbering_increment(
        self,
        titles: List[TitleInfo]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """检查编号递增"""
        errors = []
        warnings = []

        # 跟踪各级标题的编号状态
        level_1_last = 0
        level_2_last: Dict[int, int] = {}
        level_3_last = 0
        level_4_last = 0
        current_level_1: Optional[int] = None

        for title in titles:
            if title.numbering == "(missing)":
                continue

            if title.level == Level.LEVEL_1:
                level_1_last += 1
                num = int(title.numbering)
                if num != level_1_last:
                    errors.append(ValidationError(
                        line=title.line_num,
                        error_type=ErrorType.INCREMENT,
                        level="Level 1",
                        message=f"Level 1 标题编号错误：期望 {level_1_last}，实际 {num}",
                        severity=Severity.ERROR
                    ))
                # 无论如何都更新 current_level_1（即使编号错误）
                current_level_1 = num
                level_2_last = {}

            elif title.level == Level.LEVEL_2:
                result = self._check_level_2_increment(
                    title, current_level_1, level_2_last
                )
                # 注意：_check_level_2_increment 返回的是一个元组 (errors, warnings)
                # 而不是单个 ValidationError，因为一个标题可能同时有多个错误
                if isinstance(result, tuple):
                    err_list, warn_list = result
                    errors.extend(err_list)
                    warnings.extend(warn_list)
                elif result:
                    if result.severity == Severity.ERROR:
                        errors.append(result)
                    else:
                        warnings.append(result)

            elif title.level == Level.LEVEL_3:
                level_3_last += 1
                num = int(title.numbering.strip('()'))
                if num != level_3_last:
                    warnings.append(ValidationError(
                        line=title.line_num,
                        error_type=ErrorType.INCREMENT,
                        level="Level 3",
                        message=f"Level 3 标题编号错误：期望 {level_3_last}，实际 {num}",
                        severity=Severity.WARNING
                    ))

            elif title.level == Level.LEVEL_4:
                level_4_last += 1
                circled = title.numbering

                if circled not in CIRCLED_NUMBERS:
                    errors.append(ValidationError(
                        line=title.line_num,
                        error_type=ErrorType.FORMAT,
                        level="Level 4",
                        message=f"Level 4 标题使用了无效的带圈数字 '{circled}'，有效范围为 ①-⑳",
                        severity=Severity.ERROR
                    ))
                    continue

                expected_circled = CIRCLED_NUMBER_MAP.get(level_4_last, '?')
                if circled != expected_circled:
                    warnings.append(ValidationError(
                        line=title.line_num,
                        error_type=ErrorType.INCREMENT,
                        level="Level 4",
                        message=f"Level 4 标题编号错误：期望 {expected_circled}，实际 {circled}",
                        severity=Severity.WARNING
                    ))

        return errors, warnings

    def _check_level_2_increment(
        self,
        title: TitleInfo,
        current_level_1: Optional[int],
        level_2_last: Dict[int, int]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """检查 Level 2 编号递增"""
        errors = []
        warnings = []

        if current_level_1 is None:
            errors.append(ValidationError(
                line=title.line_num,
                error_type=ErrorType.PARENT_MISMATCH,
                level="Level 2",
                message="Level 2 标题没有父级 Level 1 标题",
                severity=Severity.ERROR
            ))
            return errors, warnings

        parts = title.numbering.split('.')
        parent_num = int(parts[0])
        child_num = int(parts[1])

        if parent_num != current_level_1:
            errors.append(ValidationError(
                line=title.line_num,
                error_type=ErrorType.PARENT_MISMATCH,
                level="Level 2",
                message=(
                    f"Level 2 标题父级编号错误："
                    f"当前在 Level 1 编号 {current_level_1} 下，"
                    f"但此标题父级为 {parent_num}"
                ),
                severity=Severity.ERROR
            ))

        # 更新该父级下的子级编号（即使父级不匹配也要更新）
        if parent_num not in level_2_last:
            level_2_last[parent_num] = 0
        level_2_last[parent_num] += 1

        if child_num != level_2_last[parent_num]:
            errors.append(ValidationError(
                line=title.line_num,
                error_type=ErrorType.INCREMENT,
                level="Level 2",
                message=(
                    f"Level 2 标题子级编号错误："
                    f"期望 {level_2_last[parent_num]}，实际 {child_num}"
                ),
                severity=Severity.ERROR
            ))

        return errors, warnings

    def _check_level_overflow(self, file_path: str) -> List[ValidationError]:
        """检查超出四级的标题"""
        errors = []

        for line_num, line in iter_code_aware_lines(file_path):
            if line.startswith("######"):
                errors.append(ValidationError(
                    line=line_num,
                    error_type=ErrorType.OVERFLOW,
                    level="Level 5+",
                    message="发现超过四级的标题（Level 5+），违反四级标题体系规范",
                    severity=Severity.ERROR
                ))

        return errors

    def _check_numbering_order(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 P1-3 编号顺序混乱"""
        warnings = []

        # 过滤掉无编号标题
        valid_titles = [t for t in titles if t.numbering != "(missing)"]

        # 按层级分组检查
        level_2_titles = [t for t in valid_titles if t.level == Level.LEVEL_2]
        level_3_titles = [t for t in valid_titles if t.level == Level.LEVEL_3]
        level_4_titles = [t for t in valid_titles if t.level == Level.LEVEL_4]

        warnings.extend(self._check_level_2_order(level_2_titles))
        warnings.extend(self._check_level_3_order(level_3_titles))
        warnings.extend(self._check_level_4_order(level_4_titles))

        return warnings

    def _check_level_2_order(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 Level 2 编号顺序"""
        warnings = []

        for i in range(1, len(titles)):
            current = titles[i]
            prev = titles[i - 1]

            current_parts = current.numbering.split('.')
            prev_parts = prev.numbering.split('.')

            current_parent = int(current_parts[0])
            current_child = int(current_parts[1])
            prev_parent = int(prev_parts[0])
            prev_child = int(prev_parts[1])

            if current_parent == prev_parent and current_child < prev_child:
                warnings.append(ValidationError(
                    line=current.line_num,
                    error_type=ErrorType.ORDER,
                    level="Level 2",
                    message=(
                        f"Level 2 标题编号顺序混乱："
                        f"{current.numbering} 出现在 {prev.numbering} 之前"
                        f"（第 {prev.line_num} 行）"
                    ),
                    severity=Severity.WARNING
                ))

        return warnings

    def _check_level_3_order(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 Level 3 编号顺序"""
        warnings = []

        for i in range(1, len(titles)):
            current = titles[i]
            prev = titles[i - 1]

            current_num = int(current.numbering.strip('()'))
            prev_num = int(prev.numbering.strip('()'))

            if current_num < prev_num:
                warnings.append(ValidationError(
                    line=current.line_num,
                    error_type=ErrorType.ORDER,
                    level="Level 3",
                    message=(
                        f"Level 3 标题编号顺序混乱："
                        f"{current.numbering} 出现在 {prev.numbering} 之前"
                        f"（第 {prev.line_num} 行）"
                    ),
                    severity=Severity.WARNING
                ))

        return warnings

    def _check_level_4_order(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 Level 4 编号顺序"""
        warnings = []

        for i in range(1, len(titles)):
            current = titles[i]
            prev = titles[i - 1]

            current_num = CIRCLED_NUMBERS.get(current.numbering, 0)
            prev_num = CIRCLED_NUMBERS.get(prev.numbering, 0)

            if current_num < prev_num:
                warnings.append(ValidationError(
                    line=current.line_num,
                    error_type=ErrorType.ORDER,
                    level="Level 4",
                    message=(
                        f"Level 4 标题编号顺序混乱："
                        f"{current.numbering} 出现在 {prev.numbering} 之前"
                        f"（第 {prev.line_num} 行）"
                    ),
                    severity=Severity.WARNING
                ))

        return warnings

    def _check_empty_titles(self, titles: List[TitleInfo]) -> List[ValidationError]:
        """检查 P1-4 空标题"""
        warnings = []

        for title in titles:
            if not title.content or title.content.strip() == '':
                warnings.append(ValidationError(
                    line=title.line_num,
                    error_type=ErrorType.EMPTY,
                    level=f"Level {title.level.value}",
                    message=f"Level {title.level.value} 标题为空：{title.raw_line}",
                    severity=Severity.WARNING
                ))

        return warnings


# ============================================================================
# 工具函数
# ============================================================================

def iter_code_aware_lines(file_path: str):
    """
    逐行读取 markdown 文件，自动跳过"代码围栏"内部的行。

    遵循 CommonMark 围栏代码块语义：
    - 一行若以 ≥3 个反引号开头（允许最多 3 空格缩进），则开启一个代码块
    - 只有遇到"相同数量反引号"的围栏行，才关闭该代码块
    - 在任何代码块开启期间，所有行都不产出（跳过）

    Yields:
        (line_num, line) —— 仅产出不在代码块内的行，line 已 rstrip
    """
    fence_len = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.rstrip()

            if fence_len > 0:
                close_match = re.match(r'^ {0,3}`{%d}' % fence_len, line)
                if close_match:
                    next_char = line[close_match.end():close_match.end()+1] if close_match.end() < len(line) else ''
                    if next_char != '`':
                        after_backticks = line[close_match.end():].strip()
                        if not after_backticks or after_backticks.isspace():
                            fence_len = 0
                continue

            open_match = FENCE_OPEN_RE.match(line)
            if open_match:
                fence_len = len(open_match.group(1))
                continue

            yield line_num, line


# ============================================================================
# 主函数
# ============================================================================

def validate_titles(file_path: str) -> Dict:
    """
    验证文档的标题体系

    Args:
        file_path: Markdown 文件路径

    Returns:
        验证结果字典
    """
    validator = TitleValidator()
    result = validator.validate(file_path)
    return result.to_dict()


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_titles.py <markdown_file_path>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    result = validate_titles(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
