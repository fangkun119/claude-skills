#!/usr/bin/env python3
"""
A/B 对比测试脚本
用于验证原版和重构版的输出是否完全一致
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestResult:
    """测试结果"""
    test_file: str
    passed: bool
    original_valid: bool
    refactored_valid: bool
    original_errors: int
    refactored_errors: int
    original_warnings: int
    refactored_warnings: int
    diff_details: str = ""
    error_message: str = ""


class ABComparator:
    """A/B 对比测试器"""

    def __init__(self, scripts_dir: Path, fixtures_dir: Path):
        self.scripts_dir = scripts_dir
        self.fixtures_dir = fixtures_dir
        self.original_script = scripts_dir / "validate_titles.py"
        self.refactored_script = scripts_dir / "validate_titles_refactored.py"

        # 检查脚本是否存在
        if not self.original_script.exists():
            raise FileNotFoundError(f"原版脚本不存在: {self.original_script}")
        if not self.refactored_script.exists():
            raise FileNotFoundError(f"重构版脚本不存在: {self.refactored_script}")

    def run_test(self, test_file: Path) -> TestResult:
        """运行单个测试"""
        print(f"  测试: {test_file.name}...", end=" ")

        try:
            # 运行原版
            original_result = self._run_script(self.original_script, test_file)
            refactored_result = self._run_script(self.refactored_script, test_file)

            # 对比结果
            passed, diff_details = self._compare_results(
                original_result,
                refactored_result,
                test_file.name
            )

            if passed:
                print("✅ PASS")
                return TestResult(
                    test_file=str(test_file),
                    passed=True,
                    original_valid=original_result.get("valid", False),
                    refactored_valid=refactored_result.get("valid", False),
                    original_errors=len(original_result.get("errors", [])),
                    refactored_errors=len(refactored_result.get("errors", [])),
                    original_warnings=len(original_result.get("warnings", [])),
                    refactored_warnings=len(refactored_result.get("warnings", [])),
                )
            else:
                print("❌ FAIL")
                return TestResult(
                    test_file=str(test_file),
                    passed=False,
                    original_valid=original_result.get("valid", False),
                    refactored_valid=refactored_result.get("valid", False),
                    original_errors=len(original_result.get("errors", [])),
                    refactored_errors=len(refactored_result.get("errors", [])),
                    original_warnings=len(original_result.get("warnings", [])),
                    refactored_warnings=len(refactored_result.get("warnings", [])),
                    diff_details=diff_details,
                    error_message="输出不一致"
                )

        except Exception as e:
            print(f"⚠️  ERROR: {e}")
            return TestResult(
                test_file=str(test_file),
                passed=False,
                original_valid=False,
                refactored_valid=False,
                original_errors=0,
                refactored_errors=0,
                original_warnings=0,
                refactored_warnings=0,
                error_message=str(e)
            )

    def _run_script(self, script: Path, test_file: Path) -> Dict:
        """运行脚本并返回结果"""
        result = subprocess.run(
            [sys.executable, str(script), str(test_file)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode not in [0, 1]:  # 0=valid, 1=invalid
            raise RuntimeError(f"脚本异常退出: {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON 解析失败: {e}\n输出: {result.stdout}")

    def _compare_results(
        self,
        original: Dict,
        refactored: Dict,
        test_name: str
    ) -> Tuple[bool, str]:
        """对比两个结果"""
        diff_details = []

        # 对比顶层字段
        if original.get("valid") != refactored.get("valid"):
            diff_details.append(f"  valid 字段不一致: {original.get('valid')} vs {refactored.get('valid')}")

        # 对比错误数量
        orig_errors = original.get("errors", [])
        refac_errors = refactored.get("errors", [])

        if len(orig_errors) != len(refac_errors):
            diff_details.append(f"  错误数量不一致: {len(orig_errors)} vs {len(refac_errors)}")
        else:
            # 逐个对比错误
            for i, (orig_err, refac_err) in enumerate(zip(orig_errors, refac_errors)):
                if orig_err != refac_err:
                    diff_details.append(f"  错误[{i}] 不一致:")
                    diff_details.append(f"    原版: {orig_err}")
                    diff_details.append(f"    重构: {refac_err}")

        # 对比警告数量
        orig_warnings = original.get("warnings", [])
        refac_warnings = refactored.get("warnings", [])

        if len(orig_warnings) != len(refac_warnings):
            diff_details.append(f"  警告数量不一致: {len(orig_warnings)} vs {len(refac_warnings)}")
        else:
            # 逐个对比警告
            for i, (orig_warn, refac_warn) in enumerate(zip(orig_warnings, refac_warnings)):
                if orig_warn != refac_warn:
                    diff_details.append(f"  警告[{i}] 不一致:")
                    diff_details.append(f"    原版: {orig_warn}")
                    diff_details.append(f"    重构: {refac_warn}")

        # 对比标题统计
        orig_count = original.get("title_count", {})
        refac_count = refactored.get("title_count", {})

        if orig_count != refac_count:
            diff_details.append(f"  标题统计不一致:")
            diff_details.append(f"    原版: {orig_count}")
            diff_details.append(f"    重构: {refac_count}")

        # 对比汇总
        orig_summary = original.get("summary", {})
        refac_summary = refactored.get("summary", {})

        if orig_summary != refac_summary:
            diff_details.append(f"  汇总信息不一致:")
            diff_details.append(f"    原版: {orig_summary}")
            diff_details.append(f"    重构: {refac_summary}")

        return len(diff_details) == 0, "\n".join(diff_details)

    def run_all_tests(self) -> List[TestResult]:
        """运行所有测试"""
        print(f"\n{'='*60}")
        print("A/B 对比测试")
        print(f"{'='*60}")
        print(f"原版脚本: {self.original_script}")
        print(f"重构脚本: {self.refactored_script}")
        print(f"测试目录: {self.fixtures_dir}")
        print(f"{'='*60}\n")

        # 获取所有测试文件
        test_files = sorted(self.fixtures_dir.glob("*.md"))

        if not test_files:
            print(f"⚠️  未找到测试文件 (*.md) 在 {self.fixtures_dir}")
            return []

        print(f"找到 {len(test_files)} 个测试文件\n")

        results = []
        for test_file in test_files:
            result = self.run_test(test_file)
            results.append(result)

        return results

    def print_summary(self, results: List[TestResult]):
        """打印测试摘要"""
        print(f"\n{'='*60}")
        print("测试摘要")
        print(f"{'='*60}")

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        print(f"\n总计: {total} 个测试")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")

        if failed > 0:
            print(f"\n失败的测试:")
            for result in results:
                if not result.passed:
                    print(f"\n  ❌ {Path(result.test_file).name}")
                    if result.error_message:
                        print(f"     错误: {result.error_message}")
                    if result.diff_details:
                        print(f"     差异:")
                        for line in result.diff_details.split('\n'):
                            print(f"       {line}")

        # 统计信息
        print(f"\n{'='*60}")
        print("统计信息")
        print(f"{'='*60}")

        total_orig_errors = sum(r.original_errors for r in results)
        total_refac_errors = sum(r.refactored_errors for r in results)
        total_orig_warnings = sum(r.original_warnings for r in results)
        total_refac_warnings = sum(r.refactored_warnings for r in results)

        print(f"\n错误总数:")
        print(f"  原版: {total_orig_errors}")
        print(f"  重构: {total_refac_errors}")

        print(f"\n警告总数:")
        print(f"  原版: {total_orig_warnings}")
        print(f"  重构: {total_refac_warnings}")

        # 最终结果
        print(f"\n{'='*60}")
        if failed == 0:
            print("🎉 所有测试通过！重构版与原版输出完全一致！")
        else:
            print(f"❌ 有 {failed} 个测试失败，需要修复")
        print(f"{'='*60}\n")

        return failed == 0


def main():
    """主函数"""
    # 获取脚本目录
    script_dir = Path(__file__).parent.parent
    fixtures_dir = script_dir / "tests" / "fixtures"

    try:
        comparator = ABComparator(script_dir, fixtures_dir)
        results = comparator.run_all_tests()
        success = comparator.print_summary(results)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
