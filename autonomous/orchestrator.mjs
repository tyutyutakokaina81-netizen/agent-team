// orchestrator.mjs
// 5役職AIの日次ループを順に実行するメインループ。
//
// 流れ:
//   1. 事前に当日予算 summary を確認
//   2. 各役職について runOfficerTurn を呼ぶ（1役職ずつ順に）
//   3. 失敗役職は skip、他は続行
//   4. ループ完了後、日次サマリを CDO/research/ に書き出す
//   5. オプションで git commit + push
//
// 実行:
//   node autonomous/orchestrator.mjs              # dry-run 自動判定、commit なし
//   node autonomous/orchestrator.mjs --commit     # 実行後に自動 commit + push
//   node autonomous/orchestrator.mjs --only CDO   # CDO 単独モード
//   node autonomous/orchestrator.mjs --dry-run    # 強制 dry-run

import { writeFile, mkdir } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as budget from './budget_guard.mjs';
import { runOfficerTurn } from './officer_runner.mjs';

const execFileAsync = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');

const DEFAULT_OFFICERS = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];

// ─────────────────────────────────────────────────────────────
// 引数 parse
// ─────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const opts = {
    officers: [...DEFAULT_OFFICERS],
    mode: 'auto', // auto | dry-run | live
    commit: false,
    push: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--commit') opts.commit = true;
    else if (a === '--push') { opts.commit = true; opts.push = true; }
    else if (a === '--dry-run') opts.mode = 'dry-run';
    else if (a === '--live') opts.mode = 'live';
    else if (a === '--only') {
      const o = argv[++i];
      if (o) opts.officers = [o];
    }
    else if (a === '--officers') {
      const list = argv[++i];
      if (list) opts.officers = list.split(',').map(s => s.trim()).filter(Boolean);
    }
  }
  return opts;
}

// ─────────────────────────────────────────────────────────────
// Git 操作（optional）
// ─────────────────────────────────────────────────────────────

async function gitStatus() {
  const { stdout } = await execFileAsync('git', ['status', '--porcelain'], { cwd: REPO_ROOT });
  return stdout.trim();
}

async function gitCurrentBranch() {
  const { stdout } = await execFileAsync('git', ['branch', '--show-current'], { cwd: REPO_ROOT });
  return stdout.trim();
}

async function gitAutoCommit({ loopDate, results }) {
  const status = await gitStatus();
  if (!status) {
    return { committed: false, reason: 'no changes' };
  }

  const successCount = results.filter(r => !r.error && !r.skipped).length;
  const skipCount = results.filter(r => r.skipped).length;
  const errorCount = results.filter(r => r.error).length;
  const monthSpend = results.find(r => r.spend)?.spend?.month ?? 0;

  const message = [
    `loop(${loopDate}): ${successCount} success / ${skipCount} skipped / ${errorCount} errors`,
    '',
    results.map(r => {
      if (r.skipped) return `- ${r.officer}: skipped (${r.reason || 'unknown'})`;
      if (r.error) return `- ${r.officer}: ERROR (${r.error.slice(0, 80)})`;
      return `- ${r.officer}: ${r.decision?.slice(0, 60) || '(no decision)'}`;
    }).join('\n'),
    '',
    `monthly spend: ¥${monthSpend.toFixed(2)} / ¥2000`,
    '',
    '自律ループによる自動コミット',
  ].join('\n');

  await execFileAsync('git', ['add', '-A'], { cwd: REPO_ROOT });
  await execFileAsync('git', ['commit', '-m', message], { cwd: REPO_ROOT });
  return { committed: true, message };
}

async function gitPush() {
  const branch = await gitCurrentBranch();
  if (!branch) {
    return { pushed: false, reason: 'detached HEAD' };
  }
  await execFileAsync('git', ['push', 'origin', branch], { cwd: REPO_ROOT });
  return { pushed: true, branch };
}

// ─────────────────────────────────────────────────────────────
// 日次サマリ書き出し
// ─────────────────────────────────────────────────────────────

async function writeLoopSummary({ loopDate, results, budgetState }) {
  const summaryDir = path.join(REPO_ROOT, 'CDO', 'research');
  await mkdir(summaryDir, { recursive: true });
  const file = path.join(summaryDir, `daily_loop_${loopDate}.md`);

  const lines = [
    `# 自律ループ実行サマリ ${loopDate}`,
    '',
    `実行時刻: ${new Date().toISOString()}`,
    '',
    '## 結果',
    '',
    '| 役職 | 状態 | 今日の決定 | 成果物 | 消費(円) |',
    '|------|------|-----------|--------|---------|',
    ...results.map(r => {
      if (r.skipped) return `| ${r.officer} | skipped | ${r.reason || ''} | — | 0 |`;
      if (r.error) return `| ${r.officer} | ERROR | ${(r.error || '').slice(0, 60)} | — | 0 |`;
      const art = r.artifactPath ? '`' + r.artifactPath + '`' : '—';
      return `| ${r.officer} | ok (${r.mode}) | ${(r.decision || '').slice(0, 60)} | ${art} | ${r.spend?.thisCall?.toFixed(2) || '0'} |`;
    }),
    '',
    '## 予算状況',
    '',
    `- 本日消費: ¥${budgetState.today.toFixed(2)} / ¥${budgetState.dailyLimit}`,
    `- 今月消費: ¥${budgetState.month.toFixed(2)} / ¥${budgetState.monthlyLimit}`,
    `- 今月残: ¥${budgetState.monthRemaining.toFixed(2)}`,
    '',
    '## task_queue 追加件数',
    '',
    results.filter(r => r.messagesQueued > 0).map(r => `- ${r.officer} → ${r.messagesQueued} 件`).join('\n') || '(なし)',
    '',
  ];

  await writeFile(file, lines.join('\n'), 'utf8');
  return file;
}

// ─────────────────────────────────────────────────────────────
// メインループ
// ─────────────────────────────────────────────────────────────

export async function runLoop(opts = {}) {
  const officers = opts.officers || DEFAULT_OFFICERS;
  const mode = opts.mode || 'auto';
  const loopDate = new Date().toISOString().slice(0, 10);

  console.log(`[orchestrator] loop start: ${loopDate}, officers=${officers.join(',')}, mode=${mode}`);

  // 事前予算チェック（当日残高ゼロならそもそも起動しない）
  const preBudget = await budget.summary();
  if (preBudget.monthRemaining <= 0 || preBudget.todayRemaining <= 0) {
    console.log('[orchestrator] budget exhausted, loop aborted');
    return {
      aborted: true,
      reason: 'budget exhausted',
      budgetState: preBudget,
    };
  }

  // 各役職ターン
  const results = [];
  for (const officer of officers) {
    console.log(`[orchestrator] running ${officer}...`);
    try {
      const r = await runOfficerTurn(officer, { mode });
      results.push(r);
      if (r.error) {
        console.error(`[orchestrator] ${officer} error: ${r.error}`);
      } else if (r.skipped) {
        console.log(`[orchestrator] ${officer} skipped: ${r.reason}`);
      } else {
        console.log(`[orchestrator] ${officer} ok: ${r.decision?.slice(0, 60)}`);
      }
    } catch (err) {
      results.push({ officer, error: `orchestrator level: ${err.message}` });
      console.error(`[orchestrator] ${officer} crashed: ${err.message}`);
    }
  }

  // 事後予算
  const postBudget = await budget.summary();

  // 日次サマリ
  const summaryPath = await writeLoopSummary({ loopDate, results, budgetState: postBudget });
  console.log(`[orchestrator] summary written: ${path.relative(REPO_ROOT, summaryPath)}`);

  return {
    aborted: false,
    loopDate,
    officers,
    mode,
    results,
    budgetState: postBudget,
    summaryPath: path.relative(REPO_ROOT, summaryPath),
  };
}

// ─────────────────────────────────────────────────────────────
// CLI エントリ
// ─────────────────────────────────────────────────────────────

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  const opts = parseArgs(process.argv.slice(2));
  const result = await runLoop(opts);

  if (result.aborted) {
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  // オプションで git commit
  if (opts.commit) {
    try {
      const commitResult = await gitAutoCommit({
        loopDate: result.loopDate,
        results: result.results,
      });
      if (commitResult.committed) {
        console.log('[orchestrator] committed');
        if (opts.push) {
          const pushResult = await gitPush();
          console.log(`[orchestrator] pushed to ${pushResult.branch}`);
        }
      } else {
        console.log(`[orchestrator] no commit: ${commitResult.reason}`);
      }
    } catch (err) {
      console.error(`[orchestrator] git operation failed: ${err.message}`);
    }
  }

  // JSON サマリを stdout へ
  console.log(JSON.stringify({
    loopDate: result.loopDate,
    summaryPath: result.summaryPath,
    officers: result.officers,
    mode: result.mode,
    successCount: result.results.filter(r => !r.error && !r.skipped).length,
    skippedCount: result.results.filter(r => r.skipped).length,
    errorCount: result.results.filter(r => r.error).length,
    budget: result.budgetState,
  }, null, 2));
}
