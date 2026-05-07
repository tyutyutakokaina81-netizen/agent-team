#!/usr/bin/env node
/**
 * daily_audit.mjs — 日次自動監査（毎日改良ループ）
 *
 * 目的：
 *   - 毎日セッション開始時に「改良候補」を自動検出して提示
 *   - Lint 系の機械的検出（broken refs / unused imports / stale entries）
 *   - 検出結果は stdout に表示するのみ（自動修正はしない）
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/daily_audit.mjs
 *   node CDO/outputs/daily_audit.mjs --quiet   # 0件なら無音
 */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { safe } from './lib/pdca_lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');

function parseArgs(argv) {
  const args = { quiet: false };
  for (const a of argv) {
    if (a === '--quiet') args.quiet = true;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

// ─────────────────────────────────────────────
// 監査1: docs内の broken refs（特定ディレクトリ参照）
// ─────────────────────────────────────────────
function auditBrokenRefs() {
  const findings = [];
  const docs = [
    'README.md', 'DATA_POLICY.md',
    'projects/2026-04-08_月30万自動化/strategy_review_2026-05-07.md',
    'projects/2026-04-08_月30万自動化/roadmap_to_100.md',
    'projects/_index.md',
  ];
  const refRe = /\b(projects|CDO|CFO|CMO|CSO|CPO|context|\.claude)\/[A-Za-z_/0-9-]+\.(md|mjs|sh|json|jsonl)/g;
  for (const doc of docs) {
    const path = join(REPO_ROOT, doc);
    if (!existsSync(path)) continue;
    const content = safe(() => readFileSync(path, 'utf-8'), '');
    const refs = [...new Set(content.match(refRe) || [])];
    for (const ref of refs) {
      // YYYY-MM-DD パターンや ... が含まれるものは prose と判断しスキップ
      if (ref.includes('YYYY') || ref.includes('...')) continue;
      if (!existsSync(join(REPO_ROOT, ref))) {
        findings.push({ doc, ref });
      }
    }
  }
  return findings;
}

// ─────────────────────────────────────────────
// 監査2: .mjs の未使用 import（簡易・名前ベース検出）
// ─────────────────────────────────────────────
function auditUnusedImports() {
  const findings = [];
  const dir = join(REPO_ROOT, 'CDO', 'outputs');
  function scan(d) {
    if (!existsSync(d)) return;
    for (const e of safe(() => readdirSync(d, { withFileTypes: true }), [])) {
      const full = join(d, e.name);
      if (e.isDirectory()) scan(full);
      else if (e.name.endsWith('.mjs')) checkFile(full);
    }
  }
  function checkFile(file) {
    const content = safe(() => readFileSync(file, 'utf-8'), '');
    const importRe = /^import\s+\{([^}]+)\}\s+from\s+['"]([^'"]+)['"]/gm;
    let m;
    while ((m = importRe.exec(content)) !== null) {
      const importLine = m[0];
      const names = m[1].split(',').map(s => {
        const trimmed = s.trim();
        const aliasMatch = trimmed.match(/(\w+)\s+as\s+(\w+)/);
        return aliasMatch ? aliasMatch[2] : trimmed;
      }).filter(Boolean);
      const rest = content.replace(importLine, '');
      for (const name of names) {
        const re = new RegExp(`\\b${name}\\b`);
        if (!re.test(rest)) {
          findings.push({ file: file.replace(REPO_ROOT + '/', ''), name });
        }
      }
    }
  }
  scan(dir);
  return findings;
}

// ─────────────────────────────────────────────
// 監査3: _index.md の更新停滞（最終ログから N日以上経過）
// ─────────────────────────────────────────────
function auditStaleIndexes(staleDays = 14) {
  const findings = [];
  const roles = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];
  const today = new Date();
  for (const role of roles) {
    const path = join(REPO_ROOT, role, '_index.md');
    if (!existsSync(path)) continue;
    const content = safe(() => readFileSync(path, 'utf-8'), '');
    const dates = [...content.matchAll(/^\| (\d{4}-\d{2}-\d{2}) \|/gm)].map(m => m[1]);
    if (dates.length === 0) continue;
    const latest = dates.sort().pop();
    const days = Math.floor((today - new Date(latest)) / (86400 * 1000));
    if (days >= staleDays) {
      findings.push({ role, latest, days });
    }
  }
  return findings;
}

// ─────────────────────────────────────────────
// 監査4: 進行中タスクが空の役職（オーナーアクション未明示）
// ─────────────────────────────────────────────
function auditEmptyTasks() {
  const findings = [];
  const roles = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];
  for (const role of roles) {
    const path = join(REPO_ROOT, role, '_index.md');
    if (!existsSync(path)) continue;
    const content = safe(() => readFileSync(path, 'utf-8'), '');
    const m = content.match(/## 進行中タスク\s*\n+([\s\S]*?)(?=\n## |$)/);
    if (!m) continue;
    const items = m[1].split('\n').filter(l => l.trim().startsWith('- ') && !l.includes('（なし）'));
    if (items.length === 0) {
      findings.push({ role });
    }
  }
  return findings;
}

// ─────────────────────────────────────────────
// 監査5: 改善ログが直近7日で何日分蓄積されているか
// ─────────────────────────────────────────────
function auditImprovementCadence() {
  const dir = join(REPO_ROOT, 'CDO', 'research', 'improvements');
  if (!existsSync(dir)) return { count: 0, target: 3 };
  const today = new Date();
  const files = safe(() => readdirSync(dir), []).filter(f => f.endsWith('_improvement.md'));
  const recent = files.filter(f => {
    const m = f.match(/^(\d{4}-\d{2}-\d{2})_/);
    if (!m) return false;
    const days = Math.floor((today - new Date(m[1])) / (86400 * 1000));
    return days <= 7;
  });
  return { count: recent.length, target: 3 };
}

// ─────────────────────────────────────────────
// メイン
// ─────────────────────────────────────────────
function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('node CDO/outputs/daily_audit.mjs [--quiet]');
    return;
  }

  const brokenRefs = auditBrokenRefs();
  const unused = auditUnusedImports();
  const stale = auditStaleIndexes();
  const emptyTasks = auditEmptyTasks();
  const improve = auditImprovementCadence();

  const totalIssues = brokenRefs.length + unused.length + stale.length + emptyTasks.length;
  const improvementShortage = improve.count < improve.target;

  if (args.quiet && totalIssues === 0 && !improvementShortage) return;

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🔍 日次自動監査（改良候補の検出）');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  if (brokenRefs.length === 0) {
    console.log('🟢 broken refs: なし');
  } else {
    console.log(`🟡 broken refs: ${brokenRefs.length}件`);
    brokenRefs.forEach(f => console.log(`   - ${f.doc} → ${f.ref}`));
  }

  if (unused.length === 0) {
    console.log('🟢 未使用 import: なし');
  } else {
    console.log(`🟡 未使用 import: ${unused.length}件`);
    unused.forEach(f => console.log(`   - ${f.file}: ${f.name}`));
  }

  if (stale.length === 0) {
    console.log('🟢 _index.md 停滞: なし');
  } else {
    console.log(`🟡 _index.md 停滞 (14日以上更新なし): ${stale.length}件`);
    stale.forEach(f => console.log(`   - ${f.role}/_index.md (最終: ${f.latest}, ${f.days}日前)`));
  }

  if (emptyTasks.length === 0) {
    console.log('🟢 進行中タスク空欄: なし');
  } else {
    console.log(`🟡 進行中タスクが空欄の役職: ${emptyTasks.length}件`);
    emptyTasks.forEach(f => console.log(`   - ${f.role}/_index.md`));
  }

  if (improvementShortage) {
    console.log(`🟡 改善ログ蓄積不足: 直近7日で${improve.count}日分（目標 ${improve.target}日以上）`);
  } else {
    console.log(`🟢 改善ログ蓄積: 直近7日で${improve.count}日分`);
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  if (totalIssues === 0 && !improvementShortage) {
    console.log('✨ 改良候補なし。継続を推奨。');
  } else {
    console.log(`💡 改良候補 ${totalIssues + (improvementShortage ? 1 : 0)}件。明日の朝会で検討してください。`);
  }
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
}

main();
