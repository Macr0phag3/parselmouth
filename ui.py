import ast
import json
import time

from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree


VERSION = "v3.0"

VERBOSE_LEVELS = {
    0: "only show the run summary",
    1: "show high-level bypass progress",
    2: "show target payloads and selected attempts",
    3: "show cache hits, skips, and rejection reasons",
}

LOG_LEVELS = {
    "error": {"threshold": 0, "style": "error"},
    "warn": {"threshold": 1, "style": "warn"},
    "info": {"threshold": 1, "style": "info"},
    "detail": {"threshold": 2, "style": "detail"},
    "debug": {"threshold": 3, "style": "debug"},
}

_SKIP_LABELS = {
    "white_skip": "not in whitelist",
    "black_skip": "excluded by blacklist",
}

console = Console(
    theme=Theme(
        {
            "muted": "dim white",
            "info": "bold white",
            "detail": "cyan",
            "debug": "dim white",
            "warn": "bold yellow",
            "warn_plain": "yellow",
            "error": "bold red",
            "accent": "bold cyan",
            "success": "bold green",
            "payload": "bold blue",
            "node_type": "grey70",
            "root_node_type": "bold white",
            "node_value": "bold deep_sky_blue1",
            "payload_context": "bold white",
            "bypass": "bold cyan",
            "result_payload": "spring_green3",
        }
    ),
    highlight=False,
)

CONSOLE_OPTS = dict(
    markup=False,
    highlight=False,
    soft_wrap=True,
    overflow="fold",
    no_wrap=False,
    crop=False,
)


class RuntimeStatus:
    _FIELD_ORDER = ("attempts", "depth", "cache", "node", "step")
    _FIELD_META = {
        "depth": ("depth", "detail"),
        "attempts": ("attempts", "detail"),
        "cache": ("cache", "detail"),
        "step": ("step", "bypass"),
        "node": ("node", "payload_context"),
    }
    _SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, console, *, enabled=None):
        self.console = console
        if enabled is None:
            enabled = bool(getattr(console, "is_terminal", False)) and not bool(
                getattr(console, "is_dumb_terminal", False)
            )

        self.enabled = bool(enabled)
        self._live = None
        self._start_ts = None
        self._fields = {}
        self._message = ""

    def start(self, text="", **fields):
        self._fields.clear()
        self._message = ""
        self._start_ts = time.time()

        if self.enabled and self._live is None:
            self._live = Live(
                console=self.console,
                auto_refresh=True,
                refresh_per_second=10,
                transient=True,
                redirect_stdout=True,
                redirect_stderr=True,
                vertical_overflow="crop",
                get_renderable=self._render,
            )
            self._live.start()

        self.update(text=text, **fields)

    def update(self, text=None, **fields):
        if text is not None:
            self._message = str(text)

        for key, value in fields.items():
            if key not in self._FIELD_META:
                continue

            if value is None:
                self._fields.pop(key, None)
                continue

            limit = 64 if key == "node" else 40 if key == "step" else 20
            self._fields[key] = self._shorten(str(value).replace("\n", " "), limit)

        if not self.enabled or self._live is None:
            return

        self._live.refresh()

    def stop(self, *, persist=False):
        last_renderable = None
        had_live = self._live is not None
        if persist and had_live:
            last_renderable = self._render()

        if self._live is not None:
            self._live.stop()
            self._live = None

        if last_renderable is not None:
            self.console.print(last_renderable)

        self._fields.clear()
        self._message = ""
        self._start_ts = None

    def _render(self):
        line = Text(no_wrap=True, overflow="ellipsis")
        elapsed = 0.0 if self._start_ts is None else max(time.time() - self._start_ts, 0.0)
        spinner = self._SPINNER_FRAMES[int(elapsed * 8) % len(self._SPINNER_FRAMES)]
        line.append(spinner, style="accent")
        line.append(" ", style="muted")
        line.append(f"{elapsed:3.1f}s", style="accent")

        for key in self._FIELD_ORDER:
            if key not in self._fields:
                continue

            label, style = self._FIELD_META.get(key, (key, "detail"))
            line.append("  ", style="muted")
            line.append(label, style="muted")
            line.append(" ", style="muted")
            line.append(self._fields[key], style=style)

        if self._message:
            line.append("  |  ", style="muted")
            line.append(self._message, style="info")

        return line

    @staticmethod
    def _shorten(text, limit):
        if len(text) <= limit:
            return text

        if limit <= 6:
            return text[:limit]

        keep = limit - 3
        head = keep // 2
        tail = keep - head
        return f"{text[:head]}...{text[-tail:]}"


def normalize_verbose(verbose):
    return max(0, min(int(verbose), max(VERBOSE_LEVELS)))


def richify(value):
    if isinstance(value, Text):
        value.no_wrap = False
        value.overflow = "fold"
        return value

    if isinstance(value, str):
        rich_text = Text.from_ansi(value)
        rich_text.no_wrap = False
        rich_text.overflow = "fold"
        return rich_text

    return Text(str(value), no_wrap=False, overflow="fold")


def rich_print(*args):
    console.print(
        *[richify(arg) for arg in args],
        **CONSOLE_OPTS,
    )


def styled_text(
    text,
    *,
    focus=None,
    base_style="payload_context",
    focus_style="node_value",
):
    text = str(text)
    rich_text = Text(no_wrap=False, overflow="fold")
    if focus is None:
        rich_text.append(text, style=base_style)
        return rich_text

    focus = str(focus)
    start = text.find(focus)
    if start == -1:
        rich_text.append(text, style=base_style)
        return rich_text

    end = start + len(focus)
    rich_text.append(text[:start], style=base_style)
    rich_text.append(text[start:end], style=focus_style)
    rich_text.append(text[end:], style=base_style)
    return rich_text


def colored_text(text, color, bold=True, *, no_wrap=False, overflow="fold"):
    style = {
        "gray": "bright_black",
        "red": "red",
        "green": "green",
        "yellow": "yellow",
        "blue": "blue",
        "cyan": "cyan",
        "white": "white",
    }.get(color, "white")
    if bold and color != "gray":
        style = f"bold {style}"
    return Text(str(text), style=style, no_wrap=no_wrap, overflow=overflow)


def build_logo():
    logo_text = Text(no_wrap=True, overflow="ignore")
    logo_text.append("   ▏ ▏", style="green")
    logo_text.append("\n")
    logo_text.append(" (o  O)", style="green")
    logo_text.append("\n")
    logo_text.append("  \\__/", style="green")
    logo_text.append("\n")
    logo_text.append("   ", style="green")
    logo_text.append("▕", style="red")
    return logo_text


logo = build_logo()


def format_bypass_func(func_name):
    cls_name, step = func_name.split(".", 1)
    return f"{cls_name.removeprefix('Bypass_')}.{step}"


def _collect_used_bypass(p9h):
    used = []

    def walk_attempt(attempt_id):
        attempt = p9h.bypass_history["attempts"][attempt_id]
        func_name = format_bypass_func(attempt["func"])
        if func_name not in used:
            used.append(func_name)

        for run_id in attempt["child_run_ids"]:
            run = p9h.bypass_history["runs"][run_id]
            for node_id in run["root_node_ids"]:
                child_node = p9h.bypass_history["nodes"][node_id]
                child_attempt_id = child_node["selected_attempt_id"]
                if child_attempt_id is not None:
                    walk_attempt(child_attempt_id)

    for node_id in p9h.root_node_ids:
        node = p9h.bypass_history["nodes"][node_id]
        attempt_id = node["selected_attempt_id"]
        if attempt_id is not None:
            walk_attempt(attempt_id)

    return used


def _collect_failure_stats(p9h):
    failed = 0
    skipped = 0

    for node_id in p9h.root_node_ids:
        node = p9h.bypass_history["nodes"][node_id]
        if node["selected_attempt_id"] is not None or node.get("cache_status") == "pass":
            continue

        if node.get("cache_status") == "fail" and not node["attempt_ids"]:
            failed += 1
            continue

        for attempt_id in node["attempt_ids"]:
            attempt = p9h.bypass_history["attempts"][attempt_id]
            if attempt["reason"] in _SKIP_LABELS or attempt["reason"] == "not_applicable":
                skipped += 1
            elif not attempt["success"]:
                failed += 1

    return failed, skipped


def print_run_config(args, specify_bypass_map):
    verbose_desc = VERBOSE_LEVELS[args.v]
    optimize_mode = (
        "shortest"
        if args.shortest
        else "minimal char set"
        if args.minset
        else "first hit"
    )

    logo_text = logo.copy()
    logo_text.no_wrap = True
    logo_text.overflow = "ignore"

    table = Table.grid(padding=(0, 1))
    table.add_column(style="muted", no_wrap=True)
    table.add_column()
    table.add_row("payload", colored_text(args.payload, "blue"))
    table.add_row(
        "keyword rule",
        colored_text(args.rule or None, "blue" if args.rule else "gray"),
    )
    table.add_row(
        "regex rule",
        colored_text(args.re_rule or None, "blue" if args.re_rule else "gray"),
    )
    table.add_row("optimize", Text(optimize_mode, style="accent"))
    table.add_row("specify bypass", colored_text(specify_bypass_map, "white"))
    table.add_row(
        "verbose",
        Text(f"{args.v}:", style="accent")
        + Text(f" {verbose_desc}", style="muted"),
    )

    content = Table.grid(padding=(0, 3))
    content.add_column(no_wrap=True, vertical="middle")
    content.add_column(vertical="top")
    content.add_row(logo_text, table)

    title = Text("parselmouth", style="accent")
    title.append(" ", style="muted")
    title.append(VERSION, style="detail")

    console.print(
        Align.center(
            Panel.fit(
                content,
                title=title,
                border_style="accent",
            )
        )
    )


def print_rewrite_header():
    console.print(Text("[+] Rewrite blocked nodes", style="info"), soft_wrap=True)


def print_run_summary(payload, exp, result, cost, p9h, c_payload, *, check_func):
    summary = Table.grid(padding=(0, 1))
    summary.add_column(style="muted", no_wrap=True)
    summary.add_column()
    summary.add_row(
        "status",
        (
            Text("success", style="success")
            if result
            else Text("failed", style="error")
        )
        + Text("  ", style="muted")
        + Text(f"{round(cost, 2)}s", style="accent"),
    )
    summary.add_row(
        "metrics",
        Text(f"len {len(exp)} | charset {len(set(exp))}", style="accent"),
    )

    if result:
        used = _collect_used_bypass(p9h)
        summary.add_row(
            "used",
            Text(", ".join(used), style="payload")
            if used
            else Text("None", style="muted"),
        )
        if p9h.result_warnings:
            warning_text = Text(no_wrap=False, overflow="fold")
            for index, warning in enumerate(p9h.result_warnings):
                if index:
                    warning_text.append("\n")
                warning_text.append("- ", style="warn")
                warning_text.append(warning["message"], style="warn")
                disable_hint = warning.get("disable_hint", "")
                if disable_hint:
                    warning_text.append("\n")
                    warning_text.append("  you can disable it by ")
                    warning_text.append(disable_hint, style="payload")
            summary.add_row("warning", warning_text)
    else:
        failed, skipped = _collect_failure_stats(p9h)
        final_hits = check_func(exp)
        summary.add_row(
            "attempts",
            Text(f"{failed} failed | {skipped} skipped", style="accent"),
        )
        summary.add_row(
            "reason",
            Text(
                f"still hits {json.dumps([str(hit) for hit in final_hits], ensure_ascii=False)}",
                style="warn",
            )
            if final_hits
            else Text("no valid bypass path found", style="warn"),
        )

    console.print(
        Align.center(
            Panel.fit(
                summary,
                title="Result",
                border_style="success" if result else "error",
            )
        )
    )

    console.print(
        Text("rewrite:", style="muted"),
        colored_text(payload, "blue"),
        Text(" -> ", style="muted"),
        richify(c_payload),
        **CONSOLE_OPTS,
    )


class P9HRenderMixin:
    def cprint(self, *args, depth=None, level="info"):
        level_config = LOG_LEVELS[level]
        if self.verbose < level_config["threshold"]:
            return

        depth = self.depth if depth is None else depth
        prefix = Text("  " * depth)
        prefix.append(f"[{level.upper()}]", style=level_config["style"])
        console.print(
            prefix,
            *[richify(arg) for arg in args],
            **CONSOLE_OPTS,
        )

    def _status_node_label(self, node, raw_code):
        return f"{node.__class__.__name__} {raw_code}"

    def _node_label(self, node, raw_code):
        raw_code = str(raw_code)
        if isinstance(node, ast.Name):
            return Text.assemble(
                ("- ", "muted"),
                ("[Name] ", "node_type"),
                styled_text(raw_code, focus=raw_code),
                no_wrap=False,
                overflow="fold",
            )

        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                value = repr(node.value)
                return Text.assemble(
                    ("- ", "muted"),
                    ("[String] ", "node_type"),
                    styled_text(value, focus=value),
                    no_wrap=False,
                    overflow="fold",
                )
            if isinstance(node.value, int):
                return Text.assemble(
                    ("- ", "muted"),
                    ("[Int] ", "node_type"),
                    (str(node.value), "node_value"),
                    no_wrap=False,
                    overflow="fold",
                )
            return Text.assemble(
                ("- ", "muted"),
                ("[Constant] ", "node_type"),
                (repr(node.value), "node_value"),
                no_wrap=False,
                overflow="fold",
            )

        if isinstance(node, ast.Attribute):
            return Text.assemble(
                ("- ", "muted"),
                ("[Attribute] ", "node_type"),
                styled_text(raw_code, focus=f".{node.attr}", focus_style="node_value"),
                no_wrap=False,
                overflow="fold",
            )

        if isinstance(node, ast.Subscript):
            slice_code = ast.unparse(node.slice)
            return Text.assemble(
                ("- ", "muted"),
                ("[Subscript] ", "node_type"),
                styled_text(raw_code, focus=f"[{slice_code}]", focus_style="node_value"),
                no_wrap=False,
                overflow="fold",
            )

        if isinstance(node, ast.keyword):
            focus = "**" if node.arg is None else f"{node.arg}="
            return Text.assemble(
                ("- ", "muted"),
                ("[Keyword] ", "node_type"),
                styled_text(raw_code, focus=focus, focus_style="node_value"),
                no_wrap=False,
                overflow="fold",
            )

        return Text.assemble(
            ("- ", "muted"),
            (f"[{node.__class__.__name__}] ", "node_type"),
            (raw_code, "node_value"),
            no_wrap=False,
            overflow="fold",
        )

    def _render_progress_line(self, depth, node, steps, helpers, result):
        indent = Text("  " * depth)
        text = Text(no_wrap=False, overflow="fold")
        text.append_text(self._build_node_header(node, keep_prefix=True))
        text.append(" -> ", style="muted")
        for index, step in enumerate(steps):
            if index:
                text.append(" & ", style="muted")
            text.append(step, style="bypass")
        if helpers:
            text.append(" ", style="muted")
            text.append("(+ ", style="muted")
            for index, helper in enumerate(helpers):
                if index:
                    text.append(", ", style="muted")
                text.append(helper, style="bypass")
            text.append(")", style="muted")
        text.append(" -> ", style="muted")
        text.append_text(
            Text(
                str(result),
                style="result_payload",
                no_wrap=False,
                overflow="fold",
            )
        )
        return indent, text

    def _unwrap_main_node(self, node):
        while True:
            attempt_id = node["selected_attempt_id"]
            if attempt_id is None:
                break
            attempt = self.bypass_history["attempts"][attempt_id]
            main_run_id = attempt["main_child_run_id"]
            if main_run_id is None:
                break

            run = self.bypass_history["runs"][main_run_id]
            if run["source"] != node["raw"] or len(run["root_node_ids"]) != 1:
                break

            child_node = self.bypass_history["nodes"][run["root_node_ids"][0]]
            if child_node["raw"] != node["raw"]:
                break
            node = child_node

        return node

    def _build_detail_tree(self, node_id, is_root=False):
        node = self._unwrap_main_node(self.bypass_history["nodes"][node_id])

        tree = Tree(
            self._build_node_header(node, is_root=is_root),
            guide_style="muted",
        )
        if node.get("cache_status") is not None:
            if node.get("cache_status") == "pass":
                tree.add(self._build_cached_success_line(node, "reuse "))
            else:
                tree.add(self._build_trace_cache_line(node))
            return tree

        selected_attempt_id = node["selected_attempt_id"]
        if selected_attempt_id is None:
            return tree

        attempt = self.bypass_history["attempts"][selected_attempt_id]
        if not attempt["success"]:
            return tree

        line = Text(no_wrap=False, overflow="fold")
        line.append("use ", style="muted")
        line.append(attempt["step"], style="bypass")

        has_child_nodes = any(
            self.bypass_history["runs"][run_id]["root_node_ids"]
            for run_id in attempt["child_run_ids"]
        )
        line.append(" -> ", style="muted")
        if has_child_nodes:
            line.append(str(attempt["result"]), style="result_payload")
            branch = tree.add(line)
            self._add_attempt_preview(branch, attempt)
            for run_id in attempt["child_run_ids"]:
                for child_node_id in self.bypass_history["runs"][run_id]["root_node_ids"]:
                    branch.children.append(self._build_detail_tree(child_node_id))
        else:
            line.append(str(attempt["result"]), style="result_payload")
            tree.add(line)

        return tree

    def _build_node_header(self, node, *, is_root=False, keep_prefix=False):
        label = node["label"].copy()
        if not keep_prefix and label.plain.startswith("- "):
            label = label[2:]

        if is_root:
            end = label.plain.find("] ")
            if end != -1 and label.plain.startswith("["):
                label.stylize("root_node_type", 0, end + 2)

        hits = node.get("hits", [])
        if hits:
            label.append(" ", style="muted")
            label.append("hits", style="muted")
            label.append(": ", style="muted")
            label.append(
                json.dumps([str(hit) for hit in hits], ensure_ascii=False),
                style="warn_plain" if self.verbose >= 2 else "warn",
            )
        return label

    def _build_trace_attempt_line(self, attempt):
        line = Text(no_wrap=False, overflow="fold")
        line.append("try ", style="muted")
        line.append(attempt["step"], style="bypass")
        line.append(" -> ", style="muted")

        if attempt["success"]:
            line.append(str(attempt["result"]), style="result_payload")
            return line

        reason = attempt["reason"]
        if reason in _SKIP_LABELS:
            line.append("skip", style="muted")
            line.append(f", {_SKIP_LABELS[reason]}", style="muted")
            return line
        if reason == "not_applicable":
            line.append("skip", style="muted")
            line.append(", not applicable", style="muted")
            return line
        if reason == "blocked":
            line.append("fail", style="warn")
            line.append(", still hits: ", style="muted")
            line.append(
                json.dumps(
                    [str(hit) for hit in attempt.get("blocked_hits", [])],
                    ensure_ascii=False,
                ),
                style="warn",
            )
            return line

        line.append("fail", style="warn")
        return line

    def _append_step_chain(self, line, steps, helpers):
        for index, step in enumerate(steps):
            if index:
                line.append(" & ", style="muted")
            line.append(step, style="bypass")
        if helpers:
            line.append(" ", style="muted")
            line.append("(+ ", style="muted")
            for index, helper in enumerate(helpers):
                if index:
                    line.append(", ", style="muted")
                line.append(helper, style="bypass")
            line.append(")", style="muted")

    def _build_cached_success_line(self, node, prefix):
        steps = list(node.get("cache_steps", []))
        helpers = list(node.get("cache_helpers", []))
        line = Text(no_wrap=False, overflow="fold")
        line.append(prefix, style="muted")
        self._append_step_chain(line, steps, helpers)
        line.append(" -> ", style="muted")
        line.append(str(node.get("cache_result", "")), style="result_payload")
        return line

    def _build_trace_cache_line(self, node):
        line = Text(no_wrap=False, overflow="fold")
        line.append("cached", style="detail")
        line.append(": ", style="muted")
        line.append("fail", style="warn")
        return line

    def _build_success_line(self, attempt, label, style):
        line = Text(no_wrap=False, overflow="fold")
        line.append(label, style=style)
        line.append(" => ", style="muted")
        line.append(attempt["step"], style="bypass")
        if attempt["helpers"]:
            line.append(" ", style="muted")
            line.append("(+ ", style="muted")
            line.append(", ".join(attempt["helpers"]), style="bypass")
            line.append(")", style="muted")
        line.append(" => ", style="muted")
        line.append(str(attempt["result"]), style="result_payload")
        return line

    def _build_attempt_result_line(
        self,
        payload,
        label="got payload",
        label_style="muted",
        payload_style="white",
    ):
        line = Text(no_wrap=False, overflow="fold")
        line.append(label, style=label_style)
        line.append(": ", style="muted")
        line.append(str(payload), style=payload_style)
        return line

    def _add_attempt_preview(self, branch, attempt):
        preview = None
        run_id = attempt.get("main_child_run_id")
        if run_id is None and attempt["child_run_ids"]:
            run_id = attempt["child_run_ids"][-1]
        if run_id is not None:
            preview = self.bypass_history["runs"][run_id]["source"]

        if not preview or preview == str(attempt["result"]):
            return
        branch.add(self._build_attempt_result_line(preview))

    def _build_trace_tree(self, node_id, is_root=False):
        node = self._unwrap_main_node(self.bypass_history["nodes"][node_id])
        tree = Tree(
            self._build_node_header(node, is_root=is_root),
            guide_style="muted",
        )

        if node.get("cache_status") is not None:
            if node.get("cache_status") == "pass":
                tree.add(self._build_cached_success_line(node, "reuse "))
            else:
                tree.add(self._build_trace_cache_line(node))
            return tree

        selected_attempt_id = node["selected_attempt_id"]
        for attempt_id in node["attempt_ids"]:
            attempt = self.bypass_history["attempts"][attempt_id]
            is_selected = attempt_id == selected_attempt_id and attempt["success"]
            line = self._build_trace_attempt_line(attempt)
            has_child_nodes = any(
                self.bypass_history["runs"][run_id]["root_node_ids"]
                for run_id in attempt["child_run_ids"]
            )
            if not is_selected and not has_child_nodes:
                tree.add(line)
                continue

            branch = tree.add(line)
            if has_child_nodes:
                self._add_attempt_preview(branch, attempt)
                for run_id in attempt["child_run_ids"]:
                    for child_node_id in self.bypass_history["runs"][run_id]["root_node_ids"]:
                        branch.children.append(self._build_trace_tree(child_node_id))
            if is_selected and is_root:
                branch.add(self._build_success_line(attempt, "success", "success"))

        return tree

    def _print_result(self):
        if self.depth != 0:
            return

        if self.verbose == 1:
            lines = []
            for node_id in self.root_node_ids:
                node = self.bypass_history["nodes"][node_id]
                attempt_id = node["selected_attempt_id"]
                if attempt_id is None:
                    continue
                lines.append(node)

            extra_helpers = []
            if len(lines) == 1:
                known = set(lines[0]["steps"]) | set(lines[0]["helpers"])
                for other in self.bypass_history["attempts"].values():
                    if (
                        other["success"]
                        and other["step"] not in known
                        and other["step"] not in extra_helpers
                    ):
                        extra_helpers.append(other["step"])

            for node in lines:
                indent, text = self._render_progress_line(
                    node["depth"],
                    node,
                    node["steps"],
                    [*node["helpers"], *extra_helpers],
                    node["result"],
                )
                line = Text(no_wrap=False, overflow="fold")
                line.append_text(indent)
                line.append_text(text)
                console.print(line, **CONSOLE_OPTS)
        elif self.verbose == 2:
            for node_id in self.root_node_ids:
                console.print(
                    self._build_detail_tree(node_id, is_root=True),
                    **CONSOLE_OPTS,
                )
        elif self.verbose == 3:
            for node_id in self.root_node_ids:
                console.print(
                    self._build_trace_tree(node_id, is_root=True),
                    **CONSOLE_OPTS,
                )


__all__ = [
    "P9HRenderMixin",
    "RuntimeStatus",
    "VERSION",
    "colored_text",
    "VERBOSE_LEVELS",
    "build_logo",
    "console",
    "format_bypass_func",
    "logo",
    "normalize_verbose",
    "print_rewrite_header",
    "print_run_config",
    "print_run_summary",
    "rich_print",
    "richify",
    "styled_text",
]
