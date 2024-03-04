import parselmouth as p9h


test_map = {
    # payload & rules
    "-1": [[], ["1", "~", "True", "all", "len", "*", "unicode_forbidden"]],
    "1": [
        [],
        ["1"],
        ["1", "True"],
        ["1", "True", "*"],
        ["1", "True", "all", "*"],
        ["1", "True", "all", "*", "unicode_forbidden"],
        ["1", "True", "(", "*"],
        ["0", "1", "3", "4", "5", "6", "7", "8", "True", "False", "("],
    ],
    "1000": [
        ["0", "1", "2", "3", "4", "5", "6", "7", "9", "-", "*", "True", "False", "("]
    ],
    "24": [["0", "1", "2", "3", "4", "5", "6", "7", "9", "True", "False", "("]],
    "88": [["0", "1", "2", "3", "4", "5", "6", "7", "9", "True", "False", "("]],
    "2024": [
        [],
        ["0", "1"],
        ["0", "1", "'", '"', "*", "+"],
        ["0", "1", "unicode_forbidden"],
    ],
    "'macr0phag3'": [
        [],
        ["macr0phag3"],
        ["'"],
        ['"'],
        ["'", '"', "chr", "bytes", "unicode_forbidden"],
    ],
    "__import__": [[], ["__"], ["import"], ["imp", "rt"]],
    "str.find": [
        [],
        ["."],
        ["find", "unicode_forbidden"],
        ["find", "unicode_forbidden", "chr"],
        [".", "'", '"', "unicode_forbidden", "chr", "bytes"],
        [".", "'", '"', "unicode_forbidden", "chr", "+", "dict"],
        [".", "'", '"', "unicode_forbidden", "chr", "dict"],
    ],
    "__import__('os').popen('whoami').read()": [
        [],
        ["."],
        ["read"],
        ["__", ".", "'", '"', "read"],
        ["__", ".", "'", '"', "read", "chr"],
    ],
}
print("[+] 开始测试")
for payload in test_map:
    for rule in test_map[payload]:
        p9h.BLACK_CHAR = rule
        bypassed, c_result = p9h.color_check(
            p9h.P9H(payload, useless_func=[], depth=1, versbose=0).visit()
        )
        print(
            f"  - [{p9h.put_color(bypassed, 'green' if bypassed else 'red')}] "
            f"{p9h.put_color(payload, 'white')} => {c_result} with {p9h.put_color(p9h.BLACK_CHAR, 'yellow')}"
        )
