import time

import parselmouth as p9h


def bypass(payload, name, specify_bypass_map):
    global failed, total

    p9h.BLACK_CHAR = config["rule"]
    p9h_ins = p9h.P9H(
        payload,
        specify_bypass_map=specify_bypass_map,
        depth=1,
        versbose=0,
    )
    st = time.time()
    bypass_result = p9h_ins.visit()
    et = time.time()
    bypassed, c_result = p9h.color_check(bypass_result)
    bypassed = bypassed and eval(bypass_result) == eval(payload)
    total += 1
    if not bypassed:
        failed += 1

    print(
        f"    - [{round(et-st, 2):.2f}s] {p9h.put_color(['FAIL', 'SUCC'][bypassed], 'green' if bypassed else 'red')} "
        f"{p9h.put_color(name, 'blue')} "
        f"=> {c_result} with {p9h.put_color(p9h.BLACK_CHAR, 'white')}"
    )


simple_testcases = {
    "Bypass_Int": {
        "1": [
            {
                "rule": ["1"],
                "bypass_func": ["by_trans", "by_cal", "by_unicode"],
            },
            {
                "rule": ["1", "True", "all"],
                "bypass_func": ["by_trans", "by_cal", "by_unicode"],
            },
            {
                "rule": ["1", "True", "all", "(", "*", "+"],
                "bypass_func": ["by_trans", "by_cal"],
            },
            {
                "rule": ["0", "1", "3", "4", "5", "6", "7", "8", "True", "False", "("],
                "bypass_func": ["by_cal"],
            },
            {
                "rule": [
                    "0",
                    "1",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "True",
                    "False",
                    "*",
                    "+",
                ],
                "bypass_func": ["by_cal"],
            },
        ],
        "2": [
            {
                "rule": ["2"],
                "bypass_func": ["by_bin", "by_trans", "by_cal", "by_unicode"],
            },
            {
                "rule": ["2", "True"],
                "bypass_func": ["by_bin", "by_trans", "by_cal", "by_unicode"],
            },
        ],
        "12": [
            {
                "rule": ["12"],
                "bypass_func": ["by_bin", "by_hex", "by_ord", "by_cal", "by_unicode"],
            },
            {
                "rule": ["12", "True"],
                "bypass_func": ["by_bin", "by_hex", "by_ord", "by_cal", "by_unicode"],
            },
        ],
        "1000": [
            {
                "rule": [
                    "0",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "9",
                    "-",
                    "*",
                    "True",
                    "False",
                ],
                "bypass_func": ["by_cal", "by_ord"],
            }
        ],
        "2024": [
            {
                "rule": ["2", "4"],
                "bypass_func": ["by_bin", "by_hex", "by_ord", "by_cal", "by_unicode"],
            },
            {
                "rule": ["1", "2", "4", "*"],
                "bypass_func": ["by_hex", "by_cal", "by_ord", "by_unicode"],
            },
        ],
        "-1": [
            {"rule": ["1"], "bypass_func": ["by_cal", "by_unicode"]},
            {
                "rule": ["0", "1", "3", "4", "5", "6", "7", "8"],
                "bypass_func": ["by_cal"],
            },
            {
                "rule": ["0", "1", "3", "4", "5", "6", "7", "8", "*", "+"],
                "bypass_func": ["by_cal"],
            },
            {
                "rule": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "+"],
                "bypass_func": ["by_cal"],
            },
            {
                "rule": ["1", "~", "True", "all", "len", "*"],
                "bypass_func": [],
            },
        ],
        "-2024": [
            {"rule": ["2", "4"], "bypass_func": ["by_cal", "by_unicode"]},
            {
                "rule": ["0", "1", "3", "4", "5", "6", "7", "8"],
                "bypass_func": ["by_cal"],
            },
            {
                "rule": ["0", "1", "2", "3", "4", "5", "6", "7", "8", " "],
                "bypass_func": ["by_cal"],
            },
        ],
    },
    "Bypass_String": {
        "'macr0phag3'": [
            {
                "rule": ["macr0phag3"],
                "bypass_func": [
                    "by_char",
                    "by_reverse",
                    "by_dict",
                    "by_bytes_single",
                    "by_bytes_full",
                    "by_join_map_str",
                ],
            },
            {
                "rule": ["macr0phag3", "+"],
                "bypass_func": ["by_char", "by_bytes_single", "by_format"],
            },
            {"rule": ["'"], "bypass_func": ["*"]},
            {"rule": ['"'], "bypass_func": ["*"]},
            {"rule": ["'", '"', "chr", "bytes", "1", "b", "x", "0"], "bypass_func": []},
            {
                "rule": ["'", '"', "chr", "bytes", "1", "b", "x", "0", "+", " "],
                "bypass_func": [],
            },
        ],
        "'你好世界'": [
            {"rule": ["'", '"'], "bypass_func": ["by_char", "by_dict"]},
            {"rule": ["你"], "bypass_func": ["by_join_map_str"]},
        ],
    },
    "Bypass_Attribute": {
        "str.find": [
            {"rule": [" ", "."], "bypass_func": ["*"]},
            {"rule": ["find"], "bypass_func": ["*"]},
            {"rule": ["find", "chr", "ᶜ"], "bypass_func": ["*"]},
            {"rule": ["find", "chr", "ᶜ", ":"], "bypass_func": ["*"]},
            {
                "rule": [" ", "\t", "find", "chr", "ᶜ", ":", "0", "1"],
                "bypass_func": ["*"],
            },
        ],
    },
    "Bypass_Name": {
        "__import__": [
            {"rule": ["__"], "bypass_func": ["*"]},
            {"rule": ["import"], "bypass_func": ["*"]},
            {"rule": ["imp", "rt"], "bypass_func": ["*"]},
        ],
    },
    "Integrated": {
        "__import__('os').popen('whoami').read()": [
            {"rule": ["read", "'", '"'], "bypass_func": []},
            {"rule": [".", "read", "popen"], "bypass_func": []},
            {"rule": ["__", ".", "'", '"', "read", "chr", "ᶜ"], "bypass_func": []},
            {"rule": ["__", ".", "'", '"', "read", "chr", "ᶜ", "="], "bypass_func": []},
            {
                "rule": [
                    "__",
                    ".",
                    "'",
                    '"',
                    "read",
                    "chr",
                    "ᶜ",
                    "=",
                    ":",
                    "0",
                    "1",
                    " ",
                    "\t",
                ],
                "bypass_func": [],
            },
        ],
    },
}
print("[*] run simple test cases\n")
failed = total = 0
for bypass_type in simple_testcases:
    attr = vars(getattr(p9h.bypass_tools, bypass_type, dict))
    print(f"[+] {bypass_type}")

    all_funcs = {name: attr[name] for name in attr if name.startswith("by_")}
    test_report = {i: 0 for i in all_funcs}
    print("  [-]", list(all_funcs))
    for payload in simple_testcases[bypass_type]:
        print("  [-]", p9h.put_color(payload, "blue"))
        for config in simple_testcases[bypass_type][payload]:
            if config["bypass_func"] == ["*"]:
                bypass_funcs = list(all_funcs)
            else:
                bypass_funcs = config["bypass_func"]

            if bypass_funcs:
                for name in bypass_funcs:
                    test_report[name] += 1
                    specify_bypass_map = {"white": {bypass_type: [name]}, "black": []}
                    bypass(payload, name, specify_bypass_map)
            else:
                bypass(payload, "BruteForce", {})

    print("  [+] report")
    # print(test_report)
    for i in test_report:
        _color = ["yellow", "green"][bool(test_report[i])]
        print(
            f"    [-] {p9h.put_color(i, _color)}: "
            f"{p9h.put_color(test_report[i], 'cyan')}"
        )

    print()

print(f"[*] 总计测试用例数量: {p9h.put_color(total, 'cyan')}")
if failed:
    print(p9h.put_color(f"[!] 发现 {failed} 个失败 case", "yellow"))
else:
    print(p9h.put_color(f"[*] 所有测试用例均通过检测", "green"))
