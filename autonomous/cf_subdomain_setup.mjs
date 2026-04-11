#!/usr/bin/env node
// autonomous/cf_subdomain_setup.mjs
//
// Cloudflare workers.dev サブドメインを自動で取得 or 登録する。
// 成功時: 登録済みサブドメイン名を stdout に出力、exit 0
// 失敗時: エラーメッセージを stderr に出力、exit 1
//
// 環境変数:
//   CLOUDFLARE_API_TOKEN (必須)
//   WORKERS_SUBDOMAIN    (optional、登録したい名前を指定)
//
// 使い方:
//   export CLOUDFLARE_API_TOKEN=cfut_...
//   node autonomous/cf_subdomain_setup.mjs
//   # stdout: your-subdomain

const TOKEN = process.env.CLOUDFLARE_API_TOKEN;
if (!TOKEN) {
  console.error('[cf_subdomain] CLOUDFLARE_API_TOKEN is not set');
  process.exit(1);
}

const CF = 'https://api.cloudflare.com/client/v4';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json',
};

async function cfGet(path) {
  const res = await fetch(CF + path, { headers });
  const text = await res.text();
  try { return { status: res.status, json: JSON.parse(text) }; }
  catch { return { status: res.status, json: null, raw: text }; }
}

async function cfPut(path, body) {
  const res = await fetch(CF + path, {
    method: 'PUT',
    headers,
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try { return { status: res.status, json: JSON.parse(text) }; }
  catch { return { status: res.status, json: null, raw: text }; }
}

function log(msg) { console.error(`[cf_subdomain] ${msg}`); }

// ─── 1. アカウント ID 取得 ───
const acc = await cfGet('/accounts');
if (!acc.json?.success || !acc.json.result?.[0]?.id) {
  log('could not fetch account list');
  log('response: ' + JSON.stringify(acc.json || acc.raw).slice(0, 300));
  process.exit(1);
}
const accountId = acc.json.result[0].id;
log(`account ID: ${accountId}`);

// ─── 2. 現在のサブドメイン確認 ───
const sub = await cfGet(`/accounts/${accountId}/workers/subdomain`);
const existing = sub.json?.result?.subdomain;
if (existing) {
  log(`existing subdomain: ${existing}.workers.dev`);
  // stdout: accountId <TAB> subdomain
  process.stdout.write(`${accountId}\t${existing}\n`);
  process.exit(0);
}

// ─── 3. 新規登録 ───
function randomName() {
  if (process.env.WORKERS_SUBDOMAIN) return process.env.WORKERS_SUBDOMAIN;
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let suffix = '';
  for (let i = 0; i < 6; i++) suffix += chars[Math.floor(Math.random() * chars.length)];
  return `toyama-ai-${suffix}`;
}

let registered = null;
for (let attempt = 1; attempt <= 4; attempt++) {
  const name = attempt === 1 ? randomName() : `toyama-ai-${Date.now().toString(36).slice(-6)}-${attempt}`;
  log(`registering subdomain (attempt ${attempt}): ${name}`);
  const put = await cfPut(`/accounts/${accountId}/workers/subdomain`, { subdomain: name });
  if (put.json?.success) {
    registered = name;
    log(`✓ registered: ${name}.workers.dev`);
    break;
  }
  const err = put.json?.errors?.[0];
  log(`registration failed: ${err?.code || '?'} ${err?.message || '(no detail)'}`);
  if (err?.code === 10033 || err?.message?.toLowerCase().includes('already') || err?.message?.toLowerCase().includes('taken')) {
    continue; // 名前衝突、リトライ
  }
  // その他のエラーは致命的
  log('full response: ' + JSON.stringify(put.json || put.raw).slice(0, 500));
  process.exit(1);
}

if (!registered) {
  log('all registration attempts exhausted');
  log(`manually register at: https://dash.cloudflare.com/${accountId}/workers/onboarding`);
  process.exit(1);
}

// stdout: accountId <TAB> subdomain
process.stdout.write(`${accountId}\t${registered}\n`);
process.exit(0);
