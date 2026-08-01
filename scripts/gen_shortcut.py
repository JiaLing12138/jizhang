#!/usr/bin/env python3
"""生成「记账OCR」快捷指令（带苹果签名，iOS 可直接导入）。

【2026-08-01 深夜 第七版：urlencode 疑似本机失效，双方案对照】

实测结论：
  - 截屏→裁剪→提取文字：能出字（①有）
  - urlencode：①的原文能取到，但编码后 ②③ 都空（连纯文字"测试ABC"也空）
    → URL 编码动作在本机疑似不输出内容；换两种方案对照：
    A. WFInput 改用 WFTextTokenString（字符串参数的标准序列化，此前一直用 Attachment）
    B. Base64 编码（is.workflow.actions.base64encode，另一个编码动作）

调试版（--debug，19 步）：4 个弹窗：
  ①原文：提取文字（对照组）
  ②编码A：urlencode + WFTextTokenString 传入
  ③编码B：urlencode + 纯字符串"测试ABC"传入（验证动作本身）
  ④Base64：base64encode 结果（备用方案）
  URL 链用 ② 的输出（若 ② 有字，页面直接预填）

生产版：待 ②③④ 结果定稿后更新。

plist 关键：
  - 普通捷径(非 ActionExtension)，可被「背面双击 / 小组件 / 手动」触发
  - plist 根直接是 WFWorkflow dict（不包 {"WFWorkflow":...}，否则 sign 丢动作）
  - UUID 必须大写
"""
import plistlib
import subprocess
import uuid
import sys
import os

BASE_URL = "https://gcore.jsdelivr.net/gh/JiaLing12138/jizhang@main/personal.html"

DEBUG = "--debug" in sys.argv
DOUBAO = "--doubao" in sys.argv
DOUBAO_DEBUG = "--doubao-debug" in sys.argv


DOUBAO_CATS_FALLBACK = "餐饮、外卖、咖啡茶饮、交通、打车、加油、购物、超市、网购、服饰、居住、水电燃气、医疗、娱乐、学习、通讯、人情、其他"
DOUBAO_INC_CATS_FALLBACK = "工资、兼职、理财、红包、报销、退款、其他"


def read_cats_from_page():
    """分类清单的单一事实来源 = personal.html 的 CAT_EXP / CAT_INC。
    改页面分类后重跑本脚本即可，无需手动同步提示词。"""
    import re as _re
    import os
    page = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "personal.html")
    def _pick(pattern, fallback):
        m = _re.search(pattern, src, _re.S)
        if m:
            cats = _re.findall(r"'([^']+)'", m.group(1))
            if len(cats) >= 3:
                return "、".join(cats)
        return fallback
    try:
        src = open(page, encoding="utf-8").read()
    except Exception:
        return DOUBAO_CATS_FALLBACK, DOUBAO_INC_CATS_FALLBACK
    exp = _pick(r"var CAT_EXP=\[(.*?)\];", DOUBAO_CATS_FALLBACK)
    inc = _pick(r"var CAT_INC=\[(.*?)\];", DOUBAO_INC_CATS_FALLBACK)
    return exp, inc


DOUBAO_CATS, DOUBAO_INC_CATS = read_cats_from_page()

DOUBAO_PROMPT = (
    "你是我的个人记账助手。下面是从微信支付账单截屏识别出的文字（可能含识别错误）。"
    "请识别其中最主要的一笔交易，只输出一个 JSON 对象，不要代码块、不要解释、不要任何其他文字：\n"
    '{"amt":"金额，数字最多两位小数，如6.00","cat":"分类，从下面列表选最贴切的一个",'
    '"note":"备注，商家/商品等，20字以内，没有就填空字符串",'
    '"date":"交易日期，格式YYYY-MM-DD，文字里没有就填空字符串",'
    '"type":"exp或inc：支出为exp，退款/收入为inc"}\n'
    "type=exp（支出）时，分类从下面选：\n" + DOUBAO_CATS + "\n"
    "type=inc（退款/收入）时，分类从下面选：\n" + DOUBAO_INC_CATS + "\n"
    "如果确实无法识别金额，输出 {\"amt\":\"\",\"cat\":\"\",\"note\":\"\",\"date\":\"\",\"type\":\"exp\"}\n"
    "待识别文字：\n\ufffc"
)


def uid():
    """大写 UUID（真实 iOS 文件格式）"""
    return str(uuid.uuid4()).upper()


def wrap(value, stype="WFTextTokenAttachment"):
    return {"Value": value, "WFSerializationType": stype}


def action_output(uuid, name, coerce=False):
    d = {"OutputUUID": uuid, "Type": "ActionOutput", "OutputName": name}
    if coerce:
        d["Aggrandizements"] = [
            {"CoercionItemClass": "WFStringContentItem",
             "Type": "WFCoercionVariableAggrandizement"}]
    return d


def var(name):
    return {"VariableName": name, "Type": "Variable"}


def text_token_string(s, attaches):
    """显示类文本（弹窗消息等）：必须 WFTextTokenString"""
    return wrap(
        {"string": s, "attachmentsByRange": attaches},
        "WFTextTokenString")


def insert_positions(s, refs):
    """按顺序把 U+FFFC 占位符的位置映射到 refs 里的变量引用"""
    out = {}
    it = iter(refs)
    for i, ch in enumerate(s):
        if ch == "\ufffc":
            out["{%d, 1}" % i] = next(it)
    return out


def build_actions():
    """入口：调试版/生产版"""
    return build_debug_actions() if DEBUG else build_prod_actions()


def crop_extract_chain(u_shot, u_ext):
    """截屏 → 取宽高 → 高-132 → 裁剪 → 提取文字，返回动作列表"""
    u_w = uid(); u_h = uid(); u_calc = uid(); u_rh = uid(); u_crop = uid()
    return [
        # 0. 截屏（与钱迹一致，背面双击可触发）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.takescreenshot",
         "WFWorkflowActionParameters": {"UUID": u_shot}},
        # 1. 取截屏宽度
        {"WFWorkflowActionIdentifier": "is.workflow.actions.properties.images",
         "WFWorkflowActionParameters": {
             "UUID": u_w,
             "WFInput": wrap(action_output(u_shot, "截屏")),
             "WFContentItemPropertyName": "Width"}},
        # 2. 取截屏高度
        {"WFWorkflowActionIdentifier": "is.workflow.actions.properties.images",
         "WFWorkflowActionParameters": {
             "UUID": u_h,
             "WFInput": wrap(action_output(u_shot, "截屏")),
             "WFContentItemPropertyName": "Height"}},
        # 3. 计算 RealHeight = 高度 - 132（裁掉顶部状态栏）
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
        # 5. 裁剪：裁掉顶部 132px（与钱迹一致）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.image.crop",
         "WFWorkflowActionParameters": {
             "UUID": u_crop,
             "WFInput": wrap(action_output(u_shot, "截屏")),
             "WFImageCropY": "132",
             "WFImageCropWidth": wrap(action_output(u_w, "Width")),
             "WFImageCropHeight": wrap(var("RealHeight")),
             "WFImageCropPosition": "Custom"}},
        # 6. 从裁剪后的图提取文字（苹果原生 Live Text）
        {"WFWorkflowActionIdentifier": "is.workflow.actions.extracttextfromimage",
         "WFWorkflowActionParameters": {
             "UUID": u_ext,
             "WFImage": wrap(action_output(u_crop, "裁剪后的图像"))}},
    ]


def url_chain(u_enc, u_text, u_url, u_open):
    """编码结果 → 拼URL → url → openurl（全程直接动作输出引用，不用变量）"""
    return [
        # 文本动作构造 URL：?ocr=<编码结果>
        {"WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
         "WFWorkflowActionParameters": {
             "UUID": u_text,
             "WFTextActionText": text_token_string(
                 BASE_URL + "?ocr=\ufffc",
                 {"{%d, 1}" % len(BASE_URL + "?ocr="): action_output(u_enc, "URL Encoded Text")})}},
        # URL 动作：单附件指向 gettext 输出
        {"WFWorkflowActionIdentifier": "is.workflow.actions.url",
         "WFWorkflowActionParameters": {
             "UUID": u_url,
             "WFURLActionURL": text_token_string(
                 "\ufffc",
                 {"{0, 1}": action_output(u_text, "Text")})}},
        # 打开 URL
        {"WFWorkflowActionIdentifier": "is.workflow.actions.openurl",
         "WFWorkflowActionParameters": {
             "UUID": u_open,
             "WFInput": wrap(action_output(u_url, "URL"))}},
    ]


def build_prod_actions():
    """生产版（暂按 v7 候选：WFTextTokenString 传入 urlencode）"""
    u_shot = uid(); u_ext = uid(); u_coerce = uid()
    u_enc = uid(); u_text = uid(); u_url = uid(); u_open = uid()

    return (
        crop_extract_chain(u_shot, u_ext) +
        [
            # 文本动作：把提取结果强制转成纯文本
            {"WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
             "WFWorkflowActionParameters": {
                 "UUID": u_coerce,
                 "WFTextActionText": text_token_string(
                     "\ufffc",
                     {"{0, 1}": action_output(u_ext, "Text from Image", coerce=True)})}},
            # URL 编码：WFInput 用 WFTextTokenString（字符串参数标准序列化）
            {"WFWorkflowActionIdentifier": "is.workflow.actions.urlencode",
             "WFWorkflowActionParameters": {
                 "UUID": u_enc,
                 "WFInput": text_token_string(
                     "\ufffc",
                     {"{0, 1}": action_output(u_coerce, "Text", coerce=True)})}},
        ] +
        url_chain(u_enc, u_text, u_url, u_open)
    )


def doubao_intent(u_prompt, u_db):
    """「问豆包」AppIntent：参数格式照抄真实「语音记账」捷径（AskAssistantIntent）"""
    return {
        "WFWorkflowActionIdentifier": "com.bot.doubao.AskAssistantIntent",
        "WFWorkflowActionParameters": {
            "UUID": u_db,
            "text": text_token_string(
                "\ufffc",
                {"{0, 1}": action_output(u_prompt, "Text")}),
            "AppIntentDescriptor": {
                "TeamIdentifier": "96L78H6LMH",
                "BundleIdentifier": "com.bot.doubao",
                "Name": "豆包",
                "AppIntentIdentifier": "AskAssistantIntent",
            },
            "showResult": True,
            "ShowWhenRun": False,
            "CustomOutputName": "豆包输出",
            "isTTSEnabled": False,
        },
    }


def build_doubao_actions(debug=False):
    """豆包版：OCR 原文 + 提示词 → 问豆包 → 原文和豆包输出都进 URL
    页面优先解析 ai= 的 JSON，失败自动退回本地规则解析 ocr=。"""
    u_shot = uid(); u_ext = uid(); u_coerce = uid()
    u_prompt = uid(); u_db = uid()
    u_enc_ai = uid(); u_enc_ocr = uid()
    u_text = uid(); u_url = uid(); u_open = uid()

    a = []
    def act(ident, params):
        a.append({"WFWorkflowActionIdentifier": ident,
                  "WFWorkflowActionParameters": params})

    a += crop_extract_chain(u_shot, u_ext)
    # OCR 原文 → 强制纯文本
    act("is.workflow.actions.gettext",
        {"UUID": u_coerce,
         "WFTextActionText": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_ext, "Text from Image", coerce=True)})})
    # 构造提示词（正文 + OCR 原文）
    act("is.workflow.actions.gettext",
        {"UUID": u_prompt,
         "WFTextActionText": text_token_string(
             DOUBAO_PROMPT,
             {"{%d, 1}" % DOUBAO_PROMPT.rindex("\ufffc"): action_output(u_coerce, "Text", coerce=True)})})
    # 问豆包
    a.append(doubao_intent(u_prompt, u_db))

    if debug:
        act("is.workflow.actions.alert",
            {"UUID": uid(), "WFAlertActionTitle": "豆包输出",
             "WFAlertActionMessage": text_token_string(
                 "豆包=[\ufffc]",
                 insert_positions("豆包=[\ufffc]",
                                  [action_output(u_db, "豆包输出", coerce=True)])),
             "WFAlertActionCancelButtonShown": False})

    # 原文 + 豆包输出分别 URL 编码
    act("is.workflow.actions.urlencode",
        {"UUID": u_enc_ocr,
         "WFInput": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_coerce, "Text", coerce=True)})})
    act("is.workflow.actions.urlencode",
        {"UUID": u_enc_ai,
         "WFInput": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_db, "豆包输出", coerce=True)})})
    # 拼 URL：?ocr=<原文>&ai=<豆包>
    url_str = BASE_URL + "?ocr=\ufffc&ai=\ufffc"
    act("is.workflow.actions.gettext",
        {"UUID": u_text,
         "WFTextActionText": text_token_string(
             url_str,
             insert_positions(url_str, [
                 action_output(u_enc_ocr, "URL Encoded Text"),
                 action_output(u_enc_ai, "URL Encoded Text")]))})
    act("is.workflow.actions.url",
        {"UUID": u_url,
         "WFURLActionURL": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_text, "Text")})})
    act("is.workflow.actions.openurl",
        {"UUID": u_open, "WFInput": wrap(action_output(u_url, "URL"))})
    return a


def build_debug_actions():
    """调试版 v7：①原文 ②编码A(WFTextTokenString) ③编码B(纯字符串) ④Base64"""
    u_shot = uid(); u_ext = uid(); u_coerce = uid()
    u_enc_a = uid(); u_enc_b = uid(); u_b64 = uid()
    u_text = uid(); u_url = uid(); u_open = uid()

    a = []
    def act(ident, params):
        a.append({"WFWorkflowActionIdentifier": ident,
                  "WFWorkflowActionParameters": params})

    a += crop_extract_chain(u_shot, u_ext)
    # ① 文本动作（强转纯文本）→ 弹窗
    act("is.workflow.actions.gettext",
        {"UUID": u_coerce,
         "WFTextActionText": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_ext, "Text from Image", coerce=True)})})
    act("is.workflow.actions.alert",
        {"UUID": uid(), "WFAlertActionTitle": "①原文",
         "WFAlertActionMessage": text_token_string(
             "原文=[\ufffc]",
             insert_positions("原文=[\ufffc]",
                              [action_output(u_coerce, "Text", coerce=True)])),
         "WFAlertActionCancelButtonShown": False})
    # ② 原文 → urlencode（WFTextTokenString 传入）→ 弹窗
    act("is.workflow.actions.urlencode",
        {"UUID": u_enc_a,
         "WFInput": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_coerce, "Text", coerce=True)})})
    act("is.workflow.actions.alert",
        {"UUID": uid(), "WFAlertActionTitle": "②编码A",
         "WFAlertActionMessage": text_token_string(
             "编码A=[\ufffc]",
             insert_positions("编码A=[\ufffc]",
                              [action_output(u_enc_a, "URL Encoded Text", coerce=True)])),
         "WFAlertActionCancelButtonShown": False})
    # ③ urlencode + 纯字符串"测试ABC"（验证动作本身）
    act("is.workflow.actions.urlencode",
        {"UUID": u_enc_b, "WFInput": "测试ABC"})
    act("is.workflow.actions.alert",
        {"UUID": uid(), "WFAlertActionTitle": "③编码B",
         "WFAlertActionMessage": text_token_string(
             "编码B=[\ufffc]",
             insert_positions("编码B=[\ufffc]",
                              [action_output(u_enc_b, "URL Encoded Text", coerce=True)])),
         "WFAlertActionCancelButtonShown": False})
    # ④ base64encode（备用方案）
    act("is.workflow.actions.base64encode",
        {"UUID": u_b64,
         "WFInput": wrap(action_output(u_coerce, "Text", coerce=True)),
         "WFEncodeMode": "Encode",
         "WFBase64LineBreakMode": "None"})
    act("is.workflow.actions.alert",
        {"UUID": uid(), "WFAlertActionTitle": "④Base64",
         "WFAlertActionMessage": text_token_string(
             "Base64=[\ufffc]",
             insert_positions("Base64=[\ufffc]",
                              [action_output(u_b64, "Base64 Encoded Text", coerce=True)])),
         "WFAlertActionCancelButtonShown": False})
    # URL 链用 ② 编码A
    act("is.workflow.actions.gettext",
        {"UUID": u_text,
         "WFTextActionText": text_token_string(
             BASE_URL + "?ocr=\ufffc",
             {"{%d, 1}" % len(BASE_URL + "?ocr="): action_output(u_enc_a, "URL Encoded Text")})})
    act("is.workflow.actions.url",
        {"UUID": u_url,
         "WFURLActionURL": text_token_string(
             "\ufffc", {"{0, 1}": action_output(u_text, "Text")})})
    act("is.workflow.actions.openurl",
        {"UUID": u_open, "WFInput": wrap(action_output(u_url, "URL"))})
    return a


def main():
    if DOUBAO_DEBUG:
        out_name = "shortcuts/记账OCR豆包-调试.shortcut"
        actions = build_doubao_actions(debug=True)
        wf_name = "记账OCR豆包-调试"
    elif DOUBAO:
        out_name = "shortcuts/记账OCR豆包.shortcut"
        actions = build_doubao_actions()
        wf_name = "记账OCR豆包"
    else:
        out_name = "shortcuts/记账OCR-调试.shortcut" if DEBUG else "shortcuts/记账OCR.shortcut"
        actions = build_actions()
        wf_name = "记账OCR-调试" if DEBUG else "记账OCR"
    unsigned = out_name + ".unsigned.shortcut"

    shortcut = {
        "WFWorkflowActions": actions,
        "WFWorkflowClientVersion": "4610.1",
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowName": wf_name,
        "WFWorkflowImportQuestions": [],
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 61974,
            "WFWorkflowIconStartColor": 3031607807,
        },
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
    size = os.path.getsize(out_name)
    print(f"✅ 已生成签名快捷指令：{out_name}（{size} bytes）")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import decode_shortcut as dec
    wf = dec.decode_shortcut(out_name)
    n = len(wf.get("WFWorkflowActions", []))
    print(f"🔎 解码验证：签名后动作数 = {n}")
    if n != len(actions):
        print(f"⚠️ 警告：动作数 {n} ≠ 期望 {len(actions)}，sign 又丢动作了！")
        sys.exit(1)
    print("✅ 动作全部保留，导入后不会再是空快捷指令。")


if __name__ == "__main__":
    main()
