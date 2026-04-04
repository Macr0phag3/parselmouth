import argparse
import json
import re
import time

import parselmouth as p9h
from rich.text import Text

from ui import (
    colored_text,
    console,
    print_rewrite_header,
    print_run_config,
    print_run_summary,
    rich_print,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="parselmouth, automated python sandbox escape payload bypass framework"
    )
    parser.add_argument("--payload", required=True, help="bypass rule")
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="increase process output (-v progress, -vv detail, -vvv trace)",
    )
    parser.add_argument("--re-rule", default="", help="rule in regex")
    parser.add_argument("--rule", nargs="+", default="", help="rules")
    parser.add_argument(
        "--specify-bypass",
        default="{}",
        help='eg. {"black": {"Bypass_Int": "by_unicode, by_hex"}}',
    )
    parser.add_argument("--shortest", action="store_true", help="found shortest exp")
    parser.add_argument(
        "--minset", action="store_true", help="found minimal character set exp"
    )
    return parser


def validate_args(args):
    if args.shortest and args.minset:
        console.print(colored_text("[x] --shortest or --minset, not both", "red"))
        raise SystemExit(1)

    try:
        specify_bypass_map = json.loads(args.specify_bypass)
    except Exception as exc:
        console.print(
            colored_text(
                f"""[!] --specify-bypass is invalid: {exc}."""
                """eg. --specify-bypass '{"white": {"Bypass_Attribute": "by_vars"}}'""",
                "red",
            )
        )
        raise SystemExit(1)

    if args.re_rule:
        try:
            re.compile(args.re_rule)
        except Exception:
            console.print(colored_text("[x] --re-rule regex is invalid", "red"))
            raise SystemExit(1)

        if re.findall(args.re_rule, "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"):
            rich_print(
                colored_text(
                    "[!] regex can match unicode numbers, use `\\d` or `.` carefully",
                    "yellow",
                )
            )

        if re.findall(args.re_rule, "ᑐ ᑌ ᑎ ᕮ"):
            rich_print(colored_text("[!] regex is toooooo broad", "yellow"))

    return specify_bypass_map


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.v = p9h.normalize_verbose(args.v)
    specify_bypass_map = validate_args(args)

    print_run_config(args, specify_bypass_map)

    p9h.BLACK_CHAR = {"kwd": args.rule, "re_kwd": args.re_rule}
    status = p9h.RuntimeStatus(console)
    runner = p9h.P9H(
        args.payload,
        verbose=args.v,
        specify_bypass_map=specify_bypass_map,
        min_len=args.shortest,
        min_set=args.minset,
        status=status,
    )

    start_ts = time.time()
    print_rewrite_header()
    status.start(
        "rewrite blocked nodes",
        depth=runner.depth,
        attempts=0,
        cache="0p/0f",
    )
    try:
        exp = runner.visit()
    except KeyboardInterrupt:
        status.stop(persist=True)
        console.print()
        console.print(colored_text("[!] exit? yes, master", "yellow"))
        cost_line = Text("[*] cost ", style="muted")
        cost_line.append_text(colored_text(f"{round(time.time() - start_ts, 2)}s", "cyan"))
        console.print(cost_line)
        raise SystemExit(1)
    except Exception:
        status.stop()
        raise
    else:
        status.stop(persist=True)

    end_ts = time.time()
    result, c_payload = p9h.color_check(exp)
    print_run_summary(
        args.payload,
        exp,
        result,
        end_ts - start_ts,
        runner,
        c_payload,
        check_func=p9h.check,
    )


if __name__ == "__main__":
    main()
