import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.table import Table
from rich.text import Text

import parselmouth as p9h


ROOT = Path(__file__).resolve().parent
CLI = ROOT / "cli.py"
QUOTE_RE = "'|\""
DOC_INDEX_RE = "'|\"|system|id|a|b"
DOC_INDEX_SCALE_RE = "os|sys|'|\"|b"


@dataclass(frozen=True)
class StressCase:
    name: str
    payload: str
    covers: tuple[str, ...]
    re_rule: str = ""
    rule: tuple[str, ...] = ()
    extra_args: tuple[str, ...] = ()
    specify_bypass: dict = field(default_factory=dict)


def method_id(cls_name, func_name):
    return f"{cls_name}.{func_name}"


def method_case(
    cls_name,
    func_name,
    payload,
    *,
    re_rule="",
    rule=(),
    extra_args=(),
    name=None,
):
    return StressCase(
        name=name or method_id(cls_name, func_name),
        payload=payload,
        covers=(method_id(cls_name, func_name),),
        re_rule=re_rule,
        rule=tuple(rule),
        extra_args=tuple(extra_args),
        specify_bypass={"white": {cls_name: func_name}},
    )


def inventory_methods():
    result = []
    for cls_name, cls in vars(p9h.bypass_tools).items():
        if not cls_name.startswith("Bypass_"):
            continue
        if cls_name == "Bypass_Call":
            func_names = cls.dynamic_func_names()
        else:
            func_names = [name for name in cls.__dict__ if name.startswith("by_")]

        for func_name in func_names:
            result.append(method_id(cls_name, func_name))

    return tuple(result)


def coverage_cases():
    return [
        method_case("Bypass_Int", "by_trans", "1", re_rule=r"1"),
        method_case("Bypass_Int", "by_bin", "9", re_rule=r"9"),
        method_case("Bypass_Int", "by_hex", "19", re_rule=r"9"),
        method_case("Bypass_Int", "by_cal", "2024", re_rule=r"[01345678]"),
        method_case("Bypass_Int", "by_ord", "10", re_rule=r"0|1"),
        method_case("Bypass_Int", "by_unicode", "2024", re_rule=r"[0-9]"),
        method_case("Bypass_String", "by_empty_str", "''", re_rule=QUOTE_RE),
        method_case("Bypass_String", "by_quote_trans", "'macr0phag3'", re_rule=r"'"),
        method_case("Bypass_String", "by_char_add", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_dict", "'macr0phag3'", re_rule=QUOTE_RE),
        method_case("Bypass_String", "by_hex_encode", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_unicode_encode", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_char_format", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_format", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_char", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_reverse", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_bytes_single", "'macr0phag3'", re_rule=r"mac"),
        method_case("Bypass_String", "by_bytes_full", "'macr0phag3'", re_rule=r"mac"),
        method_case(
            "Bypass_String",
            "by_doc_index",
            "'system'",
            re_rule=DOC_INDEX_RE,
        ),
        method_case("Bypass_Name", "by_unicode", "__import__", re_rule=r"__"),
        method_case(
            "Bypass_Name",
            "by_builtins_attr",
            "__import__",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Name",
            "by_builtins_item",
            "__import__",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Name",
            "by_builtin_func_self",
            "__import__",
            re_rule=r"^__import__$|id",
        ),
        method_case(
            "Bypass_Name",
            "by_frame",
            "__import__",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Name",
            "by_running_frame",
            "__import__",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Attribute",
            "by_getattr",
            "str.find",
            re_rule=r"find",
        ),
        method_case(
            "Bypass_Attribute",
            "by_vars",
            "str.find",
            re_rule=r"find",
        ),
        method_case(
            "Bypass_Attribute",
            "by_dict_attr",
            "str.find",
            re_rule=r"find",
        ),
        method_case(
            "Bypass_Subscript",
            "by_getitem_attr",
            "a[0]",
            re_rule=r"\[",
        ),
        method_case(
            "Bypass_Subscript",
            "by_getitem_getattr",
            "a[0]",
            re_rule=r"\[",
        ),
        method_case(
            "Bypass_Call",
            "by_unicode",
            "__import__('os')",
            re_rule=r"__",
        ),
        method_case(
            "Bypass_Call",
            "by_builtins_attr",
            "__import__('os')",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Call",
            "by_builtins_item",
            "__import__('os')",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Call",
            "by_builtin_func_self",
            "__import__('os')",
            re_rule=r"^__import__$|id",
        ),
        method_case(
            "Bypass_Call",
            "by_frame",
            "__import__('os')",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Call",
            "by_running_frame",
            "__import__('os')",
            re_rule=r"^__import__$",
        ),
        method_case(
            "Bypass_Call",
            "by_getattr",
            "str.find('s')",
            re_rule=r"find",
        ),
        method_case(
            "Bypass_Call",
            "by_vars",
            "str.find('s')",
            re_rule=r"find",
        ),
        method_case(
            "Bypass_Call",
            "by_dict_attr",
            "str.find('s')",
            re_rule=r"find",
        ),
        method_case(
            "Bypass_Keyword",
            "by_unicode",
            "f(test=1)",
            re_rule=r"test",
        ),
        method_case(
            "Bypass_BoolOp",
            "by_bitwise",
            "a and b",
            re_rule=r"and",
        ),
        method_case(
            "Bypass_BoolOp",
            "by_arithmetic",
            "a or b",
            re_rule=r"or",
        ),
    ]


def extended_cases():
    cases = [
        method_case(
            "Bypass_Int",
            "by_cal",
            "2024",
            re_rule=r"[01345678]",
            extra_args=("--shortest",),
            name="Bypass_Int.by_cal shortest",
        ),
        method_case(
            "Bypass_String",
            "by_doc_index",
            "'systemsystemsystem'",
            re_rule=DOC_INDEX_RE,
            extra_args=("--shortest",),
            name="Bypass_String.by_doc_index shortest",
        ),
        method_case(
            "Bypass_String",
            "by_doc_index",
            "'systemsystemsystem'",
            re_rule=DOC_INDEX_RE,
            extra_args=("--minset",),
            name="Bypass_String.by_doc_index minset",
        ),
        method_case(
            "Bypass_Name",
            "by_builtin_func_self",
            "__import__",
            re_rule=r"^__import__$|id",
            extra_args=("--minset",),
            name="Bypass_Name.by_builtin_func_self minset",
        ),
        method_case(
            "Bypass_BoolOp",
            "by_bitwise",
            "a or b",
            re_rule=r"or",
            name="Bypass_BoolOp.by_bitwise or-branch",
        ),
        method_case(
            "Bypass_BoolOp",
            "by_arithmetic",
            "a and b",
            re_rule=r"and",
            name="Bypass_BoolOp.by_arithmetic and-branch",
        ),
    ]

    for depth in [5, 10, 20, 40]:
        payload = ".".join(["a", *[f"x{i}" for i in range(depth)]])
        cases.append(
            StressCase(
                name=f"Bypass_Attribute.by_getattr depth={depth}",
                payload=payload,
                covers=(),
                re_rule=r"\.",
                specify_bypass={"white": {"Bypass_Attribute": "by_getattr"}},
            )
        )

    for depth in [4, 8, 16, 32]:
        payload = "a" + "".join(f"[{i}]" for i in range(depth))
        cases.append(
            StressCase(
                name=f"Bypass_Subscript.by_getitem_attr depth={depth}",
                payload=payload,
                covers=(),
                re_rule=r"\[",
                specify_bypass={"white": {"Bypass_Subscript": "by_getitem_attr"}},
            )
        )
        cases.append(
            StressCase(
                name=f"Bypass_Subscript.by_getitem_getattr depth={depth}",
                payload=payload,
                covers=(),
                re_rule=r"\[",
                specify_bypass={"white": {"Bypass_Subscript": "by_getitem_getattr"}},
            )
        )

    for count in [1, 3, 6, 12]:
        payload = repr("system" * count)
        cases.append(
            StressCase(
                name=f"Bypass_String.by_doc_index len={len('system' * count)}",
                payload=payload,
                covers=(),
                re_rule=DOC_INDEX_SCALE_RE,
                specify_bypass={"white": {"Bypass_String": "by_doc_index"}},
            )
        )

    for count in [1, 2, 4, 8]:
        payload = repr("macr0phag3" * count)
        for func_name in ["by_format", "by_char_format", "by_reverse"]:
            cases.append(
                StressCase(
                    name=f"Bypass_String.{func_name} len={10 * count}",
                    payload=payload,
                    covers=(),
                    re_rule=r"mac",
                    specify_bypass={"white": {"Bypass_String": func_name}},
                )
            )

    for depth in [3, 5, 8, 12]:
        payload = ".".join(["a", *[f"x{i}" for i in range(depth)]])
        cases.append(
            StressCase(
                name=f"Bypass_Attribute.by_vars attr-depth={depth}",
                payload=payload,
                covers=(),
                re_rule=r"\.",
                specify_bypass={"white": {"Bypass_Attribute": "by_vars"}},
            )
        )

    for func_name in ["by_getattr", "by_vars", "by_dict_attr"]:
        for depth in [1, 2, 3, 4]:
            chain = ".".join(
                ["popen('whoami')", *[f"read({2020 + i})" for i in range(depth)]]
            )
            cases.append(
                StressCase(
                    name=f"Bypass_Call.{func_name} call-chain depth={depth}",
                    payload=f"__import__('os').{chain}",
                    covers=(),
                    re_rule=r"\(",
                    specify_bypass={"white": {"Bypass_Call": func_name}},
                )
            )

    return cases


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run stress tests for every bypass method."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="timeout in seconds for each cli.py run",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="run depth/length/pathological stress cases after the full method coverage suite",
    )
    parser.add_argument(
        "--match",
        default="",
        help="only run cases whose name contains this substring",
    )
    parser.add_argument(
        "--show-command",
        action="store_true",
        help="print the generated cli.py command for each case",
    )
    parser.add_argument(
        "--no-coverage-check",
        action="store_true",
        help="do not fail when the default registry does not cover every bypass method",
    )
    return parser.parse_args(argv)


def build_command(case):
    cmd = [
        sys.executable,
        str(CLI),
        "--payload",
        case.payload,
    ]

    if case.re_rule:
        cmd.extend(["--re-rule", case.re_rule])

    if case.rule:
        cmd.append("--rule")
        cmd.extend(case.rule)

    if case.specify_bypass:
        cmd.extend(
            [
                "--specify-bypass",
                json.dumps(case.specify_bypass, ensure_ascii=False),
            ]
        )

    cmd.extend(case.extra_args)
    return cmd


def detect_summary(output):
    if "status  success" in output or "status   success" in output:
        return "success"
    if "status  failed" in output or "status   failed" in output:
        return "failed"
    return "unknown"


def run_case(case, timeout, show_command=False):
    cmd = build_command(case)

    if show_command:
        command_line = Text("  $ ")
        command_line.append(shlex.join(cmd))
        p9h.console.print(command_line)

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - start
        return {
            "name": case.name,
            "covers": case.covers,
            "runtime": duration,
            "status": "timeout",
            "summary": "unknown",
            "stdout_len": 0,
            "stderr_len": 0,
            "returncode": None,
        }

    duration = time.perf_counter() - start
    output = proc.stdout + proc.stderr
    return {
        "name": case.name,
        "covers": case.covers,
        "runtime": duration,
        "status": "ok" if proc.returncode == 0 else f"rc={proc.returncode}",
        "summary": detect_summary(output),
        "stdout_len": len(proc.stdout),
        "stderr_len": len(proc.stderr),
        "returncode": proc.returncode,
    }


def build_results_table(results):
    table = Table(title="Stress Test Report")
    table.add_column("case", style="bold white", no_wrap=True, overflow="ellipsis")
    table.add_column("run", justify="center", no_wrap=True)
    table.add_column("result", justify="center", no_wrap=True)
    table.add_column("time", justify="right", no_wrap=True)
    table.add_column("stdout", justify="right", no_wrap=True)
    table.add_column("stderr", justify="right", no_wrap=True)

    for result in results:
        if result["status"] == "timeout":
            run_text = p9h.colored_text("TIMEOUT", "red")
        elif result["status"] == "ok":
            run_text = p9h.colored_text("ok", "green")
        else:
            run_text = p9h.colored_text(result["status"], "yellow")

        summary_color = {
            "success": "green",
            "failed": "yellow",
            "unknown": "red",
        }.get(result["summary"], "white")

        table.add_row(
            result["name"],
            run_text,
            p9h.colored_text(result["summary"], summary_color),
            f"{result['runtime']:.2f}s",
            str(result["stdout_len"]),
            str(result["stderr_len"]),
        )

    return table


def build_coverage_table(methods, case_coverage, result_by_method):
    table = Table(title="Bypass Coverage")
    table.add_column("method", style="bold white", no_wrap=True, overflow="ellipsis")
    table.add_column("case", no_wrap=True, overflow="ellipsis")
    table.add_column("result", justify="center", no_wrap=True, overflow="ellipsis")
    table.add_column("time", justify="right", no_wrap=True)

    for method in methods:
        case_name = case_coverage.get(method)
        result = result_by_method.get(method)
        if case_name is None:
            case_cell = p9h.colored_text("missing", "red")
            result_cell = p9h.colored_text("missing", "red")
            time_cell = "-"
        else:
            case_cell = case_name
            if result is None:
                result_cell = p9h.colored_text("not-run", "yellow")
                time_cell = "-"
            else:
                color = {
                    "success": "green",
                    "failed": "yellow",
                    "unknown": "red",
                }.get(result["summary"], "white")
                if result["status"] == "timeout":
                    result_cell = p9h.colored_text("timeout", "red")
                else:
                    result_cell = p9h.colored_text(result["summary"], color)
                time_cell = f"{result['runtime']:.2f}s"

        table.add_row(method, case_cell, result_cell, time_cell)

    return table


def print_summary(results, inventory, covered_methods, missing_methods):
    total = len(results)
    timeout_count = sum(1 for item in results if item["status"] == "timeout")
    success_count = sum(1 for item in results if item["summary"] == "success")
    failed_count = sum(1 for item in results if item["summary"] == "failed")
    unknown_count = sum(1 for item in results if item["summary"] == "unknown")
    max_case = max(results, key=lambda item: item["runtime"])

    line = Text("[*] cases: ")
    line.append_text(p9h.colored_text(total, "cyan"))
    line.append(" | success: ")
    line.append_text(p9h.colored_text(success_count, "green"))
    line.append(" | failed: ")
    line.append_text(p9h.colored_text(failed_count, "yellow"))
    line.append(" | unknown: ")
    line.append_text(p9h.colored_text(unknown_count, "red"))
    line.append(" | timeout: ")
    line.append_text(
        p9h.colored_text(timeout_count, "red" if timeout_count else "green")
    )
    p9h.console.print(line)

    coverage_line = Text("[*] bypass methods covered: ")
    coverage_line.append_text(
        p9h.colored_text(f"{len(covered_methods)}/{len(inventory)}", "cyan")
    )
    if missing_methods:
        coverage_line.append(" | missing: ")
        coverage_line.append_text(p9h.colored_text(", ".join(missing_methods), "red"))
    else:
        coverage_line.append(" | missing: ")
        coverage_line.append_text(p9h.colored_text("none", "green"))
    p9h.console.print(coverage_line)

    slowest = Text("[*] slowest: ")
    slowest.append_text(p9h.colored_text(max_case["name"], "white"))
    slowest.append(" -> ")
    slowest.append_text(p9h.colored_text(f"{max_case['runtime']:.2f}s", "cyan"))
    p9h.console.print(slowest)


def collect_cases(run_extended=False, match=""):
    cases = coverage_cases()
    if run_extended:
        cases.extend(extended_cases())

    if match:
        cases = [case for case in cases if match in case.name]

    return cases


def validate_coverage(cases, inventory):
    case_coverage = {}
    for case in cases:
        for method in case.covers:
            case_coverage.setdefault(method, case.name)

    missing_methods = [method for method in inventory if method not in case_coverage]
    return case_coverage, missing_methods


def map_results_to_methods(results):
    mapped = {}
    for result in results:
        for method in result["covers"]:
            mapped.setdefault(method, result)
    return mapped


def main(argv=None):
    args = parse_args(argv)
    inventory = inventory_methods()
    case_coverage, missing_methods = validate_coverage(coverage_cases(), inventory)
    if missing_methods and not args.no_coverage_check:
        p9h.console.print(
            p9h.colored_text(
                "[x] stress_test.py does not yet cover every bypass method", "red"
            )
        )
        for method in missing_methods:
            p9h.console.print(Text(f"  - {method}"))
        raise SystemExit(1)

    cases = collect_cases(run_extended=args.extended, match=args.match)
    if not cases:
        p9h.console.print(p9h.colored_text("[x] no matched stress cases", "red"))
        raise SystemExit(1)

    mode = "coverage+extended" if args.extended else "coverage"
    header = Text("[*] running stress cases: ")
    header.append_text(p9h.colored_text(len(cases), "cyan"))
    header.append(" | timeout: ")
    header.append_text(p9h.colored_text(f"{args.timeout:.1f}s", "cyan"))
    header.append(" | mode: ")
    header.append_text(
        p9h.colored_text(mode, "yellow" if args.extended else "green")
    )
    p9h.console.print(header)

    results = [run_case(case, args.timeout, show_command=args.show_command) for case in cases]
    result_by_method = map_results_to_methods(results)
    covered_methods = tuple(method for method in inventory if method in case_coverage)

    p9h.console.print()
    p9h.console.print(build_results_table(results))
    p9h.console.print()
    p9h.console.print(build_coverage_table(inventory, case_coverage, result_by_method))
    p9h.console.print()
    print_summary(results, inventory, covered_methods, missing_methods)


if __name__ == "__main__":
    main()
