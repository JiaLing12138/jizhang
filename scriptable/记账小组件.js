// 记账 · 桌面小组件（本月支出/收入/结余 + 最近一笔）
// 用法：Scriptable 里长按运行一次（生成小组件），或加到桌面小组件选择本脚本。

const D = importModule('记账数据');

function buildWidget() {
  const st = D.loadState();
  const records = (st && st.records) || [];
  const cm = D.curMonth();
  let exp = 0, inc = 0, latest = null;
  records.forEach(function (r) {
    if ((r.date || '').slice(0, 7) === cm) {
      if (r.major === 'inc') inc += Number(r.amt) || 0;
      else if (r.major === 'exp') exp += Number(r.amt) || 0;
    }
    if (!latest || (r.date + ' ' + (r.time || '')) > (latest.date + ' ' + (latest.time || ''))) latest = r;
  });

  const w = new ListWidget();
  const grad = new LinearGradient();
  grad.colors = [new Color('#4453e0'), new Color('#7d8bff')];
  grad.locations = [0, 1];
  w.backgroundGradient = grad;
  w.setPadding(14, 14, 14, 14);

  const title = w.addText('本月账单');
  title.font = Font.boldSystemFont(13);
  title.textColor = Color.white();
  w.addSpacer(6);

  const line1 = w.addText('支出 ' + D.fmt(exp));
  line1.font = Font.boldSystemFont(22);
  line1.textColor = Color.white();
  const line2 = w.addText('收入 ' + D.fmt(inc) + ' · 结余 ' + D.fmt(inc - exp));
  line2.font = Font.mediumSystemFont(12);
  line2.textColor = new Color('#ffffff', 0.85);

  if (latest) {
    w.addSpacer(8);
    const lw = w.addText('最近：' + (latest.cat || '') + ' ' + D.fmt(latest.amt) + (latest.major === 'inc' ? '（收）' : ''));
    lw.font = Font.regularSystemFont(11);
    lw.textColor = new Color('#ffffff', 0.75);
    lw.lineLimit = 1;
  }

  w.url = 'scriptable:///run/记账';
  return w;
}

const widget = buildWidget();
Script.setWidget(widget);
if (!config.runsInWidget) {
  widget.presentMedium();
}
