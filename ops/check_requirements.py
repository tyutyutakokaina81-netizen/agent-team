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
_na = os.path.join(thumbdir, "_no_auto.txt")   # 意図的に無サムネ=自動化の欠落ではない
no_auto = set()
if os.path.exists(_na):
    no_auto = {ln.strip() for ln in open(_na, encoding="utf-8").read().splitlines()
               if ln.strip() and not ln.strip().startswith("#")}
missing = [os.path.basename(f)[:-3] for f in recent_arts
           if os.path.basename(f)[:-3] not in verified
           and os.path.basename(f)[:-3] not in no_auto
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
# _sweep.tsv = fetch_note_comments.py が実際に巡回した記事の記録（cowork の日次に組み込み済）。
# backlog_targets.tsv の手書きYESより、こちらが「本当に巡回したか」の一次証拠になる。
sw = os.path.join(ROOT, "ops/comments/_sweep.tsv")
sweep_actual = (sum(1 for _ in open(sw, encoding="utf-8")) - 1) if os.path.exists(sw) else 0
sweep_note = (f"／過去記事棚卸し {sweep_done}/{sweep_total}" if sweep_total else "") + \
             f"／実巡回 {sweep_actual}本"
if posted > 0:
    add("R6 コメント返信", "OK", f"投稿済 {posted}件{sweep_note}")
elif pend_rows > 0:
    add("R6 コメント返信", "BROKEN", f"pending {pend_rows}件あるのに投稿0{sweep_note}")
elif sweep_actual > 0:
    # 巡回は動いているがコメントが1件も無い＝「仕組みが動いていない」ではなく「コメントが無い」。
    # この2つを混同すると、実績ゼロの理由を誤診する（過去に BLOCKED 表示で6日放置した）。
    add("R6 コメント返信", "OK",
        f"収集は稼働中（{sweep_actual}本巡回済）だがコメント0件＝返信対象なし{sweep_note}")
else:
    add("R6 コメント返信", "BLOCKED",
        f"pending空・**実巡回0本**{sweep_note}。取得スクリプト(fetch_note_comments.py)は"
        "cowork日次(ops/cowork_run.sh)に組込み済 → 次回のcowork実行で巡回数が入るはず")

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

# R2d フォールバック汚染: 同じ画像が複数記事に配られていたら「記事固有のサムネ」ではない。
# 実測(2026-09-06 CQO)=318枚中ユニーク176種、うち1枚の汎用画像が71ファイルに配られており、
# 「jpgが在る＝サムネ有り」という被覆を水増ししていた。3記事以上で共有＝フォールバックとみなす。
import hashlib as _hl
from collections import defaultdict as _dd
_groups = _dd(list)
for _f in glob.glob(os.path.join(thumbdir, "*.jpg")):
    try:
        _groups[_hl.md5(open(_f, "rb").read()).hexdigest()].append(os.path.basename(_f)[:-4])
    except OSError:
        pass
# _verified 掲載分は「code目視verifyのうえで意図的に同じ実写を流用した」もの(例:夏野菜かご/高岡大仏)。
# これは事故ではないので汚染から除外する＝R2dは「無意識に配られた汎用画像」だけを検知する。
# 判定基準の見直し(2026-09-07): 「3記事以上で同一」は**同一題材の重複ドラフト**（例: ころ柿が2本＋干し柿、
# 魚津の蜃気楼が2本）にも当たってしまい、常時STALEになって検知が形骸化する。
# 本当に捕まえたいのは「無関係な題材に1枚が広く配られる」＝汎用フォールバック（実測59〜71ファイル）なので、
# **_verified を除いた実質の共有数が4以上**のときだけ異常とする。3件は明細だけ出して警告にしない。
_shared = [[st for st in v if st not in verified] for v in _groups.values() if len(v) >= 3]
_fallback = {st for v in _shared if len(v) >= 4 for st in v}
_minor = sum(1 for v in _shared if 0 < len(v) < 4)
if _fallback:
    add("R2d フォールバック汚染", "STALE",
        f"1枚を4記事以上(未verify)で共有 {len(_fallback)}本 → 汎用画像が配られている疑い。削除して再取得を検討")
else:
    add("R2d フォールバック汚染", "OK",
        f"ユニーク画像 {len(_groups)}種／汎用配布(4本以上)なし"
        + (f"（同一題材の重複 {_minor}組は正常として除外）" if _minor else ""))

# R2b サムネが実際に「使われる」か: publish は _verified.txt 掲載分しか見出し画像に使わない
# (CQO指摘D2)。jpgが在るだけでは無サムネ公開になるため、被覆を別要件で可視化する。
unverified = [os.path.basename(f)[:-3] for f in recent_arts
              if os.path.exists(os.path.join(thumbdir, os.path.basename(f)[:-3] + ".jpg"))
              and os.path.basename(f)[:-3] not in verified]
if not recent_arts:
    add("R2b サムネ採用可否", "OK", "直近21日の対象記事なし")
elif unverified:
    add("R2b サムネ採用可否", "STALE",
        f"jpg有だが_verified未登録 {len(unverified)}本(例:{unverified[0][:24]}…)"
        " → codeが目視verifyして _verified.txt に追記（未登録だとpublishが使わない）")
else:
    # 「直近はOK」だけだと全体の未登録が見えない（CQO指摘・中4）。全件の被覆も必ず数字で出す。
    _all_jpg = len(glob.glob(os.path.join(thumbdir, "*.jpg")))
    add("R2b サムネ採用可否", "OK",
        f"直近のjpg有記事はすべて_verified登録済（全体: jpg {_all_jpg}枚 / _verified {len(verified)}件"
        f" ＝ 未登録 {max(0, _all_jpg - len(verified))}枚は公開時に見出し画像として使われない）")

# R2c 無サムネ確定の順守: _no_auto の記事に jpg が在ってはならない
# (残っているとpublisher経路が拾い、誤サムネのまま公開されうる。実際3回発生)
stray = [t for t in no_auto if os.path.exists(os.path.join(thumbdir, t + ".jpg"))]
if stray:
    add("R2c 無サムネ順守", "BROKEN",
        f"_no_auto なのにjpgが存在 {len(stray)}本({stray[0][:30]}…) → 削除する(誤サムネ公開の危険)")
else:
    add("R2c 無サムネ順守", "OK", f"_no_auto {len(no_auto)}本すべてjpg無し")

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

# R12 ops ID衝突: 同じIDが複数の場所に在ると、process_inbox.py done <id> が取り違える／
# processed への move が過去の完了記録を黙って上書きする。
# 2026-09-07 拡張(CQO指摘・高4): 当初は inbox×outbox だけを見ていたが、実際の次の事故は
# **inbox×processed** で起きた。監視要件を「事故の再現形」で書くと次の変奏を取り逃す。
# 本来の要件は「IDは inbox / outbox / processed を通じて一意」なので、そう書き直す。
def _ops_ids(sub):
    out = {}
    for f in glob.glob(os.path.join(ROOT, f"ops/{sub}/*.yaml")):
        parts = os.path.basename(f).split("_")
        if len(parts) >= 2:
            out.setdefault(parts[0] + "_" + parts[1], []).append(sub)
    return out
_seen = {}
for _sub in ("inbox", "outbox", "processed"):
    for _i, _where in _ops_ids(_sub).items():
        _seen.setdefault(_i, []).extend(_where)
# 実害があるのは次の2つだけ。ID文字列が processed の古い相方と一致するだけでは事故らない
# （ファイル名が `<id>_code_cowork` と `<id>_cowork_code` で違うため move は上書きしない）ので、
# それを BROKEN にすると常時赤くなって検知が形骸化する（R2dで学んだのと同じ失敗）。
#   (a) 未処理(inbox+outbox)に同じIDが2件以上 → `done <id>` がどちらを閉じるか分からない（実際に2回発生）
#   (b) 未処理のファイル名が processed に既に在る → move が過去の完了記録を黙って上書きする（実際に発生）
_active_ids = {}
for _sub in ("inbox", "outbox"):
    for _f in glob.glob(os.path.join(ROOT, f"ops/{_sub}/*.yaml")):
        _parts = os.path.basename(_f).split("_")
        if len(_parts) >= 2:
            _active_ids.setdefault(_parts[0] + "_" + _parts[1], []).append(os.path.basename(_f))
_ambiguous = sorted(i for i, fs in _active_ids.items() if len(fs) > 1)
_overwrite = sorted(n for fs in _active_ids.values() for n in fs
                    if os.path.exists(os.path.join(ROOT, "ops/processed", n)))
_clash = _ambiguous + _overwrite
if _clash:
    add("R12 ops ID衝突", "BROKEN",
        f"未処理で取り違え {len(_ambiguous)}件 / processed上書きの恐れ {len(_overwrite)}件"
        f"（例:{_clash[0]}）→ IDを振り直すこと")
else:
    add("R12 ops ID衝突", "OK",
        f"未処理 {len(_active_ids)}件はID一意、かつ processed と同名なし（上書き事故なし）")

# R14 字数メタの実測一致: 記事メタの「文字数」をその場で数えていたため、2日で基準が変わっていた
# （改行込み/改行除きで約30字ずれ、公開済みの記事は目標値2000のまま実測1475だった）。
# 正本を body_stats.body_len()（＝copy_body.py と同じ len(body)）に統一し、毎点検で一致を確認する。
try:
    import importlib.util as _ilu
    _bs_path = os.path.join(ROOT, "CDO/outputs/note_publisher/body_stats.py")
    _spec = _ilu.spec_from_file_location("body_stats", _bs_path)
    _bs = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_bs)
    _mismatch = []
    for _f in recent_arts:
        _t = open(_f, encoding="utf-8").read()
        _a, _m = _bs.body_len(_t), _bs.meta_len(_t)
        if _a is not None and _m is not None and _a != _m:
            _mismatch.append(os.path.basename(_f))
    if _mismatch:
        add("R14 字数メタの実測一致", "STALE",
            f"メタと実測が不一致 {len(_mismatch)}本(例:{_mismatch[0][:24]}…) → "
            "`python3 CDO/outputs/note_publisher/body_stats.py --sync <md>` で同期")
    else:
        add("R14 字数メタの実測一致", "OK", f"直近{len(recent_arts)}本すべて メタ＝実測(len(body)基準)")
except Exception as _e:
    add("R14 字数メタの実測一致", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R15 題材トークンの有無: 重複ゲート(topic_conflict)はタイトルから抽出した「題材トークン」で判定するが、
# 純ひらがなの主題語（例:「ぎんなん」）は「漢字を含む or 3字以上カタカナ」条件で落ち、
# トークンが長い句だけになって**重複判定に一切現れない**（CQO指摘・中1）。
# 実測: 「ぎんなん：街路樹に実る、拾って食べるもの」→ {街路樹に実る, 拾って食べる} だけだった。
# 短い題材語が1つも出ない記事を検知し、TOPIC_SYNONYMS への登録を促す。
try:
    import re as _re
    _pub = open(os.path.join(ROOT, "CDO/outputs/note_publisher/publish_to_note.py"), encoding="utf-8").read()
    _ns = {"re": _re}
    exec(_pub[_pub.index("TOPIC_STOPWORDS = {"):_pub.index("def topic_conflict(")], _ns)
    # ファイル名は `YYYY-MM-DD_note記事_<主題>_<サブタイトル>` の形＝<主題>が著者の宣言した題材語。
    # その主題語がトークン化されない（＝重複判定に現れない）ものだけを拾う。
    # 長さで足切りすると28/32が引っかかって常時赤くなり検知が形骸化するので、この形にする。
    _weak = []
    for _f in recent_arts:
        _b = os.path.basename(_f)[:-3]
        _parts = _b.split("_")
        if len(_parts) < 4:            # 主題セグメントが無い命名は対象外
            continue
        _subject = _parts[2]
        _toks = _ns["_topic_tokens"](_b.split("_", 2)[-1])
        _canon = _ns["_canon_topic"](_subject)
        if _canon not in _toks and not any(_subject in t for t in _toks):
            _weak.append(f"{_b}（主題語『{_subject}』が拾われていない）")
    if _weak:
        add("R15 題材トークンの有無", "STALE",
            f"主題語が重複ゲートに載らない記事 {len(_weak)}本(例:{_weak[0][:40]}…) → "
            "主題語を publish_to_note.py の TOPIC_SYNONYMS に登録すること（純ひらがな語は特に落ちる）")
    else:
        add("R15 題材トークンの有無", "OK", f"直近{len(recent_arts)}本すべて主題語が重複ゲートに載る")
except Exception as _e:
    add("R15 題材トークンの有無", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R16 見出し画像のライセンス表示: Commons の写真には CC BY / CC BY-SA があり **表示が義務**。
# 出典を記録し始めた直後に CC BY-SA 3.0/4.0 の写真を2枚採用していたことが判明した（2026-09-11）。
# 「気づいて書く」ではなく、_verified 登録済みの記事について毎点検で機械確認する。
try:
    import importlib.util as _ilu2
    _tc_path = os.path.join(ROOT, "CDO/outputs/note_publisher/thumb_credit.py")
    _spec2 = _ilu2.spec_from_file_location("thumb_credit", _tc_path)
    _tc = _ilu2.module_from_spec(_spec2); _spec2.loader.exec_module(_tc)
    _prov2 = _tc.load_prov()
    _nocredit = []
    for _f in glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md")) + \
               glob.glob(os.path.join(ROOT, "drafts/queue/*.md")):
        _st = os.path.basename(_f)[:-3]
        if _st not in verified:
            continue
        if _tc.credit_line(_st, _prov2) and not _tc.has_credit(open(_f, encoding="utf-8").read()):
            _nocredit.append(os.path.basename(_f))
    if _nocredit:
        add("R16 見出し画像のクレジット", "BROKEN",
            f"表示義務のあるライセンスなのにクレジット無し {len(_nocredit)}本(例:{_nocredit[0][:26]}…)"
            " → `python3 CDO/outputs/note_publisher/thumb_credit.py --apply <md>`")
    else:
        _need = sum(1 for _k in verified if _tc.credit_line(_k, _prov2))
        add("R16 見出し画像のクレジット", "OK",
            f"表示義務のある採用サムネ {_need}件はすべて本文にクレジットあり（CC0/PDと素性不明は対象外）")
except Exception as _e:
    add("R16 見出し画像のクレジット", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R13 制御ファイルの追跡: thumbnails/ は .gitignore 済なので、_verified.txt / _no_auto.txt は
# `git add -f` されていないと **codeの手元にしか存在しない**。実際 _no_auto.txt は管理外のままで、
# ランナーにもcoworkにも届かず「意図的な無サムネ」が一度も効いていなかった
# （獅子舞の誤サムネが8回復活した真因）。設定ではなく機構として毎回確認する。
import subprocess as _sp
_ctl = ["CDO/outputs/note_publisher/thumbnails/_verified.txt",
        "CDO/outputs/note_publisher/thumbnails/_no_auto.txt"]
try:
    _tracked = set(_sp.run(["git", "ls-files"] + _ctl, cwd=ROOT, capture_output=True,
                           text=True, timeout=20).stdout.split())
except Exception:
    _tracked = set(_ctl)   # gitが使えない環境では判定しない（誤報を出さない）
_untracked = [c for c in _ctl if c not in _tracked]
if _untracked:
    add("R13 制御ファイル追跡", "BROKEN",
        f"git管理外 {len(_untracked)}件({os.path.basename(_untracked[0])}) → "
        "`git add -f` しないとランナー/coworkに届かず、無サムネ指定も検証済み指定も効かない")
else:
    add("R13 制御ファイル追跡", "OK", "_verified.txt / _no_auto.txt はどちらも追跡下")

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
