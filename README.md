# parselmouth
一个自动化的 Python 沙箱逃逸 payload bypass 框架

<img alt="image" src="https://github.com/Macr0phag3/parselmouth/assets/20874963/e4f2765d-ba39-49ba-bcf7-02ab3e83a042">

## 1. 快速入门
- python 版本最好是 >= 3.10
- 安装依赖: `pip install -r requirements`

### 1.1 通过 CLI 使用
- 获取帮助信息：`python parselmouth.py -h`
- 指定 payload 与 rule: `python parselmouth.py  --payload "__import__('os').popen('whoami').read()" --rule "__" "." "'" '"' "read" "chr"`
- 可以通过 `--specify-bypass` 指定 bypass function 的黑白名单；例如如果不希望 int 通过 unicode 字符的规范化进行 bypass，可以指定参数: `--specify-bypass '{"black": {"Bypass_Int": ["by_unicode"]}}'`
- 通过指定参数 `-v` 可以增加输出的信息；通过 `-vv` 可以输出 debug 信息，但通常是不需要的
- 在定制化 bypass 函数之后，如果想做测试，可以将测试的 payload 和 rule 放在 `run_test.py` 里面，然后通过 `python parselmouth.py --run-test` 进行测试（直接运行 `run_test.py` 也行）

### 1.2 通过 import 使用
```python
import parselmouth as p9h


p9h.BLACK_CHAR = [".", "'", '"', "chr", "dict"]
runner = p9h.P9H("__import__('os').popen('whoami').read()", specify_bypass_map={"black": {"Bypass_Name": ["by_unicode"]}}, versbose=0)
result = runner.visit()
status, c_result = p9h.color_check(result)
print(status, c_result, result)
```

`p9h.P9H` 关键参数解释：
- `source_code`: 需要 bypass 的 payload
- `specify_bypass_map`: 指定 bypass function 的黑白名单；例如如果不希望变量名通过 unicode 字符的规范化进行 bypass，可以传参 `{"black": {"Bypass_Name": ["by_unicode"]}}`
- `versbose`: 输出的详细程度（`0` ~ `3`）
- `depth`: 通常情况下不需要使用这个参数；打印信息时所需要的缩进数量
- `cannot_bypass`: 通常情况下不需要使用这个参数；用于指定无法 bypass 的情况，值示例 `["chr(97)"]`

### 1.3 定制化使用
**在定制化之前，最好先阅读下[这篇解释原理的文章](https://www.tr0y.wang/2024/03/04/parselmouth/)以及 `parselmouth.py`、`bypass_tools.py` 的主要代码**

方法一：参考文章 [传送门](https://www.tr0y.wang/2024/03/04/parselmouth/#%E5%AE%9A%E5%88%B6%E5%8C%96%E5%BC%80%E5%8F%91)

方法二：
- 要新增一个 ast 类型的识别与处理，需要在 `parselmouth.py` 中的 `P9H` 新增一个 `visit_` 方法
- 如果希望通过与目标交互的方式进行 payload 检查，可以改写 check 方法，原则是如果检查通过返回空 `[]`；如果检查不通过的话，最好是返回不通过的字符，如果条件有限，返回任意不为空的列表也可以
- 对已有的 ast 类型，需要新增不同的处理函数，则需要在 `bypass_tools.py` 中找到对应的 bypass 类型，并新增一个 `by_` 开头的方法。同一个类下的 bypass 函数，使用顺序取决于对应类中定义的顺序，先被定义的函数会优先尝试进行 bypass


## 2. 当前 bypass function

目前支持：

|  类   |   方法名  | payload | bypass | 解释说明 |
| ----- | -------- | ------- | ------- | ----- |
| Bypass_Int    | by_trans | `0` | `len(())` | |
| Bypass_Int    | by_bin   | `10` | `0b1010` |将数字转为二进制 |
| Bypass_Int    | by_hex   | `10` | `0xa`    |将数字转为十六进制 |
| Bypass_Int    | by_cal   | `10` | `5*2`    |将数字转为算式 |
| Bypass_Int    | by_unicode   | `10` | `int('𝟣𝟢')`    | int + unicode 绕过|
| ————   | ————   | ———— | ———— | ————|
| Bypass_String    | by_quote_trans   | `["macr0phag3"]` | `['macr0phag3']`  | bytes 绕过限制 2|
| Bypass_String    | by_reverse   | `"macr0phag3"` | `"3gahp0rcam"[::-1]`    | 字符串逆序绕过|
| Bypass_String    | by_char   | `"macr0phag3"` |  `(chr(109) + chr(97) + chr(99) + chr(114) + chr(48) + chr(112) + chr(104) + chr(97) + chr(103) + chr(51))`   | char 绕过字符限制|
| Bypass_String    | by_dict   | `"macr0phag3"` | `list(dict(amacr0phag3=()))[0][1:]`  | dict 绕过限制|
| Bypass_String    | by_bytes_1   | `"macr0phag3"` | `str(bytes([109]))[2] + str(bytes([97]))[2] + str(bytes([99]))[2] + str(bytes([114]))[2] + str(bytes([48]))[2] + str(bytes([112]))[2] + str(bytes([104]))[2] + str(bytes([97]))[2] + str(bytes([103]))[2] + str(bytes([51]))[2]`  | bytes 绕过限制|
| Bypass_String    | by_bytes_2   | `"macr0phag3"` | `bytes([109, 97, 99, 114, 48, 112, 104, 97, 103, 51])`  | bytes 绕过限制 2|
| ————   | ————   | ———— | ———— | ————|
| Bypass_Name    | by_unicode   | `__import__` | `_＿import_＿` | unicode 绕过|
| ————   | ————   | ———— | ———— | ————|
| Bypass_Attribute    | by_getattr   | `str.find` | `getattr(str, 'find')` | unicode 绕过|
| ————   | ————   | ———— | ———— | ————|
| Bypass_Keyword    | by_unicode   | `str(object=1)` | `str(ᵒbject=1)` | unicode 绕过|


以及上述所有方法的组合 bypass。

如果在使用的过程中发现有比较好用的 bypass 手法，或者任何问题都可以提交 issue :D


## 3. Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="400">

[![Stargazers over time](https://starchart.cc/Macr0phag3/parselmouth.svg)](https://starchart.cc/Macr0phag3/parselmouth)
