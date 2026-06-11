/**
 * pipeline_server.mjs — iPhone操作対応パイプラインサーバー
 *
 * 起動: node pipeline_server.mjs
 * PORT: 環境変数 PIPELINE_PORT（デフォルト3001）
 * 認証: 環境変数 PIPELINE_TOKEN（必須）
 *
 * エンドポイント:
 *   GET  /          → iPhone操作パネル（HTML）
 *   GET  /status    → パイプライン稼働状況
 *   POST /search    → 案件検索フェーズ開始
 *   POST /deliver   → 納品フェーズ開始
 *   GET  /results   → 最新の案件・評価結果
 *   GET  /log       → 実行ログ（最新100行）
 */

import { createServer } from 'node:http';
import { spawn }        from 'node:child_process';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const PORT    = process.env.PIPELINE_PORT || 3001;
const HOST    = '0.0.0.0';                          // iPhone からアクセス可能にする
const TOKEN   = process.env.PIPELINE_TOKEN || '';
const __dir   = dirname(fileURLToPath(import.meta.url));
const PIPELINE_DIR = join(__dir, 'projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline');
const OUTPUT_DIR   = join(__dir, 'projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/outputs');

// ─────────────────────────────────────────────
// 状態管理
// ─────────────────────────────────────────────
const state = {
  status: 'idle',       // idle | running | done | error
  phase:  '',           // search | deliver
  log:    [],           // 実行ログ
  startedAt: null,
  finishedAt: null,
  lastResults: null,
};

function addLog(line) {
  const entry = `[${new Date().toLocaleTimeString('ja-JP')}] ${line}`;
  state.log.push(entry);
  if (state.log.length > 200) state.log.shift();
  console.log(entry);
}

// ─────────────────────────────────────────────
// Pythonスクリプト実行
// ─────────────────────────────────────────────
function runPython(scriptArgs) {
  return new Promise((resolve, reject) => {
    const proc = spawn('python3', scriptArgs, {
      cwd: PIPELINE_DIR,
      env: { ...process.env },
    });
    proc.stdout.on('data', d => d.toString().split('\n').filter(Boolean).forEach(addLog));
    proc.stderr.on('data', d => d.toString().split('\n').filter(Boolean).forEach(l => addLog(`[ERR] ${l}`)));
    proc.on('close', code => code === 0 ? resolve() : reject(new Error(`exit ${code}`)));
  });
}

// ─────────────────────────────────────────────
// 最新の結果ファイルを取得
// ─────────────────────────────────────────────
function getLatestResults() {
  try {
    const files = readdirSync(OUTPUT_DIR)
      .filter(f => f.endsWith('_evaluated.json') || f.endsWith('_applications.json'))
      .map(f => ({ name: f, mtime: statSync(join(OUTPUT_DIR, f)).mtime }))
      .sort((a, b) => b.mtime - a.mtime);
    if (!files.length) return null;
    return JSON.parse(readFileSync(join(OUTPUT_DIR, files[0].name), 'utf-8'));
  } catch { return null; }
}

// ─────────────────────────────────────────────
// ヘルパー
// ─────────────────────────────────────────────
function json(res, status, body) {
  const payload = JSON.stringify(body, null, 2);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(payload),
    'Access-Control-Allow-Origin': '*',
  });
  res.end(payload);
}

function html(res, content) {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(content);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end',  () => resolve(Buffer.concat(chunks).toString()));
    req.on('error', reject);
  });
}

function checkAuth(req, res) {
  if (!TOKEN) return true;                          // TOKEN未設定なら認証スキップ
  const auth = req.headers['authorization'] || '';
  const t    = new URL(`http://x${req.url}`).searchParams.get('token') || '';
  if (auth === `Bearer ${TOKEN}` || t === TOKEN) return true;
  json(res, 401, { error: 'Unauthorized' });
  return false;
}

// ─────────────────────────────────────────────
// iPhone操作パネル（HTML）
// ─────────────────────────────────────────────
function renderPanel() {
  const tokenParam = TOKEN ? `?token=${TOKEN}` : '';
  return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <title>パイプライン操作パネル</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #f2f2f7; color: #1c1c1e; }
    .header { background: #1c1c1e; color: #fff; padding: 20px 16px 16px; }
    .header h1 { font-size: 20px; font-weight: 700; }
    .header p  { font-size: 13px; color: #8e8e93; margin-top: 4px; }
    .status-bar { background: #fff; padding: 12px 16px; border-bottom: 1px solid #e5e5ea;
                  display: flex; align-items: center; gap: 10px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #34c759; }
    .dot.running { background: #ff9f0a; animation: pulse 1s infinite; }
    .dot.error   { background: #ff3b30; }
    .dot.idle    { background: #8e8e93; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
    .status-text { font-size: 14px; font-weight: 500; }
    .section { padding: 16px; }
    .section h2 { font-size: 13px; color: #8e8e93; text-transform: uppercase;
                  letter-spacing: .5px; margin-bottom: 10px; }
    .card { background: #fff; border-radius: 12px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,.08); }
    .btn { display: flex; align-items: center; padding: 16px;
           border: none; background: none; width: 100%; text-align: left;
           border-bottom: 1px solid #f2f2f7; cursor: pointer; }
    .btn:last-child { border-bottom: none; }
    .btn-icon { width: 36px; height: 36px; border-radius: 8px;
                display: flex; align-items: center; justify-content: center;
                font-size: 18px; margin-right: 12px; flex-shrink: 0; }
    .btn-icon.blue   { background: #e1f0ff; }
    .btn-icon.green  { background: #e3f9e5; }
    .btn-icon.orange { background: #fff3e0; }
    .btn-text h3 { font-size: 15px; font-weight: 600; }
    .btn-text p  { font-size: 13px; color: #8e8e93; margin-top: 2px; }
    .btn-arrow { margin-left: auto; color: #c7c7cc; font-size: 16px; }
    .log-box { background: #1c1c1e; color: #30d158; border-radius: 12px;
               padding: 14px; font-family: monospace; font-size: 12px;
               max-height: 220px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
    .results { margin-top: 8px; }
    .job-card { background: #fff; border-radius: 12px; padding: 14px; margin-bottom: 10px;
                box-shadow: 0 1px 3px rgba(0,0,0,.08); }
    .job-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
    .job-meta  { font-size: 12px; color: #8e8e93; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 20px;
             font-size: 11px; font-weight: 700; margin-right: 6px; }
    .badge.go      { background: #e3f9e5; color: #1a7f37; }
    .badge.caution { background: #fff3e0; color: #b45309; }
    .badge.nogo    { background: #ffeaea; color: #c0392b; }
    .toast { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
             background: #1c1c1e; color: #fff; padding: 10px 20px; border-radius: 20px;
             font-size: 14px; opacity: 0; transition: opacity .3s; pointer-events: none; }
    .toast.show { opacity: 1; }
    #loading { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.4);
               align-items: center; justify-content: center; z-index: 100; }
    #loading.show { display: flex; }
    .spinner { width: 40px; height: 40px; border: 4px solid #fff3;
               border-top-color: #fff; border-radius: 50%; animation: spin .8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="header">
    <h1>🤖 パイプライン操作</h1>
    <p>データ入力・スクレイピング自動化</p>
    <p style="margin-top:6px"><a href="/tavern" style="color:#0a84ff;font-size:13px;text-decoration:none">🍺 ルイーダの酒場（役員に仕事をたのむ）›</a></p>
  </div>

  <div class="status-bar" id="statusBar">
    <div class="dot idle" id="statusDot"></div>
    <span class="status-text" id="statusText">待機中</span>
  </div>

  <div class="section">
    <h2>操作</h2>
    <div class="card">
      <button class="btn" onclick="triggerSearch()">
        <div class="btn-icon blue">🔍</div>
        <div class="btn-text">
          <h3>案件を検索・評価</h3>
          <p>クラウドワークス・ランサーズを検索して自動評価</p>
        </div>
        <span class="btn-arrow">›</span>
      </button>
      <button class="btn" onclick="triggerDeliver()">
        <div class="btn-icon green">📦</div>
        <div class="btn-text">
          <h3>作業実行・納品準備</h3>
          <p>受注後の作業・念査・納品文生成</p>
        </div>
        <span class="btn-arrow">›</span>
      </button>
      <button class="btn" onclick="loadResults()">
        <div class="btn-icon orange">📋</div>
        <div class="btn-text">
          <h3>結果を確認</h3>
          <p>最新の評価結果・応募文を表示</p>
        </div>
        <span class="btn-arrow">›</span>
      </button>
    </div>
  </div>

  <div class="section">
    <h2>実行ログ</h2>
    <div class="log-box" id="logBox">ログはここに表示されます...</div>
  </div>

  <div class="section" id="resultsSection" style="display:none">
    <h2>案件リスト</h2>
    <div class="results" id="resultsList"></div>
  </div>

  <div id="loading"><div class="spinner"></div></div>
  <div class="toast" id="toast"></div>

  <script>
    const TOKEN = '${TOKEN}';
    const headers = TOKEN
      ? { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN }
      : { 'Content-Type': 'application/json' };

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg; t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2500);
    }

    function setLoading(on) {
      document.getElementById('loading').classList.toggle('show', on);
    }

    async function updateStatus() {
      try {
        const r = await fetch('/status${tokenParam}');
        const d = await r.json();
        const dot  = document.getElementById('statusDot');
        const text = document.getElementById('statusText');
        dot.className = 'dot ' + d.status;
        const labels = { idle:'待機中', running:'実行中...', done:'完了', error:'エラー' };
        text.textContent = (labels[d.status] || d.status) + (d.phase ? ' — ' + d.phase : '');
        if (d.log?.length) {
          document.getElementById('logBox').textContent = d.log.slice(-50).join('\\n');
        }
      } catch(e) {}
    }

    async function triggerSearch() {
      if (!confirm('案件検索を開始しますか？（数分かかります）')) return;
      setLoading(true);
      try {
        const r = await fetch('/search', { method: 'POST', headers });
        const d = await r.json();
        showToast(d.ok ? '🔍 検索開始しました' : '❌ ' + d.error);
      } catch(e) { showToast('❌ 通信エラー'); }
      setLoading(false);
    }

    async function triggerDeliver() {
      if (!confirm('作業・納品フェーズを開始しますか？')) return;
      setLoading(true);
      try {
        const r = await fetch('/deliver', { method: 'POST', headers });
        const d = await r.json();
        showToast(d.ok ? '📦 納品準備開始' : '❌ ' + d.error);
      } catch(e) { showToast('❌ 通信エラー'); }
      setLoading(false);
    }

    async function loadResults() {
      setLoading(true);
      try {
        const r = await fetch('/results${tokenParam}');
        const jobs = await r.json();
        const sec  = document.getElementById('resultsSection');
        const list = document.getElementById('resultsList');
        if (!jobs?.length) { showToast('結果がまだありません'); setLoading(false); return; }
        list.innerHTML = jobs.slice(0,20).map(j => {
          const v = j.verdict || 'NO-GO';
          const cls = v === 'GO' ? 'go' : v === 'CAUTION' ? 'caution' : 'nogo';
          const price = j.estimated_price_jpy ? '¥' + j.estimated_price_jpy.toLocaleString() : '';
          return \`<div class="job-card">
            <div class="job-title">\${j.title || ''}</div>
            <div class="job-meta">
              <span class="badge \${cls}">\${v} \${j.total||0}点</span>
              \${price ? '<span>' + price + '</span>' : ''}
              <span> · \${j.platform||''}</span>
            </div>
            \${j.url ? '<div style="margin-top:8px"><a href="' + j.url + '" style="font-size:12px;color:#007aff">案件ページを開く ›</a></div>' : ''}
          </div>\`;
        }).join('');
        sec.style.display = 'block';
        sec.scrollIntoView({ behavior: 'smooth' });
      } catch(e) { showToast('❌ 取得エラー'); }
      setLoading(false);
    }

    // 5秒ごとに状態更新
    updateStatus();
    setInterval(updateStatus, 5000);
  </script>
</body>
</html>`;
}

// ─────────────────────────────────────────────
// ルーティング
// ─────────────────────────────────────────────
async function handleRequest(req, res) {
  const { method } = req;
  const urlObj = new URL(`http://x${req.url}`);
  const path   = urlObj.pathname;

  // HTML操作パネル
  if (method === 'GET' && path === '/') {
    return html(res, renderPanel());
  }

  // ルイーダの酒場（役員ダッシュボード）
  if (method === 'GET' && path === '/tavern') {
    try {
      return html(res, readFileSync(join(__dir, 'tavern.html'), 'utf-8'));
    } catch {
      return json(res, 404, { error: 'tavern.html not found' });
    }
  }

  // 状態確認（認証不要）
  if (method === 'GET' && path === '/status') {
    return json(res, 200, {
      status: state.status,
      phase:  state.phase,
      startedAt:  state.startedAt,
      finishedAt: state.finishedAt,
      log: state.log.slice(-50),
    });
  }

  if (!checkAuth(req, res)) return;

  // 案件検索フェーズ開始
  if (method === 'POST' && path === '/search') {
    if (state.status === 'running') {
      return json(res, 409, { error: '既に実行中です' });
    }
    state.status = 'running';
    state.phase  = 'search';
    state.startedAt = new Date().toISOString();
    state.log = [];
    addLog('案件検索フェーズ開始');
    json(res, 200, { ok: true, message: '検索を開始しました' });

    // バックグラウンドで実行
    runPython(['run_pipeline.py', 'search'])
      .then(() => { state.status = 'done'; state.finishedAt = new Date().toISOString(); addLog('✅ 完了'); })
      .catch(e => { state.status = 'error'; addLog(`❌ エラー: ${e.message}`); });
    return;
  }

  // 納品フェーズ開始
  if (method === 'POST' && path === '/deliver') {
    if (state.status === 'running') {
      return json(res, 409, { error: '既に実行中です' });
    }
    state.status = 'running';
    state.phase  = 'deliver';
    state.startedAt = new Date().toISOString();
    state.log = [];
    addLog('納品フェーズ開始');
    json(res, 200, { ok: true, message: '納品フェーズを開始しました' });

    runPython(['run_pipeline.py', 'deliver'])
      .then(() => { state.status = 'done'; state.finishedAt = new Date().toISOString(); addLog('✅ 完了'); })
      .catch(e => { state.status = 'error'; addLog(`❌ エラー: ${e.message}`); });
    return;
  }

  // 最新結果取得
  if (method === 'GET' && path === '/results') {
    const results = getLatestResults();
    return json(res, 200, results || []);
  }

  json(res, 404, { error: 'Not Found' });
}

// ─────────────────────────────────────────────
// 起動
// ─────────────────────────────────────────────
if (!TOKEN) {
  console.warn('⚠️  PIPELINE_TOKEN が未設定です。本番環境では必ず設定してください。');
  console.warn('   export PIPELINE_TOKEN=your-secret-token');
}

const server = createServer(async (req, res) => {
  const start = performance.now();
  try { await handleRequest(req, res); }
  catch (err) { json(res, 500, { error: 'Internal Server Error' }); }
  const ms = (performance.now() - start).toFixed(2);
  console.log(`${req.method} ${req.url} ${res.statusCode} ${ms}ms`);
});

server.listen(PORT, HOST, () => {
  console.log(`\n🤖 パイプラインサーバー起動`);
  console.log(`   http://localhost:${PORT}  （ローカル）`);
  console.log(`   http://[サーバーIP]:${PORT}  （iPhone からアクセス）`);
  if (TOKEN) console.log(`   トークン認証: 有効`);
});
