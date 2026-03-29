import ast
import string
import inspect
import functools
import copy
import builtins
import types

import parselmouth as p9h
from expression_solver import find_expression


def get_builtin_func_self_names():
    result = []
    for name in dir(builtins):
        obj = getattr(builtins, name, None)
        if inspect.isbuiltin(obj) and getattr(obj, "__self__", None) is builtins:
            result.append(name)

    return tuple(sorted(result, key=lambda item: (len(item), item)))


BUILTIN_FUNC_SELF_NAMES = get_builtin_func_self_names()


def recursion_protect(func):
    @functools.wraps(func)
    def _protect(self, __func_name=func.__name__):
        stack = []
        ns = get_stack()[2:]
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
            frame_func_name = s[2].get("__func_name", s[1])
            if not frame_func_name.startswith("by_"):
                continue

            if "self" not in s[2]:
                continue

            stack.append(
                (
                    s[0],
                    frame_func_name,
                    ast.dump(s[2]["self"].node, include_attributes=False),
                )
            )

        var = ast.dump(self.node, include_attributes=False)
        if (self.__class__.__name__, __func_name, var) in stack:
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
        time_budget = 2.5 if self.p9h_self.min_len else 1.5
        atom_map = {}
        digit_atoms = []
        operators = [op for op in ("**", "*", "+", "-") if not p9h.check(op)]
        allow_parentheses = not p9h.check("(") and not p9h.check(")")
        for atom in self.valid_num:
            try:
                text = ast.unparse(ast.parse(atom, mode="eval"))
            except Exception:
                text = atom.replace(" ", "")

            if p9h.check(text, ignore_space=True):
                continue

            value = eval(atom)
            if isinstance(value, bool):
                value = int(value)

            current = atom_map.get(value)
            if current is None or len(text) < len(current):
                atom_map[value] = text

            if text.isdigit() and len(text) == 1:
                digit_atoms.append(text)

        for i in digit_atoms:
            for j in digit_atoms:
                for k in ["", *digit_atoms]:
                    text = f"{i}{j}{k}"
                    if len(text) > 1 and text[0] == "0":
                        continue
                    if p9h.check(text, ignore_space=True):
                        continue

                    value = int(text)
                    current = atom_map.get(value)
                    if current is None or len(text) < len(current):
                        atom_map[value] = text

        result = find_expression(
            atoms=[(text, value) for value, text in atom_map.items()],
            operators=operators,
            target=self.node._value,
            allow_parentheses=allow_parentheses,
            shortest=self.p9h_self.min_len,
            max_depth=4,
            time_budget=time_budget,
        )
        if result is not None:
            return self.P9H(result).visit()
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
    def by_builtins_attr(self):
        """
        __import__ => __builtins__.__import__
        """

        name = self.node._value
        return self.P9H(f"__builtins__.{name}").visit()

    @recursion_protect
    def by_builtins_item(self):
        """
        __import__ => __builtins__['__import__']
        """

        name = self.node._value
        return self.P9H(f"__builtins__[{repr(name)}]").visit()

    @recursion_protect
    def by_builtin_func_self(self):
        """
        __import__ => id.__self__.__import__
        """

        name = self.node._value
        if not hasattr(builtins, name):
            return name

        avail_builtin_func_names = [
            builtin_func_name
            for builtin_func_name in BUILTIN_FUNC_SELF_NAMES
            if builtin_func_name != name and not p9h.check(builtin_func_name)
        ]

        # 下沉最小长度的判定逻辑
        if self.p9h_self.min_set:
            avail_exp = []
            for builtin_func_name in avail_builtin_func_names:
                result = self.P9H(f"{builtin_func_name}.__self__.{name}").visit()
                avail_exp.append(result)

            if avail_exp:
                return min(avail_exp, key=lambda item: (len(set(item)), len(item), item))

        return self.P9H(f"{avail_builtin_func_names[0]}.__self__.{name}").visit()

    @recursion_protect
    def by_frame(self):
        name = self.node._value
        if not hasattr(builtins, name):
            return name

        return self.P9H(f"(i for i in ()).gi_frame.f_builtins[{repr(name)}]").visit()

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
    """
    Bypass_Call 的 by_ 函数是动态生成的
    因此与 Bypass_Name/Bypass_Attribute 的 by_ 函数一致
    """

    @classmethod
    def dynamic_func_names(cls):
        result = []
        for sub_cls in (Bypass_Name, Bypass_Attribute):
            for func_name in sub_cls.__dict__:
                if func_name.startswith("by_") and func_name not in result:
                    result.append(func_name)

        return tuple(result)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 统一成 (被调用对象, 位置参数, 关键字参数) 结构，方便后续不同 bypass 复用
        self.node._value = (
            getattr(self.node, "func"),
            getattr(self.node, "args"),
            getattr(self.node, "keywords"),
        )

    def _sub_bypass(self):
        # Call 本身不直接发明 payload，而是把 () 前面的被调用对象
        # 交给对应的 Name/Attribute bypass 去产出候选写法
        func_node = self.node._value[0]
        bypass_cls = {
            ast.Name: Bypass_Name,
            ast.Attribute: Bypass_Attribute,
        }.get(type(func_node))
        if bypass_cls is None:
            return

        bypass_ins = bypass_cls(p9h.BLACK_CHAR, func_node, self.p9h_self)
        yield from bypass_ins.get_map().items()

    def _wrapper(self, func_name, method):
        def _dynamic_wrapper(_self):
            func_candidate = method()
            if func_candidate is None:
                # 说明该绕过不适用
                return None

            # 参数和关键字参数也直接递归走 P9H，避免 ast.unparse 把子节点绕过结果回退掉
            call_args = [_self.P9H(arg).visit() for arg in _self.node._value[1]]
            call_args.extend(
                _self.P9H(keyword).visit() for keyword in _self.node._value[2]
            )
            return f"{func_candidate}({','.join(call_args)})"

        _dynamic_wrapper.__name__ = func_name
        _dynamic_wrapper.__qualname__ = f"{self.__class__.__name__}.{func_name}"
        _dynamic_wrapper = recursion_protect(_dynamic_wrapper)
        return types.MethodType(_dynamic_wrapper, self)

    def get_map(self):
        return {
            func_name: self._wrapper(func_name, method)
            for func_name, method in self._sub_bypass()
        }


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
