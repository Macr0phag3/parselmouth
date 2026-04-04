import ast
import re
import sys
import functools

from rich.text import Text

import bypass_tools
from ui import (
    P9HRenderMixin,
    RuntimeStatus,
    colored_text,
    console,
    format_bypass_func as _format_bypass_func,
    logo,
    normalize_verbose,
    richify,
)


def color_check(result):
    result = str(result)
    hits = check(result)
    if not hits:
        return True, colored_text(result, "green")

    hit_mask = [False] * len(result)
    for hit in hits:
        if not hit:
            continue
        start = 0
        while True:
            index = result.find(hit, start)
            if index == -1:
                break
            for offset in range(index, min(index + len(hit), len(result))):
                hit_mask[offset] = True
            start = index + 1

    colored_result = Text(no_wrap=False, overflow="fold")
    index = 0
    while index < len(result):
        is_hit = hit_mask[index]
        end = index + 1
        while end < len(result) and hit_mask[end] == is_hit:
            end += 1
        colored_result.append(
            result[index:end],
            style="warn" if is_hit else "green",
        )
        index = end

    return False, colored_result


def cache_check_func(func, maxsize=99999, extra_key_func=None):
    # 为 check 函数统一加缓存：
    # 1. 先把 AST 归一化成源码字符串，避免按对象身份缓存
    # 2. extra_key_func 可把规则等外部状态并入缓存 key，防止一个 P9H 实例多次使用串缓存
    # 3. 既用于内置 check，也自动用于用户 monkeypatch 的 challenge_check
    @functools.lru_cache(maxsize=maxsize)
    def _cached(payload, ignore_space, extra_key):
        result = func(payload, ignore_space)
        if result is None:
            return ()

        return tuple(result)

    @functools.wraps(func)
    def _wrapper(payload, ignore_space=False):
        if isinstance(payload, ast.AST):
            payload = ast.unparse(payload)

        return list(
            _cached(
                str(payload),
                bool(ignore_space),
                extra_key_func() if extra_key_func else None,
            )
        )

    _wrapper._p9h_cached = True
    _wrapper._p9h_check_impl = func
    return _wrapper


def check(payload, ignore_space=False):
    """
    检查 payload 中是否命中规则
    可以被覆盖用于自定义检测逻辑
    cache_check_func 会自动使用 lru_cache 来提速 check
    """

    kwd = tuple(BLACK_CHAR.get("kwd", []))
    re_kwd = BLACK_CHAR.get("re_kwd", "")
    if not kwd and not re_kwd:
        # 无规则？提示一下
        console.print(colored_text("[!] rule is empty, do not need bypass", "red"))
        raise SystemExit(1)

    payload = str(payload)
    kwd_check = [
        i for i in kwd
        if (not ignore_space or (ignore_space and i not in [" ", "\t"]))
        and i in payload
    ]
    re_check = (
        set(re.findall(re_kwd, payload))
        if re_kwd
        else set()
    ) - ({" ", "\t"} if ignore_space else set())
    return kwd_check + sorted(re_check)


check = cache_check_func(
    check,
    extra_key_func=lambda: (
        tuple(BLACK_CHAR.get("kwd", [])),
        BLACK_CHAR.get("re_kwd") or "",
    ),
)


def normalize_specify_bypass_map(specify_bypass_map):
    """
    检查并规范化 specify_bypass_map
    """

    if specify_bypass_map is None:
        return {}

    if not isinstance(specify_bypass_map, dict):
        raise ValueError("must be a dict")

    normalized = {}
    for mode, class_map in specify_bypass_map.items():
        if mode not in ["white", "black"]:
            raise ValueError("can only use keys `white` or `black`")

        if class_map is None:
            normalized[mode] = {}
            continue

        if not isinstance(class_map, dict):
            raise ValueError(
                f"`{mode}` must be like `{{'Bypass_Class': 'by_func1, by_func2, ...'}}`"
            )

        normalized_class_map = {}
        for cls_name, func_names in class_map.items():
            cls = vars(bypass_tools).get(cls_name)
            if cls is None:
                raise ValueError(f"bypass class not found: {cls_name}")

            if isinstance(func_names, str):
                func_names = [
                    name.strip() for name in func_names.split(",") if name.strip()
                ]
            else:
                raise ValueError(
                    f"`{mode} {cls_name}` must be a comma-separated string of bypass functions"
                )

            if not func_names:
                raise ValueError(
                    f"`{mode} {cls_name}` has no bypass function"
                )

            # 有些 Bypass_Class 有些方法是动态生成的，需要特殊处理
            missing_func_names = [
                func_name
                for func_name in func_names
                if not hasattr(cls, func_name) and func_name not in (
                    cls.dynamic_func_names() if hasattr(cls, "dynamic_func_names") else []
                )
            ]
            if missing_func_names:
                raise ValueError(
                    f"bypass func not found in {cls_name}: {missing_func_names!r}"
                )

            normalized_class_map[cls_name] = func_names

        normalized[mode] = normalized_class_map

    return normalized


class P9H(P9HRenderMixin, ast._Unparser):
    def __init__(
        self,
        source_code,
        depth=0,
        verbose=1,
        bypass_history=None,
        min_len=False,
        min_set=False,
        specify_bypass_map=None,
        status=None, # 用于实时状态面板
        parent_attempt_id=None, # 用于 trace
    ):
        globals()["FORMAT_SPACE"] = ""
        # 自动给 check 函数加上缓存机制
        globals()["check"] = (
            globals()["check"]
            if getattr(globals()["check"], "_p9h_cached", False)
            else cache_check_func(globals()["check"])
        )
        self.source_code = source_code
        try:
            self.source_node = (
                source_code
                if isinstance(source_code, ast.AST)
                else ast.parse(source_code)
            )
        except Exception:
            console.print(
                colored_text("[!] invalid python code:", "red"),
                colored_text(source_code, "white"),
            )
            raise

        self.verbose = normalize_verbose(verbose)
        self.bypass_history = bypass_history or {
            "success": {},  # 已知成功绕过的 payload
            "failed": set(),  # 已知无法绕过的 payload
            "runs": {},  # 每次运行的记录
            "nodes": {},  # 被拦截节点的记录
            "attempts": {},  # 每次 bypass 尝试的记录
            "next_run_id": 1,  # 下一个运行 ID
            "next_node_id": 1,  # 下一个节点 ID
            "next_attempt_id": 1,  # 下一个尝试 ID
        }

        self.depth = depth
        self.min_len = min_len
        self.min_set = min_set
        self.specify_bypass_map = normalize_specify_bypass_map(specify_bypass_map)
        self.status = status
        self.parent_attempt_id = parent_attempt_id
        self._active_attempt_id = None
        self.root_node_ids = []
        self.result = None
        self.result_warnings = []
        self.run_id = self._new_id("next_run_id")
        run_source = ast.unparse(source_code) if isinstance(source_code, ast.AST) else str(source_code)
        self.bypass_history["runs"][self.run_id] = {
            "id": self.run_id,
            "source": run_source,
            "parent_attempt_id": self.parent_attempt_id,
            "root_node_ids": self.root_node_ids,
            "result": None,
            "warnings": [],
        }
        if self.parent_attempt_id is not None:
            self.bypass_history["attempts"][self.parent_attempt_id]["child_run_ids"].append(
                self.run_id
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

    def _write_str_avoiding_backslashes(self, string, *, _write=True):
        """Write string literal value with a best effort attempt to avoid backslashes."""
        quote_types = [i for i in ["'", '"'] if not check(i)]  # 这里直接舍弃 ''' 和 """
        string, quote_types = self._str_literal_helper(
            string, quote_types=quote_types, escape_special_whitespace=True
        )
        quote_type = quote_types[0]
        result = f"{quote_type}{string}{quote_type}"
        if _write:
            self.write(f"{quote_type}{string}{quote_type}")
        return result

    def _update_runtime_status(self, text=None, **fields):
        """
        P9H 给运行时状态栏发进度消息的统一出口
        """

        if self.status is None:
            # 说明不需要实时 ui
            return

        payload = {
            "depth": self.depth,
            "attempts": len(self.bypass_history["attempts"]),
            "cache": (
                f"{len(self.bypass_history['success'])}p/{len(self.bypass_history['failed'])}f"
            ),
        }
        payload.update(fields)
        self.status.update(text=text, **payload)

    def _new_id(self, key):
        """
        从 bypass_history 中创建一个新的自增 ID
        """

        id_ = self.bypass_history[key]
        self.bypass_history[key] += 1
        return id_

    def _check_bypass_skip(self, cls_name, func_name):
        """
        检查 bypass 函数是否应被跳过，
          - 跳过的话，返回跳过原因
          - 不跳过的话，返回 None
        """

        sbm = self.specify_bypass_map
        if "white" in sbm:
            if cls_name in sbm["white"] and func_name not in sbm["white"][cls_name]:
                return "white_skip"
        if "black" in sbm:
            if cls_name in sbm["black"] and func_name in sbm["black"][cls_name]:
                return "black_skip"
        return None

    def _build_attempt_steps(self, attempt):
        """
        把当前 attempt 和它递归触发的子 attempt绕过尝试，
        整理成一个 steps + helpers 的结构（-vv/-vvv 使用）
          - steps: 这次 bypass 最终主要是靠哪几步走通的
          - helpers: 为了让 steps 成立，还递归用了哪些手法
        """

        steps = [attempt["step"]]
        helpers = []
        seen = set(steps)

        # 当前这个 attempt 可能触发了很多次子 P9H 运行
        # 需要选出真正产出了当前 attempt 最终结果的那条子链
        for run_id in reversed(attempt["child_run_ids"]):
            run = self.bypass_history["runs"][run_id]
            if run["result"] == attempt["result"]:
                attempt["main_child_run_id"] = run_id
                break

        for run_id in attempt["child_run_ids"]:
            # 顺着刚才的子 run 往下找它的所有节点
            run = self.bypass_history["runs"][run_id]
            use_main_step = run_id == attempt["main_child_run_id"]
            for node_id in run["root_node_ids"]:
                node = self.bypass_history["nodes"][node_id]
                child_attempt_id = node["selected_attempt_id"]
                if child_attempt_id is None:
                    continue

                child_attempt = self.bypass_history["attempts"][child_attempt_id]
                child_steps = list(child_attempt["steps"])
                if use_main_step and child_steps:
                    # 把第一个 step 当作主链头
                    head = child_steps.pop(0)
                    if head not in seen:
                        steps.append(head)
                        seen.add(head)
                    # 其余的舍弃，让 steps 保持简洁，只展示主链上的关键一步
                    use_main_step = False

                # 把其余子步骤都当作辅助信息放进 helpers
                for step in [*child_steps, *child_attempt["helpers"]]:
                    if step not in seen and step not in helpers:
                        helpers.append(step)

        return steps, helpers

    def _new_node_record(self, raw_code, node_label, hits):
        """
        给当前这个被拦住的 AST 节点建一条 trace
        """

        node_id = self._new_id("next_node_id")
        self.bypass_history["nodes"][node_id] = {
            "id": node_id,
            "raw": raw_code,
            "label": richify(node_label),
            "depth": self.depth + 1,
            "hits": list(hits),
            "attempt_ids": [],
            "selected_attempt_id": None,
            "steps": [],
            "helpers": [],
            "result": None,
            "cache_status": None,
            "cache_result": None,
            "cache_steps": [],
            "cache_helpers": [],
        }
        self.root_node_ids.append(node_id)
        return node_id

    def _get_bypass_warnings(self, method):
        func = getattr(method, "__func__", method)
        messages = getattr(func, "_p9h_warnings", ())
        if not messages:
            return []

        if isinstance(messages, (str, dict)):
            messages = [messages]

        warnings = []
        for message in messages:
            if not message:
                continue

            if isinstance(message, dict):
                text = str(message.get("message", "")).strip()
                disable_hint = str(message.get("disable_hint", "")).strip()
            else:
                text = str(message).strip()
                disable_hint = ""

            if not text:
                continue

            warnings.append(
                {
                    "message": text,
                    "disable_hint": disable_hint,
                }
            )

        return warnings

    def _collect_attempt_warnings(self, attempt_id, seen_attempt_ids=None, seen_messages=None):
        if attempt_id is None:
            return []

        if seen_attempt_ids is None:
            seen_attempt_ids = set()
        if seen_messages is None:
            seen_messages = set()

        if attempt_id in seen_attempt_ids:
            return []
        seen_attempt_ids.add(attempt_id)

        attempt = self.bypass_history["attempts"][attempt_id]
        warnings = []
        for warning in attempt.get("warnings", []):
            key = (
                warning.get("message", ""),
                warning.get("disable_hint", ""),
            )
            if key in seen_messages:
                continue
            seen_messages.add(key)
            warnings.append(warning)

        for run_id in attempt["child_run_ids"]:
            run = self.bypass_history["runs"][run_id]
            for node_id in run["root_node_ids"]:
                child_attempt_id = self.bypass_history["nodes"][node_id]["selected_attempt_id"]
                warnings.extend(
                    self._collect_attempt_warnings(
                        child_attempt_id,
                        seen_attempt_ids=seen_attempt_ids,
                        seen_messages=seen_messages,
                    )
                )

        return warnings

    def collect_result_warnings(self):
        seen_attempt_ids = set()
        seen_messages = set()
        warnings = []

        for node_id in self.root_node_ids:
            node = self.bypass_history["nodes"][node_id]
            warnings.extend(
                self._collect_attempt_warnings(
                    node["selected_attempt_id"],
                    seen_attempt_ids=seen_attempt_ids,
                    seen_messages=seen_messages,
                )
            )

        return warnings

    def try_bypass(self, bypass_funcs, node):
        """
        尝试绕过当前节点
        """
        old_len = len(self._source)
        bypass_funcs["by_raw"]()
        raw_code = "".join(self._source[old_len:])
        node_label = self._node_label(node, raw_code)
        hits = check(raw_code)
        if not hits:
            # 原始写法未命中规则，不需要绕过
            return raw_code

        # 清空修改，保护堆栈
        self._source = self._source[:old_len]
        node_id = self._new_node_record(raw_code, node_label, hits)
        trace_node = self.bypass_history["nodes"][node_id]
        node_status = self._status_node_label(node, raw_code)
        self._update_runtime_status(
            "blocked node",
            node=node_status,
        )

        if raw_code in self.bypass_history["success"]:
            # 说明之前已经成功绕过过，直接使用缓存结果
            cached = self.bypass_history["success"][raw_code]
            result = cached["result"]
            trace_node["cache_steps"] = list(cached["steps"])
            trace_node["cache_helpers"] = list(cached["helpers"])
            trace_node["cache_status"] = "pass"
            trace_node["cache_result"] = result
            trace_node["result"] = result
            self._source += [result]
            self._update_runtime_status(
                "cache hit",
                node=node_status,
            )
            return result

        if raw_code in self.bypass_history["failed"]:
            # 说明之前已经尝试过，无法绕过，直接返回原始代码
            trace_node["cache_status"] = "fail"
            trace_node["result"] = raw_code
            self._source += [raw_code]
            self._update_runtime_status(
                "cache miss",
                node=node_status,
            )
            return raw_code

        # by_raw 没有实际的绕过效果，删除
        del bypass_funcs["by_raw"]

        found = False
        best_result = None
        best_attempt_id = None
        # 逐个尝试 bypass
        for func in bypass_funcs:
            # 开始做一些准备工作
            # 先完整登记进 trace 系统，并建立好递归上下文，然后才进入真正执行阶段
            cls_name, func_name = bypass_funcs[func].__qualname__.split(".")
            step_name = _format_bypass_func(f"{cls_name}.{func}")
            attempt_id = self._new_id("next_attempt_id")
            # 构造当前 attempt 的相关信息
            attempt = {
                "id": attempt_id,  # 唯一 ID
                "node_id": node_id,  # 所属节点 ID
                "func": cls_name + "." + func,  # 完整 bypass 函数名
                "step": func,  # 自身对应的步骤名
                "steps": [],  # 归纳出的主链步骤
                "helpers": [],  # 从递归子调用归纳出的辅助步骤
                "main_child_run_id": None,  # 产出最终结果的主子运行 ID
                "success": False,  # 是否成功绕过
                "result": None,  # 返回的 payload
                "reason": None,  # 未成功时的原因
                "blocked_hits": [],  # 当前 result 仍命中的黑名单项
                "child_run_ids": [],  # 触发的子运行 ID
                "warnings": self._get_bypass_warnings(bypass_funcs[func]),  # 可能的适用性告警
            }
            self.bypass_history["attempts"][attempt_id] = attempt
            self.bypass_history["nodes"][node_id]["attempt_ids"].append(attempt_id)

            skip_reason = self._check_bypass_skip(cls_name, func_name)
            if skip_reason:
                attempt["reason"] = skip_reason
                continue

            self._update_runtime_status(
                "try bypass",
                node=node_status,
                step=step_name,
            )
            old_len = len(self._source)
            prev_attempt_id = self._active_attempt_id
            self._active_attempt_id = attempt["id"]

            # 实际执行 bypass 函数
            try:
                result = bypass_funcs[func]()
            finally:
                self._active_attempt_id = prev_attempt_id
            self._source = self._source[:old_len]

            if result is None:
                attempt["reason"] = "not_applicable"
                continue

            attempt["result"] = result
            blocked = check(result)
            if blocked:
                attempt["reason"] = "blocked"
                attempt["blocked_hits"] = list(blocked)
            else:
                attempt["success"] = True
                self._update_runtime_status(
                    "bypass succeeded",
                    node=node_status,
                    step=step_name,
                )
                attempt["steps"], attempt["helpers"] = self._build_attempt_steps(attempt)
                if self.min_len:
                    if best_result is None or len(result) < len(best_result):
                        best_result = result
                        best_attempt_id = attempt["id"]
                        found = True
                elif self.min_set:
                    # TODO
                    # 这里需要考虑到历史 bypass 时用到的字符
                    # 否则就是贪心算法，容易陷入局部最优
                    # 先用贪心吧，后面再优化
                    if best_result is None or len(set(result)) < len(set(best_result)):
                        best_result = result
                        best_attempt_id = attempt["id"]
                        found = True
                else:
                    best_result = result
                    best_attempt_id = attempt["id"]
                    found = True
                    break

        if not found:
            result = raw_code
            self.bypass_history["nodes"][node_id]["result"] = result
            self.bypass_history["failed"].add(raw_code)
            self._update_runtime_status(
                "all bypasses failed",
                node=node_status,
                step=None,
            )
        else:
            result = best_result
            node = self.bypass_history["nodes"][node_id]
            node["selected_attempt_id"] = best_attempt_id
            node["result"] = result
            best_attempt = self.bypass_history["attempts"][best_attempt_id]
            node["steps"] = list(best_attempt["steps"])
            node["helpers"] = list(best_attempt["helpers"])
            self.bypass_history["success"][raw_code] = {
                "result": result,
                "steps": list(node["steps"]),
                "helpers": list(node["helpers"]),
            }
            self._update_runtime_status(
                "found best bypass",
                node=node_status,
                step=_format_bypass_func(best_attempt["func"]),
            )

        self._source += [result]
        return result

    def fill(self, text=""):
        pass

    def write(self, *text):
        """
        覆盖掉 write 主要是为了自定义 FORMAT_SPACE
        若后续新增 bypass 时发现出现了空格，就是在这里漏掉了
        """
        stack = bypass_tools.get_stack(num=5)
        _text = text[:]
        # print(_text, [i[1] for i in stack if i[1].startswith("visit_")])
        visit_stacks = [i[1] for i in stack if i[1].startswith("visit_")]
        if visit_stacks and visit_stacks[0] in [
            "visit_BinOp",
            "visit_Call",
            "visit_List",
            "visit_Tuple",
        ]:
            _text = [i.replace(" ", FORMAT_SPACE) for i in text]

        self._source.extend(_text)

    def visit(self):
        self._source = []
        self._update_runtime_status(
            "rewrite source",
            node=None,
            step=None,
        )
        self.traverse(self.source_node)
        self.result = "".join(self._source)
        self.bypass_history["runs"][self.run_id]["result"] = self.result
        self.result_warnings = self.collect_result_warnings()
        self.bypass_history["runs"][self.run_id]["warnings"] = list(self.result_warnings)
        self._update_runtime_status(
            "rewrite complete",
            node=None,
            step=None,
        )
        self._print_result()
        return self.result

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
        return self.try_bypass(func_map, node)

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
            ),
            node,
        )

    def visit_Subscript(self, node):
        def _by_raw():
            self.set_precedence(ast._Precedence.ATOM, node.value)
            self.traverse(node.value)
            with self.delimit("[", "]"):
                if isinstance(node.slice, ast.Tuple):
                    for i, elt in enumerate(node.slice.elts):
                        if i > 0:
                            self.write(",")
                        self.traverse(elt)
                else:
                    self.traverse(node.slice)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Subscript(
                    BLACK_CHAR, node, p9h_self=self
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
                bypass_tools.Bypass_Keyword(BLACK_CHAR, node, p9h_self=self).get_map(),
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
                        self.write(", ")
                    else:
                        comma = True

                    self.traverse(e)

                for e in node.keywords:
                    if comma:
                        self.write(", ")
                    else:
                        comma = True

                    self.traverse(e)

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_Call(BLACK_CHAR, node, p9h_self=self).get_map(),
                **{"by_raw": _by_raw},
            ),
            node,
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
                ),
                node,
            )

        with self.require_parens(operator_precedence, node):
            self.write(operator)
            # factor prefixes (+, -, ~) shouldn't be separated
            # from the value they belong, (e.g: +1 instead of + 1)
            if operator_precedence is not ast._Precedence.FACTOR:
                self.write(" ")
            self.set_precedence(operator_precedence, node.operand)
            self.traverse(node.operand)

    def visit_Compare(self, node):
        with self.require_parens(ast._Precedence.CMP, node):
            self.set_precedence(
                ast._Precedence.CMP.next(),
                node.left,
                *node.comparators,
            )
            self.traverse(node.left)
            for op_node, comparator in zip(node.ops, node.comparators):
                op = self.cmpops[op_node.__class__.__name__]
                # 只压缩纯符号比较；`is not` / `not in` 等仍需保留空格保证语法正确
                if op in ["==", "!=", "<", "<=", ">", ">="]:
                    self.write(op)
                else:
                    self.write(f" {op} ")
                self.traverse(comparator)

    def visit_BoolOp(self, node):
        def _by_raw():
            self.write("(")
            self.set_precedence(
                (
                    ast._Precedence.OR
                    if isinstance(node.op, ast.Or)
                    else ast._Precedence.AND
                ),
                node,
            )
            for i, value in enumerate(node.values):
                if i > 0:
                    self.write(f" {self.boolops[node.op.__class__.__name__]} ")
                self.traverse(value)
            self.write(")")

        return self.try_bypass(
            dict(
                bypass_tools.Bypass_BoolOp(BLACK_CHAR, node, p9h_self=self).get_map(),
                **{"by_raw": _by_raw},
            ),
            node,
        )


Recursion_LIMIT = 5000
sys.setrecursionlimit(Recursion_LIMIT)
BLACK_CHAR = {}
FORMAT_SPACE = None

__all__ = [
    "BLACK_CHAR",
    "P9H",
    "RuntimeStatus",
    "bypass_tools",
    "cache_check_func",
    "check",
    "color_check",
    "colored_text",
    "console",
    "logo",
    "normalize_specify_bypass_map",
    "normalize_verbose",
]
