#!/usr/bin/env node
/**
 * watch_and_post.mjs — note自動投稿ウォッチャー
 *
 * 実行：node watch_and_post.mjs
 *
 * 動作：
 *   1. 一定間隔（デフォルト60秒）で git pull を実行
 *   2. posts/drafts/ に published/ と重複しない新規 .md を検出
 *   3. 各ファイルに対して post_to_note.mjs を起動して自動投稿
 *   4. 成功したら drafts/ → published/ へ移動してコミット・プッシュ
 *
 * 1度起動して放置すれば、リモートに新記事が push されるたびに自動投稿する。
 *
 * 停止：Ctrl+C
 * 環境変数：
 *   WATCH_INTERVAL_MS — ポーリング間隔（デフォルト 60000 ms）
 */

import { execSync, spawnSync } from 'node:child_process';
import { existsSync, readdirSync, mkdirSync, renameSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '../../..');
const DRAFTS = join(REPO, 'projects/2026-04-18_note執筆/posts/drafts');
const PUBLISHED = join(REPO, 'projects/2026-04-18_note執筆/posts/published');
const POST_SCRIPT = join(__dirname, 'post_to_note.mjs');
const INTERVAL_MS = Number(process.env.WATCH_INTERVAL_MS || 60000);

if (!existsSync(PUBLISHED)) mkdirSync(PUBLISHED, { recursive: true });

const failedFiles = new Set();

function getBranch() {
  return execSync('git rev-parse --abbrev-ref HEAD', { cwd: REPO }).toString().trim();
}

function run(cmd, opts = {}) {
  return execSync(cmd, { cwd: REPO, stdio: 'pipe', ...opts }).toString().trim();
}

function gitPull(branch) {
  try {
    run(`git pull origin ${branch}`);
    return true;
  } catch (e) {
    console.error(`   ⚠ git pull 失敗: ${e.message.split('\n')[0]}`);
    return false;
  }
}

function unpublishedDrafts() {
  if (!existsSync(DRAFTS)) return [];
  const publishedSet = new Set(readdirSync(PUBLISHED));
  return readdirSync(DRAFTS)
    .filter(f => f.endsWith('.md') && !publishedSet.has(f) && !failedFiles.has(f))
    .map(f => ({ name: f, path: join(DRAFTS, f) }));
}

function postDraft(draft) {
  console.log(`\n📝 投稿開始: ${draft.name}`);
  const result = spawnSync('node', [POST_SCRIPT, draft.path], {
    stdio: 'inherit',
  });
  return result.status === 0;
}

function moveAndCommit(draft, branch) {
  const dest = join(PUBLISHED, draft.name);
  renameSync(draft.path, dest);

  const relSrc = draft.path.replace(REPO + '/', '');
  const relDst = dest.replace(REPO + '/', '');
  const msg = `chore(note): 公開済に移動 (${draft.name})\n\n自動投稿ウォッチャーによる記録`;
  try {
    run(`git add "${relSrc}" "${relDst}"`);
    run(`git commit -m "${msg}"`);
    run(`git push origin ${branch}`);
    console.log(`   → Git反映完了: ${relDst}`);
    return true;
  } catch (e) {
    console.warn(`   ⚠ Gitコミット/プッシュ失敗: ${e.message.split('\n')[0]}`);
    return false;
  }
}

async function tick() {
  const branch = getBranch();
  const ts = new Date().toLocaleTimeString('ja-JP');
  console.log(`[${ts}] pull（${branch}）...`);

  if (!gitPull(branch)) return;

  const drafts = unpublishedDrafts();
  if (drafts.length === 0) {
    console.log('   未投稿なし');
    return;
  }

  console.log(`   🆕 ${drafts.length}件の未投稿を検出`);
  for (const d of drafts) {
    const ok = postDraft(d);
    if (ok) {
      moveAndCommit(d, branch);
    } else {
      console.error(`   ❌ 失敗: ${d.name} — このセッション中は再試行しません`);
      failedFiles.add(d.name);
    }
  }
}

console.log('🤖 note 自動投稿ウォッチャー起動');
console.log(`   Repo:     ${REPO}`);
console.log(`   Drafts:   ${DRAFTS}`);
console.log(`   Interval: ${INTERVAL_MS / 1000}秒`);
console.log('   停止: Ctrl+C\n');

await tick();
setInterval(tick, INTERVAL_MS);
