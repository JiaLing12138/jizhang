#!/usr/bin/env node
/* 记账 OCR 本地规则回归测试
 * 用法：node scripts/test_ocr.js（或本仓库打包的 node）
 * 作用：把 personal.html 里的识别函数抽出来跑真实语料，防止改规则改坏。 */
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'personal.html'), 'utf8');
/* personal.html 有多个 <script> 块（head 里清参脚本 + 主逻辑），取最后一个主块 */
const blocks = html.match(/<script>([\s\S]*?)<\/script>/g) || [];
const src = blocks.length ? blocks[blocks.length - 1].replace(/^<script>/, '').replace(/<\/script>$/, '') : '';

function grab(fn){
  const i = src.indexOf('function ' + fn);
  if (i < 0) throw new Error('找不到函数 ' + fn);
  const s = src.indexOf('{', i);
  let d = 0, q = null, j = s;
  while (j < src.length) {
    const c = src[j];
    if (q) { if (c === '\\') { j += 2; continue; } if (c === q) q = null; }
    else if (c === "'" || c === '"' || c === '`') q = c;
    else if (c === '{') d++;
    else if (c === '}') { d--; if (d === 0) return src.slice(i, j + 1); }
    j++;
  }
  throw new Error('函数未闭合 ' + fn);
}

const code = [
  src.match(/var CAT_EXP=\[.*?\];/s)[0],
  src.match(/var CAT_INC=\[.*?\];/s)[0],
  src.match(/var CAT_ASSET=\[.*?\];/s)[0],
  src.match(/var MERCHANT=\{[\s\S]*?\};/s)[0],
  src.match(/var LINEKW=\{[\s\S]*?\};/s)[0],
  'var PAGE_QUERY="";',
  grab('toAmt'), grab('extractAmount'), grab('extractDate'), grab('cleanNoteLine'),
  grab('isRefund'), grab('detectCategory'), grab('parseAiJson'), grab('matchCat'),
].join('\n');

eval(code);

let pass = 0, fail = 0;
function T(name, actual, expect){
  const ok = String(actual) === String(expect);
  if (ok) pass++; else fail++;
  console.log((ok ? '  ✓ ' : '  ✗ ') + name + '  →  ' + JSON.stringify(actual) + (ok ? '' : '（期望 ' + JSON.stringify(expect) + '）'));
}

console.log('== 金额提取 ==');
T('美团 ¥26.00', extractAmount('微信支付\n美团外卖\n支付金额 ¥26.00'), 26);
T('星巴克 ¥38.50', extractAmount('星巴克咖啡 ¥38.50'), 38.5);
T('千分位 ¥1,234.56', extractAmount('合计 ¥1,234.56'), 1234.56);
T('千分位中文逗号', extractAmount('合计 ¥1，234.56'), 1234.56);
T('负号退款 ¥-6.00', extractAmount('退款 ¥-6.00'), 6);
T('负号在前 -¥6.00', extractAmount('-¥6.00'), 6);
T('合计 6.00元', extractAmount('合计 6.00元'), 6);
T('关键词优先级（实付优先）', extractAmount('商品金额 ¥26.00 优惠 ¥0.00 实付 ¥26.00'), 26);
T('退款到账', extractAmount('退款到账 ¥38.50'), 38.5);
T('单号不干扰', extractAmount('交易单号 4200003120202607318735183904 已支付 ¥6.00'), 6);
T('无金额', extractAmount('没有金额的文字'), null);

console.log('== 分类 ==');
T('美团外卖', detectCategory('收款方 美团外卖\n支付金额 ¥26.00'), '外卖');
T('星巴克', detectCategory('星巴克咖啡 ¥38.50'), '咖啡茶饮');
T('滴滴', detectCategory('滴滴出行 ¥12.00'), '打车');
T('中石化', detectCategory('中石化加油 ¥300.00'), '加油');
T('罗森便利店', detectCategory('收款方 罗森便利店\n¥15.80'), '超市');
T('淘宝', detectCategory('淘宝订单 ¥88.00'), '网购');
T('优衣库', detectCategory('优衣库 ¥199.00'), '服饰');
T('电费', detectCategory('电费缴纳 ¥150.00'), '水电燃气');
T('房租', detectCategory('房租 ¥2200.00'), '居住');
T('肯德基', detectCategory('肯德基 ¥36.00'), '外卖');
T('12306', detectCategory('12306 高铁票 ¥553.00'), '交通');
T('海底捞', detectCategory('海底捞火锅 ¥268.00'), '餐饮');
T('药店', detectCategory('药店购药 ¥25.00'), '医疗');
T('话费', detectCategory('话费充值 ¥100.00'), '通讯');
T('红包', detectCategory('红包 ¥200.00'), '人情');
T('书店', detectCategory('新华书店 ¥45.00'), '学习');
T('万达影城', detectCategory('万达影城 ¥40.00'), '娱乐');
T('收款方 王小明（人）', detectCategory('收款方 王小明\n转账 ¥66.00'), '其他');
T('商户名称 中国移动', detectCategory('商户名称 中国移动\n¥50.00'), '通讯');

console.log('== 退款判断 ==');
T('退款成功', isRefund('微信支付 退款成功 ¥6.00'), true);
T('原路退回', isRefund('已退款 原路退回 ¥38.50'), true);
T('退货', isRefund('退货退款 已到账'), true);
T('正常购买', isRefund('美团外卖 ¥26.00 已支付'), false);

console.log('== 日期 ==');
T('横杠日期', extractDate('交易时间 2026-08-01 20:15'), '2026-08-01');
T('斜杠日期', extractDate('2026/8/1'), '2026-08-01');
T('中文日期', extractDate('2026年8月1日 12:30'), '2026-08-01');
T('无日期', extractDate('美团外卖 ¥26.00'), '');
T('非法日期', extractDate('2026-13-99'), '');

console.log('== 备注 ==');
T('收款方标签', cleanNoteLine('收款方 美团外卖\n支付金额 ¥26.00', 26), '美团外卖');
T('交易对方标签', cleanNoteLine('交易对方 王小明\n转账 ¥66.00', 66), '王小明');
T('商户名称标签', cleanNoteLine('商户名称 罗森便利店\n¥15.80', 15.8), '罗森便利店');
T('备注标签', cleanNoteLine('转账成功\n备注: 请客吃饭\n¥200.00', 200), '请客吃饭');
T('金额行邻居', cleanNoteLine('已支付 ¥6.00\n美团外卖\n合计 6.00元', 6), '美团外卖');
T('无金额原文', cleanNoteLine('没有任何金额的文字', null), '没有任何金额的文字');

console.log('== 金额校验 ==');
T('toAmt 6.005', toAmt('6.005'), 6.01);
T('toAmt 1e27', toAmt('1e27'), null);
T('toAmt 0', toAmt('0'), null);

console.log('== 豆包 JSON 解析 ==');
T('纯 JSON', parseAiJson('{"amt":"6","cat":"外卖"}').amt, '6');
T('代码块 JSON', parseAiJson('```json\n{"amt":"6","cat":"外卖"}\n```').cat, '外卖');
T('夹带 JSON', parseAiJson('好的：{"amt":"12.5","cat":"交通"} 请查收').amt, '12.5');
T('乱码', parseAiJson('无法识别'), null);

console.log('\n结果：' + pass + ' 通过，' + fail + ' 失败');
process.exit(fail ? 1 : 0);
