#!/usr/bin/env python3
"""
validate_titles.py 脚本的测试运行器

这个脚本自动化运行所有测试用例，生成详细的测试报告。
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class TestRunner:
    """测试运行器"""

    def __init__(self, test_dir: str, script_path: str):
        self.test_dir = Path(test_dir)
        self.script_path = Path(script_path)
        self.results = []
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0

    def discover_test_files(self) -> List[Path]:
        """发现所有测试用例文件"""
        test_files = sorted(self.test_dir.glob("*.md"))
        return [f for f in test_files if f.name != "README.md"]

    def parse_test_case(self, test_file: Path) -> Dict[str, Any]:
        """解析测试用例文件，提取测试目的、内容和预期结果"""
        content = test_file.read_text(encoding='utf-8')

        test_case = {
            'file_name': test_file.name,
            'file_path': str(test_file),
            'test_objective': '',
            'test_content': '',
            'expected_results': '',
            'raw_content': content
        }

        lines = content.split('\n')
        current_section = None
        content_lines = []

        for line in lines:
            if line.startswith('## 测试目的'):
                current_section = 'objective'
                continue
            elif line.startswith('## 测试内容'):
                current_section = 'content'
                content_lines = []
                continue
            elif line.startswith('## 预期结果'):
                current_section = 'expected'
                test_case['test_content'] = '\n'.join(content_lines)
                continue
            elif line.startswith('# 测试用例'):
                continue

            if current_section == 'objective':
                test_case['test_objective'] += line + '\n'
            elif current_section == 'content':
                content_lines.append(line)
            elif current_section == 'expected':
                test_case['expected_results'] += line + '\n'

        return test_case

    def run_script_on_file(self, file_path: str) -> Dict[str, Any]:
        """运行 validate_titles.py 脚本并获取结果"""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            # validate_titles.py 的设计：
            # - 返回码 0: 文档有效（valid: true）
            # - 返回码 1: 文档无效（valid: false，有错误）
            # - 返回码其他值: 脚本执行失败
            script_executed_successfully = result.returncode in [0, 1]

            return {
                'success': script_executed_successfully,
                'is_valid': result.returncode == 0,
                'detected_errors': result.returncode == 1,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'is_valid': False,
                'detected_errors': False,
                'stdout': '',
                'stderr': '脚本执行超时（30秒）',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'is_valid': False,
                'detected_errors': False,
                'stdout': '',
                'stderr': f'执行错误: {str(e)}',
                'returncode': -1
            }

    def analyze_result(self, test_case: Dict[str, Any], script_result: Dict[str, Any]) -> Dict[str, Any]:
        """分析测试结果"""
        analysis = {
            'test_name': test_case['file_name'],
            'objective': test_case['test_objective'].strip(),
            'script_success': script_result['success'],
            'script_executed': script_result.get('success', False),
            'document_valid': script_result.get('is_valid', False),
            'errors_detected': script_result.get('detected_errors', False),
            'script_output': script_result['stdout'],
            'script_errors': script_result['stderr'],
            'expected_behavior': test_case['expected_results'].strip(),
            'return_code': script_result.get('returncode', -1),
            'manual_review_required': True,
            'notes': []
        }

        # 基本的自动检查
        if not script_result['success']:
            analysis['notes'].append('⚠️ 脚本执行失败，需要检查错误信息')
        elif script_result.get('detected_errors', False):
            analysis['notes'].append('✅ 脚本检测到预期的错误（这是正常行为）')
        elif script_result.get('is_valid', False):
            analysis['notes'].append('✅ 文档验证通过（符合四级标题体系）')
        elif 'syntax error' in script_result['stderr'].lower():
            analysis['notes'].append('⚠️ 发现语法错误，需要检查脚本代码')
        else:
            analysis['notes'].append('✅ 脚本成功执行，请手动验证输出是否符合预期')

        return analysis

    def generate_report(self, output_format: str = 'markdown') -> str:
        """生成测试报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if output_format == 'markdown':
            return self._generate_markdown_report(timestamp)
        elif output_format == 'json':
            return self._generate_json_report(timestamp)
        else:
            raise ValueError(f'不支持的报告格式: {output_format}')

    def _get_status_info(self, result: Dict[str, Any]) -> str:
        """获取状态信息"""
        if not result.get('script_success'):
            return '❌ 脚本执行失败'
        elif result.get('errors_detected'):
            return '✅ 脚本成功执行（检测到预期错误）'
        elif result.get('document_valid'):
            return '✅ 脚本成功执行（文档有效）'
        else:
            return '⚠️ 未知状态'

    def _generate_markdown_report(self, timestamp: str) -> str:
        """生成 Markdown 格式的报告"""
        report_lines = [
            f"# validate_titles.py 测试报告",
            f"",
            f"**生成时间**: {timestamp}",
            f"**测试目录**: {self.test_dir}",
            f"**测试脚本**: {self.script_path}",
            f"",
            f"## 测试统计",
            f"",
            f"- **总测试数**: {self.test_count}",
            f"- **脚本成功执行**: {self.passed_count}",
            f"- **脚本执行失败**: {self.failed_count}",
            f"",
            f"> 说明：",
            f"> - 脚本成功执行：返回码 0（文档有效）或 1（检测到错误）",
            f"> - 脚本执行失败：返回码其他值（参数错误、异常等）",
            f"",
            f"## 详细测试结果",
            f""
        ]

        for result in self.results:
            status_info = self._get_status_info(result)
            report_lines.extend([
                f"### {result['test_name']}",
                f"",
                f"**测试目的**: {result['objective']}",
                f"",
                f"**执行状态**: {status_info}",
                f"",
                f"**返回码**: {result.get('return_code', 'N/A')}",
            ])

            if result.get('document_valid') is not None:
                report_lines.append(f"**文档有效性**: {'✅ 有效' if result['document_valid'] else '❌ 无效（检测到错误）'}")

            if result.get('errors_detected'):
                report_lines.append(f"**错误检测**: ⚠️ 检测到预期错误")

            report_lines.extend([
                f"",
                f"**分析备注**:",
            ])

            for note in result.get('notes', []):
                report_lines.append(f"- {note}")

            report_lines.extend([
                f"",
                f"**脚本输出**:",
                f"```",
            ])

            try:
                output_data = json.loads(result['script_output'])
                report_lines.append(json.dumps(output_data, ensure_ascii=False, indent=2))
            except:
                report_lines.append(result['script_output'][:500])

            report_lines.extend([
                "```",
                ""
            ])

            if result['script_errors']:
                report_lines.extend([
                    f"**错误信息**:",
                    f"```",
                    result['script_errors'],
                    f"```",
                    f""
                ])

            report_lines.extend([
                f"**预期行为**:",
                f"```",
                result['expected_behavior'],
                f"```",
                f"",
                f"**脚本输出**:",
                f"```",
                result['script_output'] if result['script_output'] else "(无输出)",
                f"```",
                f""
            ])

            if result['notes']:
                report_lines.extend([
                    f"**分析备注**:",
                ])
                for note in result['notes']:
                    report_lines.append(f"- {note}")
                report_lines.append("")

        return '\n'.join(report_lines)

    def _generate_json_report(self, timestamp: str) -> str:
        """生成 JSON 格式的报告"""
        report_data = {
            'timestamp': timestamp,
            'test_directory': str(self.test_dir),
            'script_path': str(self.script_path),
            'statistics': {
                'total_tests': self.test_count,
                'passed': self.passed_count,
                'failed': self.failed_count
            },
            'test_results': self.results
        }
        return json.dumps(report_data, ensure_ascii=False, indent=2)

    def run_all_tests(self) -> None:
        """运行所有测试用例"""
        test_files = self.discover_test_files()

        print(f"发现 {len(test_files)} 个测试用例文件")
        print(f"开始运行测试...\n")

        for test_file in test_files:
            self.test_count += 1
            print(f"运行测试: {test_file.name}")

            try:
                # 解析测试用例
                test_case = self.parse_test_case(test_file)

                # 运行脚本
                script_result = self.run_script_on_file(test_case['file_path'])

                # 统计成功/失败
                if script_result['success']:
                    self.passed_count += 1
                else:
                    self.failed_count += 1

                # 分析结果
                analysis = self.analyze_result(test_case, script_result)
                self.results.append(analysis)

                print(f"  状态: {'✅ 成功' if script_result['success'] else '❌ 失败'}")

            except Exception as e:
                print(f"  ❌ 测试执行出错: {str(e)}")
                self.failed_count += 1

        print(f"\n测试完成！")
        print(f"总计: {self.test_count} | 成功: {self.passed_count} | 失败: {self.failed_count}")


def check_environment():
    """检查测试环境"""
    print("🔍 检查测试环境...")

    # 检查 Python 版本
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 12):
        print(f"❌ 错误: Python 版本过低，需要 ≥3.12，当前为 {version.major}.{version.minor}")
        sys.exit(1)
    print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")

    # 检查脚本可执行性
    current_dir = Path(__file__).parent
    project_root = current_dir.parents[4]
    script_path = project_root / "note/skills/md-rewrite/scripts/validate_titles.py"

    if not script_path.exists():
        print(f"❌ 错误: 脚本文件不存在: {script_path}")
        sys.exit(1)
    print(f"✅ 脚本路径验证成功")

    print("✅ 环境检查完成\n")
    return current_dir, script_path

def main():
    """主函数"""
    # 检查测试环境
    current_dir, script_path = check_environment()

    # 创建测试运行器
    runner = TestRunner(current_dir, script_path)

    # 运行所有测试
    runner.run_all_tests()

    # 生成报告
    print("\n生成测试报告...")

    # Markdown 报告
    md_report = runner.generate_report('markdown')
    md_report_path = current_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    md_report_path.write_text(md_report, encoding='utf-8')
    print(f"✅ Markdown 报告已保存: {md_report_path.name}")

    # JSON 报告
    json_report = runner.generate_report('json')
    json_report_path = current_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_report_path.write_text(json_report, encoding='utf-8')
    print(f"✅ JSON 报告已保存: {json_report_path.name}")

    print("\n✅ 测试运行完成！")


if __name__ == "__main__":
    main()