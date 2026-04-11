// memory.mjs
// 自律ループの各役職の短期・長期記憶を管理する。
//
// 短期記憶 (short_term):
//   直近 N ターンの要約。毎ターン末に1エントリ追加される。
//   容量上限を超えたら古いものから捨てる。
//   プロンプトに注入されて、役職に "過去やったこと" のコンテキストを与える。
//
// 長期記憶 (long_term):
//   月次以上の粒度で圧縮された要約。短期の古いエントリから作られる。
//   Phase 2 時点では手動圧縮（CDO の meta review が後日実装）。
//
// 保存先:
//   autonomous/state/memory/<officer>.json

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const MEMORY_DIR = path.join(__dirname, 'state', 'memory');

// ─────────────────────────────────────────────────────────────
// 設定
// ─────────────────────────────────────────────────────────────

export const MEMORY_CONFIG = {
  shortTermLimit: 10,   // 短期記憶の保持件数（古い順に捨てる）
  shortTermChars: 200,  // 1エントリあたりの要約文字数上限
  longTermLimit: 24,    // 長期記憶の保持件数（月次換算で2年分）
};

// ─────────────────────────────────────────────────────────────
// ヘルパ
// ─────────────────────────────────────────────────────────────

function memoryFile(officer) {
  return path.join(MEMORY_DIR, `${officer}.json`);
}

function emptyMemory() {
  return {
    short_term: [],
    long_term: [],
    updated_at: null,
  };
}

async function loadMemory(officer) {
  const file = memoryFile(officer);
  if (!existsSync(file)) return emptyMemory();
  try {
    const content = await readFile(file, 'utf8');
    const parsed = JSON.parse(content);
    if (!Array.isArray(parsed.short_term)) parsed.short_term = [];
    if (!Array.isArray(parsed.long_term)) parsed.long_term = [];
    return parsed;
  } catch {
    return emptyMemory();
  }
}

async function saveMemory(officer, memory) {
  await mkdir(MEMORY_DIR, { recursive: true });
  memory.updated_at = new Date().toISOString();
  await writeFile(memoryFile(officer), JSON.stringify(memory, null, 2) + '\n', 'utf8');
}

function truncate(str, n) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n - 1) + '…' : str;
}

// ─────────────────────────────────────────────────────────────
// 公開 API
// ─────────────────────────────────────────────────────────────

/**
 * 役職の記憶を読み込んで、プロンプト向けの短文サマリを返す。
 * @param {string} officer
 * @returns {Promise<{ shortTerm: Array, longTerm: Array, raw: object }>}
 */
export async function recall(officer) {
  const mem = await loadMemory(officer);
  return {
    shortTerm: mem.short_term,
    longTerm: mem.long_term,
    raw: mem,
  };
}

/**
 * 1ターンの結果を短期記憶に1エントリ追加する。
 * @param {string} officer
 * @param {object} entry - { date, decision, rationale, artifactPath }
 */
export async function remember(officer, entry) {
  const mem = await loadMemory(officer);
  const compact = {
    date: entry.date || new Date().toISOString().slice(0, 10),
    decision: truncate(entry.decision || '', MEMORY_CONFIG.shortTermChars),
    rationale: truncate(entry.rationale || '', MEMORY_CONFIG.shortTermChars),
    artifact: entry.artifactPath || null,
  };
  mem.short_term.push(compact);
  // 古いものから捨てる
  if (mem.short_term.length > MEMORY_CONFIG.shortTermLimit) {
    mem.short_term = mem.short_term.slice(-MEMORY_CONFIG.shortTermLimit);
  }
  await saveMemory(officer, mem);
  return mem;
}

/**
 * プロンプトに注入しやすい形の短期記憶テキストを生成する。
 */
export function formatShortTermForPrompt(shortTerm) {
  if (!shortTerm || shortTerm.length === 0) {
    return '(短期記憶: まだなし)';
  }
  return shortTerm
    .map(e => `- ${e.date}: ${e.decision} (${e.artifact || 'no artifact'})`)
    .join('\n');
}

/**
 * 長期記憶の圧縮（月次）。Phase 2 では手動呼び出しのみ。
 * CDO の meta review で使う想定。
 */
export async function compressMonthly(officer, month) {
  const mem = await loadMemory(officer);
  // month = "YYYY-MM"
  const monthEntries = mem.short_term.filter(e => (e.date || '').startsWith(month));
  if (monthEntries.length === 0) {
    return { compressed: false, reason: 'no entries for month' };
  }
  const summary = {
    month,
    count: monthEntries.length,
    decisions: monthEntries.map(e => e.decision).slice(0, 20),
    created_at: new Date().toISOString(),
  };
  mem.long_term.push(summary);
  if (mem.long_term.length > MEMORY_CONFIG.longTermLimit) {
    mem.long_term = mem.long_term.slice(-MEMORY_CONFIG.longTermLimit);
  }
  await saveMemory(officer, mem);
  return { compressed: true, summary };
}

/**
 * 全役職の記憶サマリ（CLI / Review Dashboard 用）
 */
export async function allSummary(officers = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO']) {
  const out = {};
  for (const o of officers) {
    const mem = await loadMemory(o);
    out[o] = {
      shortTermCount: mem.short_term.length,
      longTermCount: mem.long_term.length,
      latestDecision: mem.short_term[mem.short_term.length - 1]?.decision || null,
      updated_at: mem.updated_at,
    };
  }
  return out;
}

// ─────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────
//
// node autonomous/memory.mjs summary
// node autonomous/memory.mjs show CDO
// node autonomous/memory.mjs compress CDO 2026-04

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  const cmd = process.argv[2] || 'summary';
  if (cmd === 'summary') {
    console.log(JSON.stringify(await allSummary(), null, 2));
  } else if (cmd === 'show') {
    const officer = process.argv[3];
    if (!officer) { console.error('usage: show <OFFICER>'); process.exit(1); }
    console.log(JSON.stringify(await recall(officer), null, 2));
  } else if (cmd === 'compress') {
    const officer = process.argv[3];
    const month = process.argv[4];
    if (!officer || !month) { console.error('usage: compress <OFFICER> <YYYY-MM>'); process.exit(1); }
    console.log(JSON.stringify(await compressMonthly(officer, month), null, 2));
  } else {
    console.error(`Unknown command: ${cmd}`);
    console.error('Usage: memory.mjs [summary|show <OFFICER>|compress <OFFICER> <YYYY-MM>]');
    process.exit(1);
  }
}
