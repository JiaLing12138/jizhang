#!/usr/bin/env python3
"""生成「记账OCR本地版」快捷指令（Scriptable 版，带苹果签名）。

流程：截屏 → 裁剪 → 提取文字 → 复制到剪贴板 → 打开 scriptable:///run/记账?clip=1
（不经过 URL 编码，绕开 urlencode 动作在本机失效的问题）

用法：python3 scripts/gen_shortcut_local.py
输出：shortcuts/记账OCR本地版.shortcut
"""
import os
import plistlib
import subprocess
import sys
import uuid

SCRIPT_URL = "scriptable:///run/%E8%AE%B0%E8%B4%A6?clip=1"  # 记账


def uid():
    return str(uuid.uuid4()).upper()


def wrap(value, stype="WFTextTokenAttachment"):
    return {"Value": value, "WFSerializationType": stype}


def action_output(uuid_, name, coerce=False):
    d = {"OutputUUID": uuid_, "Type": "ActionOutput", "OutputName": name}
    if coerce:
        d["Aggrandizements"] = [
            {"CoercionItemClass": "WFStringContentItem",
             "Type": "WFCoercionVariableAggrandizement"}]
    return d


def var(name):
    return {"VariableName": name, "Type": "Variable"}


def text_token_string(s, attaches):
    return wrap({"string": s, "attachmentsByRange": attaches}, "WFTextTokenString")


def build_actions():
    u_shot = uid(); u_w = uid(); u_h = uid(); u_calc = uid(); u_rh = uid()
    u_crop = uid(); u_ext = uid(); u_coerce = uid(); u_clip = uid()
    u_text = uid(); u_url = uid(); u_open = uid()

    return [
        # 0. 截屏（背面双击可触发）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.takescreenshot",
         "WFWorkflowActionParameters": {"UUID": u_shot}},
        # 1-2. 取宽高
        {"WFWorkflowActionIdentifier": "is.workflow.actions.properties.images",
         "WFWorkflowActionParameters": {
             "UUID": u_w, "WFInput": wrap(action_output(u_shot, "截屏")),
             "WFContentItemPropertyName": "Width"}},
        {"WFWorkflowActionIdentifier": "is.workflow.actions.properties.images",
         "WFWorkflowActionParameters": {
             "UUID": u_h, "WFInput": wrap(action_output(u_shot, "截屏")),
             "WFContentItemPropertyName": "Height"}},
        # 3. RealHeight = 高度 - 132（裁掉顶部状态栏）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.calculateexpression",
         "WFWorkflowActionParameters": {
             "UUID": u_calc,
             "Input": wrap(
                 {"string": "\ufffc-132",
                  "attachmentsByRange": {"{0, 1}": action_output(u_h, "高度")}},
                 "WFTextTokenString")}},
        # 4. 变量 RealHeight
        {"WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
         "WFWorkflowActionParameters": {
             "UUID": u_rh,
             "WFInput": wrap(action_output(u_calc, "Calculation Result")),
             "WFVariableName": "RealHeight"}},
        # 5. 裁剪顶部 132px
        {"WFWorkflowActionIdentifier": "is.workflow.actions.image.crop",
         "WFWorkflowActionParameters": {
             "UUID": u_crop,
             "WFInput": wrap(action_output(u_shot, "截屏")),
             "WFImageCropY": "132",
             "WFImageCropWidth": wrap(action_output(u_w, "Width")),
             "WFImageCropHeight": wrap(var("RealHeight")),
             "WFImageCropPosition": "Custom"}},
        # 6. 提取文字（苹果原生 Live Text）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.extracttextfromimage",
         "WFWorkflowActionParameters": {
             "UUID": u_ext,
             "WFImage": wrap(action_output(u_crop, "裁剪后的图像"))}},
        # 7. 强制纯文本
        {"WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
         "WFWorkflowActionParameters": {
             "UUID": u_coerce,
             "WFTextActionText": text_token_string(
                 "\ufffc", {"{0, 1}": action_output(u_ext, "Text from Image", coerce=True)})}},
        # 8. 复制到剪贴板（不编码，Scriptable 直接读）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.copytoClipboard",
         "WFWorkflowActionParameters": {
             "UUID": u_clip,
             "WFInput": wrap(action_output(u_coerce, "Text", coerce=True))}},
        # 9-11. 打开 Scriptable 记账
        {"WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
         "WFWorkflowActionParameters": {
             "UUID": u_text,
             "WFTextActionText": text_token_string(SCRIPT_URL, {})}},
        {"WFWorkflowActionIdentifier": "is.workflow.actions.url",
         "WFWorkflowActionParameters": {
             "UUID": u_url,
             "WFURLActionURL": text_token_string(
                 "\ufffc", {"{0, 1}": action_output(u_text, "Text")})}},
        {"WFWorkflowActionIdentifier": "is.workflow.actions.openurl",
         "WFWorkflowActionParameters": {
             "UUID": u_open, "WFInput": wrap(action_output(u_url, "URL"))}},
    ]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    out_name = os.path.join(root, "shortcuts", "记账OCR本地版.shortcut")
    unsigned = out_name + ".unsigned.shortcut"

    actions = build_actions()
    shortcut = {
        "WFWorkflowActions": actions,
        "WFWorkflowClientVersion": "4610.1",
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowName": "记账OCR本地版",
        "WFWorkflowImportQuestions": [],
        "WFWorkflowIcon": {"WFWorkflowIconGlyphNumber": 61974,
                           "WFWorkflowIconStartColor": 3031607807},
        "WFQuickActionSurfaces": [],
        "WFWorkflowHasShortcutInputVariables": False,
    }

    with open(unsigned, "wb") as f:
        plistlib.dump(shortcut, f, fmt=plistlib.FMT_BINARY)

    try:
        subprocess.run(["shortcuts", "sign", "--mode", "anyone",
                        "--input", unsigned, "--output", out_name],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        if os.path.exists(unsigned):
            os.remove(unsigned)
        print("❌ 签名失败：", e.stderr)
        sys.exit(1)

    os.remove(unsigned)
    print("✅ 已生成：%s（%d bytes）" % (out_name, os.path.getsize(out_name)))

    sys.path.insert(0, here)
    import decode_shortcut as dec
    wf = dec.decode_shortcut(out_name)
    n = len(wf.get("WFWorkflowActions", []))
    print("🔎 解码验证：签名后动作数 = %d（期望 %d）" % (n, len(actions)))
    if n != len(actions):
        print("⚠️ 警告：动作数不一致，sign 丢动作了！")
        sys.exit(1)
    print("✅ 动作全部保留")


if __name__ == "__main__":
    main()
