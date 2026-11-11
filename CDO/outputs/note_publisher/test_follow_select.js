// フォローボタンの選び方の試験（node test_follow_select.js で実行）
// _cowork_growth.py の中の JS を**そのまま**取り出して、合成ページに当てる。
// 2026-11-11: 10/14 がタイムアウト・4/14 が already-following だった原因を
//   調べていて、owns の判定が body まで上がって**どのボタンも著者のものに
//   見えていた**ことが分かったので、その場で試験を書いた。
// ※note 本体にはつながない（A1）。DOM の形だけを見る試験。
const { chromium } = require('playwright');
const fs = require('fs');

// 実際の Python 側の選び方をそのまま写したもの
function pick(hits, handle) {
  if (hits.some(function (h) { return h.state === 'following' && h.owns; })) return 'already-following';
  const cands = hits.filter(function (h) { return h.state === 'follow'; });
  if (cands.length === 0) return 'no-follow-btn';
  const owned = cands.filter(function (h) { return h.owns; });
  if (handle && owned.length === 0) return 'no-author-follow-btn';
  let pool = owned.length ? owned : cands;
  const vis = pool.filter(function (h) { return h.vis; });
  pool = vis.length ? vis : pool;
  return 'idx=' + pool[0].i;
}

const CASES = [
  ['①他人のボタンが先頭にある（11-11の実害）',
   '<div><a href="/other_user">o</a><button>フォローする</button></div>' +
   '<div id="a"><a href="/target_user">t</a><button>フォローする</button></div>',
   'idx=1', '別人(idx=0)を押さない'],
  ['②著者のボタンが隠れている方と見える方の両方ある',
   '<div style="display:none"><a href="/target_user">t</a><button>フォローする</button></div>' +
   '<div><a href="/target_user">t</a><button>フォローする</button></div>',
   'idx=1', '見えている方を選ぶ＝30秒待ちが起きない'],
  ['③よその人が「フォロー中」・著者は未フォロー',
   '<div><a href="/other_user">o</a><button>フォロー中</button></div>' +
   '<div><a href="/target_user">t</a><button>フォローする</button></div>',
   'idx=1', 'already-following を返さない（4/14の誤判定）'],
  ['④著者が本当に「フォロー中」',
   '<div><a href="/target_user">t</a><button>フォロー中</button></div>',
   'already-following', '正しく済み判定'],
  ['⑤著者のボタンが無い（他人だけ）',
   '<div><a href="/other_user">o</a><button>フォローする</button></div>',
   'no-author-follow-btn', '押さないで次へ'],
  ['⑥1枚のカードに2人のリンクが入っている',
   '<div><a href="/target_user">t</a><a href="/other_user">o</a><button>フォローする</button></div>',
   'no-author-follow-btn', '誰のものか不明なので押さない'],
  ['⑦検索リンクをハンドルと誤認しない',
   '<div><a href="/search">検索</a><a href="/target_user">t</a><button>フォローする</button></div>',
   'idx=0', '/search をハンドルと数えたら2人になり no-author-follow-btn になる'],
  ['⑧絶対URLのプロフィールリンク',
   '<div><a href="https://note.com/target_user">t</a><button>フォローする</button></div>',
   'idx=0', 'https://note.com/ を剥がして比べる']
];

(async () => {
  const py = fs.readFileSync(__dirname + '/_cowork_growth.py', 'utf8');
  const js = py.split('js = """')[1].split('"""')[0];
  const browser = await chromium.launch();
  const page = await browser.newPage();
  let ng = 0;
  for (const c of CASES) {
    await page.setContent(c[1] + '<button>関係ないボタン</button>');
    const hits = await page.evaluate('(' + js + ')("target_user")');
    const got = pick(hits, 'target_user');
    const ok = got === c[2];
    if (!ok) ng++;
    console.log((ok ? '[OK] ' : '[NG] ') + c[0]);
    console.log('      結果=' + got + ' / 期待=' + c[2] + ' … ' + c[3]);
    if (!ok) console.log('      hits=' + JSON.stringify(hits));
  }
  await browser.close();
  console.log('--- 失敗 ' + ng + ' / ' + CASES.length + ' 件');
  process.exit(ng ? 1 : 0);
})();
