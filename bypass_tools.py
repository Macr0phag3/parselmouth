import ast
import string
import inspect
import json
import functools
import copy
import builtins
import types
import unicodedata

import parselmouth as p9h
from expression_solver import find_expression


def get_builtin_func_self_names():
    result = []
    for name in dir(builtins):
        obj = getattr(builtins, name, None)
        if inspect.isbuiltin(obj) and getattr(obj, "__self__", None) is builtins:
            result.append(name)

    return tuple(sorted(result, key=lambda item: (len(item), item)))

def get_builtin_doc_name():
    result = []
    for name in dir(builtins):
        obj = getattr(builtins, name, None)
        if isinstance(getattr(obj, "__doc__", None), str):
            result.append(name)

    return tuple(sorted(result, key=lambda item: (len(item), item)))

def get_multi_char_items():
    result = {}
    allowed = set(string.ascii_letters + string.digits + "_")
    for codepoint in range(0x110000):
        char = chr(codepoint)
        normalized = unicodedata.normalize("NFKC", char)
        if len(normalized) <= 1:
            continue

        if any(i not in allowed for i in normalized):
            continue

        if not char.isidentifier():
            continue

        if not normalized.isidentifier():
            continue

        result.setdefault(normalized, []).append(char)

    preferred = {
        normalized: max(chars)
        for normalized, chars in result.items()
    }

    return tuple(sorted(preferred.items(), key=lambda item: (-len(item[0]), item[0])))

BUILTIN_DOC_NAMES = get_builtin_doc_name()
BUILTIN_SELF_NAMES = get_builtin_func_self_names()
MULTI_CHAR_ITEMS = get_multi_char_items()

def replace_with_ligature(identifier):
    """
    连字符替换
    """
    result = identifier
    for normalized, ligature in MULTI_CHAR_ITEMS:
        candidate = result.replace(normalized, ligature)
        if candidate == result:
            continue

        result = candidate
        if not p9h.check(result):
            return result

    return None


def payload_warning(*messages):
    def _decorator(func):
        prefix = func.__qualname__
        cls_name, func_name = prefix.rsplit(".", 1)
        disable_hint = json.dumps({"black": {cls_name: func_name}})
        func._p9h_warnings = tuple(
            {
                "message": f"{prefix}: {message}",
                "disable_hint": disable_hint,
            }
            for message in messages
            if message
        )
        return func

    return _decorator


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
        self.P9H = self._spawn_p9h
        p9h.BLACK_CHAR = rule

    def _spawn_p9h(self, source_code, **kwargs):
        specify_bypass_map = {
            mode: {
                cls_name: ", ".join(func_names)
                for cls_name, func_names in class_map.items()
            }
            for mode, class_map in self.p9h_self.specify_bypass_map.items()
        }
        return p9h.P9H(
            source_code,
            bypass_history=self.p9h_self.bypass_history,
            specify_bypass_map=specify_bypass_map,
            min_len=self.p9h_self.min_len,
            min_set=self.p9h_self.min_set,
            depth=self.p9h_self.depth + 3 if self.p9h_self.verbose >= 2 else self.p9h_self.depth + 2,
            verbose=self.p9h_self.verbose,
            status=self.p9h_self.status,
            parent_attempt_id=self.p9h_self._active_attempt_id,
            **kwargs,
        )

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
                "[] != []",
                "[] is []",
                "[] > []",
                "[] < []",
            ],
            1: [
                "True",
                "0**0",
                "all( () )",
                "[] == []",
                "[] is not []",
            ],
            2: ["len( str( () ) )", "len( ((), ()) )"],
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

        time_budget = 5 if self.p9h_self.min_len else 2
        # digit atom 足够多时会额外生成大量两位/三位数候选，给 solver 稍微多一点时间
        if len(digit_atoms) >= 5:
            time_budget += 2

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
        if self.node._value == "":
            return self.P9H("str()").visit()
        else:
            return None

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
        # 利用标识符构建字符串的 bypass
        iden = self.node._value
        iden_tail = ""
        if not iden.isidentifier():
            iden_tail = "[1:]"
            letters = [i for i in string.ascii_letters + "_" if not p9h.check(i)]
            if not letters:
                return None

            iden = letters[0] + iden

            if not iden.isidentifier():
                # 存在非法标识符
                return None

        exps = [
            f"list(dict({iden}=()))[0]",
            f"list(dict({iden}=())).pop()",
            f"dict({iden}=()).popitem()[0]",
            f"next(iter(dict({iden}=())))",
            f"max(dict({iden}=()))",
             # 如果这里面 check 都失败了，
             # 那么最终会返回这个，因为这个是最好的选择
            f"min(dict({iden}=()))",
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
        _s = [
            (i[1], i[2]["self"].node._value)
            for i in get_stack()
            if i[1].startswith("by_") and "self" in i[2]
        ][1:]
        for func_name, node_value in _s:
            # 如果之前用过 bypass 是 chr_format
            # 并且参数就是 chr_format 所必须的字符 % 与 c
            # 就不要再用 chr_format bypass 尝试了
            if func_name == "by_char_format" and (set(node_value) & set("%c")):
                return None

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
        for func_name, node_value in [
            (i[1], i[2]["self"].node._value)
            for i in get_stack()
            if i[1].startswith("by_") and "self" in i[2]
        ][1:]:
            # 如果之前用过 bypass 是 format
            # 并且参数就是 format 所必须的字符 { 与 }
            # 就不要再用 format bypass 尝试了
            if func_name == "by_format" and (set(node_value) & set("{}")):
                return None

        _loc = "{}" * len(self.node._value)
        exp = [f"chr({ord(i)})" for i in self.node._value]
        payload = f"'{_loc}'.format({','.join(exp)})"
        return self.P9H(payload).visit()

    @recursion_protect
    def by_char(self):
        return self._join([f"chr({ord(i)})" for i in self.node._value])

    @recursion_protect
    def by_reverse(self):
        s = [
            (i[1], i[2]["self"].node._value)
            for i in get_stack()
            if i[1].startswith("by_") and "self" in i[2]
        ]
        if len(s) > 1 and s[0] == s[1] and s[0][1] == s[1][1][::-1]:
            # 放弃 bypass
            # 避免出现 "123" -> "123"[::-1][::-1] 的现象
            return None

        return self.P9H(
            f"{repr(self.node._value[::-1])}[::-1]",
        ).visit()

    @recursion_protect
    def by_bytes_single(self):
        byte_list = [ord(i) for i in self.node._value]
        if all([i in range(256) for i in byte_list]):
            return self._join([f"str(bytes([{i}]))[2]" for i in byte_list])
        else:
            return None

    @recursion_protect
    def by_bytes_full(self):
        byte_list = [ord(i) for i in self.node._value]
        if all([i in range(0, 256) for i in byte_list]):
            return self.P9H(
                f"bytes({str(byte_list)}).decode()",
            ).visit()

        return None

    @recursion_protect
    def by_doc_index(self):
        if self.node._value == "":
            return None

        avail_exp = []
        for name in BUILTIN_DOC_NAMES:
            if p9h.check(name):
                continue

            source_exp = f"{name}.__doc__"
            source_text = getattr(builtins, name).__doc__

            char_exp = {}
            for char in self.node._value:
                if char in char_exp:
                    continue

                if not (self.p9h_self.min_len or self.p9h_self.min_set):
                    idx = source_text.find(char)
                    if idx == -1:
                        char_exp = None
                        break

                    char_exp[char] = self.P9H(f"{source_exp}[{idx}]").visit()
                    continue

                best_piece = None
                for idx, source_char in enumerate(source_text):
                    # 寻找符合条件的 index
                    if source_char != char:
                        continue

                    piece = self.P9H(f"{source_exp}[{idx}]").visit()
                    if self.p9h_self.min_set:
                        if best_piece is None or (
                            len(set(piece)),
                            len(piece),
                            piece,
                        ) < (
                            len(set(best_piece)),
                            len(best_piece),
                            best_piece,
                        ):
                            best_piece = piece
                    else:
                        if best_piece is None or (len(piece), piece) < (
                            len(best_piece),
                            best_piece,
                        ):
                            best_piece = piece

                if best_piece is None:
                    char_exp = None
                    break

                char_exp[char] = best_piece

            if char_exp is None:
                continue

            result = self._join(char_exp[char] for char in self.node._value)
            if not (self.p9h_self.min_len or self.p9h_self.min_set):
                return result

            avail_exp.append(result)

        if not avail_exp:
            return None

        if self.p9h_self.min_set:
            return min(avail_exp, key=lambda item: (len(set(item)), len(item), item))

        if self.p9h_self.min_len:
            return min(avail_exp, key=lambda item: (len(item), item))

        return avail_exp[0]


class Bypass_Name(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = getattr(self.node, "id")

    @recursion_protect
    def by_ligature(self):
        return replace_with_ligature(self.node._value)

    @recursion_protect
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

    @payload_warning(
        "__builtins__ may be a dict"
    )
    @recursion_protect
    def by_builtins_attr(self):
        """
        __import__ => __builtins__.__import__
        """

        name = self.node._value
        return self.P9H(f"__builtins__.{name}").visit()

    @payload_warning(
        "__builtins__ may be a module/object"
    )
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
            return None

        avail_builtin_func_names = [
            builtin_func_name
            for builtin_func_name in BUILTIN_SELF_NAMES
            if builtin_func_name != name and not p9h.check(builtin_func_name)
        ]

        if not avail_builtin_func_names:
            return None

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
            return None

        return self.P9H(f"(i for i in ()).gi_frame.f_builtins[{repr(name)}]").visit()

    @recursion_protect
    def by_running_frame(self):
        """
        __import__ => running generator frame -> caller frame -> f_builtins['__import__']
        """

        name = self.node._value
        if not hasattr(builtins, name):
            return None

        return self.P9H(
            f"[[*a[0]].pop() for a in [[]] if [a.append((i.gi_frame.f_back for i in a))]][0].f_back.f_builtins[{repr(name)}]"
        ).visit()

class Bypass_Attribute(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = [getattr(self.node, "value"), getattr(self.node, "attr")]

    def _build_attr_access(self, attr_name):
        node = self.node._value[0]
        value_exp = self.P9H(node).visit()
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            value_exp += " "
        elif not isinstance(
            # 这些类型不用加括号
            node,
            (
                ast.Name,ast.Attribute, ast.Call, ast.Subscript, ast.Constant,
                ast.List, ast.Tuple, ast.Dict, ast.Set,
                ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp
            ),
        ):
            value_exp = f"({value_exp})"

        return f"{value_exp}.{attr_name}"

    @recursion_protect
    def by_ligature(self):
        _, attr_name = self.node._value
        attr_candidate = replace_with_ligature(attr_name)
        if attr_candidate is None:
            return None

        return self._build_attr_access(attr_candidate)

    @recursion_protect
    def by_unicode(self):
        _, attr_name = self.node._value
        attr_candidate = Bypass_Name(
            p9h.BLACK_CHAR, ast.Name(attr_name), self.p9h_self
        ).by_unicode()

        return self._build_attr_access(attr_candidate)

    @recursion_protect
    def by_getattr(self):
        return self.P9H(
            f"getattr({self.P9H(self.node._value[0]).visit()}, {repr(self.node._value[1])})",
        ).visit()

    @payload_warning(
        "may fail for inherited attributes, descriptors, __getattr__-provided attributes, or basic types"
    )
    @recursion_protect
    def by_vars(self):
        """
        str.find => vars(str)["find"]
        """
        node, attr_name = self.node._value
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "vars"
        ):
            return None

        # 注意
        # vars(bytes([111,115]))
        # vars(1+1)
        # 之类，是不行的，因为基础类型没有 __dict__
        return self.P9H(
            f"vars({self.P9H(node).visit()})[{repr(attr_name)}]",
        ).visit()

    @payload_warning(
        "may fail for inherited attributes, descriptors, or __getattr__-provided attributes"
    )
    @recursion_protect
    def by_dict_attr(self):
        """
        str.find => str.__dict__["find"]
        """
        # 注意
        # bytes([111,115]).__dict__
        # (1+1).__dict__
        # 之类，是不行的，以为基础类型没有 __dict__
        node, attr_name = self.node._value
        if attr_name in ["__dict__", "__getitem__"]:
            # 防止无限递归下去
            return None

        return self.P9H(
            f"{self.P9H(node).visit()}.__dict__[{repr(attr_name)}]",
        ).visit()


class Bypass_Subscript(_Bypass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node._value = [getattr(self.node, "value"), getattr(self.node, "slice")]

    def _getitem_arg_part(self, node):
        if node is None:
            return "None"

        return self._getitem_arg(node)

    def _getitem_arg(self, node):
        if isinstance(node, ast.Slice):
            lower = self._getitem_arg_part(node.lower)
            upper = self._getitem_arg_part(node.upper)
            step = self._getitem_arg_part(node.step)

            if node.step is not None:
                return f"slice({lower},{upper},{step})"

            if node.lower is None and node.upper is None:
                return "slice(None)"

            if node.lower is None:
                return f"slice(None,{upper})"

            if node.upper is None:
                return f"slice({lower},None)"

            return f"slice({lower},{upper})"

        if isinstance(node, ast.Tuple):
            # 暂时只支持一元索引
            # 像 a[1:2,3] / a[0,1] 这类多维索引暂不支持
            return None

        return self.P9H(node).visit()

    @recursion_protect
    def by_getitem_attr(self):
        """
        a[b] => a.__getitem__(b)
        """
        value, index = self.node._value
        index_exp = self._getitem_arg(index)
        if index_exp is None:
            return None

        return self.P9H(
            f"{self.P9H(value).visit()}.__getitem__({index_exp})",
        ).visit()

    @recursion_protect
    def by_getitem_getattr(self):
        """
        a[b] => getattr(a, '__getitem__')(b)
        """
        value, index = self.node._value
        index_exp = self._getitem_arg(index)
        if index_exp is None:
            return None

        return self.P9H(
            f"getattr({self.P9H(value).visit()}, '__getitem__')({index_exp})",
        ).visit()


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
    def by_ligature(self):
        arg, value = self.node._value
        if arg is None:
            return None

        result = Bypass_Name(p9h.BLACK_CHAR, ast.Name(arg), self.p9h_self).by_ligature()
        if result is None:
            return None

        return result + "=" + self.P9H(value).visit()

    @recursion_protect
    def by_unicode(self):
        arg, value = self.node._value
        result = ""
        if arg is None:
            result += "**"
        else:
            # arg 即为具名参数的 id
            # 这里直接 hack 掉，直达 Bypass_Name
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
        (c1 and (c2 or c3)) or (c2 and c3) => c1 & (c2 | c3) | c2 & c3
        """

        op, values = self.node._value
        op_map = {"Or": "|", "And": "&"}

        return self.P9H(
            f"({self.P9H(values[0]).visit()}) {op_map[op]} ({self.P9H(values[1]).visit()})"
        ).visit()

    @recursion_protect
    def by_arithmetic(self):
        """
        c1 or c2  => (bool(c1) + bool(c2))
        c1 and c2 => (bool(c1) * bool(c2))
        """
        op, values = self.node._value

        if op == "Or":
            return self.P9H(
                f"(bool({self.P9H(values[0]).visit()}) + bool({self.P9H(values[1]).visit()}))"
            ).visit()

        elif op == "And":
            return self.P9H(
                f"(bool({self.P9H(values[0]).visit()}) * bool({self.P9H(values[1]).visit()}))"
            ).visit()
        else:
            # 其实不存在其他类型
            # 暂时预留吧免得出错
            return None
