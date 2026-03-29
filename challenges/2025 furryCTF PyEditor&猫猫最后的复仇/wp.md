
这题需要把题目的 `validate_code()` 接到 `p9h.check`，因为它不是简单的字符串黑名单，而是 AST 级别的调用限制：

- `__import__` 是“调用时禁”
- `.system` 也是“调用时禁”

因为 `/api/run` 失败时只会返回 `启动失败`，所以这条链只能拿到“过 / 不过”的黑盒信息，拿不到 AST 校验的具体失败原因。

思路如下：

1. 先把题目服务当成一个“黑盒校验器”。
   `parselmouth` 每次想判断某个子表达式能不能过时，就把这段 payload 丢给 `/api/run`。如果返回 `success: true`，就说明这一版 payload 至少能通过题目的 AST 校验和启动流程；这时立刻再调一次 `/api/terminate` 把进程杀掉，只把它当成布尔 oracle 用，不让服务器上堆一堆测试进程。

2. 等 `parselmouth` 搜到最终 payload 之后，再单独跑一次真实执行。
   这一步不能只看 `/api/run` 的返回值，因为它只告诉我们“进程有没有启动”，不告诉我们命令真正输出了什么。所以这里要再连一次 SocketIO，监听 `output` 和 `process_end` 事件，把题目后端发出来的 stdout/stderr 收完整。

3. 这样整条链就分成两层：
   第一层是“搜索阶段”的黑盒 oracle，只负责回答“这版 payload 过不过”；
   第二层是“验收阶段”的真实执行，负责确认最后那条 payload 真的把 `id` 跑出来了。


`exp.py` 内置的 payload 是

```python
__import__('os').system('id')
```

它会自动转成

```python
getattr(__builtins__.__import__('os'),'system')('id')
```

并成功执行 `id`。
