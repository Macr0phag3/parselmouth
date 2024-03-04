# parselmouth
一个自动化的 Python 沙箱逃逸 payload bypass 框架

## 快速入门
- python 版本最好是 >= 3.10
- 安装依赖: `pip install -r requirements`

### 通过 CLI 使用
- 获取帮助信息：`python parselmouth.py -h`
- 指定 payload 与 rule: `python parselmouth.py  --payload "__import__('os').popen('whoami').read()" --rule "__" "." "'" '"' "read" "chr"`
- 在指定 rule 的时候，如果不希望通过 unicode 字符的规范化进行 bypass，可以在规则中加上 `unicode_forbidden`
- 通过指定参数 `-v` 可以增加输出的信息；通过 `-vv` 可以输出 debug 信息，但通常是不需要的
- 在定制化 bypass 函数之后，如果想做测试，可以将测试的 payload 和 rule 放在 `run_test.py` 里面，然后通过 `python parselmouth.py --run-test` 进行测试（直接运行 `run_test.py` 也行）

### 通过 import 使用
```python
import parselmouth as p9h


p9h.BLACK_CHAR = [".", "'", '"', "unicode_forbidden", "chr", "dict"]
runner = p9h.P9H("__import__('os').popen('whoami').read()", [], 0, versbose=0)
result = runner.visit()
status, c_result = p9h.color_check(result)
print(status, c_result, result)
```

### 定制化 bypass 逻辑
**在定制化之前，最好先阅读下这篇解释原理的文章（待发布）以及 `parselmouth.py`、`bypass_tools.py` 的主要代码**

- 如果要新增一个 ast 类型的识别与处理，需要在 `parselmouth.py` 中的 `P9H` 新增一个 `visit_` 方法
- 如果是对已有的 ast 类型，需要新增不同的处理函数，则需要在 `bypass_tools.py` 中找到对应的 bypass 类型，并新增一个 `by_` 开头的方法。同一个类下的 bypass 函数，使用顺序取决于对应类中定义的顺序，先被定义的函数会优先尝试进行 bypass


## Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="500">

[![Stargazers over time](https://starchart.cc/Macr0phag3/parselmouth.svg)](https://starchart.cc/Macr0phag3/parselmouth)
