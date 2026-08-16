#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""『雨晴を待つ / Where the Rain Clears』二言語リーダーHTMLを原稿から生成。
出力: (1) Artifact用(body内容のみ・<title>/<style>/<script>含む)  (2) Pages用 完全HTML。"""
import html, re
from pathlib import Path

ROOT = Path("/home/user/agent-team/projects/2026-08-16_恋愛小説_180p")
JP = ROOT/"原稿"; EN = ROOT/"EN/chapters"
SCRATCH = Path("/tmp/claude-0/-home-user-agent-team/541d05a5-44d1-535f-a657-46689f13d632/scratchpad")
PAGES_OUT = Path("/home/user/agent-team/apps/toyama-guide/rain-clears.html")

# (eyebrow_jp, eyebrow_en, title_jp, title_en, jp_files, en_files)
CH = [
 ("序","Prologue","三月の光","The March Light",["00_プロローグ.txt"],["00_prologue.txt"]),
 ("第一章","Chapter One","海の見える駅","The Station by the Sea",["01_第一章.txt"],["01_chapter01.txt"]),
 ("第二章","Chapter Two","汀という喫茶店","The Coffee Shop Called Migiwa",["02_第二章.txt"],["02_chapter02.txt"]),
 ("第三章","Chapter Three","ほたるいかの夜","The Night of the Firefly Squid",["03_第三章.txt"],["03_chapter03.txt"]),
 ("第四章","Chapter Four","女岩の約束","The Promise at Meiwa Rock",["04_第四章.txt"],["04_chapter04.txt"]),
 ("第五章","Chapter Five","白えびの季節","The Season of White Shrimp",["05_第五章.txt"],["05_chapter05.txt"]),
 ("第六章","Chapter Six","海王丸の帆","The Sails of the Kaiwo Maru",["06_第六章.txt"],["06_chapter06.txt"]),
 ("第七章","Chapter Seven","開かずの引き出し","The Locked Drawer",["07_第七章.txt"],["07_chapter07.txt"]),
 ("第八章","Chapter Eight","すれ違いの秋","A Misunderstanding in Autumn",["08_第八章.txt"],["08_chapter08.txt"]),
 ("第九章","Chapter Nine","新湊の夕暮れ","Dusk at Shinminato",["09_第九章.txt"],["09_chapter09.txt"]),
 ("第十章","Chapter Ten","寒ぶり起こし","The Thunder That Wakes the Yellowtail",["10_第十章.txt"],["10_chapter10.txt"]),
 ("第十一章","Chapter Eleven","雪の予報","The Forecast of Snow",["11_第十一章.txt"],["11_chapter11.txt"]),
 ("第十二章","Chapter Twelve","冬の夜明け","The Winter Daybreak",["12_第十二章.txt"],["12_chapter12.txt"]),
 ("結","Epilogue","また、雨が晴れて","And Again, the Rain Clears",["13_エピローグ.txt"],["13_epilogue.txt"]),
]

def jp_paras(files):
    out=[]
    for f in files:
        lines=(JP/f).read_text(encoding="utf-8").splitlines()
        # 先頭の見出し行(　　　…章…)を除去
        body=[l for l in lines]
        while body and (body[0].strip()=="" or re.match(r"^[　\s]*(プロローグ|第[一二三四五六七八九十]+章|エピローグ)", body[0])):
            body.pop(0)
        for l in body:
            s=l.strip()
            if s: out.append(s)
    return out

def en_paras(files):
    out=[]
    for f in files:
        txt=(EN/f).read_text(encoding="utf-8")
        # 先頭見出し行(PROLOGUE.../CHAPTER.../EPILOGUE...)を落とす
        parts=[p.strip() for p in txt.split("\n\n") if p.strip()]
        if parts and re.match(r"^(PROLOGUE|CHAPTER|EPILOGUE)\b", parts[0], re.I):
            parts=parts[1:]
        # 末尾のTHE END等はそのまま生かす
        for p in parts:
            out.append(" ".join(p.split("\n")))
    return out

def esc(s): return html.escape(s, quote=False)

# ---- 目次 ----
toc=[]
for i,(eb,eben,tj,te,_,_) in enumerate(CH):
    toc.append(f'<li><a href="#ch{i}"><span class="i-jp">{esc(eb)}　{esc(tj)}</span><span class="i-en">{esc(eben)} · {esc(te)}</span></a></li>')
toc_html='<ol class="toc">'+''.join(toc)+'</ol>'

# ---- 章本文 ----
secs=[]
for i,(eb,eben,tj,te,jf,ef) in enumerate(CH):
    jp="".join(f"<p>{esc(p)}</p>" for p in jp_paras(jf))
    en="".join(f"<p>{esc(p)}</p>" for p in en_paras(ef))
    secs.append(f'''<section class="chapter" id="ch{i}">
  <header class="ch-head">
    <p class="eyebrow"><span class="i-jp">{esc(eb)}</span><span class="i-en">{esc(eben)}</span></p>
    <h2><span class="i-jp">{esc(tj)}</span><span class="i-en">{esc(te)}</span></h2>
    <div class="rule" aria-hidden="true"><span></span>◦<span></span></div>
  </header>
  <div class="prose lang-jp">{jp}</div>
  <div class="prose lang-en">{en}</div>
</section>''')
sections_html="\n".join(secs)

STYLE = r"""
:root{
  --bg:#f6f1ea; --surface:#fffdf9; --ink:#20263f; --ink-soft:#4a4f66;
  --gold:#c9913f; --rose:#c07863; --indigo:#3c4c7e; --line:#e4dccf;
  --sky-top:#26305a; --sky-mid:#7a6a86; --sky-low:#d99a63; --sky-gold:#f0c675;
  --measure:min(38em,90vw);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#12172a; --surface:#181e35; --ink:#e9e3d5; --ink-soft:#a9adc0;
  --gold:#e2b463; --rose:#d68d78; --indigo:#8fa2d6; --line:#2a3252;
  --sky-top:#0c1024; --sky-mid:#37304e; --sky-low:#8a5a44; --sky-gold:#c79a52;
}}
:root[data-theme="dark"]{
  --bg:#12172a; --surface:#181e35; --ink:#e9e3d5; --ink-soft:#a9adc0;
  --gold:#e2b463; --rose:#d68d78; --indigo:#8fa2d6; --line:#2a3252;
  --sky-top:#0c1024; --sky-mid:#37304e; --sky-low:#8a5a44; --sky-gold:#c79a52;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Hiragino Mincho ProN","Hiragino Mincho Pro","Yu Mincho","YuMincho","Noto Serif JP","Noto Serif CJK JP",serif;
  line-height:1.95;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased}
.latin{font-family:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,"Times New Roman",serif}
.sans{font-family:system-ui,-apple-system,"Segoe UI","Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif}

/* 言語切替 */
.lang-en{display:none}
:root[data-lang="en"] .lang-jp{display:none}
:root[data-lang="en"] .lang-en{display:block}
.i-en{display:none}.i-jp{display:inline}
:root[data-lang="en"] .i-en{display:inline}:root[data-lang="en"] .i-jp{display:none}
:root[data-lang="en"] .prose{ /* 英語は横書きのラテン組み */
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;line-height:1.75}

/* トップバー */
.bar{position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;
  gap:1rem;padding:.6rem clamp(1rem,4vw,2rem);background:color-mix(in srgb,var(--bg) 86%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.bar .brand{font-size:.95rem;letter-spacing:.02em;color:var(--ink);text-decoration:none;font-weight:600}
.bar .brand .sub{color:var(--ink-soft);font-weight:400}
.toggle{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--surface)}
.toggle button{appearance:none;border:0;background:transparent;color:var(--ink-soft);
  font:inherit;font-size:.8rem;padding:.35rem .8rem;cursor:pointer;letter-spacing:.03em}
.toggle button[aria-pressed="true"]{background:var(--indigo);color:#fff}
.toggle button:focus-visible{outline:2px solid var(--gold);outline-offset:2px}

/* ヒーロー＝夜明けの空 */
.hero{position:relative;min-height:64vh;display:grid;place-items:end center;overflow:hidden;
  background:linear-gradient(180deg,var(--sky-top) 0%,var(--sky-mid) 46%,var(--sky-low) 74%,var(--sky-gold) 100%)}
.hero .stars{position:absolute;inset:0 0 40% 0;background-image:
  radial-gradient(1.2px 1.2px at 20% 30%,#fff8,transparent),
  radial-gradient(1px 1px at 60% 18%,#fff7,transparent),
  radial-gradient(1.4px 1.4px at 80% 40%,#fff6,transparent),
  radial-gradient(1px 1px at 38% 12%,#fff6,transparent),
  radial-gradient(1px 1px at 72% 26%,#fff5,transparent);opacity:.9}
.hero .sun{position:absolute;left:50%;bottom:30%;width:120px;height:120px;transform:translateX(-50%);
  border-radius:50%;background:radial-gradient(circle,#fff6d6 0%,#f5c86e 42%,transparent 70%);filter:blur(2px)}
.hero svg{position:absolute;left:0;right:0;bottom:0;width:100%;height:38%;display:block}
.hero .titlewrap{position:relative;z-index:2;text-align:center;padding:0 1.2rem 8vh;color:#fff;
  text-shadow:0 2px 20px rgba(10,14,30,.45)}
.hero h1{margin:0;font-size:clamp(2.6rem,8vw,5rem);letter-spacing:.06em;font-weight:600;text-wrap:balance}
.hero .en-title{font-size:clamp(1rem,3vw,1.6rem);letter-spacing:.22em;text-transform:uppercase;
  margin:.7rem 0 0;opacity:.92}
.hero .tagline{margin:.9rem auto 0;max-width:34em;font-size:clamp(.9rem,2.3vw,1.05rem);opacity:.9}

/* 導入・目次 */
.intro{max-width:var(--measure);margin:0 auto;padding:clamp(2.4rem,6vw,4rem) 1.2rem 0}
.intro p{color:var(--ink-soft)}
.toc{max-width:var(--measure);margin:2rem auto 0;padding:1.4rem 1.4rem;list-style:none;counter-reset:t;
  background:var(--surface);border:1px solid var(--line);border-radius:14px}
.toc li{counter-increment:t;border-bottom:1px dashed var(--line)}
.toc li:last-child{border-bottom:0}
.toc a{display:flex;gap:.8rem;align-items:baseline;padding:.62rem .2rem;text-decoration:none;color:var(--ink)}
.toc a:hover{color:var(--gold)}
.toc a::before{content:counter(t,decimal-leading-zero);font-size:.72rem;color:var(--gold);
  font-variant-numeric:tabular-nums;min-width:1.7em}
.toc .i-en{color:var(--ink-soft);font-size:.95em}

/* 本文 */
main{max-width:var(--measure);margin:0 auto;padding:0 1.2rem 6rem}
.chapter{padding-top:clamp(3rem,8vw,5.5rem)}
.ch-head{text-align:center;margin-bottom:2rem}
.eyebrow{margin:0;font-size:.72rem;letter-spacing:.34em;text-transform:uppercase;color:var(--gold);
  font-family:system-ui,-apple-system,"Yu Gothic",sans-serif}
.ch-head h2{margin:.5rem 0 0;font-size:clamp(1.5rem,4.4vw,2.1rem);font-weight:600;letter-spacing:.04em;text-wrap:balance}
:root[data-lang="en"] .ch-head h2{font-family:"Iowan Old Style",Palatino,Georgia,serif}
.rule{display:flex;align-items:center;justify-content:center;gap:.8rem;margin:1.1rem auto 0;color:var(--gold);opacity:.8}
.rule span{height:1px;width:min(22vw,90px);background:linear-gradient(90deg,transparent,var(--gold))}
.rule span:last-child{background:linear-gradient(90deg,var(--gold),transparent)}
.prose p{margin:0 0 1.15em;text-indent:1em}
.prose p:first-child{text-indent:0}
.prose p:first-child::first-letter{font-size:2.6em;line-height:.8;float:left;padding:.05em .12em 0 0;color:var(--rose)}
:root[data-lang="en"] .prose p{text-indent:1.4em}
:root[data-lang="en"] .prose p:first-child::first-letter{color:var(--rose)}

.endnote{max-width:var(--measure);margin:2rem auto 0;padding:1.6rem 1.2rem 3rem;text-align:center;color:var(--ink-soft);
  border-top:1px solid var(--line);font-size:.9rem}
.endnote .fin{font-size:1.1rem;letter-spacing:.3em;color:var(--gold);margin-bottom:.8rem}
a.top{color:var(--indigo);text-decoration:none;border-bottom:1px solid var(--line)}
a.top:hover{color:var(--gold)}
"""

SCRIPT = r"""
(function(){
  var root=document.documentElement;
  var saved=null; try{saved=localStorage.getItem('rc-lang')}catch(e){}
  if(saved==='en') root.setAttribute('data-lang','en');
  function set(l){ if(l==='en')root.setAttribute('data-lang','en'); else root.removeAttribute('data-lang');
    try{localStorage.setItem('rc-lang',l)}catch(e){}
    document.querySelectorAll('[data-lang-btn]').forEach(function(b){b.setAttribute('aria-pressed', b.getAttribute('data-lang-btn')===l);});
  }
  document.addEventListener('click',function(e){var b=e.target.closest('[data-lang-btn]'); if(b){set(b.getAttribute('data-lang-btn'));}});
  set(saved==='en'?'en':'jp');
})();
"""

HERO = '''<header class="hero">
  <div class="stars" aria-hidden="true"></div>
  <div class="sun" aria-hidden="true"></div>
  <svg viewBox="0 0 1200 260" preserveAspectRatio="none" aria-hidden="true">
    <path d="M0,150 L120,110 150,150 260,95 330,150 470,120 520,150 700,150 760,150 900,105 970,150 1080,120 1200,150 1200,260 0,260 Z" fill="#20264a"/>
    <path d="M150,150 138,128 162,128 Z M330,150 315,120 345,120 Z M700,150 686,124 714,124 Z M970,150 956,126 984,126 Z" fill="#eef1fb"/>
    <path d="M0,178 L1200,178 1200,260 0,260 Z" fill="#243a63" opacity="0.9"/>
    <g><path d="M735,178 q-8,-26 20,-30 q26,-2 22,30 Z" fill="#161a30"/>
       <line x1="748" y1="150" x2="748" y2="140" stroke="#161a30" stroke-width="2"/><circle cx="748" cy="138" r="5" fill="#152021"/>
       <line x1="760" y1="150" x2="760" y2="138" stroke="#161a30" stroke-width="2"/><circle cx="760" cy="136" r="5" fill="#152021"/></g>
  </svg>
  <div class="titlewrap">
    <h1>雨晴を待つ</h1>
    <p class="en-title latin">Where the Rain Clears</p>
    <p class="tagline"><span class="i-jp">富山湾・海の見える町の、ひと冬の恋物語。</span><span class="i-en latin">A quiet romance on Toyama Bay — one winter, one promise.</span></p>
  </div>
</header>'''

INTRO = '''<div class="intro">
  <p><span class="i-jp">東京で心をすり減らした遥は、亡き祖母の家を片づけるために、海の向こうに立山連峰がそびえる故郷へ帰ってくる。海辺の喫茶店を営む寡黙なカメラマン・湊は、二年前に海で亡くした兄のために、毎朝、女岩の向こうの立山を撮り続けていた——。全12話・日本語と英語で読めます。</span><span class="i-en latin">Burned out in Tokyo, Haruka comes home to a coast where snow mountains rise from the sea, to clear out her late grandmother's house. Minato, who runs a seaside coffee shop, photographs those mountains every dawn — waiting for the one clear winter morning his late brother never saw. Read in Japanese or English.</span></p>
</div>'''

TOCBLOCK = '<nav aria-label="目次 / Contents">'+toc_html+'</nav>'

ENDNOTE = '''<div class="endnote">
  <div class="fin"><span class="i-jp">了</span><span class="i-en latin">FIN</span></div>
  <p><span class="i-jp">この物語はフィクションです。実在の地名・風物を借りていますが、人物・団体はすべて架空です。</span><span class="i-en latin">This story is fiction. Real place names are borrowed; all characters and events are imaginary.</span></p>
  <p><a class="top" href="#top"><span class="i-jp">↑ 最初にもどる</span><span class="i-en latin">↑ Back to top</span></a></p>
</div>'''

BAR = '''<div class="bar" id="top">
  <a class="brand" href="#top">雨晴を待つ <span class="sub latin">/ Where the Rain Clears</span></a>
  <div class="toggle" role="group" aria-label="言語 / Language">
    <button data-lang-btn="jp" aria-pressed="true">日本語</button>
    <button data-lang-btn="en" aria-pressed="false">English</button>
  </div>
</div>'''

BODY = BAR+HERO+INTRO+TOCBLOCK+"<main>"+sections_html+ENDNOTE+"</main>"

# --- Artifact用（<title>/<style>/<script>＋内容。html/head/bodyなし） ---
artifact = f'''<title>雨晴を待つ · Where the Rain Clears</title>
<style>{STYLE}</style>
{BODY}
<script>{SCRIPT}</script>'''
(SCRATCH/"rain-clears.html").write_text(artifact, encoding="utf-8")

# --- Pages用（完全HTML＋SEO/OG） ---
desc="富山湾・雨晴海岸を舞台にした恋愛小説『雨晴を待つ / Where the Rain Clears』全12話・日英対訳。海越しの立山連峰を撮る男と、東京から帰った女の、ひと冬の物語。"
pages = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>雨晴を待つ / Where the Rain Clears — 富山湾の恋愛小説</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="https://tyutyutakokaina81-netizen.github.io/agent-team/toyama/rain-clears.html">
<meta property="og:type" content="book">
<meta property="og:title" content="雨晴を待つ / Where the Rain Clears">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="https://tyutyutakokaina81-netizen.github.io/agent-team/toyama/rain-clears.html">
<meta name="twitter:card" content="summary_large_image">
<style>{STYLE}</style>
</head>
<body>
{BODY}
<script>{SCRIPT}</script>
</body>
</html>'''
PAGES_OUT.write_text(pages, encoding="utf-8")

print("artifact:", (SCRATCH/"rain-clears.html").stat().st_size, "bytes")
print("pages   :", PAGES_OUT, PAGES_OUT.stat().st_size, "bytes")
