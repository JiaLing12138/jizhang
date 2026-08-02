// 记账 · Scriptable 本地版（数据存 iCloud Drive/Scriptable/记账数据.json）
// 由快捷指令「记账OCR本地版」用 scriptable:///run/记账?clip=1 拉起，也可手动运行。

const D = importModule('记账数据');

function pagePath() {
  const fm = D.fileManager();
  return fm.documentsDirectory() + '/记账页面.html';
}

function readPage() {
  try {
    const fm = D.fileManager();
    const p = pagePath();
    if (!fm.fileExists(p)) return null;
    return fm.readString(p);
  } catch (e) { return null; }
}

async function run(qp) {
  qp = qp || {};
  const isQuick = qp.clip === '1';
  let ocrText = '';
  if (isQuick) {
    try { ocrText = Pasteboard.getString() || ''; } catch (e) {}
  }

  let html = readPage();
  if (!html) {
    const a = new Alert();
    a.title = '缺少页面文件';
    a.message = '没找到 记账页面.html。请确认它在 Scriptable 的 iCloud 文件夹里（文件 App → iCloud 云盘 → Scriptable）。';
    a.addAction('好');
    await a.present();
    return;
  }

  const state = D.loadState();
  const safeState = JSON.stringify(state).replace(/</g, '\\u003c');
  const safeOcr = JSON.stringify(ocrText || '').replace(/</g, '\\u003c');
  html = html.replace('/*__STATE__*/null', safeState).replace("/*__OCR__*/''", safeOcr);

  const wv = new WebView();
  wv.onShouldStartLoad = (req) => {
    const url = (req && req.url) || '';
    if (url.indexOf('scriptable://save') === 0) {
      wv.evaluateJavaScript("document.getElementById('__out').value").then((payload) => {
        try {
          const st = JSON.parse(payload);
          D.saveState({ records: st.records || [], savings: st.savings || [], accounts: st.accounts || [], assets: st.assets || [] });
        } catch (e) { console.log('save error: ' + e); }
      });
      return false;
    }
    if (url.indexOf('scriptable://backup') === 0) {
      wv.evaluateJavaScript("document.getElementById('__out').value").then((payload) => {
        try {
          const st = JSON.parse(payload);
          const p = D.backupToFile(st);
          const a = new Alert();
          a.title = '已备份';
          a.message = p ? ('备份已保存到：\n' + p + '\n\n在 iPhone 的 文件 App → iCloud 云盘 → Scriptable 里可以找到。') : '备份失败（写入出错）。';
          a.addAction('好');
          a.present();
        } catch (e) { console.log('backup error: ' + e); }
      });
      return false;
    }
    if (url.indexOf('scriptable://import') === 0) {
      (async () => {
        try {
          const dp = new DocumentPicker(['public.json']);
          const fileUrl = await dp.pickFile();
          const data = dp.getFileData(fileUrl);
          const text = data ? data.toRawString() : '';
          const parsed = JSON.parse(text);
          if (!parsed || typeof parsed !== 'object') throw new Error('bad format');
          const safe = JSON.stringify(parsed).replace(/</g, '\\u003c');
          await wv.evaluateJavaScript('window.__importFromScriptable(' + safe + ')');
        } catch (e) { console.log('import error: ' + e); }
      })();
      return false;
    }
    return true;
  };

  await wv.loadHTML(html, null);
  await wv.present();
}

module.exports = {
  run: run,
  runQuick: function () { return run({ clip: '1' }); }
};

/* 直接运行（手动点开或 scriptable:///run/记账）才执行；被其他脚本 import 时不自动执行 */
if (config.scriptName === '记账') {
  run(args.queryParameters || {});
}
