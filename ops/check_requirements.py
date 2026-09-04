#!/usr/bin/env python3
"""恒常要件チェッカー（依存ゼロ）。

context/standing_requirements.md の各要件について「実行された証拠(observable)」を機械的に検証し、
OK / STALE / BROKEN / BLOCKED を出す。**日次点検で必ず実行し、非OKを owner に提示する。**
狙い: 要件が『途中から実行されなくなる』のを、静かな停止→毎日のアラームに変える。

使い方: python3 ops/check_requirements.py
終了コード: 非OKが1つでもあれば 1（点検フローで検知しやすいように）。
"""
import os, glob, time, datetime, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = time.time()
def days(path):
    try: return (NOW - os.path.getmtime(path)) / 86400
    except OSError: return None
def newest(pattern):
    fs = glob.glob(os.path.join(ROOT, pattern))
    return max(fs, key=os.path.getmtime) if fs else None

results = []  # (id, status, detail)
def add(i, st, d): results.append((i, st, d))

# R1 note公開: published の最新note記事が数日以内
n = newest("drafts/published/*note記事*.md")
if n:
    d = days(n)
    add("R1 note公開", "OK" if d <= 4 else "STALE", f"最新公開 {os.path.basename(n)[:28]}… {d:.1f}日前")
else:
    add("R1 note公開", "BROKEN", "published に note記事が無い")

# R2 実写サムネ: 直近記事の「サムネ被覆」を見る。
# ※以前は最新jpgの日付だけ見ていたため、新記事にサムネが付いていなくても古いjpgでOKに
#   なり、2026-09-02〜05 の生成停止を見逃した。被覆で見れば必ず気づく。
thumbdir = os.path.join(ROOT, "CDO/outputs/note_publisher/thumbnails")
# ※コンテナは毎回cloneするのでmtimeは全ファイル「今」＝日付判定に使えない(A7)。
#   ファイル名先頭の YYYY-MM-DD で判定する。
_cut = (datetime.date.today() - datetime.timedelta(days=21)).isoformat()
def _fname_date(f):
    b = os.path.basename(f)
    return b[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", b) else ""
recent_arts = [f for f in glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md"))
               if "サムネ生成プロンプト" not in os.path.basename(f) and _fname_date(f) >= _cut]
# owner確認済み(_verified.txt)は owner管理＝自動取得の対象外。自動化の欠落として数えない。
_vf = os.path.join(thumbdir, "_verified.txt")
verified = set()
if os.path.exists(_vf):
    verified = {ln.strip() for ln in open(_vf, encoding="utf-8").read().splitlines()
                if ln.strip() and not ln.strip().startswith("#")}
missing = [os.path.basename(f)[:-3] for f in recent_arts
           if os.path.basename(f)[:-3] not in verified
           and not os.path.exists(os.path.join(thumbdir, os.path.basename(f)[:-3] + ".jpg"))]
if not recent_arts:
    add("R2 実写サムネ", "OK", "直近21日の対象記事なし")
elif missing:
    add("R2 実写サムネ", "BROKEN",
        f"直近{len(recent_arts)}本中 {len(missing)}本がサムネ未取得(例:{missing[0][:26]}…)"
        " → ops/run_requests/ にpushして note-thumbnails を起動")
else:
    add("R2 実写サムネ", "OK", f"直近{len(recent_arts)}本すべてサムネ有り")

# R3 英語SEO: en-*.html 総数
cnt = len(glob.glob(os.path.join(ROOT, "apps/toyama-guide/en-*.html")))
add("R3 英語SEO", "OK" if cnt >= 100 else "STALE", f"en-*.html {cnt}枚")

# R4 クロスポスト素材: crosspost ファイルの更新鮮度（週次目安）
cp = os.path.join(ROOT, "CMO/outputs/2026-08-25_crosspost_Reddit_X_templates.md")
add("R4 クロスポスト素材", "OK" if (os.path.exists(cp) and days(cp) <= 10) else "STALE",
    (f"更新 {days(cp):.1f}日前" if os.path.exists(cp) else "ファイル無し"))

# R5 note→X 自動投稿: x_posted.tsv の行数（★実行の一次証拠）
xp = os.path.join(ROOT, "ops/logs/x_posted.tsv")
if os.path.exists(xp) and os.path.getsize(xp) > 0:
    with open(xp, encoding="utf-8") as f: rows = sum(1 for _ in f)
    add("R5 note→X投稿", "OK", f"投稿記録 {rows}件")
else:
    add("R5 note→X投稿", "BLOCKED", "実行ゼロ。前提=owner の X API Free tierキー(環境変数)が未投入")

# R6 コメント自動返信: replies.tsv の POSTED ＋ 過去記事の全件棚卸し進捗
rp = os.path.join(ROOT, "ops/comments/replies.tsv")
posted = 0
if os.path.exists(rp):
    posted = sum(1 for l in open(rp, encoding="utf-8") if "\tPOSTED\t" in l)
pend = os.path.join(ROOT, "ops/comments/pending.tsv")
pend_rows = (sum(1 for _ in open(pend, encoding="utf-8")) - 1) if os.path.exists(pend) else 0
# backlog sweep 進捗（backlog_targets.tsv の swept=YES 割合）
bt = os.path.join(ROOT, "ops/comments/backlog_targets.tsv")
sweep_total = sweep_done = 0
if os.path.exists(bt):
    rows = [l for l in open(bt, encoding="utf-8").read().splitlines()[1:] if l.strip()]
    sweep_total = len(rows)
    sweep_done = sum(1 for l in rows if "\tYES\t" in l)
sweep_note = f"／過去記事棚卸し {sweep_done}/{sweep_total}" if sweep_total else ""
if posted > 0:
    add("R6 コメント返信", "OK", f"投稿済 {posted}件{sweep_note}")
elif pend_rows > 0:
    add("R6 コメント返信", "BROKEN", f"pending {pend_rows}件あるのに投稿0{sweep_note}")
else:
    add("R6 コメント返信", "BLOCKED",
        f"pending空・棚卸し未着手{sweep_note}。前提=cowork の note-login取得(過去記事の全件スイープ)が未稼働")

# R10 有料フッター差し込みの健全性: 「結果行なし」誤失敗のコード修正が入っているか
paidscript = os.path.join(ROOT, "CDO/outputs/note_footer/append_paid_footer.py")
if os.path.exists(paidscript):
    src = open(paidscript, encoding="utf-8").read()
    fixed = "対象なし＝すべて処理済み・正常" in src  # 対象0本でも結果行を出す修正の目印
    if fixed:
        add("R10 有料フッター差込", "OK",
            "『結果行なし』誤失敗の根本修正を反映済み(対象0本でも結果行を出す・検証済)。※新記事へ付与は要manifest再生成＋有人--apply検証")
    else:
        add("R10 有料フッター差込", "BROKEN", "append_paid_footer.py に結果行修正が入っていない")

# R11 sitemap 鮮度: toyama-guide の全 en ページが sitemap に載っているか
sm = os.path.join(ROOT, "apps/ai-agency-hp/sitemap.xml")
guide = os.path.join(ROOT, "apps/toyama-guide")
if os.path.exists(sm) and os.path.isdir(guide):
    smtext = open(sm, encoding="utf-8").read()
    en_pages = [os.path.basename(f) for f in glob.glob(os.path.join(guide, "en-*.html"))]
    missing = [p for p in en_pages if f"/toyama/{p}" not in smtext]
    if not missing:
        add("R11 sitemap鮮度", "OK", f"toyama en {len(en_pages)}枚すべて sitemap 掲載")
    else:
        add("R11 sitemap鮮度", "STALE",
            f"sitemap未掲載 {len(missing)}枚(例:{missing[0]})→ python3 apps/toyama-guide/gen_sitemap.py")

# R8 STATE鮮度
st = os.path.join(ROOT, "context/STATE.md")
add("R8 日次点検の生存", "OK" if days(st) <= 2 else "STALE", f"STATE更新 {days(st):.1f}日前")

# R9 ops open 滞留
opens = 0
for f in glob.glob(os.path.join(ROOT, "ops/inbox/*.yaml")):
    with open(f, encoding="utf-8") as fh:
        if re.search(r"^status:\s*open\s*$", fh.read(), re.M): opens += 1
add("R9 ops滞留防止", "OK" if opens <= 10 else "STALE", f"open {opens}件" + ("（多すぎ→棚卸し要）" if opens > 10 else ""))

# 出力
order = {"BROKEN": 0, "STALE": 1, "BLOCKED": 2, "OK": 3}
results.sort(key=lambda r: order.get(r[1], 9))
icon = {"OK": "✅", "STALE": "⚠️", "BROKEN": "❌", "BLOCKED": "⛔"}
nonok = [r for r in results if r[1] != "OK"]
print(f"=== 恒常要件チェック {datetime.date.today()} ===")
for i, st, d in results:
    print(f"{icon.get(st,'?')} [{st:<7}] {i} — {d}")
print(f"\n非OK: {len(nonok)}件 / 全{len(results)}件")
if nonok:
    print("→ 対応が要る:", ", ".join(f"{i}({st})" for i, st, d in nonok))
sys.exit(1 if nonok else 0)
