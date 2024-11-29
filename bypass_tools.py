import operator
import ast
import string
import inspect
import functools
import copy
import builtins

import sympy  # type: ignore

import parselmouth as p9h


def recursion_protect(func):
    @functools.wraps(func)
    def _protect(self):
        stack = []
        ns = get_stack()
        # print(len(ns))
        # print(
        #     [
        #         (i[0] + "." + i[1], i[2]["self"].node._value)
        #         for i in get_stack()
        #         if i[1].startswith("by_")
        #     ]
        # )
        # print([(i[0] + "." + i[1]) for i in get_stack()])
        for s in ns:
            if not s[1].startswith("by_"):
                continue

            stack.append((s[0], s[1], s[2]["self"].node._value))

        var = self.node._value
        if (self.__class__.__name__, func.__name__, var) in stack:
            # 本轮调用的 函数+参数 在调用链之前就出现过
            # 说明不同的 bypass 函数之间出现了循环依赖
            # 这个时候应该舍弃掉这个 bypass 函数
            return None

        # print(func.__name__, self.node._value, stack)
        return func(self)

    return _protect


def get_stack(num=0):
    used_funcs = []
    if num == 0:
        stack = [i.frame for i in inspect.stack()]
    else:
        stack = []
        ic = inspect.currentframe()
        while ic and len(stack) <= num:
            stack.append(ic)
            ic = ic.f_back

    for frame in stack:
        # 获取当前层的上下文信息
        arg_info = inspect.getargvalues(frame)

        class_name = ""
        if "self" in frame.f_locals:
            class_name = frame.f_locals["self"].__class__.__name__

        # 打印调用链中的函数名和参数
        used_funcs.append(
            (
                class_name,
                frame.f_code.co_name,
                {k: arg_info.locals[k] for k in arg_info.args},
            )
        )

    return used_funcs


class _Bypass:
    def __init__(self, rule, node, p9h_self):
        self.node = node
        self.p9h_self = p9h_self
        self.P9H = functools.partial(
            p9h.P9H,
            bypass_history=p9h_self.bypass_history,
            specify_bypass_map=p9h_self.specify_bypass_map,
            min_len=p9h_self.min_len,
            min_set=p9h_self.min_set,
            depth=p9h_self.depth + 3 if p9h_self.verbose >= 2 else p9h_self.depth + 2,
            versbose=p9h_self.verbose,
        )
        p9h.BLACK_CHAR = rule

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

        # 填充 0-9 缺失的数字
        self.valid_num = []
        for i in list(range(10))[::-1]:
            if not p9h.check(i, ignore_space=True):
                self.valid_num.append(str(i))

            elif i in self.translate_map:
                for j in self.translate_map[i]:
                    if not p9h.check(j, ignore_space=True):
                        self.valid_num.append(str(j))
                        break

    @recursion_protect
    def by_trans(self):
        translate_map = copy.deepcopy(self.translate_map)
        translate_map[1].extend([f"-~{i}" for i in translate_map[0] + [0]])
        if self.node._value in translate_map:
            # 直接返回替代
            for i in translate_map[self.node._value]:
                if not p9h.check(i, ignore_space=True):
                    return self.P9H(str(i)).visit()

        return str(self.node._value)

    @recursion_protect
    def by_bin(self):
        return bin(self.node._value)

    @recursion_protect
    def by_hex(self):
        return hex(self.node._value)

    @recursion_protect
    def by_cal(self):
        def _calculate(target, old_expr):
            stacks = [i[2]["target"] for i in get_stack() if i[1] == "_calculate"][1:]
            if target in stacks or target in can_not_cal:
                return None

            if set(str(target)).issubset(single_valid_num) and not p9h.check(
                target, ignore_space=True
            ):
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
                            # print(f"{old_expr}{left}{op}{right}")
                            return f"{old_expr}{left}{op}{right}"

                        if first:
                            _old_expr = f"({left}{op}{right})"
                            if v in valid_num_map:
                                _old_expr = "x" + valid_num_map[v]
                        else:
                            _old_expr = old_expr + f"{left}{op}{right}"
                            if v in valid_num_map:
                                _old_expr = old_expr + "x" + valid_num_map[v]

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
                                if v <= 0 or abs(n_left - target) > abs(
                                    target - v - n_left
                                ):
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
        single_valid_num = {
            str(i) for i in range(10) if not p9h.check(i, ignore_space=True)
        }
        _valid_num = self.valid_num[:]
        valid_num_map = dict(zip(map(int, map(eval, _valid_num)), _valid_num))
        # print(_valid_num, valid_num_map)
        can_not_cal = []
        try:
            result = _calculate(target, "")
            # print(result)
        except RecursionError:
            print(f"\n[x] 爆栈了: calculate, {target}, {ops}, {self.valid_num}")
            __import__("sys").exit(1)

        if result is not None:
            try:
                _result = str(sympy.simplify(result)).replace("x", "")
            except Exception as e:
                # print(f"[DEBUG] sympy simplify error: {e}")
                pass
            else:
                if not p9h.check(_result, ignore_space=True):
                    return self.P9H(_result).visit()

            return self.P9H(result.replace("x", "")).visit()

        else:
            # print(f"[DEBUG] Calculation failed for target: {target}")
            return str(self.node._value)

    @recursion_protect
    def by_ord(self):
        prefix = ""
        if self.node._value < 0:
            prefix = "-"

        value = abs(self.node._value)
        if 0 <= value < 0x110000:
            return self.P9H(f"{prefix}ord({repr(chr(value))})").visit()
        else:
            return self.node._value

    @recursion_protect
    def by_unicode(self):
        # 注意，\d 是会匹配到任意数字 unicode 的
        # 证明:
        # for i in range(0x110000):
        #     i = chr(i)
        #     try:
        #         int(i)
        #     except:
        #         continue
        #     if not re.findall("\d", i):
        #         print(i)
        # 结果为空
        umap = dict(zip(string.digits, "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"))
        return self.P9H(
            f'int({repr("".join([umap.get(i, i) for i in str(self.node._value)]))})',
        ).visit()


class Bypass_String(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = getattr(self.node, "value")

    def _join(self, items):
        items = list(items)
        if len(items) == 1:
            return self.P9H(items[0]).visit()

        if p9h.check("+"):
            # + 在黑名单中，使用 str.join 替代
            return self.P9H(f"''.join(({','.join(items)}))").visit()
        else:
            # 否则直接使用 +
            # 这里最好加上括号，对原有运算优先级造成影响
            return "(" + self.P9H(f"{'+'.join(items)}").visit() + ")"

    @recursion_protect
    def by_empty_str(self):
        # p9h.P9H._write_str_avoiding_backslashes 中
        # 做了特殊处理，这里直接使用 repr 即可
        if self.node._value == "":
            return self.P9H(f"str()").visit()
        else:
            return repr(self.node._value)

    @recursion_protect
    def by_quote_trans(self):
        # p9h.P9H._write_str_avoiding_backslashes 中
        # 做了特殊处理，这里直接使用 repr 即可
        return repr(self.node._value)

    @recursion_protect
    def by_char_add(self):
        """
        'macr0phag3' => 'm'+'a'+'c'+'r'+'0'+'p'+'h'+'a'+'g'+'3'
        """

        return self._join(map(repr, list(self.node._value)))

    @recursion_protect
    def by_dict(self):
        # 用于利用标识符构建字符串的 bypass
        iden = self.node._value
        iden_tail = ""
        if not iden.isidentifier():
            iden_tail = "[1:]"
            letters = [i for i in string.ascii_letters + "_" if not p9h.check(i)]
            if not letters:
                return repr(self.node._value)

            iden = letters[0] + iden

            if not iden.isidentifier():
                # 非法标识符
                return repr(self.node._value)

        exps = [
            f"list(dict({iden}=()))[0]",
            f"list(dict({iden}=())).pop()",
            f"dict({iden}=()).popitem()[0]",
            f"next(iter(dict({iden}=())))",
            f"min(dict({iden}=()))",
            f"max(dict({iden}=()))",
        ]
        for exp in exps:
            exp += iden_tail
            if not p9h.check(exp):
                return self.P9H(exp).visit()

        return self.P9H(exp).visit()

    @recursion_protect
    def by_hex_encode(self):
        # hex 编码理论上通过编解码，也可以支持非 ascii 字符
        # 但是算了，感觉不是很实用
        if all(ord(i) in range(256) for i in self.node._value):
            r = "".join("\\x{:02x}".format(ord(c)) for c in self.node._value)
            return f"'{r}'"
        else:
            return repr(self.node._value)

    @recursion_protect
    def by_unicode_encode(self):
        r = "".join("\\u{:04x}".format(ord(c)) for c in self.node._value)
        return f"'{r}'"

    @recursion_protect
    def by_char_format(self):
        """
        '__builtins__' => '%c%c%c%c%c%c%c%c%c%c%c%c' % (95,95,98,117,105,108,116,105,110,115,95,95)
        """

        # 避免无限递归
        _s = [i for i in get_stack() if i[1].startswith("by_")][1:]
        for i in _s:
            # 如果上一个 bypass 用的也是 chr_format
            # 并且参数就是 chr_format 所必须的字符 %、c
            # 就不要再用 chr_format bypass 尝试了
            if i[1] == "by_char_format" and set(i[2]) | set("%c"):
                return repr(self.node._value)

        format_str = "%c" * len(self.node._value)
        if len(self.node._value) == 1:
            # 防止出现 "%c" % -5**2+7+7**2+9**2-True
            num = "(" + self.P9H(str(ord(self.node._value))).visit() + ")"
        else:
            num = str(tuple(map(ord, self.node._value)))

        result = f"({self.P9H(repr(format_str)).visit()})%{num}"
        return self.P9H(result).visit()

    @recursion_protect
    def by_format(self):
        # 避免无限递归
        _s = [i for i in get_stack() if i[1].startswith("by_")][1:]
        for i in _s:
            # 如果上一个 bypass 用的也是 format
            # 并且参数就是 format 所必须的字符 {、}
            # 就不要再用 format bypass 尝试了
            if i[1] == "by_format" and set(i[2]) | set("{}"):
                return repr(self.node._value)

        _loc = "{}" * len(self.node._value)
        exp = [f"chr({ord(i)})" for i in self.node._value]
        return self.P9H(f"'{_loc}'.format({','.join(exp)})").visit()

    @recursion_protect
    def by_char(self):
        return self._join([f"chr({ord(i)})" for i in self.node._value])

    @recursion_protect
    def by_reverse(self):
        s = [
            (s[0], s[1], s[2]["self"].node._value)
            for s in get_stack()
            if s[1].startswith("by_")
        ]
        if len(s) > 1 and s[0][:2] == s[1][:2] and s[0][2] == s[1][2][::-1]:
            # 放弃 bypass
            # 避免出现 "123" -> "123"[::-1][::-1] 的现象
            return repr(self.node._value)

        result = self.P9H(
            f"{repr(self.node._value[::-1])}[::-1]",
        ).visit()
        return result

    @recursion_protect
    def by_bytes_single(self):
        byte_list = [ord(i) for i in self.node._value]
        if all([i in range(256) for i in byte_list]):
            return self._join([f"str(bytes([{i}]))[2]" for i in byte_list])
        else:
            return repr(self.node._value)

    @recursion_protect
    def by_bytes_full(self):
        byte_list = [ord(i) for i in self.node._value]
        if all([i in range(0, 256) for i in byte_list]):
            return self.P9H(
                f"bytes({str(byte_list)}).decode()",
            ).visit()

        return repr(self.node._value)


class Bypass_Name(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = getattr(self.node, "id")

    def by_unicode(self):
        umap = dict(
            zip(
                string.digits + string.ascii_letters + "_",
                "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁＿",
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

    @recursion_protect
    def by_builtins(self):
        """
        __import__ => __builtins__.__import__
        """

        name = self.node._value
        # 注意这里不能使用  getattr(__builtins__, func_name, None)
        # 因为本文件是要被 import 的，此时 __builtins__ 会变成字典
        if not getattr(builtins, name, None):
            return name

        return self.P9H(f"__builtins__.{name}").visit()


class Bypass_Attribute(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = [getattr(self.node, "value"), getattr(self.node, "attr")]

    @recursion_protect
    def by_getattr(self):
        return self.P9H(
            f"getattr({self.P9H(self.node._value[0]).visit()}, {repr(self.node._value[1])})",
        ).visit()

    @recursion_protect
    def by_vars(self):
        """
        str.find => vars(str)["find"]
        """
        # 注意
        # vars(bytes([111,115]))
        # vars(1+1)
        # 之类，是不行的，以为基础类型没有 __dict__
        # 因此保险起见，这里适用类型还是用白名单吧
        if type(self.node._value[0]) in (ast.Name,):
            return self.P9H(
                f"vars({self.P9H(self.node._value[0]).visit()})[{repr(self.node._value[1])}]",
            ).visit()
        else:
            return None

    @recursion_protect
    def by_dict_attr(self):
        """
        str.find => str.__dict__["find"]
        """
        # 注意
        # vars(bytes([111,115]))
        # vars(1+1)
        # 之类，是不行的，以为基础类型没有 __dict__
        # 因此保险起见，这里适用类型还是用白名单吧
        if type(self.node._value[0]) in (ast.Name,):
            return self.P9H(
                f"{self.P9H(self.node._value[0]).visit()}.__dict__[{repr(self.node._value[1])}]",
            ).visit()
        else:
            return None


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
            # arg 即为具名参数的 id
            # 这里直接 hack 掉直达 Bypass_Name
            # 因为此时这里一定是 Name, 否则是非法的语句
            result += (
                Bypass_Name(p9h.BLACK_CHAR, ast.Name(arg), self.p9h_self).by_unicode()
                + "="
            )

        return result + self.P9H(value).visit()


class Bypass_BoolOp(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 存储布尔运算的左右操作数和操作符
        self.node._value = (
            getattr(self.node, "op").__class__.__name__,
            getattr(self.node, "values"),
        )

    @recursion_protect
    def by_bitwise(self):
        """
        (c1 and (c2 or c3)) or (c2 and c3) => c1&(c2|c3)|c2&c3
        """

        op, values = self.node._value
        op_map = {"Or": "|", "And": "&"}

        return self.P9H(
            f"({self.P9H(values[0]).visit()}) {op_map[op]} ({self.P9H(values[1]).visit()})"
        ).visit()

    @recursion_protect
    def by_arithmetic(self):
        """
        c1 or c2  => (bool(c1)+bool(c2))
        c1 and c2 => (bool(c1)*bool(c2))
        """
        op, values = self.node._value

        if op == "Or":
            return self.P9H(
                f"(bool({self.P9H(values[0]).visit()})+bool({self.P9H(values[1]).visit()}))"
            ).visit()

        elif op == "And":
            return self.P9H(
                f"(bool({self.P9H(values[0]).visit()})*bool({self.P9H(values[1]).visit()}))"
            ).visit()
        else:
            return None
