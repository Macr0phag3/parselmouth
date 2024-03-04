import ast
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
        result = result.replace(hited, f"{Style.BRIGHT}{Fore.YELLOW}{hited}{Fore.BLUE}")

    c_result = put_color(result, "green")
    return not bool(hited_chr), c_result


def check(payload):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

    # self.cprint(f"检查是否命中黑名单: {payload}", level="debug")
    return [i for i in BLACK_CHAR if i in str(payload)]


class P9H(ast._Unparser):
    def __init__(self, source_code, useless_func, depth, versbose=1):
        self.source_code = source_code
        self.source_node = (
            source_code if isinstance(source_code, ast.AST) else ast.parse(source_code)
        )
        self.verbose = versbose
        self.useless_func = useless_func
        self.depth = depth + 1

        super().__init__()

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

    def try_bypass(self, bypass_funcs, node):
        old_len = len(self._source)
        bypass_funcs["by_raw"]()
        raw_code = "".join(self._source[old_len:])
        self.cprint(f"got payload: {put_color(raw_code, 'blue')}", depth=self.depth + 1)
        if not check(raw_code):
            self.cprint(put_color(f"do not need bypass", "green"), depth=self.depth + 2)
            return raw_code

        if raw_code in self.useless_func:
            # 已知无法 bypass
            self.cprint(
                f"already knew {put_color(raw_code, 'blue')} cannot bypass",
                level="info",
                depth=self.depth + 2,
            )
            return raw_code

        # 清空修改，保护堆栈
        self._source = self._source[:old_len]

        del bypass_funcs["by_raw"]
        for func in bypass_funcs:
            old_len = len(self._source)
            result = bypass_funcs[func]()
            self._source = self._source[:old_len]

            if result is None:
                continue

            hited_chr = check(result)
            if hited_chr:
                self.cprint(
                    f"use {put_color(func, 'cyan')} cannot bypass {put_color(raw_code, 'blue')}, hited: {put_color(hited_chr, 'yellow')}",
                    level="debug",
                    depth=self.depth + 2,
                )
            else:
                self.cprint(
                    f"use {put_color(func, 'cyan')} bypass success",
                    depth=self.depth + 2,
                )
                self.cprint(
                    put_color(raw_code, "blue"),
                    "->",
                    put_color(result, "green"),
                    depth=self.depth + 2,
                )
                break

        else:
            self.cprint(put_color(f"cannot bypass: {raw_code}", "yellow"))
            self.useless_func.append(raw_code)
            # print(f"{self.useless_func} 结束，回退")
            result = raw_code

        self._source += [result]
        # print("当前 payload:", self._source)
        return result

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
                bypass_tools.Bypass_Name(
                    BLACK_CHAR,
                    node,
                    useless_func=self.useless_func,
                    depth=self.depth,
                ).get_map(),
                **{"by_raw": _by_raw},
            ),
            node,
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
            int: bypass_tools.Bypass_Int(
                BLACK_CHAR,
                node,
                useless_func=self.useless_func,
                depth=self.depth,
            ).get_map(),
            str: bypass_tools.Bypass_String(
                BLACK_CHAR,
                node,
                useless_func=self.useless_func,
                depth=self.depth,
            ).get_map(),
        }

        func_map = value_map.get(type(node.value), value_map.get(node.value, None))

        if func_map is None:
            # 没有定义 bypass 方法的基础常量
            return _by_raw()

        func_map["by_raw"] = _by_raw
        return self.try_bypass(
            func_map,
            node,
        )

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
                    BLACK_CHAR,
                    node,
                    useless_func=self.useless_func,
                    depth=self.depth,
                ).get_map(),
                **{"by_raw": _by_raw},
            ),
            node,
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
                bypass_tools.Bypass_Keyword(
                    BLACK_CHAR,
                    node,
                    useless_func=self.useless_func,
                    depth=self.depth,
                ).get_map(),
                **{"by_raw": _by_raw},
            ),
            node,
        )

    def visit_Call(self, node):
        def _by_raw():
            self.set_precedence(ast._Precedence.ATOM, node.func)
            self.traverse(node.func)
            with self.delimit("(", ")"):
                comma = False
                for e in node.args:
                    if comma:
                        self.write(f",{FORMAT_SPACE}")
                    else:
                        comma = True

                    self.traverse(e)

                for e in node.keywords:
                    if comma:
                        self.write(f",{FORMAT_SPACE}")
                    else:
                        comma = True

                    self.traverse(e)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Call(
                    BLACK_CHAR,
                    node,
                    useless_func=self.useless_func,
                    depth=self.depth,
                ).get_map(),
                **{"by_raw": _by_raw},
            ),
            node,
        )


FORMAT_SPACE = " "
BLACK_CHAR = []

if __name__ == "__main__":
    # print(
    #     """
    # -|--- \033[1;33m ,---. \033[0m,---.
    # |    \033[1;33m | O | \033[0m,---|
    # `---'\033[1;33m `---' \033[0m`---^ st
    # """
    # )

    parser = argparse.ArgumentParser(
        description="parselmouth, automated python sandbox escape payload bypass framework"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--payload", help="bypass rule")
    group.add_argument("--run-test", action="store_true", help="run test")
    parser.add_argument("-v", action="count", default=0, help="verbose level")
    parser.add_argument("--rule", nargs="+", default="", help="rules")
    args = parser.parse_args()

    if args.run_test:
        __import__("run_test")
    else:
        print(f"[*] payload: {put_color(args.payload, 'blue')}")
        print(f"  [*] rules: {put_color(args.rule, 'cyan')}")
        print(f"  [*] versbose: {put_color(args.v, 'white')}")
        BLACK_CHAR = args.rule
        p9h = P9H(args.payload, [], 0, versbose=args.v)
        result, c_payload = color_check(p9h.visit())

        print(
            "[*] result:",
            put_color("success" if result else "failed", "green" if result else "red"),
        )
        print("[*]", put_color(args.payload, "blue"), "=>", c_payload)