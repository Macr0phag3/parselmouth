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
    try:
        bypassed = bypassed and eval(bypass_result) == eval(payload)
    except Exception:
        print(
            f"{p9h.put_color('[DEBUG] payload 异常', 'red')}, {payload} with {p9h.put_color(p9h.BLACK_CHAR, 'white')}\n",
            bypass_result,
        )
        raise

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
                "rule": {"kwd": ["1"], "re_kwd": "1"},
                "bypass_func": ["by_trans", "by_cal", "by_unicode"],
            },
            {
                "rule": {"kwd": ["1", "True", "all"], "re_kwd": "1|all|True"},
                "bypass_func": ["by_trans", "by_cal", "by_unicode"],
            },
            {
                "rule": {
                    "kwd": ["1", "True", "all", "(", "*", "+"],
                    "re_kwd": "1|True|all|\(|\*|\+",
                },
                "bypass_func": ["by_trans", "by_cal"],
            },
            {
                "rule": {
                    "kwd": [
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
                        "(",
                    ],
                    "re_kwd": "[0|0|3-8]|True|False|\(",
                },
                "bypass_func": ["by_cal"],
            },
            {
                "rule": {
                    "kwd": [
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
                    "re_kwd": "[0|1|3-8]|True|False|\*|\+",
                },
                "bypass_func": ["by_cal"],
            },
        ],
        "2": [
            {
                "rule": {"kwd": ["2"], "re_kwd": "2"},
                "bypass_func": ["by_bin", "by_trans", "by_cal", "by_unicode"],
            },
            {
                "rule": {"kwd": ["2", "True"], "re_kwd": "2|True"},
                "bypass_func": ["by_bin", "by_trans", "by_cal", "by_unicode"],
            },
        ],
        "12": [
            {
                "rule": {"kwd": ["12"], "re_kwd": "12"},
                "bypass_func": ["by_bin", "by_hex", "by_ord", "by_cal", "by_unicode"],
            },
            {
                "rule": {"kwd": ["12", "True"], "re_kwd": "12|True"},
                "bypass_func": ["by_bin", "by_hex", "by_ord", "by_cal", "by_unicode"],
            },
        ],
        "1000": [
            {
                "rule": {
                    "kwd": [
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
                    "re_kwd": "[0-6|7|9|\-|\*]|True|False",
                },
                "bypass_func": ["by_cal", "by_ord"],
            }
        ],
        "2024": [
            {
                "rule": {"kwd": ["2", "4"], "re_kwd": "2|4"},
                "bypass_func": ["by_bin", "by_hex", "by_ord", "by_cal", "by_unicode"],
            },
            {
                "rule": {"kwd": ["1", "2", "4", "*"], "re_kwd": "1|2|4|\*"},
                "bypass_func": ["by_hex", "by_cal", "by_ord", "by_unicode"],
            },
        ],
        "-1": [
            {
                "rule": {"kwd": ["1"], "re_kwd": "1"},
                "bypass_func": ["by_cal", "by_unicode"],
            },
            {
                "rule": {
                    "kwd": ["0", "1", "3", "4", "5", "6", "7", "8"],
                    "re_kwd": "[0|1|3-8]",
                },
                "bypass_func": ["by_cal"],
            },
            {
                "rule": {
                    "kwd": ["0", "1", "3", "4", "5", "6", "7", "8", "*", "+"],
                    "re_kwd": "[0|1|3-8|\*|\+]",
                },
                "bypass_func": ["by_cal"],
            },
            {
                "rule": {
                    "kwd": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "+"],
                    "re_kwd": "[0-9|\*|\+]",
                },
                "bypass_func": ["by_cal"],
            },
            {
                "rule": {
                    "kwd": ["1", "~", "True", "all", "len", "*"],
                    "re_kwd": "1|~|True|all|len|\*",
                },
                "bypass_func": [],
            },
        ],
        "-2024": [
            {
                "rule": {"kwd": ["2", "4"], "re_kwd": "2|4"},
                "bypass_func": ["by_cal", "by_unicode"],
            },
            {
                "rule": {
                    "kwd": ["0", "1", "3", "4", "5", "6", "7", "8"],
                    "re_kwd": "0|1|[3-8]",
                },
                "bypass_func": ["by_cal"],
            },
            {
                "rule": {
                    "kwd": ["0", "1", "2", "3", "4", "5", "6", "7", "8", " "],
                    "re_kwd": "[0-8| ]",
                },
                "bypass_func": ["by_cal"],
            },
        ],
    },
    "Bypass_String": {
        "'macr0phag3'": [
            {
                "rule": {"kwd": ["macr0phag3"], "re_kwd": "macr0phag3"},
                "bypass_func": [
                    "by_char",
                    "by_reverse",
                    "by_dict",
                    "by_bytes_single",
                    "by_bytes_full",
                    "by_unicode_encode",
                    "by_hex_encode",
                    "by_char_format",
                    "by_char_add",
                ],
            },
            {
                "rule": {"kwd": ["macr0phag3", "+"], "re_kwd": "macr0phag3|\+"},
                "bypass_func": [
                    "by_char",
                    "by_bytes_single",
                    "by_format",
                    "by_unicode_encode",
                    "by_hex_encode",
                    "by_char_format",
                ],
            },
            {"rule": {"kwd": ["'"], "re_kwd": "'"}, "bypass_func": ["*"]},
            {"rule": {"kwd": ['"'], "re_kwd": '"'}, "bypass_func": ["*"]},
            {
                "rule": {
                    "kwd": ["'", '"', "chr", "bytes", "1", "b", "x", "0"],
                    "re_kwd": "'|\"|chr|bytes|1|b|x|0",
                },
                "bypass_func": [],
            },
            {
                "rule": {
                    "kwd": ["'", '"', "chr", "bytes", "1", "b", "x", "0", "+", " "],
                    "re_kwd": "'|\"|chr|bytes|1|b|x|0|\+| ",
                },
                "bypass_func": [],
            },
        ],
        "'你好世界'": [
            {
                "rule": {"kwd": ["'", '"'], "re_kwd": "'|\""},
                "bypass_func": ["by_char", "by_dict"],
            },
            {
                "rule": {"kwd": ["你"], "re_kwd": "你"},
                "bypass_func": [
                    "by_unicode_encode",
                    "by_char_format",
                ],
            },
        ],
        "'__builtins__'": [
            {
                "rule": {
                    "kwd": ["__builtins__", "c", "𝒄"],
                    "re_kwd": "__builtins__|c|𝒄",
                },
                "bypass_func": [],
            }
        ],
    },
    "Bypass_Attribute": {
        "str.find": [
            {"rule": {"kwd": [" ", "."], "re_kwd": " |\."}, "bypass_func": ["*"]},
            {"rule": {"kwd": ["find"], "re_kwd": "find"}, "bypass_func": ["*"]},
            {
                "rule": {"kwd": ["find", "chr", "ᶜ"], "re_kwd": "find|chr|ᶜ"},
                "bypass_func": ["*"],
            },
            {
                "rule": {"kwd": ["find", "chr", "ᶜ", ":"], "re_kwd": "find|chr|ᶜ|:"},
                "bypass_func": ["*"],
            },
            {
                "rule": {
                    "kwd": [" ", "\t", "find", "chr", "ᶜ", ":", "0", "1"],
                    "re_kwd": " |\t|find|chr|ᶜ|:|0|1",
                },
                "bypass_func": ["*"],
            },
        ],
    },
    "Bypass_Name": {
        "__import__": [
            {"rule": {"kwd": ["__i"], "re_kwd": "__i"}, "bypass_func": ["*"]},
            {"rule": {"kwd": ["import"], "re_kwd": "import"}, "bypass_func": ["*"]},
            {"rule": {"kwd": ["imp", "rt"], "re_kwd": "imp|rt"}, "bypass_func": ["*"]},
            {"rule": {"kwd": ["__", "o", "𝒐"], "re_kwd": "__|o|𝒐"}, "bypass_func": []},
        ],
    },
    "Integrated": {
        "__import__('os').popen('whoami').read()": [
            {
                "rule": {"kwd": ["read", "'", '"'], "re_kwd": "read|'|\""},
                "bypass_func": [],
            },
            {
                "rule": {"kwd": [".", "read", "popen"], "re_kwd": "\.|read|popen"},
                "bypass_func": [],
            },
            {
                "rule": {
                    "kwd": ["__", ".", "'", '"', "read", "chr", "ᶜ"],
                    "re_kwd": "__|\.|'|\"|read|chr|ᶜ",
                },
                "bypass_func": [],
            },
            {
                "rule": {
                    "kwd": ["__", ".", "'", '"', "read", "chr", "ᶜ", "="],
                    "re_kwd": "__|\.|'|\"|read|chr|ᶜ|=",
                },
                "bypass_func": [],
            },
            {
                "rule": {
                    "kwd": [
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
                    "re_kwd": "__|\.|'|\"|read|chr|ᶜ|=|:|0|1| |\t",
                },
                "bypass_func": [],
                #         },
                #     ],
                # },
                # "Bypass_BoolOp": {
                #     "True or False": [
                #         {
                #             "rule": {"kwd": ["or"], "re_kwd": "or"},
                #             "bypass_func": ["by_bitwise", "by_arithmetic"],
                #         },
                #     ],
                #     "True and False": [
                #         {
                #             "rule": {"kwd": ["and"], "re_kwd": "and"},
                #             "bypass_func": ["by_bitwise", "by_arithmetic"],
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
