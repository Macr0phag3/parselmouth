import operator
import string
import inspect
import functools

import sympy

import parselmouth as p9h


def recursion_protect(func):
    @functools.wraps(func)
    def _protect(self):
        stack = []
        for s in get_stack():
            if not s[1].startswith("by_"):
                continue

            stack.append((s[0], s[1], s[2]["self"].node._value))

        if (self.__class__.__name__, func.__name__, self.node._value) in stack:
            # 本轮调用的 函数+参数 在调用链之前就出现过
            # 说明不同的 bypass 函数之间出现了循环依赖
            # 这个时候应该舍弃掉这个 bypass 函数
            return None

        return func(self)

    return _protect


def get_stack():
    used_funcs = []
    stack = inspect.stack()
    for frame_info in stack:
        # 获取当前层的上下文信息
        frame = frame_info.frame
        arg_info = inspect.getargvalues(frame)

        class_name = ""
        if "self" in frame.f_locals:
            class_name = frame.f_locals["self"].__class__.__name__

        # 打印调用链中的函数名和参数
        used_funcs.append(
            (
                class_name,
                frame_info.function,
                {k: arg_info.locals[k] for k in arg_info.args},
            )
        )

    return used_funcs


class _Bypass:
    def __init__(self, rule, node, cannot_bypass, depth, specify_bypass_map):
        self.node = node
        self.P9H = functools.partial(
            p9h.P9H,
            cannot_bypass=cannot_bypass,
            specify_bypass_map=specify_bypass_map,
            depth=depth,
            versbose=0,
        )
        p9h.BLACK_CHAR = rule
        # p9h.VERBOSE = 0

    def get_map(self):
        # bypass 函数的顺序取决于对应类中定义的顺序
        # 先被定义的函数会优先尝试进行 bypass

        return {
            i: getattr(self, i) for i in self.__class__.__dict__ if i.startswith("by_")
        }


class Bypass_Int(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = getattr(self.node, "value")

        self.translate_map = {
            0: [
                "False",
                "len( () )",
                "any( () )",
                "bool( bool )",
            ],
            1: [
                "True",
                "0**0",
                "all( () )",
                "len( ((), ()) )",
            ],
            2: ["len( str( () ) )"],
        }
        self.translate_map[1].extend([f"-~{i}" for i in self.translate_map[0] + [0]])

        # 填充 0-9 缺失的数字
        self.valid_num = []
        for i in list(range(10))[::-1]:
            if not p9h.check(i):
                self.valid_num.append(str(i))

            elif i in self.translate_map:
                for j in self.translate_map[i]:
                    if not p9h.check(j):
                        self.valid_num.append(str(j))
                        break

    @recursion_protect
    def by_trans(self):
        if self.node._value in self.translate_map:
            # 直接返回替代
            for i in self.translate_map[self.node._value]:
                if not p9h.check(i):
                    return self.P9H(str(i)).visit()

        return str(self.node._value)

    @recursion_protect
    def by_bin(self):
        return bin(int(self.node._value))

    @recursion_protect
    def by_hex(self):
        return hex(int(self.node._value))

    @recursion_protect
    def by_cal(self):
        def _calculate(target, old_expr):
            stacks = [i[2]["target"] for i in get_stack() if i[1] == "_calculate"][1:]
            if target in stacks or target in can_not_cal:
                return None

            if set(str(target)).issubset(single_valid_num):
                return f"{old_expr}x{target}"

            first = not bool(old_expr)

            for op in ops:
                for left in _valid_num:
                    n_left = eval(left)
                    left = "x" + left if n_left else left
                    for right in _valid_num:
                        n_right = eval(right)
                        right = "x" + right

                        v = ops[op](n_left, n_right)

                        if v == n_left:
                            continue

                        if v == target:
                            return f"{old_expr}{left}{op}{right}"

                        if first:
                            _old_expr = (
                                str(v) if v in _valid_num else f"{left}{op}{right}"
                            )
                        else:
                            _old_expr = (
                                f"{old_expr}{v}"
                                if v in _valid_num
                                else f"{old_expr}({left}{op}{right})"
                            )

                        if abs(v - target) > abs(n_left - target):
                            # print(f"  - 显然，经过运算，相比 left={left} 距离目标更远了，算式无效")
                            continue

                        # print(
                        #     "\n[*] 选中表达式:",
                        #     f"{left}{op}{right}",
                        # )
                        # print(" 新一轮", target, f"{left}{op}{right}={v}", old_expr)
                        # # input()

                        for new_op in ops:
                            # print(f"  - 尝试运算符 {new_op}")
                            if new_op == "-":
                                # print("    - 求", f"{left}{op}{right} - n == {target} ?")
                                if abs(n_left - target) > abs(target - v - n_left):
                                    # print(stacks)
                                    # print(f"    - 会爆栈，不用这个运算符了 {new_op}, v={v}, target={target}")
                                    continue

                                result = _calculate(v - target, _old_expr + "-(")
                                if result is None:
                                    continue

                                return result + ")"

                            elif new_op == "+":
                                # print("    - 求", f"{left}{op}{right} + n == {target} ?")
                                if abs(n_left - target) < abs(target - v - n_left):
                                    # print(stacks)
                                    # print(f"    - 会爆栈，不用这个运算符了 {new_op}, v={v}, target={target}")
                                    continue

                                result = _calculate(target - v, _old_expr + "+")
                                if result is None:
                                    continue

                                return result

                            elif new_op == "*":
                                # print("    - 在 * 里面")
                                if v == 0:
                                    continue

                                times, mod = divmod(target, v)
                                if times in [0, 1]:
                                    continue

                                if v in [1]:
                                    continue

                                if abs(times * v) > target:
                                    continue

                                if mod == 0:
                                    mod_expr = ""
                                else:
                                    _mod = _calculate(mod, "")
                                    if _mod is None:
                                        continue
                                    mod_expr = ["+", "-"][mod <= 0] + _mod

                                times_expr = _calculate(times, "")
                                if times_expr is None:
                                    continue

                                if len(times_expr) > 1:
                                    times_expr = f"({times_expr})"

                                return f"{_old_expr}*{times_expr}{mod_expr}"
                            else:
                                # print("运算符未定义")
                                continue

            can_not_cal.append(target)
            return None

        _ops = {
            "**": operator.pow,
            "*": operator.mul,
            "+": operator.add,
            "-": operator.sub,
        }

        ops = {op: fn for op, fn in _ops.items() if not p9h.check(op)}

        target = self.node._value
        single_valid_num = {str(i) for i in range(10) if not p9h.check(i)}
        _valid_num = self.valid_num[:]

        can_not_cal = []
        try:
            result = _calculate(target, "")
        except RecursionError:
            print(f"\n[x] 爆栈了: calculate, {target}, {ops}, {self.valid_num}")
            __import__("sys").exit(1)

        if result is not None:
            _result = str(sympy.simplify(result)).replace(" ", "").replace("x", "")
            if not p9h.check(_result):
                return _result

            _result = result.replace("(", "").replace(")", "").replace("x", "")
            try:
                sympy.simplify(_result)
            except:
                pass
            else:
                if not p9h.check(_result):
                    return _result

            return result.replace("x", "")

        else:
            return str(self.node._value)

    @recursion_protect
    def by_unicode(self):
        umap = dict(zip(string.digits, "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"))
        return self.P9H(
            f'int({repr("".join([umap[i] for i in str(self.node._value)]))})',
        ).visit()


class Bypass_String(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = getattr(self.node, "value")

    @recursion_protect
    def by_char(self):
        # print("by_char", self.node._value)
        return (
            "("
            + self.P9H(
                "+".join([f"chr({ord(i)})" for i in self.node._value]),
            ).visit()
            + ")"
        )

    @recursion_protect
    def by_reverse(self):
        s = [
            (s[0], s[1], s[2]["self"].node._value)
            for s in get_stack()
            if s[1].startswith("by_")
        ]
        if s[0][:2] == s[1][:2] and s[0][2] == s[1][2][::-1]:
            # 避免出现 "123" -> "123"[::-1][::-1] 的现象
            return repr(self.node._value)

        # print("by_reverse", self.node._value)
        return self.P9H(
            f"{repr(self.node._value[::-1])}[::-1]",
        ).visit()

    @recursion_protect
    def by_dict(self):
        letters = [i for i in string.ascii_letters + "_" if not p9h.check(i)]
        if not letters:
            return self.node._value

        res = self.P9H(
            f"list(dict({letters[0]}{self.node._value}=()))[0][1:]",
        ).visit()
        try:
            # 部分字符串无法作为标识符，这里检查一下
            eval(res)
            return res
        except Exception:
            return self.node._value

    @recursion_protect
    def by_bytes_1(self):
        return self.P9H(
            "+".join([f"str(bytes([{ord(i)}]))[2]" for i in self.node._value]),
        ).visit()

    @recursion_protect
    def by_bytes_2(self):
        byte_list = [ord(i) for i in self.node._value]
        if all(map(lambda x: x in range(0, 256), byte_list)):
            return self.P9H(
                f"bytes({str(byte_list)})",
            ).visit()

        return self.node._value


class Bypass_Name(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = getattr(self.node, "id")

    def by_unicode(self):
        umap = dict(
            zip(
                string.digits + string.ascii_letters + "_",
                "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫ᵃᵇᶜᵈᵉᶠᵍʰᵢʲᵏˡᵐⁿᵒᵖ𝐪ʳˢᵗᵘᵛʷˣʸᶻᴬᴮCᴰᴱFᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾＱᴿ𝖲ᵀᵁⱽᵂⅩ𝖸Z＿",
            )
        )

        _result = self.node.id
        for kwd in p9h.check(self.node.id):
            fixed_str = ""
            # 特殊处理 _
            if kwd[0] == "_":
                _kwd = list(kwd[1:])
                fixed_str = "_"
            else:
                _kwd = list(kwd)

            for _i, _k in enumerate(_kwd):
                if _k in umap:
                    # 当前的算法是找到一个就替换结束
                    _kwd[_i] = umap[_k]
                    break

            _result = _result.replace(kwd, fixed_str + "".join(_kwd))

        return _result


class Bypass_Attribute(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = [getattr(self.node, "value"), getattr(self.node, "attr")]

    @recursion_protect
    def by_getattr(self):
        return self.P9H(
            f"getattr({self.P9H(self.node._value[0]).visit()}, {repr(self.node._value[1])})",
        ).visit()


class Bypass_Call(_Bypass):
    pass


class Bypass_Keyword(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.node._value = (getattr(self.node, "arg"), getattr(self.node, "value"))

    @recursion_protect
    def by_unicode(self):
        arg, value = self.node._value
        result = ""
        if arg is None:
            result += "**"
        else:
            result += self.P9H(arg).visit() + "="

        return result + self.P9H(value).visit()
