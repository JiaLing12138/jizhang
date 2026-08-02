#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 记账模板.js + 记账页面.html 打包成单个 记账.js（页面以 base64 内嵌），
并同步到 Scriptable 的 iCloud 目录。
用法：python3 scripts/build_scriptable_bundle.py
"""
import base64
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "scriptable", "记账模板.js")
PAGE = os.path.join(ROOT, "scriptable", "记账页面.html")
OUT = os.path.join(ROOT, "scriptable", "记账.js")
MARK = "/*__PAGE_B64__*/''"

tpl = open(TPL, encoding="utf-8").read()
if MARK not in tpl:
    raise SystemExit("模板里找不到占位符：" + MARK)

html = open(PAGE, encoding="utf-8").read()
b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
out = tpl.replace(MARK, "/*__PAGE_B64__*/'" + b64 + "'")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)
print("OK -> %s (%d bytes)" % (OUT, len(out.encode("utf-8"))))

dst = os.path.expanduser("~/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents")
if os.path.isdir(dst):
    shutil.copy2(OUT, os.path.join(dst, "记账.js"))
    print("已同步到 Scriptable iCloud 目录")
else:
    print("提示：未找到 Scriptable iCloud 目录，请手动复制 记账.js 过去")
