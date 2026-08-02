// 记账 · Scriptable 本地版（页面已内嵌，无需外部 html 文件）
// 模板文件：scripts/build_scriptable_bundle.py 会把 记账页面.html 以 base64 注入后生成 记账.js

const PAGE_HTML_B64 = /*__PAGE_B64__*/'';

let D = null;
try { D = importModule('记账数据'); } catch (e) { D = null; }

function logLine(s) {
  try {
    const fm = FileManager.local();
    const p = fm.documentsDirectory() + '/记账运行日志.txt';
    const old = fm.fileExists(p) ? fm.readString(p) : '';
    fm.writeString(p, old + new Date().toISOString() + '  ' + s + '\n');
  } catch (e) {}
}

function alertMsg(title, msg) {
  const a = new Alert();
  a.title = title || '';
  a.message = msg || '';
  a.addAction('好');
  return a.present();
}

function decodePage() {
  if (!PAGE_HTML_B64) return { ok: false, why: 'empty' };
  try {
    const d = Data.fromBase64String(PAGE_HTML_B64);
    return { ok: true, html: d.toRawString() };
  } catch (e) { logLine('decode err ' + e); return { ok: false, why: String((e && e.message) || e) }; }
}

async function run(qp) {
  qp = qp || {};
  logLine('start clip=' + (qp.clip || ''));

  if (!D) {
    await alertMsg('缺少模块', '没找到 记账数据.js。请确认它在 Scriptable 的 iCloud 文件夹里（文件 App → iCloud 云盘 → Scriptable）。');
    return;
  }

  const isQuick = qp.clip === '1';
  let ocrText = '';
  if (isQuick) {
    try { ocrText = Pasteboard.getString() || ''; } catch (e) {}
  }
  logLine('ocr=' + (ocrText ? ocrText.length : 0));

  const dec = decodePage();
  let html = dec.ok ? dec.html : null;
  if (!html) {
    // 兜底：如果内嵌为空，再试着直接从 iCloud 读页面文件（可能之前没同步下来）
    try {
      const fm = D.fileManager();
      const p = fm.documentsDirectory() + '/记账页面.html';
      if (fm.fileExists(p)) html = fm.readString(p);
    } catch (e) {}
  }
  if (!html) {
    await alertMsg('页面丢失',
      '内嵌数据状态：' + dec.why + '。\n\n如果是 empty：手机上还是旧版缓存，请把 Scriptable 完全关掉重开再试。\n如果仍不行，把 文件App → 我的iPhone → Scriptable → 记账运行日志.txt 的内容发我。');
    return;
  }

  let state;
  try { state = D.loadState(); } catch (e) { state = null; logLine('state err ' + e); }
  if (!state) state = D.defaultState();
  const safeState = JSON.stringify(state).replace(/</g, '\\u003c');
  const safeOcr = JSON.stringify(ocrText || '').replace(/</g, '\\u003c');
  html = html.replace('/*__STATE__*/null', safeState).replace("/*__OCR__*/''", safeOcr);
  logLine('html=' + html.length);

  const wv = new WebView();
  wv.onShouldStartLoad = (req) => {
    const url = (req && req.url) || '';
    if (url.indexOf('scriptable://save') === 0) {
      wv.evaluateJavaScript("document.getElementById('__out').value").then((payload) => {
        try {
          const st = JSON.parse(payload);
          D.saveState({ records: st.records || [], savings: st.savings || [], accounts: st.accounts || [], assets: st.assets || [] });
          logLine('saved');
        } catch (e) { logLine('save err ' + e); }
      });
      return false;
    }
    if (url.indexOf('scriptable://backup') === 0) {
      wv.evaluateJavaScript("document.getElementById('__out').value").then((payload) => {
        try {
          const st = JSON.parse(payload);
          const p = D.backupToFile(st);
          alertMsg('已备份', p ? ('备份已保存到：\n' + p + '\n\n在 iPhone 的 文件 App → iCloud 云盘 → Scriptable 里可以找到。') : '备份失败（写入出错）。');
        } catch (e) { logLine('backup err ' + e); }
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
        } catch (e) { logLine('import err ' + e); }
      })();
      return false;
    }
    return true;
  };

  try {
    await wv.loadHTML(html, null);
    logLine('loaded');
  } catch (e) {
    logLine('loadHTML err ' + e);
    try {
      const fm = FileManager.local();
      const tmp = fm.documentsDirectory() + '/记账运行.html';
      fm.writeString(tmp, html);
      await wv.loadFile(tmp);
      logLine('loaded via file');
    } catch (e2) {
      logLine('loadFile err ' + e2);
      await alertMsg('加载界面出错', String((e2 && e2.message) || e2));
      return;
    }
  }

  try { await wv.present(); logLine('presented'); }
  catch (e) { logLine('present err ' + e); }
}

/* 无论从 App 里点开、小组件、还是快捷指令拉起，都直接执行 */
run((args && args.queryParameters) || {}).catch(function (e) {
  logLine('fatal ' + e);
  try {
    alertMsg('记账出错了', String((e && e.message) || e));
  } catch (e2) {}
});
