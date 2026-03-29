这题本质是 REPL 外面套了一层简单字符串黑名单，所以 `exp.py` 直接把黑名单规则接到 `p9h.check`。

由于是本地复现，那么 check 函数直接调用本地的 challenge.py 传入 payload 即可直出 bypass

运行方式：

```bash
python3 exp.py
```

