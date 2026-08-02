#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 personal.html 转成 Scriptable WebView 可用的 记账页面.html。
用法：python3 scripts/build_scriptable_page.py
输出：scriptable/记账页面.html（保留原页面 UI 与逻辑，存储改为注入式 + 桥接）"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "personal.html")
OUT = os.path.join(ROOT, "scriptable", "记账页面.html")

html = open(SRC, encoding="utf-8").read()

def rep(old, new, count=1):
    global html
    n = html.count(old)
    if n < count:
        raise SystemExit("找不到替换目标（%d/%d）：\n%s" % (n, count, old[:160]))
    html = html.replace(old, new, count)

def rep_regex(pattern, new, flags=0):
    global html
    m = re.search(pattern, html, flags)
    if not m:
        raise SystemExit("正则找不到：%s" % pattern[:160])
    html = html[:m.start()] + new + html[m.end():]

# 1) 头部：地址栏清参脚本 -> 注入占位
rep("""<script>
/* 地址栏敏感参数（OCR 全文/豆包结果）必须在任何统计脚本之前清掉：
   避免平台注入的统计脚本读到账单内容；同时防止刷新重跑预填。 */
var PAGE_QUERY='';
try{ PAGE_QUERY=location.search||''; if(PAGE_QUERY) history.replaceState(null,'',location.pathname); }catch(e){}
</script>""",
"""<script>
/* 由 Scriptable 注入：INJECTED_STATE / INJECTED_OCR */
var INJECTED_STATE = /*__STATE__*/null;
var INJECTED_OCR = /*__OCR__*/'';
var INJECTED_QUICK = /*__QUICK__*/0;
</script>""")

# 2) 存储层：localStorage -> 注入状态 + persist 桥
rep("""/* 内存缓存：保证同一份引用，避免“解析两次、改了副本没存上”的脏数据（准） */
var _cache={};
function get(k){
  if(!(k in _cache)){
    try{ var v=localStorage.getItem(k); _cache[k]= v?JSON.parse(v):null; }catch(e){ _cache[k]=null; }
  }
  return _cache[k];
}
function set(k,v){ _cache[k]=v; try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }""",
"""/* Scriptable 版：数据由注入的 INJECTED_STATE 初始化，改动经 persist() 通知外部写盘 */
var _state = (INJECTED_STATE && typeof INJECTED_STATE==='object') ? INJECTED_STATE : {};
var _cache={ gr_records:_state.records||[], gr_savings:_state.savings||[], gr_accounts:_state.accounts||[], gr_assets:_state.assets||[] };
function get(k){ return _cache[k]||null; }
function set(k,v){ _cache[k]=v; persist(); }
function persist(){
  var o=document.getElementById('__out'); if(!o) return;
  o.value=JSON.stringify({records:_cache[LS.rec]||[], savings:_cache[LS.sav]||[], accounts:_cache[LS.acc]||[], assets:_cache[LS.asset]||[]});
  location.href='https://jz-save.local/';
}""")

# 3) toast 后插入确认框（WKWebView 不支持原生 confirm）
rep("""function toast(msg){ var t=$('toast'); t.textContent=msg; t.classList.add('show'); clearTimeout(t._t); t._t=setTimeout(function(){t.classList.remove('show');},1800); }""",
"""function toast(msg){ var t=$('toast'); t.textContent=msg; t.classList.add('show'); clearTimeout(t._t); t._t=setTimeout(function(){t.classList.remove('show');},1800); }
/* 确认框（WKWebView 不支持原生 confirm） */
var _confirmCb=null;
function askConfirm(msg){ return new Promise(function(res){ _confirmCb=res; var mk=$('confirmMask'); if(mk){ var cm=$('confirmMsg'); if(cm) cm.textContent=msg; mk.style.display='block'; } }); }
function confirmAnswer(yes){ var mk=$('confirmMask'); if(mk) mk.style.display='none'; if(_confirmCb){ _confirmCb(!!yes); _confirmCb=null; } }""")

# 4) 保存/删除/账户/目标 的 confirm -> askConfirm
rep("function saveRec(){", "async function saveRec(){")
rep("    if(dup && !confirm('检测到同一天、同分类、同金额的记录（可能重复记账），仍要保存吗？')) return;",
    "    if(dup && !(await askConfirm('检测到同一天、同分类、同金额的记录（可能重复记账），仍要保存吗？'))) return;")
rep("function deleteRec(id){", "async function deleteRec(id){")
rep("  if(!confirm('确定删除这条记录？')) return;",
    "  if(!(await askConfirm('确定删除这条记录？'))) return;")
rep("function deleteAccount(id){", "async function deleteAccount(id){")
rep("  if(!confirm('删除账户？账户下的攒钱目标将解除关联（数据保留为目标内记录）。')) return;",
    "  if(!(await askConfirm('删除账户？账户下的攒钱目标将解除关联（数据保留为目标内记录）。'))) return;")
rep("""  var del=$('svDelete'); if(del) del.onclick=function(){
    if(!confirm('删除此攒钱目标？相关记录（如月供）仍保留在明细里。')) return;""",
"""  var del=$('svDelete'); if(del) del.onclick=async function(){
    if(!(await askConfirm('删除此攒钱目标？相关记录（如月供）仍保留在明细里。'))) return;""")

# 5) 备份 -> 桥接
rep("""function backup(){
  var data={schemaVersion:1, exportedAt:new Date().toISOString(),
    records:records(), savings:savings(), accounts:accounts(), assets:assets()};
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a'); a.href=url; a.download='记账备份_'+today()+'.json';
  if(navigator.canShare && navigator.canShare({files:[new File([blob],'x.json',{type:'application/json'})]})){
    navigator.share({files:[new File([blob],'记账备份_'+today()+'.json',{type:'application/json'})], title:'记账备份'}).catch(function(){});
  } else { a.click(); toast('已导出备份文件'); }
  setTimeout(function(){URL.revokeObjectURL(url);},3000);
}""",
"""function backup(){ persist(); location.href='https://jz-backup.local/'; }""")

# 6) 导入 -> 桥接
rep_regex(r"""function importData\(\)\{[\s\S]*?rd\.readAsText\(f\);\n\}""",
"""function importData(){ location.href='https://jz-import.local/'; }
/* Scriptable 侧选完备份文件后注入 */
window.__importFromScriptable = function(d){
  var data=d||{};
  _cache[LS.rec]=Array.isArray(data.records)? data.records: [];
  _cache[LS.sav]=Array.isArray(data.savings)? data.savings: [];
  _cache[LS.acc]=Array.isArray(data.accounts)? data.accounts: [];
  _cache[LS.asset]=Array.isArray(data.assets)? data.assets: [];
  persist(); renderAll(); toast('导入成功');
}""")

# 7) applyOCR：URL 参数 -> 注入文本
rep_regex(r"""function applyOCR\(\)\{[\s\S]*?\n\}\nfunction b64ToText""",
"""function applyOCR(){
  var text=INJECTED_OCR||'';
  if(!text){
    if(INJECTED_QUICK){ openForm('exp'); toast('没读到剪贴板内容，请手动填写'); }
    return;
  }
  var amt=extractAmount(text); var refund=isRefund(text);
  var cat= refund? '退款' : detectCategory(text);
  var dt=extractDate(text);
  openForm(refund?'inc':'exp');
  if(amt) $('fAmt').value=amt;
  if(cat) $('fCat').value=cat;
  if(dt) $('fDate').value=dt;
  $('fNote').value=cleanNoteLine(text, amt);
  toast(refund?'识别为退款/收入，请核对':'已识别，请核对后保存');
}
function b64ToText""")

# 8) 移除文件输入元素与事件
rep('    <input type="file" id="impFile" accept="application/json" style="display:none">\n', '')
rep("  $('impFile').onchange=handleImportFile;\n", "")

# 9) 账户列表删除确认
rep("""  $('accList').addEventListener('click', function(e){ var c=e.target.closest('[data-acc]'); if(c && confirm('删除该账户？')) deleteAccount(c.dataset.acc); });""",
"""  $('accList').addEventListener('click', function(e){ var c=e.target.closest('[data-acc]'); if(c){ (async function(){ if(await askConfirm('删除该账户？')) deleteAccount(c.dataset.acc); })(); } });""")

# 10) 注入隐藏字段 + 确认框 DOM
rep('  <div class="toast" id="toast"></div>',
"""  <input type="hidden" id="__out">
  <div class="mask" id="confirmMask" style="display:none; z-index:60;" onclick="confirmAnswer(false)">
    <div class="sheet" style="max-width:320px;" onclick="event.stopPropagation()">
      <div id="confirmMsg" style="font-size:14px;line-height:1.6;padding:6px 2px 16px;"></div>
      <div class="row2">
        <button class="btn ghost" onclick="confirmAnswer(false)">取消</button>
        <button class="btn primary" onclick="confirmAnswer(true)">确定</button>
      </div>
    </div>
  </div>
  <div class="toast" id="toast"></div>""")

# 11) 自检：不能残留 localStorage / 原生 confirm / 文件输入
for bad, hint in [("localStorage", "残留 localStorage"), ("confirm('", "残留原生 confirm 调用"), ("impFile", "残留 impFile")]:
    if bad in html:
        raise SystemExit("自检失败：%s 仍存在" % hint)
for need, hint in [("/*__STATE__*/null", "状态注入占位丢失"), ("/*__OCR__*/''", "OCR 注入占位丢失"), ("/*__QUICK__*/0", "快捷标记占位丢失"), ("https://jz-save.local", "保存桥丢失"), ("__importFromScriptable", "导入桥丢失")]:
    if need not in html:
        raise SystemExit("自检失败：%s" % hint)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("OK -> %s (%d bytes)" % (OUT, len(html.encode("utf-8"))))
