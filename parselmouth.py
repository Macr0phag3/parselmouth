import ast
import json
import re
import sys
import argparse

from colorama import Fore, Style

import bypass_tools


def put_color(string, color, bold=True):
    """
    give me some color to see :P
    """

    if color == "gray":
        COLOR = Style.DIM + Fore.WHITE
    else:
        COLOR = getattr(Fore, color.upper(), "WHITE")

    return f'{Style.BRIGHT if bold else ""}{COLOR}{str(string)}{Style.RESET_ALL}'


def color_check(result):
    hited_chr = check(result)
    for hited in hited_chr:
        result = result.replace(hited, f"{Style.BRIGHT}{Fore.YELLOW}{hited}")

    if hited_chr:
        result += Fore.BLUE

    c_result = put_color(result, "green")
    return not bool(hited_chr), c_result


def check(payload, ignore_space=False):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

    if not BLACK_CHAR.get("kwd") and not BLACK_CHAR.get("re_kwd"):
        # 无规则？提示一下
        sys.exit(put_color(f"[WARN] 规则为空，不需要 bypass"), *args)

    kwd_check = [
        i
        for i in BLACK_CHAR.get("kwd", [])
        if (not ignore_space or (ignore_space and i not in [" ", "\t"]))
        and i in str(payload)
    ] + list(
        set(
            re.findall(BLACK_CHAR["re_kwd"], str(payload))
            if BLACK_CHAR.get("re_kwd")
            else []
        )
        - ({" ", "\t"} if ignore_space else set())
    )
    return kwd_check


class P9H(ast._Unparser):
    def __init__(
        self,
        source_code,
        depth=0,
        versbose=1,
        bypass_history=None,
        ensure_min=False,
        specify_bypass_map={},
    ):
        _space = [i for i in [" ", "\t"] if not check(i)]
        globals()["FORMAT_SPACE"] = ([""] + _space)[bool(_space)]
        self.source_code = source_code
        # print("source_code", depth, source_code)
        self.source_node = (
            source_code if isinstance(source_code, ast.AST) else ast.parse(source_code)
        )
        self.verbose = versbose
        if bypass_history == None:
            self.bypass_history = {"success": {}, "failed": []}
        else:
            self.bypass_history = bypass_history

        self.depth = depth
        self.ensure_min = ensure_min
        self.specify_bypass_map = specify_bypass_map

        for _type in specify_bypass_map:
            for cls_name in specify_bypass_map[_type]:
                for func_name in specify_bypass_map[_type][cls_name]:
                    if not (cls_name and func_name):
                        sys.exit("[x] white_bypass/black_bypass format is `class.func`")

                    cls = vars(bypass_tools).get(cls_name, None)
                    if not cls:
                        sys.exit(f"[x] bypass class not found: {cls_name}")

                    func = vars(cls).get(func_name, None)
                    if not func:
                        sys.exit(
                            f"[x] bypass func not found: {func_name} in {cls_name}"
                        )

        super().__init__()

    def _write_constant(self, value):
        if isinstance(value, (float, complex)):
            # Substitute overflowing decimal literal for AST infinities,
            # and inf - inf for NaNs.
            self.write(
                repr(value)
                .replace("inf", ast._INFSTR)
                .replace("nan", f"({ast._INFSTR}-{ast._INFSTR})")
            )
        elif isinstance(value, str):
            self._write_str_avoiding_backslashes(value)
        else:
            self.write(repr(value))

    def _write_str_avoiding_backslashes(
        self, string, *, quote_types=ast._ALL_QUOTES, _write=True
    ):
        """Write string literal value with a best effort attempt to avoid backslashes."""
        quote_types = [i for i in quote_types if not check(i)]
        string, quote_types = self._str_literal_helper(string, quote_types=quote_types)
        quote_type = quote_types[0]
        result = f"{quote_type}{string}{quote_type}"
        if _write:
            self.write(f"{quote_type}{string}{quote_type}")
        return result

    def cprint(self, *args, depth=None, level="info"):
        if level not in ["warn", "error"]:
            if self.verbose < 1:
                return

            elif self.verbose == 1 and level != "info":
                return

        color = {
            "debug": "gray",
            "info": "white",
        }[level]

        if depth is None:
            depth = self.depth

        print(put_color(f"{'  '*(depth)}[{level.upper()}]", color), *args)

    def try_bypass(self, bypass_funcs):
        old_len = len(self._source)
        bypass_funcs["by_raw"]()
        raw_code = "".join(self._source[old_len:])
        self.cprint(
            f"target payload: {put_color(raw_code, 'blue')}", depth=self.depth + 1
        )
        if not check(raw_code):
            self.cprint(put_color(f"do not need bypass", "green"), depth=self.depth + 2)
            return raw_code

        # 清空修改，保护堆栈
        self._source = self._source[:old_len]

        if raw_code in self.bypass_history["success"]:
            self.cprint(
                f"already knew {put_color(raw_code, 'blue')} can bypass: {self.bypass_history['success'][raw_code]}",
                level="info",
                depth=self.depth + 2,
            )
            result = self.bypass_history["success"][raw_code]
            self._source += [result]
            return result

        if raw_code in self.bypass_history["failed"]:
            # 已知无法 bypass
            self.cprint(
                f"already knew {put_color(raw_code, 'blue')} cannot bypass",
                level="info",
                depth=self.depth + 2,
            )
            self._source += [raw_code]
            return raw_code

        del bypass_funcs["by_raw"]

        # 逐个尝试 bypass
        min_exp = "1" * (10**5)
        for func in bypass_funcs:
            cls_name, func_name = bypass_funcs[func].__qualname__.split(".")

            if "white" in self.specify_bypass_map:
                if (
                    cls_name in self.specify_bypass_map["white"]
                    and func_name not in self.specify_bypass_map["white"][cls_name]
                ):
                    self.cprint(
                        f"{cls_name}.{func_name} is not in white_bypass",
                        level="debug",
                        depth=self.depth + 2,
                    )
                    continue

            elif "black" in self.specify_bypass_map:
                if (
                    cls_name in self.specify_bypass_map["black"]
                    and func_name in self.specify_bypass_map["black"][cls_name]
                ):
                    self.cprint(
                        f"{cls_name}.{func_name} is in black_bypass",
                        level="debug",
                        depth=self.depth + 2,
                    )
                    continue

            old_len = len(self._source)
            self.cprint(
                f"try {put_color(func, 'cyan')}",
                level="debug",
                depth=self.depth + 2,
            )
            # 执行 bypass 函数
            result = bypass_funcs[func]()
            self._source = self._source[:old_len]

            if result is None:
                self.bypass_history["failed"].append((func, raw_code))
                continue

            hited_chr = check(result)
            _depth = self.depth + 3 if self.verbose >= 2 else self.depth + 2
            if hited_chr:
                self.cprint(
                    f"use {put_color(func, 'cyan')} cannot bypass {put_color(raw_code, 'blue')}, hited: {put_color(hited_chr, 'yellow')}",
                    level="debug",
                    depth=_depth,
                )
            else:
                self.cprint(
                    f"use {put_color(func, 'cyan')} {put_color('bypass success', 'green')}",
                    depth=_depth,
                )
                if self.ensure_min and len(result) < len(min_exp):
                    self.cprint(f"found min exp", depth=_depth)
                    min_exp = result

                self.cprint(
                    put_color(raw_code, "blue"),
                    "->",
                    put_color(result, "green"),
                    depth=_depth,
                )

                if not self.ensure_min:
                    min_exp = result
                    break

                # print("succ", result)
                # break

        if min_exp == "1" * (10**5):
            # 说明未成功
            self.cprint(
                put_color(f"cannot bypass: {raw_code}", "yellow"), depth=self.depth + 2
            )
            self.bypass_history["failed"].append(raw_code)
            # print(f"结束，回退, {raw_code}")
            result = raw_code
        else:
            result = min_exp
            self.bypass_history["success"][raw_code] = result

        self._source += [result]
        # print("当前 payload:", self._source)
        return result

    def write(self, *text):
        """Add new source parts"""
        stack = bypass_tools.get_stack(num=5)
        _text = text[:]
        if (
            stack[2][1] == "visit_BinOp"
            or "visit_List" in str(stack[3][2].get("inter", None))
            or stack[4][1] == "visit_Call"
        ):
            _text = [i.replace(" ", FORMAT_SPACE) for i in text]
        # else:
        #     print("-" * 10, text, "-" * 10)
        #     pprint.pprint(stack)
        #     print()
        self._source.extend(_text)

    def visit(self):
        self.cprint("try bypass:", put_color(self.source_code, "blue"), level="info")
        self._source = []
        self.traverse(self.source_node)
        return "".join(self._source)

    def visit_Module(self, node):
        self._type_ignores = {
            ignore.lineno: f"ignore{ignore.tag}" for ignore in node.type_ignores
        }
        self.traverse(node.body)
        self._type_ignores.clear()

    def visit_Name(self, node):
        def _by_raw():
            self.write(node.id)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Name(BLACK_CHAR, node, p9h_self=self).get_map(),
                **{"by_raw": _by_raw},
            )
        )

    def visit_Constant(self, node):
        def _by_raw():
            value = node.value
            if isinstance(value, tuple):
                with self.delimit("(", ")"):
                    self.items_view(self._write_constant, value)

            elif value is ...:
                self.write("...")

            else:
                if node.kind == "u":
                    self.write("u")

                self._write_constant(node.value)

        value_map = {
            int: bypass_tools.Bypass_Int,
            str: bypass_tools.Bypass_String,
        }

        bypass_cls_map = value_map.get(
            type(node.value), value_map.get(node.value, None)
        )

        if bypass_cls_map is None:
            # 没有定义 bypass 方法的基础常量
            return _by_raw()

        func_map = bypass_cls_map(BLACK_CHAR, node, p9h_self=self).get_map()
        func_map["by_raw"] = _by_raw
        return self.try_bypass(func_map)

    def visit_Attribute(self, node):
        def _by_raw():
            self.set_precedence(ast._Precedence.ATOM, node.value)
            self.traverse(node.value)
            # Special case: 3.__abs__() is a syntax error, so if node.value
            # is an integer literal then we need to either parenthesize
            # it or add an extra space to get 3 .__abs__().
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, int
            ):
                self.write(" ")

            self.write(".")
            self.write(node.attr)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Attribute(
                    BLACK_CHAR, node, p9h_self=self
                ).get_map(),
                **{"by_raw": _by_raw},
            )
        )

    def visit_keyword(self, node):
        def _by_raw():
            if node.arg is None:
                self.write("**")
            else:
                self.write(node.arg)
                self.write("=")

            self.traverse(node.value)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Keyword(BLACK_CHAR, node, p9h_self=self).get_map(),
                **{"by_raw": _by_raw},
            )
        )

    def visit_Call(self, node):
        def _by_raw():
            self.set_precedence(ast._Precedence.ATOM, node.func)
            self.traverse(node.func)
            with self.delimit("(", ")"):
                comma = False
                for e in node.args:
                    if comma:
                        self.write(f", ")
                    else:
                        comma = True

                    self.traverse(e)

                for e in node.keywords:
                    if comma:
                        self.write(f", ")
                    else:
                        comma = True

                    self.traverse(e)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Call(BLACK_CHAR, node, p9h_self=self).get_map(),
                **{"by_raw": _by_raw},
            )
        )

    def visit_UnaryOp(self, node):
        # 这个函数比较特殊，目前主要在处理负数的情况
        # 因为负数整体不被视为数字类型，而是 UnaryOp + Num
        operator = self.unop[node.op.__class__.__name__]
        operator_precedence = self.unop_precedence[operator]

        if operator in ["-"] and type(getattr(node.operand, "value", None)) == int:
            node.value = int(ast.unparse(node))
            return self.try_bypass(
                dict(
                    bypass_tools.Bypass_Int(BLACK_CHAR, node, p9h_self=self).get_map(),
                    **{"by_raw": lambda: self.write(str(node.value))},
                )
            )

        with self.require_parens(operator_precedence, node):
            self.write(operator)
            # factor prefixes (+, -, ~) shouldn't be separated
            # from the value they belong, (e.g: +1 instead of + 1)
            if operator_precedence is not ast._Precedence.FACTOR:
                self.write(" ")
            self.set_precedence(operator_precedence, node.operand)
            self.traverse(node.operand)


Recursion_LIMIT = 5000
sys.setrecursionlimit(Recursion_LIMIT)
BLACK_CHAR = {}
FORMAT_SPACE = None

if __name__ == "__main__":
    print(
        """:########:  :########:  ##:::::##:\n"""
        """##.... ##: '##.... ##:  ##:::: ##:\n"""
        """##:::: ##:  ##.... ##:  ##:::: ##:\n"""
        """########:: : ########:  #########:\n"""
        """##.....::: :...... ##:  ##.... ##:\n"""
        """##:::::::: '##:::: ##:  ##:::: ##:\n"""
        """##:::::::: . #######::  ##:::: ##:\n"""
        """..:::::::: ::.......:: :..:::::..::\n""".replace(
            "#", put_color("#", "green")
        )
    )

    parser = argparse.ArgumentParser(
        description="parselmouth, automated python sandbox escape payload bypass framework"
    )
    parser.add_argument("--payload", help="bypass rule")
    parser.add_argument("-v", action="count", default=0, help="verbose level")
    parser.add_argument("--re-rule", default="", help="rule in regex")
    parser.add_argument("--rule", nargs="+", default="", help="rules")
    parser.add_argument(
        "--specify-bypass",
        default="{}",
        help='eg. {"white": {"Bypass_String": ["by_dict"]}, "black": []}',
    )
    parser.add_argument("--ensure-min", action="store_true", help="found min exp")
    args = parser.parse_args()

    print(f"[*] payload: {put_color(args.payload, 'blue')}")
    print(f"  [*] rules: {put_color(args.rule, 'cyan')}")

    specify_bypass_map = json.loads(args.specify_bypass)
    print(f"  [*] specify bypass map: {specify_bypass_map}")
    print(f"  [*] versbose: {put_color(args.v, 'white')}")

    try:
        re.compile(args.re_rule)
    except Exception:
        sys.exit("[!] --re-rule 的正则表达式有误")

    BLACK_CHAR = {"kwd": args.rule, "re_kwd": args.re_rule}
    p9h = P9H(
        args.payload,
        versbose=args.v,
        specify_bypass_map=specify_bypass_map,
        ensure_min=args.ensure_min,
    )
    result, c_payload = color_check(p9h.visit())

    print(
        "[*] result:",
        put_color("success" if result else "failed", "green" if result else "red"),
    )
    print("[*]", put_color(args.payload, "blue"), "=>", c_payload)
