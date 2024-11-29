import doctest
import test_case
import re
import ast

import parselmouth as p9h


def check_test(runner):
    test_cases = runner.test.examples[1:]
    bypass_cls = re.findall("(Bypass_\w+)", runner.test.examples[0].source)[0]
    bypass_funcs = {re.findall("(by_\w+)", i.source)[0] for i in test_cases}

    attr = vars(getattr(p9h.bypass_tools, bypass_cls, dict))
    all_funcs = {name for name in attr if name.startswith("by_")}
    print(f"\n[*] {bypass_cls}")
    tries = runner.tries - 1
    succ = tries - runner.failures
    print(
        "  [-] bypass 正确率: "
        + p9h.put_color(
            (
                f"{succ}/{tries}={100*round(succ/tries, 2)}%"
                + (f", 失败 {runner.failures} 个" if runner.failures else "")
            ),
            "yellow" if runner.failures else "green",
        )
    )
    if bypass_cls != "Bypass_Combo":  # 没有覆盖率一说
        print(
            "  [-] bypass 测试覆盖率: "
            + p9h.put_color(
                f"{len(bypass_funcs)}/{len(all_funcs)}={100*round(len(bypass_funcs)/len(all_funcs), 2)}%"
                + (
                    f", 无测试用例: {all_funcs-bypass_funcs}"
                    if all_funcs - bypass_funcs
                    else ""
                ),
                "yellow" if bypass_funcs != all_funcs else "green",
            )
        )
    return succ, runner.failures, tries


print(p9h.logo)
finder = doctest.DocTestFinder()
tests = finder.find(test_case)

all_succ = all_failed = all_tries = 0
case_record = []
for test in tests[::-1]:
    runner = doctest.DocTestRunner()
    runner.run(test)
    succ, failed, tries = check_test(runner)
    all_succ += succ
    all_failed += failed
    all_tries += tries

    for case in runner.test.examples[1:]:
        ans = case.want.strip()
        case = ast.parse(case.source).body
        args = case[-1].value.args
        if isinstance(case[0], ast.Assign):
            bypass_map = ast.unparse(case[0].value)
        else:
            bypass_map = args[0].value

        case_record.append([args[1].value, args[3].value, bypass_map, ans])

print()
for i, case in enumerate(case_record):
    print(
        f"[{i+1}]",
        p9h.put_color(case[0], "blue"),
        "with",
        p9h.put_color(case[1], "cyan"),
        "by",
        p9h.put_color(case[2], "white"),
        "=>",
        p9h.put_color(case[3], "green"),
    )

print(f"\n[*] 总计测试用例数量: {p9h.put_color(all_tries, 'cyan')}")
if all_failed:
    print(p9h.put_color(f"[!] 发现 {all_failed} 个失败 case", "yellow"))
else:
    print(p9h.put_color(f"[*] 所有测试用例均通过检测", "green"))

# print(case_record)
