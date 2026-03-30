import argparse
from fractions import Fraction
from time import perf_counter

from colorama import Fore, Style


class Atom:
    __slots__ = ("text", "value")

    def __init__(self, text, value):
        self.text = text
        self.value = value


class BinaryOp:
    __slots__ = ("left", "op", "right", "value")

    def __init__(self, left, op, right, value):
        self.left = left
        self.op = op
        self.right = right
        self.value = value


_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "**": 3}
_VALUE_LIMIT = 10**7
_TIME_CHECK_INTERVAL = 2048
_TIMED_OUT = object()
_LOW_PRECEDENCE_MARKERS = (
    "==",
    "!=",
    "<=",
    ">=",
    "<",
    ">",
    " is ",
    " is not ",
    " in ",
    " not in ",
    " and ",
    " or ",
    " if ",
    ":=",
)
_SAFE_EVAL_GLOBALS = {
    "__builtins__": {
        "Fraction": Fraction,
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "float": float,
        "int": int,
        "len": len,
        "max": max,
        "min": min,
        "pow": pow,
        "round": round,
        "str": str,
    }
}


def _put_color(string, color, bold=True):
    if color == "gray":
        tone = Style.DIM + Fore.WHITE
    else:
        tone = getattr(Fore, color.upper(), Fore.WHITE)
    return f'{Style.BRIGHT if bold else ""}{tone}{str(string)}{Style.RESET_ALL}'


def _normalize_value(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Fraction) and value.denominator == 1:
        return value.numerator
    return value


def _expr_text(node):
    if isinstance(node, Atom):
        return node.text
    return _to_str(node)


def _prefer_expr(candidate, current):
    if current is None:
        return True
    return len(_expr_text(candidate)) < len(_expr_text(current))


def _to_str(node):
    if isinstance(node, Atom):
        return node.text

    left = _wrap(node.left, node.op, is_right=False)
    right = _wrap(node.right, node.op, is_right=True)
    return f"{left}{node.op}{right}"


def _wrap(child, parent_op, is_right):
    if isinstance(child, Atom):
        if any(marker in child.text for marker in _LOW_PRECEDENCE_MARKERS):
            return f"({child.text})"
        return child.text

    child_text = _to_str(child)
    child_prec = _PREC[child.op]
    parent_prec = _PREC[parent_op]
    need_wrap = (
        child_prec < parent_prec
        or (child_prec == parent_prec and parent_op == "**" and not is_right)
        or (child_prec == parent_prec and is_right and parent_op in ("-", "/"))
    )
    return f"({child_text})" if need_wrap else child_text


def _apply(left, op, right):
    try:
        if op == "+":
            return _normalize_value(left + right)
        if op == "-":
            return _normalize_value(left - right)
        if op == "*":
            return _normalize_value(left * right)
        if op == "/":
            if right == 0:
                return None
            if isinstance(left, int) and isinstance(right, int):
                quotient, rem = divmod(left, right)
                return quotient if rem == 0 else Fraction(left, right)
            return _normalize_value(Fraction(left) / Fraction(right))
        if op == "**":
            if isinstance(right, Fraction):
                if right.denominator != 1 or right < 0:
                    return None
                right = int(right)
            if not isinstance(right, int) or right < 0 or right > 20:
                return None
            return _normalize_value(left**right)
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return None


def _value_ok(value, limit):
    return value is not None and abs(value) <= limit


def _reverse_right(target, left, op):
    try:
        if op == "+":
            return _normalize_value(target - left)
        if op == "-":
            return _normalize_value(left - target)
        if op == "*":
            if left == 0:
                return None
            if isinstance(target, int) and isinstance(left, int):
                quotient, rem = divmod(target, left)
                return quotient if rem == 0 else Fraction(target, left)
            return _normalize_value(Fraction(target) / Fraction(left))
        if op == "/":
            if target == 0:
                return None
            if isinstance(left, int) and isinstance(target, int):
                quotient, rem = divmod(left, target)
                return quotient if rem == 0 else Fraction(left, target)
            return _normalize_value(Fraction(left) / Fraction(target))
        if op == "**":
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return None


def _reverse_left(target, right, op):
    try:
        if op == "+":
            return _normalize_value(target - right)
        if op == "-":
            return _normalize_value(target + right)
        if op == "*":
            if right == 0:
                return None
            if isinstance(target, int) and isinstance(right, int):
                quotient, rem = divmod(target, right)
                return quotient if rem == 0 else Fraction(target, right)
            return _normalize_value(Fraction(target) / Fraction(right))
        if op == "/":
            if isinstance(target, int) and isinstance(right, int):
                return _normalize_value(target * right)
            return _normalize_value(Fraction(target) * Fraction(right))
        if op == "**":
            exponent = right
            if isinstance(exponent, Fraction):
                if exponent.denominator != 1:
                    return None
                exponent = int(exponent)
            if not isinstance(exponent, int) or exponent <= 0 or exponent > 20:
                return None
            if target == 0:
                return 0
            if target < 0:
                return None

            target_float = float(target)
            root = round(target_float ** (1.0 / exponent))
            for candidate in (root - 1, root, root + 1):
                if candidate >= 0 and candidate**exponent == target:
                    return candidate
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return None


def _mitm_check(known, operators, target, allow_parentheses, timed_out=None):
    for left_value, left_expr in known.items():
        for op in operators:
            if timed_out and timed_out():
                return _TIMED_OUT
            right_value = _reverse_right(target, left_value, op)
            if (
                right_value is not None
                and right_value in known
                and _apply(left_value, op, right_value) == target
            ):
                node = BinaryOp(left_expr, op, known[right_value], target)
                text = _to_str(node)
                if allow_parentheses or "(" not in text:
                    return text

            left_candidate = _reverse_left(target, left_value, op)
            if (
                left_candidate is not None
                and left_candidate in known
                and _apply(left_candidate, op, left_value) == target
            ):
                node = BinaryOp(known[left_candidate], op, left_expr, target)
                text = _to_str(node)
                if allow_parentheses or "(" not in text:
                    return text
    return None


def _format_timeout_budget(time_budget):
    if time_budget is None:
        return "None"
    return f"{time_budget:g}s"


def find_expression(
    atoms,
    operators,
    target,
    allow_parentheses=True,
    shortest=False,
    max_depth=50,
    layer_cap=15000,
    value_limit=_VALUE_LIMIT,
    time_budget=None,
    result_info=None,
):
    target = _normalize_value(target)
    known = {}
    if result_info is not None:
        result_info.clear()
        result_info["timed_out"] = False
        result_info["reason"] = None

    deadline = None
    if time_budget is not None:
        deadline = perf_counter() + max(time_budget, 0)

    checks = [0]

    def timed_out(force=False):
        if deadline is None:
            return False
        if force:
            return perf_counter() >= deadline

        checks[0] += 1
        if checks[0] < _TIME_CHECK_INTERVAL:
            return False

        checks[0] = 0
        return perf_counter() >= deadline

    def timeout_result(best_hit=None):
        if result_info is not None:
            result_info["timed_out"] = True
            result_info["reason"] = f"timed out after {_format_timeout_budget(time_budget)}"
        if best_hit is not None:
            return _to_str(best_hit)
        return None

    for text, value in atoms:
        value = _normalize_value(value)
        node = Atom(text, value)
        current = known.get(value)
        if _prefer_expr(node, current):
            known[value] = node

    if target in known:
        return _to_str(known[target])

    if not shortest:
        result = _mitm_check(known, operators, target, allow_parentheses, timed_out)
        if result is _TIMED_OUT:
            return timeout_result()
        if result is not None:
            return result

    layers = {0: dict(known)}
    for depth in range(1, max_depth + 1):
        next_layer = {}
        best_hit = None

        for left_depth in range(depth):
            right_depth = depth - 1 - left_depth
            if right_depth not in layers:
                continue

            left_layer = layers[left_depth]
            right_layer = layers[right_depth]
            for left_value, left_expr in left_layer.items():
                for right_value, right_expr in right_layer.items():
                    for op in operators:
                        if timed_out():
                            return timeout_result(best_hit)
                        value = _apply(left_value, op, right_value)
                        if not _value_ok(value, value_limit):
                            continue

                        node = BinaryOp(left_expr, op, right_expr, value)
                        text = _to_str(node)
                        if not allow_parentheses and "(" in text:
                            continue

                        if value == target:
                            if not shortest:
                                return text
                            if _prefer_expr(node, best_hit):
                                best_hit = node
                            continue

                        current = next_layer.get(value)
                        if _prefer_expr(node, current):
                            next_layer[value] = node

        if best_hit is not None:
            return _to_str(best_hit)

        if timed_out(force=True):
            return timeout_result()

        if len(next_layer) > layer_cap:
            next_layer = dict(
                sorted(
                    next_layer.items(),
                    key=lambda item: (
                        abs(float(item[0]) - float(target)),
                        len(_expr_text(item[1])),
                    ),
                )[:layer_cap]
            )

        layers[depth] = next_layer
        for value, node in next_layer.items():
            current = known.get(value)
            if _prefer_expr(node, current):
                known[value] = node

        if not shortest:
            result = _mitm_check(known, operators, target, allow_parentheses, timed_out)
            if result is _TIMED_OUT:
                return timeout_result()
            if result is not None:
                return result

    return None


def _safe_eval(source):
    return eval(source, _SAFE_EVAL_GLOBALS, {})


def _parse_atom(spec):
    if "=" in spec:
        text, value_expr = spec.split("=", 1)
        text = text.strip()
        if not text:
            raise ValueError(f"invalid atom mapping: {spec!r}")
        return text, _normalize_value(_safe_eval(value_expr.strip()))

    text = spec.strip()
    if not text:
        raise ValueError("atom cannot be empty")
    return text, _normalize_value(_safe_eval(text))


def _split_cli_list(value, separator="|"):
    return [part.strip() for part in value.split(separator) if part.strip()]


def _expand_cli_values(values, separator="|"):
    expanded = []
    for value in values:
        expanded.extend(_split_cli_list(value, separator=separator))
    return expanded


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Find an arithmetic expression from candidate atoms."
    )
    parser.add_argument(
        "--atom",
        action="append",
        default=[],
        help="Candidate atom. Repeated or pipe-separated. Supports EXPR or TEXT=VALUE.",
    )
    parser.add_argument(
        "--operator",
        action="append",
        default=[],
        help="Allowed operator. Repeated or pipe-separated. Defaults to **, *, +, -.",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target value or Python expression, for example 2024 or Fraction(1, 2).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=50,
        help="Maximum expression-tree depth. Default: 50.",
    )
    parser.add_argument(
        "--time-budget",
        type=float,
        default=5,
        help="Time budget in seconds. Default: 5. When exceeded, stop early.",
    )
    parser.add_argument(
        "--shortest",
        action="store_true",
        help="Search for the shortest expression instead of first hit.",
    )
    parser.add_argument(
        "--no-parentheses",
        dest="allow_parentheses",
        action="store_false",
        help="Disallow parentheses in the final expression.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the final expression on success.",
    )
    parser.set_defaults(allow_parentheses=True)
    return parser


def _print_cli_config(args, atoms, operators, target):
    atom_texts = [text for text, _ in atoms]
    print(
        "[*] use",
        _put_color(atom_texts, "blue"),
        "with",
        _put_color(operators, "cyan"),
        "to get",
        _put_color(repr(target), "green"),
    )
    print(f"[*] mode: {_put_color('shortest' if args.shortest else 'first-hit', 'white')}")
    print(f"[*] max depth: {_put_color(args.max_depth, 'cyan')}")
    print(f"[*] allow parentheses: {_put_color(args.allow_parentheses, 'white')}")
    print(f"[*] time budget: {_put_color(_format_timeout_budget(args.time_budget), 'cyan')}")
    print(_put_color("\n[*] solving...\n", "blue"))


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.atom:
        parser.error("at least one --atom is required")

    try:
        atom_specs = _expand_cli_values(args.atom, separator="|")
        operator_specs = _expand_cli_values(args.operator, separator="|")
        invalid_operators = [op for op in operator_specs if op not in _PREC]
        if invalid_operators:
            raise ValueError(f"invalid operator(s): {', '.join(invalid_operators)}")

        atoms = [_parse_atom(spec) for spec in atom_specs]
        target = _normalize_value(_safe_eval(args.target))
    except Exception as exc:
        parser.exit(2, f"[x] {exc}\n")

    operators = operator_specs or ["**", "*", "+", "-"]
    if not args.quiet:
        _print_cli_config(args, atoms, operators, target)

    start_ts = perf_counter()
    result_info = {}
    result = find_expression(
        atoms=atoms,
        operators=operators,
        target=target,
        allow_parentheses=args.allow_parentheses,
        shortest=args.shortest,
        max_depth=args.max_depth,
        value_limit=_VALUE_LIMIT,
        time_budget=args.time_budget,
        result_info=result_info,
    )
    cost = perf_counter() - start_ts
    if result is None:
        if not args.quiet:
            status = "failed"
            if result_info.get("reason"):
                status += f" ({result_info['reason']})"
            print("[*] result:", _put_color(status, "red"))
            print("[*] cost", _put_color(f"{round(cost, 2)}s", "cyan"))
            print(_put_color("[!] no expression found", "yellow"))
        return 1

    if not args.quiet:
        print("[*] result:", _put_color("success", "green"))
        print(f"[*] exp length is {_put_color(len(result), 'cyan')}")
        print(f"[*] exp char set size is {_put_color(len(set(result)), 'cyan')}")
        print("[*] cost", _put_color(f"{round(cost, 2)}s", "cyan"))
        print(
            f"\n[*] {_put_color(repr(target), 'green')} => {_put_color(result, 'green')}"
        )
        return 0

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
