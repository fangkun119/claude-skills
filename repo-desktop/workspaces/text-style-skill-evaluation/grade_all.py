#!/usr/bin/env python3
"""
Grading script for text-style skill evals.
Checks assertions against generated HTML outputs.
"""

import json
import os
import sys
from pathlib import Path


def load_output_file(outputs_dir):
    """Load the content from output files."""
    outputs_path = Path(outputs_dir)
    content = ""

    # Look for HTML or MD files
    for file in outputs_path.glob("*"):
        if file.suffix in [".html", ".md"]:
            content += file.read_text(encoding="utf-8")

    return content


def check_assertion(assertion, content):
    """Check if an assertion passes against the content."""
    name = assertion["name"]
    check_type = assertion["check_type"]
    expected = assertion["expected"]

    if check_type == "content_check":
        if isinstance(expected, str):
            passed = expected in content
        else:
            passed = any(e in content for e in expected)
    elif check_type == "forbidden_check":
        if isinstance(expected, str):
            passed = expected not in content
        else:
            passed = all(e not in content for e in expected)
    else:
        passed = False

    return {
        "text": name,
        "passed": passed,
        "evidence": f"Check type: {check_type}, Expected: {expected}"
    }


def grade_run(eval_dir):
    """Grade a single eval run."""
    metadata_path = Path(eval_dir) / "eval_metadata.json"
    outputs_dir = Path(eval_dir) / "outputs"

    if not metadata_path.exists():
        return None

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    content = load_output_file(outputs_dir)

    results = []
    for assertion in metadata.get("assertions", []):
        result = check_assertion(assertion, content)
        results.append(result)

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    return {
        "eval_name": metadata.get("eval_name", "unknown"),
        "prompt": metadata.get("prompt", ""),
        "assertion_results": results,
        "passed": passed_count,
        "total": total_count,
        "pass_rate": passed_count / total_count if total_count > 0 else 0.0
    }


def main():
    """Grade all eval runs in the iteration directory."""
    iteration_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    grading_results = {}

    for eval_dir in iteration_dir.iterdir():
        if eval_dir.is_dir() and eval_dir.name.startswith("eval-"):
            result = grade_run(eval_dir)
            if result:
                grading_results[eval_dir.name] = result

                # Save individual grading.json
                grading_file = eval_dir / "grading.json"
                with open(grading_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "eval_name": result["eval_name"],
                        "prompt": result["prompt"],
                        "expectations": result["assertion_results"],
                        "summary": {
                            "passed": result["passed"],
                            "total": result["total"],
                            "pass_rate": result["pass_rate"]
                        }
                    }, f, indent=2, ensure_ascii=False)

                print(f"{eval_dir.name}: {result['passed']}/{result['total']} passed ({result['pass_rate']:.1%})")


if __name__ == "__main__":
    main()
