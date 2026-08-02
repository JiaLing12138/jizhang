// 记账数据 + OCR 识别规则（Scriptable 共享模块）
// 纯规则部分可在 node 中 require 测试；文件 IO 部分依赖 Scriptable。

var CAT_EXP=['餐饮','外卖','咖啡茶饮','交通','打车','加油','购物','超市','网购','服饰','居住','水电燃气','医疗','娱乐','学习','通讯','人情','其他'];
var CAT_INC=['工资','兼职','理财','红包','报销','退款','其他'];
var CAT_ASSET=['电子设备','家具家电','交通工具','珠宝首饰','其他'];

function uid(){ return Date.now().toString(36) + Math.random().toString(36).slice(2,7); }
function fmt(n){ n=Number(n)||0; var s=(n<0?'-':''); n=Math.abs(n); var f=n.toFixed(2); f=f.replace(/\B(?=(\d{3})+(?!\d))/g,','); return s+f; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
function today(){ var d=new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function nowTime(){ var d=new Date(); return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'); }
function curMonth(){ var d=new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0'); }
function monthKey(d){ return (d||'').slice(0,7); }

/* 金额统一校验：>0、<1000 万（防科学计数法/单号误入，如 4.2e27）、保留两位小数 */
function toAmt(v){
  var n=parseFloat(v);
  if(!isFinite(n)||n<=0||n>=1e7) return null;
  return Math.round(n*100)/100;
}

function extractAmount(text){
  var clean=String(text).replace(/[0-9]{11,}/g,' ').replace(/[,，]/g,'');
  var kw=['实付','应付','实收','退款','到账','支付','付款','消费','金额','合计','总计','共计','小计','收款','转入','转账'];
  var i,m,v;
  for(i=0;i<kw.length;i++){
    var k=kw[i];
    m=clean.match(new RegExp(k+'[^0-9¥\\-]{0,6}?¥\\s*[-+]?\\s*[0-9]+(?:\\.[0-9]{1,2})?'));
    if(m){ v=Math.abs(parseFloat(m[0].replace(/[^0-9.]/g,''))); if(v>0&&v<1e7) return v; }
    m=clean.match(new RegExp(k+'[^0-9¥\\-]{0,6}?([0-9]+\\.[0-9]{1,2})'));
    if(m){ v=Math.abs(parseFloat(m[1])); if(v>0&&v<1e7) return v; }
  }
  m=clean.match(/¥\s*[-+]?\s*([0-9]+(?:\.[0-9]{1,2})?)/);
  if(m){ v=Math.abs(parseFloat(m[1])); if(v>0&&v<1e7) return v; }
  m=clean.match(/([0-9]+(?:\.[0-9]{1,2})?)/);
  if(m){ v=parseFloat(m[1]); if(v>0&&v<1e7) return v; }
  return null;
}

function extractDate(text){
  var m=String(text).match(/(20\d{2})[年\/\-\.](0?[1-9]|1[0-2])[月\/\-\.](0?[1-9]|[12]\d|3[01])[日]?/);
  if(!m) return '';
  var y=+m[1], mo=+m[2], d=+m[3];
  if(mo<1||mo>12||d<1||d>31) return '';
  return y+'-'+String(mo).padStart(2,'0')+'-'+String(d).padStart(2,'0');
}

function cleanNoteLine(text, amt){
  var t=String(text), amtStr = amt!=null ? String(amt) : '';
  var lines=t.split(/\r?\n/);
  var m, i;
  for(i=0;i<lines.length;i++){
    m=lines[i].match(/收款方[：:]?\s*([^\s]{1,30})/);
    if(m && m[1]) return m[1].slice(0,50);
  }
  for(i=0;i<lines.length;i++){
    m=lines[i].match(/交易对方[：:]?\s*([^\s]{1,30})/);
    if(m && m[1]) return m[1].slice(0,50);
  }
  for(i=0;i<lines.length;i++){
    m=lines[i].match(/商户名称?[：:]?\s*([^\s]{1,30})/);
    if(m && m[1]) return m[1].slice(0,50);
  }
  for(i=0;i<lines.length;i++){
    m=lines[i].match(/备注[：:]?\s*([^\s]{1,30})/);
    if(m && m[1]) return m[1].slice(0,50);
  }
  var idx=-1;
  for(i=0;i<lines.length;i++){
    var L=lines[i];
    if((amtStr && L.indexOf(amtStr)>=0) || /¥|([0-9]+\.[0-9]{1,2})/.test(L)){ idx=i; break; }
  }
  if(idx<0) return t.slice(0,200);
  var order=[idx];
  if(idx>0) order.push(idx-1);
  if(idx+1<lines.length) order.push(idx+1);
  if(idx+2<lines.length) order.push(idx+2);
  var NOISE=/微信支付|支付宝|已支付|支付成功|交易成功|收款方|付款方|订单号|交易单号|商户单号|商户|转账成功|完成|备注|合计|总计|共计|小计|实付|应付|支付|金额|消费|付款方式|交易时间|零钱|余额|银行卡|信用卡|花呗|云闪付|储蓄卡|优惠|商品/g;
  for(var n=0;n<order.length;n++){
    var s=lines[order[n]].replace(/[0-9]{11,}/g,' ')
           .replace(/¥\s*[0-9]+(?:\.[0-9]{1,2})?/g,' ')
           .replace(/[0-9]+\.[0-9]{1,2}/g,' ')
           .replace(NOISE,' ')
           .replace(/\s+/g,' ').trim();
    if(s) return s.slice(0,50);
  }
  return '';
}

var MERCHANT={ '餐饮':['餐厅','饭店','火锅','烧烤','小吃','食堂','面馆','日料','西餐','炒菜','快餐','酒楼','海底捞','呷哺','西贝','外婆家','太二','老乡鸡','真功夫','必胜客','萨莉亚','吉野家'],
  '外卖':['美团','饿了么','外卖','肯德基','麦当劳','汉堡','披萨','炸鸡'],
  '咖啡茶饮':['咖啡','星巴克','瑞幸','奶茶','喜茶','奈雪','茶百道','蜜雪冰城','柠檬茶','饮品'],
  '交通':['地铁','公交','高铁','12306','机票','铁路','城际','轮渡'],
  '打车':['滴滴','出租车','打车','T3','花小猪','曹操出行','高德出行'],
  '加油':['加油','中石化','中石油','加油站','壳牌'],
  '购物':['商城','百货','商场','屈臣氏','名创优品','无印良品','MUJI'],
  '超市':['超市','便利店','沃尔玛','永辉','盒马','山姆','罗森','全家','7-11','物美','大润发'],
  '网购':['京东','淘宝','天猫','拼多多','唯品会','抖音','快手','闲鱼','小红书','网购'],
  '服饰':['服饰','服装','鞋','裤','衣','优衣库','HM','H&M','ZARA','安踏','耐克','阿迪','背包','挎包'],
  '居住':['房租','物业','家政','维修','中介','自如'],
  '水电燃气':['水电','水费','电费','燃气','天然气','供暖'],
  '医疗':['医院','药店','药房','诊所','挂号','体检','医疗','卫生所','门诊'],
  '娱乐':['电影','影院','影城','万达','KTV','游戏','视频会员','演出','门票','游乐园','健身','KEEP','桌游','酒吧'],
  '学习':['书','课程','培训','学校','教育','网课','知乎','得到','文具'],
  '通讯':['话费','流量','宽带','电信','移动','联通','充值'],
  '人情':['红包','送礼','份子','礼金','请客','随礼'] };
var LINEKW={ '餐饮':['餐','饭','菜','面','食'], '外卖':['外卖','美团','饿了么','汉堡'],
  '咖啡茶饮':['咖啡','奶茶','茶饮'], '交通':['地铁','公交','车费','高铁'],
  '打车':['打车','滴滴','出租'], '加油':['加油','油费'],
  '购物':['买','购','商品'], '超市':['超市','便利店'],
  '网购':['下单','网购'], '服饰':['衣','鞋','裤'],
  '居住':['房租','物业'], '水电燃气':['电费','水费','燃气'],
  '医疗':['药','医'], '娱乐':['玩','乐','电影','健身'],
  '学习':['书','课'], '通讯':['话费','流量'],
  '人情':['红包','礼'] };
function detectCategory(text){
  var t=String(text);
  var m=t.match(/收款方[：:]\s*([^\s]{1,30})/)||t.match(/交易对方[：:]\s*([^\s]{1,30})/)||t.match(/商户名称?[：:]\s*([^\s]{1,30})/);
  var label=m?m[1]:'';
  if(label){ for(var cat in MERCHANT){ if(MERCHANT[cat].some(function(k){return label.indexOf(k)>=0;})) return cat; } }
  for(var c2 in MERCHANT){ if(MERCHANT[c2].some(function(k){return t.indexOf(k)>=0;})) return c2; }
  var lines=t.split(/\r?\n/);
  for(var i=0;i<lines.length;i++){ for(var c in LINEKW){ if(LINEKW[c].some(function(k){return lines[i].indexOf(k)>=0;})) return c; } }
  return '其他';
}

function isRefund(text){
  return /退款|退货|退票|退费|原路退回|已退/.test(text);
}

/* ---------- 汇总与账户 ---------- */
function summary(records){
  var cm=curMonth(); var exp=0, inc=0;
  (records||[]).forEach(function(r){
    if((r.date||'').slice(0,7)!==cm) return;
    if(r.major==='inc') inc += Number(r.amt)||0;
    else if(r.major==='exp') exp += Number(r.amt)||0;
  });
  return {exp:exp, inc:inc, net:inc-exp};
}
function svNet(sv){ return (sv.logs||[]).reduce(function(s,l){ return s + (l.type==='in'? Number(l.amt): -Number(l.amt)); },0); }
function loanPaid(sv){
  if(!sv.loan || !sv.loan.startMonth) return 0;
  var paid = monthDiff(sv.loan.startMonth, curMonth()) + (sv.loan.offset||0);
  return Math.max(0, Math.min(paid, sv.loan.totalMonths));
}
function monthDiff(a,b){
  var p=String(a).split('-'), q=String(b).split('-');
  return ((+q[0])*12+(+(q[1]||1))-1) - ((+p[0])*12+(+(p[1]||1))-1);
}

/* ---------- Scriptable 文件 IO（仅 Scriptable 环境可调用） ---------- */
var _fm=null; var _storage='iCloud';
function fileManager(){
  if(_fm) return _fm;
  try{
    var fm=FileManager.iCloud();
    var d=fm.documentsDirectory();
    if(d && fm.isUbiquitousItemAtPath && fm.isUbiquitousItemAtPath(d)){ _fm=fm; _storage='iCloud'; return _fm; }
  }catch(e){}
  _fm=FileManager.local(); _storage='local'; return _fm;
}
function storageName(){ fileManager(); return _storage; }
function dataPath(){ return fileManager().documentsDirectory() + '/记账数据.json'; }
function defaultState(){ return {records:[], savings:[], accounts:[], assets:[]}; }
function loadState(){
  try{
    var fm=fileManager(); var p=dataPath();
    if(fm.fileExists(p)){
      var d=JSON.parse(fm.readString(p));
      if(d && typeof d==='object') return d;
    }
  }catch(e){}
  return defaultState();
}
function saveState(st){
  try{ fileManager().writeString(dataPath(), JSON.stringify(st||defaultState())); return true; }catch(e){ return false; }
}
function backupToFile(st){
  try{
    var fm=fileManager();
    var p=fm.documentsDirectory()+'/记账备份_'+today()+'.json';
    fm.writeString(p, JSON.stringify({schemaVersion:1, exportedAt:new Date().toISOString(),
      records:(st&&st.records)||[], savings:(st&&st.savings)||[], accounts:(st&&st.accounts)||[], assets:(st&&st.assets)||[]}, null, 2));
    return p;
  }catch(e){ return ''; }
}

module.exports = {
  CAT_EXP: CAT_EXP, CAT_INC: CAT_INC, CAT_ASSET: CAT_ASSET,
  uid: uid, fmt: fmt, esc: esc, today: today, nowTime: nowTime, curMonth: curMonth, monthKey: monthKey,
  toAmt: toAmt, extractAmount: extractAmount, extractDate: extractDate, cleanNoteLine: cleanNoteLine,
  detectCategory: detectCategory, isRefund: isRefund,
  summary: summary, svNet: svNet, loanPaid: loanPaid, monthDiff: monthDiff,
  fileManager: fileManager, storageName: storageName, dataPath: dataPath,
  defaultState: defaultState, loadState: loadState, saveState: saveState, backupToFile: backupToFile
};
