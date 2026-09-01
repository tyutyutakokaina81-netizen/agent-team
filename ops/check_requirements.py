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

# R2 実写サムネ: thumbnails jpg の最新
n = newest("CDO/outputs/note_publisher/thumbnails/*.jpg")
add("R2 実写サムネ", "OK" if (n and days(n) <= 4) else ("STALE" if n else "BROKEN"),
    (f"最新jpg {days(n):.1f}日前" if n else "jpgが無い"))

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

# R6 コメント自動返信: replies.tsv の POSTED
rp = os.path.join(ROOT, "ops/comments/replies.tsv")
posted = 0
if os.path.exists(rp):
    posted = sum(1 for l in open(rp, encoding="utf-8") if "\tPOSTED\t" in l)
pend = os.path.join(ROOT, "ops/comments/pending.tsv")
pend_rows = (sum(1 for _ in open(pend, encoding="utf-8")) - 1) if os.path.exists(pend) else 0
if posted > 0:
    add("R6 コメント返信", "OK", f"投稿済 {posted}件")
elif pend_rows > 0:
    add("R6 コメント返信", "BROKEN", f"pending {pend_rows}件あるのに投稿0")
else:
    add("R6 コメント返信", "BLOCKED", "pending空。前提=cowork の note-login取得が未稼働")

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
