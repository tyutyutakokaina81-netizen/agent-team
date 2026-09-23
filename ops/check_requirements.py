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
# ★除外を先にやると「見ていないだけのOK」になる。まず**実在するか**を全件について確かめ、
# そのうえで「自動取得の欠落(missing)」と「_verified なのに画像が消えている(vanished)」を分ける。
_nojpg = [os.path.basename(f)[:-3] for f in recent_arts
          if not os.path.exists(os.path.join(thumbdir, os.path.basename(f)[:-3] + ".jpg"))]
vanished = [b for b in _nojpg if b in verified]          # owner確認済みなのに画像が無い＝事故
# ★2026-09-23 訂正: **「公開後はもう付けられない」は誤りだった。**
#   `ops/fix_header_images.sh` ＋ `set_header_image.py` が、**公開済みの投稿を開いて
#   見出し画像を後から設定する**。2026-09-19 に実際に7本これで直している（ops/header_image_todo.tsv）。
#   この仕組みを自分で作っておきながら、今日その存在を忘れて「付けられない」と書き、
#   検査の対象からも外してしまった。**直せるものを直せないことにしていた**ので元に戻す。
#   公開済みで無サムネのものは「欠落」であり、todo.tsv に積んで owner の Mac で直す。
#   （公開前に付けるのが本筋なのは変わらない＝R32。ここは取りこぼしの回収路）
try:
    import json as _json2
    _reg2 = _json2.load(open(os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json"),
                             encoding="utf-8"))
    _pubtitles2 = {str(e.get("title", "")).strip() for e in _reg2 if isinstance(e, dict)}
except Exception:
    _pubtitles2 = set()


def _is_published(_stem):
    _md = os.path.join(ROOT, "CMO/outputs", _stem + ".md")
    try:
        _m = re.search(r"##\s*タイトル\s*\n```\n(.+?)\n```", open(_md, encoding="utf-8").read(), re.S)
    except OSError:
        return False
    return bool(_m) and _m.group(1).strip() in _pubtitles2


_missing_all = [b for b in _nojpg if b not in verified and b not in no_auto]
_missing_pub = [b for b in _missing_all if _is_published(b)]
missing = [b for b in _missing_all if b not in _missing_pub]
if not recent_arts:
    add("R2 実写サムネ", "OK", "直近21日の対象記事なし")
elif missing:
    add("R2 実写サムネ", "BROKEN",
        f"直近{len(recent_arts)}本中 {len(missing)}本がサムネ未取得(例:{missing[0][:26]}…)"
        " → ops/run_requests/ にpushして note-thumbnails を起動"
        + (f"／別に**公開済みで無サムネのまま {len(_missing_pub)}本**"
           f"（`ops/header_image_todo.tsv` に積んで `bash ops/fix_header_images.sh` で後から付けられる）"
           if _missing_pub else ""))
elif _missing_pub:
    # ★2026-09-23: **ここが抜けていた。** 直前の修正は BROKEN 側の文言だけ直しており、
    #   OK 側は _missing_pub を無視したまま「すべてサムネ有り」と言っていた。
    #   実際、公開済みで無サムネの16本があるのに OK が出ていた。
    #   今朝 R2d で「文言だけ直して検出器を直していない」と書いた直後に、同じことをやっている。
    #   公開済みでも後から付けられる（fix_header_images.sh）ので、**これは欠落として数える**。
    add("R2 実写サムネ", "STALE",
        f"未公開分はすべてサムネ有り。ただし**公開済みで無サムネのまま {len(_missing_pub)}本**"
        f"(例:{sorted(_missing_pub)[0][:26]}…) → サムネを取って `_verified` に入れ、"
        f"`ops/header_image_todo.tsv` に積んで `bash ops/fix_header_images.sh` で後から付ける")
else:
    add("R2 実写サムネ", "OK", f"直近{len(recent_arts)}本すべてサムネ有り（公開済みの無サムネも0本）")

# R2e: _verified.txt に載っているのに jpg が存在しない＝「owner確認済みだから対象外」で
# 静かに落ちていた分。旧R2は verified を存在確認の**前に**除外していたため、一度載せた記事は
# 画像が消えても永久にOKだった（CQO指摘）。窓に関係なく _verified 全件を見る。
_v_all_missing = sorted(b for b in verified
                        if not os.path.exists(os.path.join(thumbdir, b + ".jpg")))
if _v_all_missing:
    add("R2e 消えたverifiedサムネ", "BROKEN",
        f"_verified.txt 掲載 {len(verified)}件のうち **{len(_v_all_missing)}件の jpg が存在しない**"
        f"(例:{_v_all_missing[0][:30]}…) → 再取得するか _verified から外す")
else:
    add("R2e 消えたverifiedサムネ", "OK", f"_verified.txt 掲載 {len(verified)}件すべて jpg 実在")

# R2f: _verified.txt に載っている記事の見出し画像が、code が目視で落としたファイル
# (fetch_thumbnails_wikimedia.REJECTED_FILES) になっていないか。
# 2026-09-15 実測で1件検出＝**高岡大仏の記事に宇都宮大仏の写真が承認済みで入っていた**。
# 目視verifyは人（私）の目なので抜ける。落とした事実を名前で持っておけば、
# 承認リストに残っている取りこぼしを機械で拾える。
try:
    import importlib.util as _ilu, json as _json
    _fwp = os.path.join(ROOT, "CDO/outputs/note_publisher/fetch_thumbnails_wikimedia.py")
    _spec = _ilu.spec_from_file_location("_fw", _fwp)
    _fw = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_fw)
    _provp = os.path.join(thumbdir, "_provenance.json")
    _prov = _json.load(open(_provp, encoding="utf-8")) if os.path.exists(_provp) else {}
    # ★母数を必ず出す。provenance にファイル名が無い stem は**判定できていない**のであって
    # 「該当なし」ではない。旧版は 119件の顔をして実際は19件しか見ておらず、同じスクリプトの
    # R16 が「100件が未記録」と正しく言っているのに R2f だけ知らないふりをしていた（CQO中1）。
    _bad2f, _judged = [], 0
    for _stem in verified:
        _rec = _prov.get(_stem)
        _f2f = _rec.get("file") if isinstance(_rec, dict) else None
        if not _f2f:
            continue                      # 出典未記録＝判定不能
        _judged += 1
        if _fw._is_rejected_file(_f2f):
            _bad2f.append((_stem, _f2f))
    _unk = len(verified) - _judged
    _note2f = (f"（判定できた {_judged}件 / 出典未記録で未検査 {_unk}件 / _verified 計 {len(verified)}件。"
               f"REJECTED_FILES {len(_fw.REJECTED_FILES)}件と照合。"
               f"※この検査は**過去に落とした名前**しか見ないので、初出の誤サムネは原理的に拾えない）")
    if not verified:
        add("R2f 落とした画像の再承認", "STALE", "_verified.txt が空＝未検査")
    elif _bad2f:
        add("R2f 落とした画像の再承認", "BROKEN",
            f"目視で落としたファイルが _verified に残っている {len(_bad2f)}件"
            f"(例:{_bad2f[0][0][:24]}… ← {str(_bad2f[0][1])[:34]}) → _verified から外して再取得 {_note2f}")
    elif _judged < len(verified) * 0.8:
        add("R2f 落とした画像の再承認", "STALE",
            f"被覆が足りない＝判定できたのは {_judged}/{len(verified)} 件だけ。"
            f"該当なしと言い切れない {_note2f}")
    else:
        add("R2f 落とした画像の再承認", "OK", f"該当なし {_note2f}")
except Exception as _e:
    add("R2f 落とした画像の再承認", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R20 報告と実体の突き合わせ: ops/cowork_run.sh が publisher の出力から grep している文字列が、
# publisher のソースに**実在するか**。
# 2026-09-12 実測: cowork_run.sh は「写真サムネは未設定」を grep して件数を数えていたが、
# publish_to_note.py はその文字列を**どこにも出していなかった**。結果、報告の
# 「写真サムネ未設定 N件」は**構造的に常に 0**で、何も測っていなかった。
# にもかかわらず、その 0 を「サムネが全部付いた証拠」として何日も報告に使っていた。
# 「報告する側」と「報告される側」は別ファイルなので、片方だけ直すとこの断線が起きる。
try:
    _runsh = os.path.join(ROOT, "ops/cowork_run.sh")
    _pubpy = os.path.join(ROOT, "CDO/outputs/note_publisher/publish_to_note.py")
    if not (os.path.exists(_runsh) and os.path.exists(_pubpy)):
        add("R20 報告と実体の突き合わせ", "STALE", "cowork_run.sh か publish_to_note.py が無い＝未検査")
    else:
        _rs = open(_runsh, encoding="utf-8").read()
        # ★**実際に出力される文字列だけ**を対象にする。ソース全文を検索すると、
        # **この検査自身が書いたコメント**に同じ文字列があるだけで「実在する」と誤判定する
        # （最初の実装がそうで、回帰テストが鳴らずに発覚した）。
        # ただし print() だけを見るのも誤りで、publisher は**sys.exit() でも**メッセージを出す
        # （ログイン切れは sys.exit）。両方を対象にしないと今度は誤検知（狼少年）になる。
        # 出力先スクリプトも1本ではない＝日次実行は publish_to_note.py と publish_paid_note.py の
        # 両方を回し、その出力をまとめて grep している。両方を突き合わせ対象にする。
        # 2026-09-22: コメント巡回の件数は **sed で抜いている**ため、grep だけを見ていた R20 は
        # それらを一度も検査していなかった（＝「写真サムネ未設定」と同じ断線が、
        # 別の抜き出し方で残っていた）。producer に fetch_note_comments.py も加える。
        _srcs = [_pubpy,
                 os.path.join(ROOT, "CDO/outputs/note_publisher/publish_paid_note.py"),
                 os.path.join(ROOT, "CDO/outputs/note_publisher/fetch_note_comments.py")]
        _ps_parts = []
        for _sp in _srcs:
            if not os.path.exists(_sp):
                continue
            _txt = open(_sp, encoding="utf-8").read()
            # 2026-09-22: 呼び出し式を正規表現で切り出す方法は**括弧で破綻する**。
            # 「未公開(draft)」のように文言自体に ")" が入ると `\(.*?\)` が途中で閉じ、
            # 実在する文言を「無い」と報告した（狼少年の一歩手前）。出力関数名も print だけでなく
            # log(...) があり、そちらも見落としていた。
            # → **ソース中の文字列リテラルを全部集める**方式に変える。コメントはリテラルではないので
            #   「検査自身のコメントに一致して OK が出る」という最初の誤りも同時に防げる。
            _ps_parts += [m.group(0) for m in
                          re.finditer(r'"(?:[^"\\\n]|\\.)*"' + "|'(?:[^'\\\\\n]|\\\\.)*'", _txt)]
        _ps = "\n".join(_ps_parts)
        # `echo "$out" | grep -q "…"` / `grep -qE "A|B"` で publisher 出力を見ている行を拾う
        _pats = []
        for _m in re.finditer(r'echo\s+"\$out"\s*\|\s*grep\s+-q(E?)\s+"([^"]+)"', _rs):
            _alts = _m.group(2).split("|") if _m.group(1) == "E" else [_m.group(2)]
            for _a in _alts:
                _a = _a.strip()
                if _a:
                    _pats.append(_a)
        # sed で件数を抜いている行も対象にする。`sed -n 's/.*<文言> \([0-9]*\).*/\1/p'`
        for _m in re.finditer(r"sed\s+-n\s+'s/\.\*(.+?)\\\(\[0-9\]\*\\\)", _rs):
            _t = _m.group(1).strip()
            if _t:
                _pats.append(_t)
        _dead = [a for a in _pats if a not in _ps]
        if not _pats:
            add("R20 報告と実体の突き合わせ", "STALE",
                "cowork_run.sh から grep 対象を1つも抽出できなかった＝検査できていない")
        elif _dead:
            add("R20 報告と実体の突き合わせ", "BROKEN",
                f"cowork_run.sh が数えている文字列のうち **{len(_dead)}件が出力側のソースに文字列として存在しない**"
                f"（例:「{_dead[0][:24]}」）→ その件数は常に0＝何も測っていない。"
                f"（検査した grep パターン {len(_pats)}件）")
        else:
            add("R20 報告と実体の突き合わせ", "OK",
                f"cowork_run.sh が数える {len(_pats)}件の文言はすべて出力側（publisher 2本＋コメント巡回）の文字列に実在する")
except Exception as _e:
    add("R20 報告と実体の突き合わせ", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R21 在庫があるのにキューが空: 2026-09-14/15 の日次実行が**公開0件**だった。
# 原因は drafts/queue/ が空だったこと＝code の投入漏れで、在庫（未公開の完成記事）は4本あった。
# R18 は「キューが空なら STALE」と言うだけで、**在庫があるのに空**という状態を区別しない。
# 記事を書いても投入しなければ1本も出ないので、ここは能動的に鳴らす。
try:
    _qdir = os.path.join(ROOT, "drafts/queue")
    _q = [f for f in glob.glob(os.path.join(_qdir, "*.md"))] if os.path.isdir(_qdir) else []
    _regp = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")
    _pub_titles = set()
    if os.path.exists(_regp):
        import json as _j21
        def _w21(o):
            if isinstance(o, dict):
                for _k, _v in o.items():
                    if _k in ("title", "file", "filename") and isinstance(_v, str):
                        _pub_titles.add(os.path.basename(_v))
                for _v in o.values():
                    _w21(_v)
            elif isinstance(o, list):
                for _v in o:
                    _w21(_v)
        _w21(_j21.load(open(_regp, encoding="utf-8")))
    # 「本文が書かれていて、まだ公開台帳に載っていない」記事を在庫とみなす（タイトル一致で突合）
    # ★母数を「直近30日分の日付を持つ記事」に絞る。CMO/outputs には数ヶ月分のファイルがあり、
    # 過去のタイトル改稿などで台帳と突き合わない古い記事が大量に残る。全件を「在庫」と数えると
    # 「未投入の在庫151本」のような**意味のない大きな数**が出て、メッセージが嘘になる
    # （母数を確かめずに数を出すのは、このリポジトリで繰り返している失敗そのもの）。
    _cut = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    _stock = []
    for _f in sorted(glob.glob(os.path.join(ROOT, "CMO/outputs/2026-*_note記事_*.md"))):
        if os.path.basename(_f)[:10] < _cut:
            continue
        _t = open(_f, encoding="utf-8").read()
        _m = re.search(r"## タイトル\n```\n(.+?)\n```", _t)
        if not _m:
            continue
        if _m.group(1).strip() in _pub_titles:
            continue
        if os.path.basename(_f) in {os.path.basename(x) for x in _q}:
            continue
        _stock.append(os.path.basename(_f)[:-3])
    if not _q and _stock:
        add("R21 在庫があるのにキューが空", "BROKEN",
            f"公開キューが空なのに**未公開の完成記事が {len(_stock)}本**ある"
            f"(例:{_stock[-1][:30]}…) → 次の日次実行が**公開0件**になる。drafts/queue/ へ投入する")
    elif not _q:
        add("R21 在庫があるのにキューが空", "OK", "キューは空だが未公開の在庫も無い＝投入漏れではない")
    else:
        add("R21 在庫があるのにキューが空", "OK",
            f"キューに {len(_q)}本（未投入の在庫 {len(_stock)}本）")
except Exception as _e:
    add("R21 在庫があるのにキューが空", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R22 日次実行(cowork側)の生存: 最後に auto-publish 報告が届いたのはいつか。
# R33 ワーカー起動の不発: R22 は cowork の**報告が届いたか**しか見ていないので、
# 「起動はしたが本体が1行も動かず、それでも rc=0 で終わった」便を拾えない。
# 実測(2026-09-23 08:45): ランチャーの `$CLA` が空のまま実行され
# `run_worker.sh: line 51: : command not found` だけが並び、キューに3本あるのに公開0本。
# それでも `exit_code=0` だった（`| tee` を挟むとパイプラインの終了コードは tee のものになるため）。
# ここでは **最新の worker ログの終了コードと launcher_error 行**を見る。
_wlogs = sorted(glob.glob(os.path.join(ROOT, "ops/logs/worker_2*.log")))
if not _wlogs:
    add("R33 ワーカー起動の不発", "STALE", "worker ログが1件も無い＝判定不能")
else:
    _wl = _wlogs[-1]
    _wtxt = open(_wl, encoding="utf-8", errors="ignore").read()
    _wname = os.path.basename(_wl)
    _rc = ""
    for _ln in _wtxt.splitlines():
        if _ln.startswith("exit_code="):
            _rc = _ln.split("=", 1)[1].strip()
    _lerr = [l for l in _wtxt.splitlines() if l.startswith("launcher_error=")]
    # 旧ランチャー（2026-09-23 の修正前）は本体が空実行でも rc=0 を出すので、
    # **文言でも見る**。積み上がった worker.log の tail を送っていた時期のログには
    # 過去便の失敗も混ざるため、これは「疑い」までにとどめ、rc と launcher_error を主にする。
    _sig = ("command not found" in _wtxt) or ("Not logged in" in _wtxt)
    if _lerr:
        add("R33 ワーカー起動の不発", "BROKEN",
            f"最新便({_wname})が**本体を動かせずに終わっている**＝{_lerr[-1][len('launcher_error='):][:60]}"
            " → owner の Mac 側の対応が要る")
    elif _rc not in ("", "0"):
        add("R33 ワーカー起動の不発", "BROKEN",
            f"最新便({_wname})の exit_code={_rc} → ログ本文を読んで原因を切り分ける")
    elif _sig:
        add("R33 ワーカー起動の不発", "STALE",
            f"最新便({_wname})は rc=0 だが、ログに `command not found` か `Not logged in` がある。"
            "旧ランチャーは積み上がった worker.log の tail を送っていたので**過去便の残骸の可能性**もある。"
            "次の便が新ランチャーで走れば判別できる")
    else:
        add("R33 ワーカー起動の不発", "OK", f"最新便({_wname})は起動に成功している（rc={_rc or 'なし'}）")

# R8 は STATE.md の更新日しか見ておらず、**code（私）が動いていれば OK を出す**。
# つまり Mac 側の cron が止まっていても OK のままで、実際 2026-09-16 の 08:00 実行が
# 丸ごと落ちたのに気づいたのは数日後だった。「誰が動いているか」を取り違えていた。
# 一次証拠＝cowork が投函する auto-publish 報告のファイル更新時刻（processed/ 込み）。
try:
    _rep = sorted(
        glob.glob(os.path.join(ROOT, "ops/outbox/*_cowork_code.yaml")) +
        glob.glob(os.path.join(ROOT, "ops/processed/*_cowork_code*.yaml")),
        key=lambda f: os.path.getmtime(f))
    _pubrep = [f for f in _rep
               if "auto-publish" in open(f, encoding="utf-8", errors="ignore").read()[:400]]
    if not _pubrep:
        add("R22 日次実行の生存", "STALE", "auto-publish 報告が1件も無い＝判定不能")
    else:
        _age_h = (time.time() - os.path.getmtime(_pubrep[-1])) / 3600
        _last = os.path.basename(_pubrep[-1])
        if _age_h > 26:
            add("R22 日次実行の生存", "BROKEN",
                f"最後の auto-publish 報告から **{_age_h:.0f}時間**（{_last}）"
                f" → Mac側の日次実行(crontab 0 8 * * *)が動いていない疑い。"
                f" `crontab -l` と `ops/logs/cron.log` を確認する")
        else:
            add("R22 日次実行の生存", "OK",
                f"最後の auto-publish 報告は {_age_h:.0f}時間前（{_last}）")
except Exception as _e:
    add("R22 日次実行の生存", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R23 ハッシュタグ: 公開キューの記事に `## ハッシュタグ` ブロックがあるか。
# 2026-09-19 実測: **2026-08-22 以降に書いた記事にタグが1本も付いていなかった**（約25本）。
# publisher は `## ハッシュタグ` の有無でしか判断しないので、書き忘れれば**タグ0個で公開される**。
# note ではタグがタグページ・おすすめ経由の主要な発見経路なので、これは reach の直接的な取りこぼし。
# 385本中295本にはタグがあるのに、途中から私が書かなくなっていた＝**人が書く前提のものは必ず抜ける**。
try:
    _qmd = glob.glob(os.path.join(ROOT, "drafts/queue/*.md"))
    _notag, _thin = [], []
    for _f in _qmd:
        _t = open(_f, encoding="utf-8").read()
        _m = re.search(r"##\s*ハッシュタグ.*?\n```\n(.+?)\n```", _t, re.S)
        if not _m:
            _notag.append(os.path.basename(_f)[:-3])
        elif len(re.findall(r"#\S+", _m.group(1))) < 5:
            _thin.append(os.path.basename(_f)[:-3])
    if not _qmd:
        add("R23 ハッシュタグ", "STALE", "公開キューが空＝未検査")
    elif _notag:
        add("R23 ハッシュタグ", "BROKEN",
            f"**タグ無しの記事が {len(_notag)}本**(例:{_notag[0][:30]}…) → タグ0個で公開されてしまう。"
            f"`## ハッシュタグ` ブロックを足す")
    elif _thin:
        add("R23 ハッシュタグ", "BROKEN",
            f"タグが5個未満の記事が {len(_thin)}本(例:{_thin[0][:30]}…) → 発見経路が細くなる")
    else:
        add("R23 ハッシュタグ", "OK", f"キュー {len(_qmd)}本すべてに5個以上のタグあり")
except Exception as _e:
    add("R23 ハッシュタグ", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R24 見出し画像の未修復: 画像なしで公開された記事が残っていないか。
# 2026-09-18 実測: publisher のサムネ用セレクタ7候補が全部Timeout（note のUI変更）し、
# **5本が見出し画像なしで公開された**。note の一覧・SNSカードは画像で決まるので、無画像は
# そのまま clickthrough の損失になる。owner が ops/fix_header_images.sh を回して DONE を付けるまで
# 未完として出し続ける（「対応予定」と覚えているだけでは必ず流れる）。
try:
    _todo = os.path.join(ROOT, "ops/header_image_todo.tsv")
    if not os.path.exists(_todo):
        add("R24 見出し画像の未修復", "STALE", "ops/header_image_todo.tsv が無い＝未検査")
    else:
        _rows = [l for l in open(_todo, encoding="utf-8").read().splitlines()
                 if l.strip() and not l.startswith("#")]
        _pend = [l.split("\t")[0] for l in _rows if not l.startswith("DONE")]
        if _pend:
            add("R24 見出し画像の未修復", "BROKEN",
                f"**画像なしで公開されたまま {len(_pend)}本**({_pend[0]}…) → "
                "owner の Mac で `bash ops/fix_header_images.sh`")
        else:
            add("R24 見出し画像の未修復", "OK", f"{len(_rows)}本すべて修復済み")
except Exception as _e:
    add("R24 見出し画像の未修復", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R25 X投稿の生存: キューに溜めるだけで一度も投稿されていない状態を検知する。
# 2026-09-17 実測: x_queue に38スレッド（現在40）あるのに ops/logs/x_posted.tsv が存在せず、
# **投稿実績ゼロ**。素材を作る側（code）だけが動いていて、出す側が一度も動いていなかった。
# 作った物が出ていないことは、作っていないことと reach 上は同じ。
try:
    _xlog = os.path.join(ROOT, "ops/logs/x_posted.tsv")
    _q = os.path.join(ROOT, "ops/x_queue.txt")
    _pending_th = 0
    if os.path.exists(_q):
        for _l in open(_q, encoding="utf-8"):
            if re.match(r"^===\s*(.+?)\s*===\s*$", _l.strip()) and "[POSTED]" not in _l:
                _pending_th += 1
    # 2026-09-19: **ファイルが在るだけで OK を出していた**。--undo で中身が空になった直後に
    # 「累計0件・最終0.0日前」で ✅ が出た＝実績ゼロなのに正常と報告する状態。
    # 「ファイルの有無」ではなく **行数（＝実際に出た本数）** で判定する。
    _xrows = 0
    if os.path.exists(_xlog):
        _xrows = len([l for l in open(_xlog, encoding="utf-8") if l.strip()])
    if _xrows == 0:
        add("R25 X投稿の生存", "BROKEN",
            f"**投稿実績ゼロ**（記録0行）／未投稿スレッド {_pending_th}本が滞留 → "
            "owner の Mac で `bash ops/run_x.sh --manual`（APIキー不要・文面を出して手で投稿）"
            "、またはキーを入れて `--go`")
    else:
        _age = days(_xlog)
        _n = _xrows
        if _age > 7:
            add("R25 X投稿の生存", "STALE",
                f"最後の投稿が {_age:.0f}日前（累計{_n}件）／未投稿 {_pending_th}本")
        else:
            add("R25 X投稿の生存", "OK", f"累計{_n}件・最終 {_age:.1f}日前／未投稿 {_pending_th}本")
except Exception as _e:
    add("R25 X投稿の生存", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R26 キューの題材重複: キューに入れた記事が、既公開と同題材で門前払いされないか。
# 2026-09-18 実測: 前日にキューへ入れた2本が**両方とも公開時の題材ゲートではねられ、公開0件**になった。
# 在庫は108本あるのに0件。「キューは埋まっている」という見た目だけ正しく、中身が全部通らない状態。
# 公開の瞬間に判定するのでは遅い（その日の枠が消える）ので、**入れた時点で同じ判定をする**。
# ★2026-09-25 修正: ここは台帳の `topic` フィールドだけを見る**独自実装**だった。
#   公開側のゲートは `topic_conflict()`（タイトルの題材トークン照合）も使うため、**判定が食い違った**。
#   実害: 「氷見と高岡：港町と古都は何が違うのか」を R26 は「重複なし」と言い、
#   公開側は『富山2日完璧ガイド：氷見と高岡を2日で巡る旅程』と同題材として弾いた。
#   判定の実装が2つあれば、いつか必ずずれる。**publisher の関数をそのまま呼ぶ**。
#   （publish_to_note.py は Playwright 未導入でも import できるようにした＝2026-09-25）
try:
    _q26 = sorted(glob.glob(os.path.join(ROOT, "drafts/queue/*.md")))
    if not _q26:
        add("R26 キューの題材重複", "STALE", "公開キューが空＝未検査")
    else:
        import sys as _sys26
        _pubdir = os.path.join(ROOT, "CDO/outputs/note_publisher")
        if _pubdir not in _sys26.path:
            _sys26.path.insert(0, _pubdir)
        import publish_to_note as _P26          # 失敗したら except で STALE（黙って通さない）
        _dup = []
        for _f in _q26:
            _t = open(_f, encoding="utf-8").read()
            _m = re.search(r"##\s*タイトル\s*\n```\n(.+?)\n```", _t, re.S)
            if not _m:
                continue
            _title = _m.group(1).strip()
            _hit = _P26.topic_conflict(_title)
            if _hit:
                _dup.append((os.path.basename(_f)[:-3], _hit[0].get("title", ""), sorted(_hit[1])))
        if _dup:
            _b, _pt, _sh = _dup[0]
            add("R26 キューの題材重複", "BROKEN",
                f"**既公開と同題材の記事が {len(_dup)}本**: {_b[:30]}… が「{'/'.join(_sh[:2])}」で "
                f"『{_pt[:30]}…』と重なる → 公開時にはねられてその日の枠が消える。"
                "キューから外すか、切り口が違うなら --allow-topic-dup で出す")
        else:
            add("R26 キューの題材重複", "OK",
                f"キュー {len(_q26)}本すべて、公開側と同じ判定(topic_conflict)で重複なし")
except Exception as _e:
    add("R26 キューの題材重複", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R32 サムネ未確定のままキューに入れていないか。
# 2026-09-22 実測: 直近に公開した7本（衣替え/むかご/二番穂/鮭/落ち葉/柿/渡り鳥）は**全部**、
# サムネが届く前に公開され、note 既定サムネで出た。画像はそのあと到着している。
# **公開済みの記事に後からサムネは付かない**ので、取得も検品もまるごと無駄打ちになる。
# キューに入れる時点で、その記事のサムネが **採用済み(_verified) になっていなければならない**。
# ★2026-09-23 方針変更（オーナー確定）: **サムネは全記事に必ず付ける**。
#   それまでは「_no_auto（無サムネ確定）でもよい」としていたが、これは code が勝手に作った
#   「誤サムネより無サムネが正」という基準で、**9月の30本中11本が無サムネで公開されていた**。
#   指示は「毎日サムネつきで書く」なので、この運用自体が誤りだった。
#   判定は「題材が合っていれば採用」で、落とすのは**明らかに別物**のときだけ。落としたら取り直す。
#   → **キューに _no_auto の記事が入っていたら BROKEN**（公開済みで後から付けられない記事を除く）。
try:
    _q32 = sorted(glob.glob(os.path.join(ROOT, "drafts/queue/*.md")))
    if not _q32:
        add("R32 サムネ未確定のまま投入", "OK", "公開キューが空＝該当なし")
    else:
        _undecided, _noimg = [], []
        for _f in _q32:
            _st = os.path.basename(_f)[:-3]
            if _st in verified:
                continue
            (_noimg if _st in no_auto else _undecided).append(_st)
        if _undecided or _noimg:
            _msg = []
            if _undecided:
                _msg.append(f"**サムネ未確定 {len(_undecided)}本**({_undecided[0][:32]}…)")
            if _noimg:
                _msg.append(f"**無サムネのまま {len(_noimg)}本**({_noimg[0][:32]}…)"
                            "＝2026-09-23 の方針変更でサムネは全記事必須。"
                            "題材が合っていれば採用し、明らかな別物なら語を変えて取り直す")
            add("R32 サムネ未確定のまま投入", "BROKEN",
                "／".join(_msg) +
                " → このまま公開すると note 既定サムネで出て、**あとから画像は付けられない**")
        else:
            add("R32 サムネ未確定のまま投入", "OK",
                f"キュー {len(_q32)}本すべて、サムネが採用済み(_verified)になっている")
except Exception as _e:
    add("R32 サムネ未確定のまま投入", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R27 サムネ検索語の登録漏れ: 新しい記事を書いたのに JP_QUERY へ題材語を登録し忘れていないか。
# 2026-09-20 実測: 09-20の2本を書いてサムネ依頼まで出したのに、fetcher の JP_QUERY に登録が無く
# **クラウドの取得が丸ごと空振り**した（成功 0 / 失敗 59）。しかもログの文言は「土地名を含むクエリが無い」で、
# 実際の原因（検索語が1本も無い）と食い違っていた。記事を書くたび人が手で登録する仕組みは必ず忘れる。
try:
    _fq = open(os.path.join(ROOT, "CDO/outputs/note_publisher/fetch_thumbnails_wikimedia.py"),
               encoding="utf-8").read()
    _keys = re.findall(r'^\s*\("([^"]+)",\s*[\["]', _fq, re.M)
    _thumbdir = os.path.join(ROOT, "CDO/outputs/note_publisher/thumbnails")
    _noauto = set()
    _na = os.path.join(_thumbdir, "_no_auto.txt")
    if os.path.exists(_na):
        _noauto = {l.strip() for l in open(_na, encoding="utf-8") if l.strip() and not l.startswith("#")}
# ★2026-09-21 修正: ここは `os.path.getmtime()` で「直近1週間」を切っていたが、**mtime は記事の
#   属性ではなく checkout の属性**。コンテナは使い捨て(A7)なので clone した瞬間に全記事の mtime が
#   同じ「今」になり、**353本すべてが「直近1週間に書いた記事」として母数に入っていた**
#   （実測: 353本中331本はファイル名の日付では1週間より古い）。
#   R21 が同じ罠を避けて**ファイル名の日付**で切っているのに、ここだけ mtime のままだった。
#   日付は記事名に入っていて checkout で変わらないので、そちらで切る。
    _cut = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    # 窓を直近1週間に絞ったぶん、**窓の外に溜まっている分は必ず数えて出す**。
    # そうしないと「母数を狭めて警報を消しただけ」になる（このリポジトリで繰り返している失敗）。
    _unreg, _old_unreg = [], []
    for _f in glob.glob(os.path.join(ROOT, "CMO/outputs/*_note記事_*.md")):
        _b = os.path.basename(_f)[:-3]
        if os.path.exists(os.path.join(_thumbdir, _b + ".jpg")) or _b in _noauto:
            continue                          # 取得済み／意図的な無サムネは対象外
        if not any(k in _b for k in _keys):
            (_unreg if _b[:10] >= _cut else _old_unreg).append(_b)
    _bl = (f"／**窓の外に {len(_old_unreg)}本の積み残し**（過去分・日次では鳴らさないが消えてはいない。"
           f"最古 {sorted(_old_unreg)[0][:26]}…）" if _old_unreg else "")
    if _unreg:
        add("R27 サムネ検索語の登録漏れ", "BROKEN",
            f"**JP_QUERY に検索語が無い記事が {len(_unreg)}本**({_unreg[0][:34]}…) → "
            "クラウドが取りに行けず空振りする。fetch_thumbnails_wikimedia.py の JP_QUERY に題材語を足す" + _bl)
    else:
        add("R27 サムネ検索語の登録漏れ", "OK",
            "直近1週間の未取得記事はすべて検索語が登録済み" + _bl)
except Exception as _e:
    add("R27 サムネ検索語の登録漏れ", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R28 既公開とのフック重複: 新しい記事のタイトル/書き出しが、既公開のタイトルと同じ言い回しでないか。
# 2026-09-20 実測: 「弁当を忘れても、傘は忘れるな」で1本書いたが、**2026-07-28 に同じことわざの記事を
# 公開済み**だった（「富山では、弁当を忘れても傘を忘れるな。— 変わりやすい空と、虹の話」）。
# R26 はファイル名の題材トークン（置き傘 vs 富山の空）しか見ないので**すり抜ける**。
# 題材が違っても**フック（ことわざ・言い回し）が同じなら読者には同じ記事**なので、文字列で重なりを見る。
try:
    import json as _json28
    _reg28 = _json28.load(open(os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json"),
                               encoding="utf-8"))
    _norm = lambda t: re.sub(r"[^\wぁ-んァ-ヶ一-龥]", "", re.sub(r"[はをがのにへとも、。・—\-—…]", "", t or ""))
    _ptitles = [(e.get("title", ""), _norm(e.get("title", ""))) for e in _reg28 if e.get("title")]
    _ptopics28 = {e.get("topic", "") for e in _reg28 if e.get("topic")}
    # ★2026-09-21: R27 と同じ理由で mtime をやめ、記事名の日付で切る（上の註を参照）。
    _cut28 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    # R27 と同じく、窓の外の分も数えて必ず出す（狭めて消しただけにしない）。
    _dups, _old_dups = [], []
    for _f in glob.glob(os.path.join(ROOT, "CMO/outputs/*_note記事_*.md")):
        _b = os.path.basename(_f)[:-3]
        _recent28 = _b[:10] >= _cut28
        _m = re.match(r"\d{4}-\d{2}-\d{2}_note記事_([^_]+)_", _b)
        if _m and _m.group(1) in _ptopics28:
            continue                       # 既公開＝R26/題材ゲートの担当
        _t = open(_f, encoding="utf-8").read()
        _ti = re.search(r"##\s*タイトル\s*\n```\n(.+?)\n```", _t, re.S)
        _bo = re.search(r"##\s*本文\s*\n```\n(.+?)\n```", _t, re.S)
        _head = _norm((_ti.group(1) if _ti else "") + (_bo.group(1)[:120] if _bo else ""))
        for _pt, _pn in _ptitles:
            # 8文字以上の連続一致を探す（助詞・記号を落としたうえで）
            for _i in range(0, max(0, len(_pn) - 7)):
                _frag = _pn[_i:_i + 8]
                if _frag and _frag in _head:
                    (_dups if _recent28 else _old_dups).append((_b, _pt, _frag))
                    break
            else:
                continue
            break
    _bl28 = (f"／**窓の外に {len(_old_dups)}本**（過去分・日次では鳴らさないが消えてはいない。"
             f"例 {sorted(_old_dups)[0][0][:26]}…）" if _old_dups else "")
    if _dups:
        _b, _pt, _frag = _dups[0]
        add("R28 既公開とのフック重複", "BROKEN",
            f"**既公開と同じ言い回しの記事が {len(_dups)}本**: {_b[:30]}… が「{_frag}」で "
            f"『{_pt[:34]}…』と重なる → フックを変えるか題材を差し替える" + _bl28)
    else:
        add("R28 既公開とのフック重複", "OK",
            "直近1週間の未公開記事に既公開タイトルとの重なりなし" + _bl28)
except Exception as _e:
    add("R28 既公開とのフック重複", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R29 英語ページのリンク切れ: 内部リンク先のファイルが実在するか。
# 2026-09-22 新設。英語ページは160枚を超え、記事を書くたびに「関連記事」を手で並べている。
# **存在しないページへのリンクは、踏んだ読者をそのまま失う**（North Star が海外読者なので直撃する）。
# 人が毎回目視する前提のものは必ず抜けるので機械に見張らせる。新設時点の実測は 0件。
try:
    _gd = os.path.join(ROOT, "apps/toyama-guide")
    _miss = []
    for _f in glob.glob(os.path.join(_gd, "*.html")):
        _t = open(_f, encoding="utf-8", errors="replace").read()
        for _h in set(re.findall(r'href="((?:en-|ja-|zh-|index)[^"#?]*\.html)"', _t)):
            if not os.path.exists(os.path.join(_gd, _h)):
                _miss.append(f"{os.path.basename(_f)}→{_h}")
    if _miss:
        add("R29 英語ページのリンク切れ", "BROKEN",
            f"**リンク切れ {len(_miss)}件**(例:{_miss[0]}) → 読者をそのまま失う。綴りかファイル名を直す")
    else:
        _n = len(glob.glob(os.path.join(_gd, "*.html")))
        add("R29 英語ページのリンク切れ", "OK", f"{_n}枚の内部リンクはすべて実在")
except Exception as _e:
    add("R29 英語ページのリンク切れ", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R30 サムネの地名不一致: 採用したサムネのファイル名に、記事に出てこない他所の地名が入っていないか。
# 2026-09-22 実測: **高岡万葉線の記事に京都市電（明治村の保存車両）が使われていた**。
# 出典の埋め戻しが進んで初めて分かった＝それまで1年近く、誤ったサムネのまま公開されていた。
# fetcher 側の `_place_mismatch()` は**クエリ**が土地を名乗るかしか見ず、**取れてきたファイル名**は見ない。
# 英語の一般語（"tram streetcar japan city"）で引くと、日本の写真ではあるが別の土地のものが来る。
# 記事が土地を名乗っていなければ他所で撮った写真でも構わない（仏壇/神棚＝東京の博物館は可）ので、
# **記事名に出てこない地名がファイル名にある**ときだけ鳴らす。
try:
    # ★2026-09-21: 地名リストが**手で書いた31語**しかなく、**新潟・福井・福島・千葉が入っていなかった**。
    #   そのため採用中の次の4件を素通りさせていた（いずれも富山の記事なのに県外の写真）:
    #     消雪パイプ → Snow removal - **Yuzawa, Niigata**
    #     夕方のチャイム → **福井県越前市**の防災行政無線
    #     水力発電 → **秋元湖**（福島）の水力発電所
    #     おはぎ → Botamochi, **Katori-city**（千葉）
    #   思いついた地名を並べる作りは、思いつかなかった地名を永久に見逃す。
    #   **47都道府県を漏れなく（富山＝地元だけ除く）** 並べ、ローマ字も対で持つ。
    _PREF = [
        ("北海道", "hokkaido"), ("青森", "aomori"), ("岩手", "iwate"), ("宮城", "miyagi"),
        ("秋田", "akita"), ("山形", "yamagata"), ("福島", "fukushima"), ("茨城", "ibaraki"),
        ("栃木", "tochigi"), ("群馬", "gunma"), ("埼玉", "saitama"), ("千葉", "chiba"),
        ("東京", "tokyo"), ("神奈川", "kanagawa"), ("新潟", "niigata"), ("石川", "ishikawa"),
        ("福井", "fukui"), ("山梨", "yamanashi"), ("長野", "nagano"), ("岐阜", "gifu"),
        ("静岡", "shizuoka"), ("愛知", "aichi"), ("三重", "mie"), ("滋賀", "shiga"),
        ("京都", "kyoto"), ("大阪", "osaka"), ("兵庫", "hyogo"), ("奈良", "nara"),
        ("和歌山", "wakayama"), ("鳥取", "tottori"), ("島根", "shimane"), ("岡山", "okayama"),
        ("広島", "hiroshima"), ("山口", "yamaguchi"), ("徳島", "tokushima"), ("香川", "kagawa"),
        ("愛媛", "ehime"), ("高知", "kochi"), ("福岡", "fukuoka"), ("佐賀", "saga"),
        ("長崎", "nagasaki"), ("熊本", "kumamoto"), ("大分", "oita"), ("宮崎", "miyazaki"),
        ("鹿児島", "kagoshima"), ("沖縄", "okinawa"),
    ]   # ※富山は地元なので入れない
    _pl = [x for pair in _PREF for x in pair] + [
        # 都道府県名を名乗らない有名地・施設名（見つけ次第足す）
        "kobe", "kanazawa", "nagoya", "kamakura", "sendai", "yokohama", "nikko", "hakone",
        "meiji-mura", "harajuku", "yuzawa", "katori", "echizen", "yokosuka", "神戸", "金沢", "名古屋",
        "鎌倉", "横浜", "日光", "箱根", "原宿", "湯沢", "香取", "越前", "江戸東京", "横須賀", "大山千枚田", "鳴門", "naruto",
    ]
    import json as _json30
    _pv = _json30.load(open(os.path.join(ROOT, "CDO/outputs/note_publisher/thumbnails/_provenance.json"),
                            encoding="utf-8"))
    _bad30 = []
    for _st in verified:
        _v = _pv.get(_st)
        if not isinstance(_v, dict):
            continue
        _f = (_v.get("file") or "").lower()
        if not _f:
            continue
        _found = [x for x in _pl if x in _f]
        # 記事名（または本文末のクレジット行）にその地名が出ていれば、開示済みとみなす
        if _found and not any(x in _st for x in _found):
            _md = os.path.join(ROOT, "CMO/outputs", _st + ".md")
            _body = open(_md, encoding="utf-8").read() if os.path.exists(_md) else ""
            # 開示のされ方は2通りある。地名をそのまま書く場合と、
            # **「※撮影地は県外」のように地名を出さずに断る**場合。
            # 地名の文字列しか探さないと後者を見落として**開示済みの記事を3件も鳴らした**
            # （消雪パイプ=「※撮影地は新潟」／さつまいも=「※撮影地は県外」／おはぎ=「撮影地は富山県外」）。
            # 要件は「県外だと読者に分かるか」なので、断り書きも開示として数える。
            _disclosed = any(x in _body for x in _found) or "撮影地" in _body
            if not _disclosed:
                _bad30.append((_st, _v.get("file"), _found[0]))
    if _bad30:
        _st, _f, _p = _bad30[0]
        add("R30 サムネの地名不一致", "BROKEN",
            f"**記事に無い地名のサムネ {len(_bad30)}件**: {_st[:30]}… に「{_p}」の写真"
            f"（{str(_f)[:40]}） → 別の土地の写真を使っていないか確認する")
    else:
        add("R30 サムネの地名不一致", "OK",
            f"採用 {len(verified)}件のうち、記事に出てこない地名を含むファイル名はなし")
except Exception as _e:
    add("R30 サムネの地名不一致", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

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
    # ★2026-09-16: **被覆を見ずに OK を出していた**。実測は 115/202 本＝56%で、
    # **87本は一度も巡回していない**。その状態で「コメント0件＝返信対象なし」と言うのは、
    # 見ていない範囲まで「無い」と断言していることになる（このリポジトリで繰り返している失敗）。
    # 公開記事の何％を見たのかを必ず出し、8割未満なら OK を出さず STALE にする。
    _regp6 = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")
    _pub_urls = set()
    try:
        import json as _j6
        def _w6(o):
            if isinstance(o, dict):
                if isinstance(o.get("url"), str):
                    _pub_urls.add(o["url"])
                for v in o.values():
                    _w6(v)
            elif isinstance(o, list):
                for v in o:
                    _w6(v)
        _w6(_j6.load(open(_regp6, encoding="utf-8")))
    except Exception:
        pass
    _swept_urls = set()
    try:
        for _l in open(sw, encoding="utf-8").read().splitlines()[1:]:
            if _l.strip():
                _swept_urls.add(_l.split("\t")[0])
    except Exception:
        pass
    _cov = (len(_swept_urls & _pub_urls) * 100 // len(_pub_urls)) if _pub_urls else 0
    _unswept = len(_pub_urls - _swept_urls)
    _cnote = (f"（公開 {len(_pub_urls)}本中 **{len(_swept_urls & _pub_urls)}本を巡回＝{_cov}%**"
              f" ／ **未巡回 {_unswept}本**）")
    if _pub_urls and _cov < 80:
        add("R6 コメント返信", "STALE",
            f"巡回した範囲ではコメント0件だが、**被覆が足りない**{_cnote}"
            f"{sweep_note} → --backlog を回して全件を見るまで「コメントは無い」と言えない")
    else:
        add("R6 コメント返信", "OK",
            f"収集は稼働中でコメント0件＝返信対象なし{_cnote}{sweep_note}")
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
# ★2026-09-22 追加: **_verified を「意図的な流用」と決めつけて検知から外していたのが穴だった**。
# 実際、おとぎの森公園2本が**埼玉の道満グリーンパーク**、富山ブラック2本が**澄んだスープのラーメン**を
# 共有しており、どちらも verified で、どちらも主題と合っていなかった（2026-09-22 に取り消し）。
# 「verifyしたから意図的なはず」は成り立たない。**verified 同士の共有は黙って除外せず、必ず明細に出す**。
# ★2026-09-23 追加: この「採用済みどうしの共有」は**毎回同じ7組を出し続けていた**。
# 中身を見たら7組とも**同一題材の別記事**（かき氷×2／蚊取り線香×2／鮎×2／高岡コロッケ×3／
# 花火×2／高岡大仏と高岡の街歩き／そば×2）で、意図的な流用だった。
# 直せないもの・直す必要のないものを毎日出し続けると、**本当に新しく現れた共有がその中に埋もれる**
# （R2 で公開済みを対象から外したのと同じ理由）。
# そこで **判断を1回だけ記録する台帳** `_shared_ok.tsv` を置き、そこに md5 がある組は数から外す。
# 台帳に無い組＝**まだ誰も見ていない共有**だけを出す。台帳は `_rejected_hashes.tsv` と同じ作法。
_sok_path = os.path.join(thumbdir, "_shared_ok.tsv")
_shared_ok = set()
if os.path.exists(_sok_path):
    for _l in open(_sok_path, encoding="utf-8"):
        _l = _l.strip()
        if _l and not _l.startswith("#"):
            _shared_ok.add(_l.split("\t")[0].strip())
_ver_shared_all = [(_h, sorted(st for st in v if st in verified))
                   for _h, v in _groups.items() if sum(1 for st in v if st in verified) >= 2]
_ver_shared = [g for _h, g in _ver_shared_all if _h not in _shared_ok]
_ver_shared_known = [g for _h, g in _ver_shared_all if _h in _shared_ok]
# ★2026-09-19 修正: 09-22 の「verified も明細に出す」対応は **報告文だけ** を直していて、
# 警報そのものは依然 verified を取り除いた数で数えていた（下の _shared が st not in verified）。
# そのため **1枚が5記事に配られていても、5本とも verified なら実質0本と数えられて ✅ が出ていた**。
# 実測(2026-09-19): 夏野菜のかご1枚が5記事（畑/家庭菜園/とうもろこし/トマト/無人販売所）に、
# 海沿いの道1枚が5記事（蜃気楼2本/魚の宝庫/海水浴/有料note）に付いていたのに OK だった。
# **配布数はverifiedを含めた全体で数える**。verified かどうかは重大度の判断にだけ使う。
_all_groups = [v for v in _groups.values() if len(v) >= 3]
_wide = [v for v in _all_groups if len(v) >= 4]                      # 4記事以上に同じ画像
_wide_used = [v for v in _wide if sum(1 for st in v if st in verified) >= 2]  # うち実際に見出しに出る
_minor = sum(1 for v in _all_groups if len(v) == 3)
_vs_note = ""
if _ver_shared:
    _vs_note = (f"／**採用済みどうしで同じ画像を共有 {len(_ver_shared)}組が未監査**"
                f"(例: {_ver_shared[0][0][:26]}…) ＝意図的な流用か、同じ誤サムネが2本に付いているかを見て、"
                f"問題なければ md5 を thumbnails/_shared_ok.tsv に記録する")
elif _ver_shared_known:
    _vs_note = f"／採用済みどうしの共有 {len(_ver_shared_known)}組はすべて監査済み(_shared_ok.tsv・同一題材の流用)"
if _wide_used:
    _ex = sorted(_wide_used, key=len, reverse=True)[0]
    add("R2d フォールバック汚染", "BROKEN",
        f"**1枚の画像が4記事以上の見出しに出ている {len(_wide_used)}組**"
        f"（最大 {len(_ex)}本: {sorted(_ex)[0][:34]}… ほか）"
        f" → 記事固有のサムネになっていない。_verified から外して個別に取り直す" + _vs_note)
elif _wide:
    add("R2d フォールバック汚染", "STALE",
        f"1枚を4記事以上で共有 {len(_wide)}組（いずれも未採用なので公開には出ない）"
        + _vs_note)
else:
    add("R2d フォールバック汚染", "OK",
        f"ユニーク画像 {len(_groups)}種／汎用配布(4本以上)なし"
        + (f"（3記事で共有 {_minor}組）" if _minor else "") + _vs_note)

# R31 中身で落とした画像の残留: REJECTED_FILES は **これから引く候補** をファイル名で弾くだけで、
# すでに thumbnails/ に落ちたコピーには効かない。実際、Marshall のビール缶は 2026-09-22 に
# REJECTED_FILES へ入れたのに、別記事(枝豆)の見出し画像としては 2026-09-19 まで残っていた。
# 出典が旧形式(文字列のみ)の 93件は元のファイル名が分からないので、**md5 でしか止められない**。
_rej_path = os.path.join(thumbdir, "_rejected_hashes.tsv")
_rej = {}
if os.path.exists(_rej_path):
    for _l in open(_rej_path, encoding="utf-8"):
        _l = _l.strip()
        if not _l or _l.startswith("#"):
            continue
        _h, _, _why = _l.partition("\t")
        _rej[_h.strip()] = _why.strip()
_left_used, _left_pool = [], []
for _h, _stems in _groups.items():
    if _h not in _rej:
        continue
    for _st in _stems:
        (_left_used if _st in verified else _left_pool).append(_st)
if _left_used:
    # 例に出す stem と、その stem 自身の理由を対にする。
    # ★最初の実装は「_rej のうち最初に見つかったハッシュの理由」を出しており、
    #   例に挙げた記事とは無関係の理由が並んでいた（メッセージだけが嘘になる型）。
    _ex_st = sorted(_left_used)[0]
    _ex_why = ""
    for _h, _stems in _groups.items():
        if _ex_st in _stems and _h in _rej:
            _ex_why = _rej[_h]
            break
    add("R31 中身で落とした画像の残留", "BROKEN",
        f"**落としたはずの画像が {len(_left_used)}本の見出しに出たままになっている**"
        f"(例: {_ex_st[:34]}…／理由: {_ex_why[:40]}…)"
        f" → _verified.txt から外し、jpg を消して取り直す"
        + (f"／未採用プールにも {len(_left_pool)}本" if _left_pool else ""))
elif _left_pool:
    # ★2026-09-23 追記: これは「公開には出ないから無害」ではない。
    # fetch_thumbnails_wikimedia.py は `if out.exists(): continue` で**jpgが在る記事を飛ばす**ので、
    # 落とした画像がそこに残っている限り、その記事は**二度と取り直されない**＝枠を塞いでいる。
    # 取り直したい記事は、jpg を消してから Action を起こすこと（消せば次のrunで対象に入る）。
    add("R31 中身で落とした画像の残留", "STALE",
        f"未採用プールに {len(_left_pool)}本残っている。見出しには出ないが、"
        f"**jpgが在る記事は取得側が飛ばす**ので取り直しの枠を塞いでいる"
        f"（取り直すなら jpg を消してから Action を起こす）")
else:
    add("R31 中身で落とした画像の残留", "OK",
        f"md5で落とした {len(_rej)}枚はどの記事にも付いていない")

# R2b サムネが実際に「使われる」か: publish は _verified.txt 掲載分しか見出し画像に使わない
# (CQO指摘D2)。jpgが在るだけでは無サムネ公開になるため、被覆を別要件で可視化する。
# ★2026-09-21: **意図的に落としたものを「登録漏れ」として鳴らしていた**。
#   栗ご飯（他県の駅弁）と有料noteの大仏（高岡大仏ではない）は目視で見て外した jpg なのに、
#   「jpg があるのに _verified に無い＝登録し忘れ」と毎回出ていた。
#   _no_auto と同じく、**中身(md5)で落としたものは対象外**にする。
#   落とした理由が残っているのに催促が続くと、本当の登録漏れが埋もれる。
_rejhash = set()
for _h, _stems in _groups.items():
    if _h in _rej:
        _rejhash.update(_stems)
unverified = [os.path.basename(f)[:-3] for f in recent_arts
              if os.path.exists(os.path.join(thumbdir, os.path.basename(f)[:-3] + ".jpg"))
              and os.path.basename(f)[:-3] not in verified
              and os.path.basename(f)[:-3] not in _rejhash]
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
    # 変数名は R2 の missing と分ける。同名だと R2 と R11 の間に処理を足したときに
    # 静かに壊れる（CQO軽2）。R2 側は add() 済みなので今は害が無いだけ。
    _sm_missing = [p for p in en_pages if f"/toyama/{p}" not in smtext]
    if not _sm_missing:
        add("R11 sitemap鮮度", "OK", f"toyama en {len(en_pages)}枚すべて sitemap 掲載")
    else:
        add("R11 sitemap鮮度", "STALE",
            f"sitemap未掲載 {len(_sm_missing)}枚(例:{_sm_missing[0]})→ python3 apps/toyama-guide/gen_sitemap.py")

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

# R19 A4自己申告の一貫性: 同じファイルの中で「事実検証ノート」と「記事情報」の A4 欄が
# 食い違っていないか。2026-09-14 に、検証ノート側だけ実態に直して**記事情報側は断定形のまま**
# 残す、という状態が2本で起きた（CQO重大3）。A4欄は「次に書く人」と「点検」が最初に読む欄なので、
# 同じファイルに真の自己申告と偽の自己申告が同居しているのが最も危険。
# 判定: 本文中にクレジット行（＝撮影者名などの固有名詞が入る）があるのに、記事情報の A4 行が
# 「〜なし」で終わる断定形だけなら BROKEN。留保（ただし/クレジット/表示義務）があれば OK。
try:
    _bad19 = []
    for _f in recent_arts:
        _t = open(_f, encoding="utf-8").read()
        _has_credit = "（見出し画像：" in _t
        _m19 = re.search(r"^- A4[:：](.*)$", _t, re.M)
        if not _has_credit or not _m19:
            continue
        _a4 = _m19.group(1)
        if not re.search(r"ただし|クレジット|表示義務|本文には", _a4):
            _bad19.append(os.path.basename(_f)[:-3])
    if not recent_arts:
        add("R19 A4自己申告の一貫性", "STALE", "直近21日の対象記事なし＝未検査")
    elif _bad19:
        add("R19 A4自己申告の一貫性", "BROKEN",
            f"クレジット行があるのに 記事情報のA4欄が『〜なし』の断定のまま {len(_bad19)}本"
            f"(例:{_bad19[0][:30]}…) → 検証ノートと同じ文言に揃える")
    else:
        add("R19 A4自己申告の一貫性", "OK",
            f"直近{len(recent_arts)}本: クレジット行のある記事のA4欄はすべて留保付き")
except Exception as _e:
    add("R19 A4自己申告の一貫性", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

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
    # 2026-09-11(CQO指摘・重大1): 従来は「表示義務ありと判定できた分」しか数えず、
    # **ライセンス未記録の96本が静かに対象外に落ちて** ✅ が出ていた。母数を必ず出す。
    # Commons は CC BY / BY-SA の比率が高く、未記録の中に表示義務のあるものが混じっている可能性が高い。
    # 2026-09-22: 「未記録」を**まだ試していない**ものと**試したが照合できなかった**ものに分ける。
    # backfill は毎run同じ先頭25件を取り直していて残りを一度も試していなかった（修正済み）。
    # 両者を一緒に数えていると、**進んでいないのか到達不能なのかが報告から分からない**。
    _need = _cc0 = _untried = _failed = 0
    for _k in verified:
        _v = _prov2.get(_k)
        _lic = _v.get("license") if isinstance(_v, dict) else None
        if _lic:
            if _tc.needs_credit(_lic):
                _need += 1
            else:
                _cc0 += 1
        elif isinstance(_v, dict) and _v.get("match") == "failed":
            _failed += 1        # 3回試して Commons 上に一致が見つからなかった（Pexels由来の疑い等）
        else:
            _untried += 1
    _unknown = _untried + _failed
    _cov = (f"（採用 {len(verified)}件の内訳: 表示義務あり {_need} / CC0・PD {_cc0} / "
            f"**未照合 {_untried} / 照合不能 {_failed}**）")
    if _nocredit:
        add("R16 見出し画像のクレジット", "BROKEN",
            f"表示義務なのにクレジット無し {len(_nocredit)}本(例:{_nocredit[0][:26]}…){_cov}"
            " → `python3 CDO/outputs/note_publisher/thumb_credit.py --apply <md>`")
    elif _unknown > 10:
        add("R16 見出し画像のクレジット", "STALE",
            f"判定できたものは全てクレジット済だが、**{_unknown}件がライセンス未記録＝判定できていない**{_cov}"
            " → backfill_provenance.py が毎run 25件ずつ照合中（codeはCommonsに繋げない=A1）。"
            "**未照合が減らないなら回っていない**＝試行回数は thumbnails/_backfill_attempts.json を見る")
    else:
        add("R16 見出し画像のクレジット", "OK", f"表示義務のある採用サムネはすべてクレジットあり{_cov}")
except Exception as _e:
    add("R16 見出し画像のクレジット", "STALE", f"判定不能: {type(_e).__name__} {str(_e)[:60]}")

# R17 文体の反復(A5/A6): メタの自己申告ではなく**本文から測る**。
# 2026-09-11(CQO指摘・重大2/3/4): 記事メタのA6欄は「英語見出し」と「英語の締め」しか比較しておらず、
#   ①日本語の冒頭・言い回し ②同日の相方との重複 ③英語の統語フレーム(命令形+and)
# が構造的な死角になっていた。実際「Live in Toyama and …」が命令形+and の4本目、
# 「たいてい〜な顔をされる／驚く」が直近5本中4本、締めの「Xではない。Yだ。」が3本連続になりかけていた。
# 人が書くメタを信じず、直近の本文どうしを機械で突き合わせる。
import re as _re17
# 2026-09-12(CQO指摘・高6): 窓が「7本」＝1日2本なので**3.5日分**しかなく、
# 実際の衝突相手（09-08虫の声・09-09初冠雪）が両方とも窓の外だった。**日数で切る**。
_A6_DAYS = 10
_cut17 = (datetime.date.today() - datetime.timedelta(days=_A6_DAYS)).isoformat()
_arts17 = sorted([f for f in glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md"))
                  if "サムネ生成プロンプト" not in os.path.basename(f)
                  and os.path.basename(f)[:10] >= _cut17],
                 key=lambda f: os.path.basename(f))


def _jp_body(_t):
    _m = _re17.search(r"##\s*本文.*?\n```\n(.+?)\n```", _t, _re17.S)
    return _m.group(1) if _m else ""


def _en_summary(_t):
    _m = _re17.search(r"##\s*English Summary\n\n\*\*(.+?)\*\*\n\n(.+?)\n\n---", _t, _re17.S)
    return _m.group(2) if _m else ""


_dupes = []
_seen_open, _seen_close, _seen_en = {}, {}, {}
# 使い回されがちな言い回し（見つかった記事名を集めて2本以上なら警告）
# 2026-09-14 作り直し(CQO重大1)。**リテラルではなく修辞の装置**で捕まえる。
# 旧版は「たいてい驚く」を持っていたのに、「驚くのは、たいてい大きさだ」「海外から来た人が家に
# 上がると、たいてい〜」を4本連続で通した。語順が違うだけで同じ装置なので、
# 「何度も使う型」を1本の正規表現で書く。新しい装置に気づいたら**文ではなく型**を足すこと。
_PHRASES = (
    # 「海外/外国の人は〜驚く・たいてい〜な顔をする」型。当社の最頻出テンプレ。
    # 文境界(。)で止めていたため、装置を2文に割ると素通りした（2026-09-15 用水路の初稿で実証）。
    # 段落＝行の中なら拾えるよう [^\n]{0,40} に広げる。多少の誤検知は警告なので許容する。
    # アンカーが「海外|外国|外から来た」固定だったため、**「外から見れば」「よそから見ると」を素通り**した
    # （2026-09-15 用水路・2026-09-16 新蕎麦で2本連続。両方未公開なのに OK が出ていた＝CQO重大4）。
    # 同じ装置は「外部者の視点を借りて自分の当たり前を相対化する」ことなので、アンカーと反応語の両方を広げる。
    ("海外の人が驚く型", r"(海外|外国|外から来た|外から見|よそから見|日本の外)[^\n]{0,40}"
                        r"(驚|たいてい|不思議な顔|微妙な顔|納得しない|奇妙|変に見え|おかしく見え|結びつかない|伝わ)"),
    ("読者に試させる型", r"(てみてほしい|試してみて|確かめてもらえたら)"),
    ("説明に詰まる型",   r"(毎回|いつも)?[^。]{0,10}(つまず|言葉に詰ま|うまく説明できない|うまく言えない)"),
    ("何も足していない型", r"(何も足して|加えているものが何も|余計なものが何も)"),
    ("もし〜なら型",     r"^もし[^。]{0,20}(なら|たら)"),
)
# 英語成果物用。日本語と同じ装置が英語に逃げるので、英語でも型で捕まえる。
_EN_PHRASES = (
    ("EN:外部者に説明する型", r"(explain(ing)?[^.]{0,30}(abroad|from outside|to (someone|people)))"
                              r"|((from|to) outside Japan)|(rarely lands)|(defeats me)"),
    ("EN:相手が驚く型",       r"(visitors?|foreigners?|people from abroad)[^.]{0,40}"
                              r"(surpris|startl|taken aback|puzzl|baffl)"),
    # 2026-09-19: `try it` が **"coun try it hatched"** のような語またぎに部分一致して誤検知した。
    # さらに「you try it a few times（何度かやってみる）」は読者への勧めですらない。
    # 語境界を付け、**読者に勧める言い回しに限定**する。狼少年になると検査ごと信用されなくなる。
    ("EN:読者に試させる型",   r"\b(try it yourself|give it a go|see for yourself|worth a try|you should try|do try)\b"),
)
_phrase_hits = {name: [] for name, _ in list(_PHRASES) + list(_EN_PHRASES)}
for _f in _arts17:
    _b = os.path.basename(_f)[:-3]
    _t = open(_f, encoding="utf-8").read()
    _body, _en = _jp_body(_t), _en_summary(_t)
    if not _body:
        continue
    # クレジット行(（見出し画像：…）)は権利表示であって締めではない。除かないと
    # R16でクレジットを入れた記事の「本当の締め」が永久に比較されなくなる（CQO指摘・高8）。
    _paras = [p for p in _body.split("\n")
              if p.strip() and not p.startswith(("#", "[", "（見出し画像："))]
    if _paras:
        _o, _c = _paras[0][:12], _paras[-1][:12]
        _seen_open.setdefault(_o, []).append(_b)
        _seen_close.setdefault(_c, []).append(_b)
        # 2026-09-16(CQO中3): 締めには骨格比較があるのに**冒頭には無かった**＝非対称な穴。
        # さらに第2段落を一切見ておらず、同日2本が両方「秋になると〜」で始まっていたのを逃した。
        _oskel = _re17.sub(r"[^もしたらならばときにはがをでとへや、。ならそれこれあれというだけでもしかない]+", "◯", _paras[0][:24])
        _seen_open.setdefault("骨格:" + _oskel, []).append(_b)
        if len(_paras) > 1:
            _seen_open.setdefault("第2段:" + _paras[1][:10], []).append(_b)
        # 文字列一致だけだと「もし日本の秋に泊まる機会」と「もし日本の秋に焼き芋を買」がすり抜ける
        # ＝R17が潰すはずだった「型は同じ・名詞だけ違う」がまさに素通りしていた（CQO指摘・高7）。
        # 名詞を落として**統語の骨格**で比べる。
        _skel = _re17.sub(r"[^もしたらならばときにはがをでとへや、。ならそれこれあれというだけでもしかない]+", "◯", _paras[-1][:24])
        _seen_close.setdefault("骨格:" + _skel, []).append(_b)
        # 2026-09-13(CQO指摘・高8): 先頭12/24字しか見ていなかったため、**段落の後半に置かれた反復**が
        # 原理的に通過していた。実測で「一般論を認める。ただ〜」という譲歩ピボットの締めが3本連続、
        # 「〜という話である」が2日連続。最終段落の**全文**から接続と文末型を抜いて比べる。
        _last = _paras[-1]
        _pivot = next((w for w in ("。ただ", "。しかし", "。けれども", "。だが", "。それでも", "。もっとも")
                       if w in _last), "")
        _tail = _re17.sub(r"^.*?([^。]{0,10}。?)$", r"\1", _last)   # 最終文の末尾10字
        if _pivot:
            _seen_close.setdefault(f"譲歩ピボット{_pivot}", []).append(_b)
        _seen_close.setdefault("文末:" + _tail[-8:], []).append(_b)
    if _en:
        _first3 = " ".join(_en.split()[:3])
        _seen_en.setdefault(_first3, []).append(_b)
    for _name, _rx in _PHRASES:
        if re.search(_rx, _body, re.M):
            _phrase_hits[_name].append(_b)
    # 英語側も装置で見る。海外読者に読まれることが North Star なので、**英語の反復のほうが致命的**
    # なのに、従来は英語要約の先頭3語しか比較していなかった（CQO中2）。
    # 実測: 「外部者に説明する」装置が EN要約に直近6日で4本あり、全部不可視だった。
    if _en:
        for _name, _rx in _EN_PHRASES:
            if re.search(_rx, _en, re.I):
                _phrase_hits[_name].append(_b + "(EN)")

# 公開済み記事は**もう直せない**ので、警告に混ぜると常時STALEになって検知が形骸化する
# （R2dで学んだのと同じ失敗）。**未公開の記事が絡む反復だけ**を「対応が要る」とし、
# 公開済みどうしの反復は件数だけ添える（次に書くときの参考情報）。
_published = {os.path.basename(f) for f in glob.glob(os.path.join(ROOT, "drafts/published/*.md"))}


def _has_unpublished(_names):
    return any(f"{n}.md" not in _published for n in _names)


_hist = 0
for _label, _d in (("日本語の冒頭", _seen_open), ("日本語の締め", _seen_close), ("英語要約の書き出し", _seen_en)):
    for _k, _v in _d.items():
        if len(_v) > 1:
            if _has_unpublished(_v):
                _dupes.append(f"{_label}が同型: {_k}…（{', '.join(x[:16] for x in _v)}）")
            else:
                _hist += 1
for _p, _v in _phrase_hits.items():
    if len(_v) > 1:
        if _has_unpublished(_v):
            _dupes.append(f"言い回し『{_p}』が{len(_v)}本（{', '.join(x[:16] for x in _v)}）")
        else:
            _hist += 1

_note17 = f"（公開済みどうしの反復 {_hist}件は変更不能のため対象外）" if _hist else ""
if _dupes:
    add("R17 文体の反復(A5/A6)", "BROKEN",
        f"**未公開記事が絡む反復 {len(_dupes)}件** → {_dupes[0][:70]}… ／ 公開前に冒頭・締め・言い回しを変える{_note17}")
else:
    add("R17 文体の反復(A5/A6)", "OK",
        f"直近{_A6_DAYS}日{len(_arts17)}本／未公開{len([f for f in _arts17 if os.path.basename(f) not in _published])}本に反復なし{_note17}")

# R18 North Star からの逸脱: 記事は「海外読者に高岡・氷見・富山を読ませる」ためのもの。
# 2026-09-12(CQO指摘・中14): 焼き芋稿は本文に「富山」が**0件**なのに、ENのdescriptionは
# "A local in Toyama"、Xは #Toyama を付けていた＝本文に根拠のない地域タグ。
# 全国題材を書くこと自体は良いが、**富山からの一次観察が1行も無いまま地域タグを付けない**。
_TOYAMA_WORDS = ("富山", "高岡", "氷見", "北陸", "立山")
# 対象は**これから公開する drafts/queue** に絞る。CMO/outputs 全体を見ると、
# 公開予定でない古い随筆（AI論など）まで拾って常時STALEになり、検知が形骸化する。
# 2026-09-13(CQO指摘・重大4): キューが空のとき `_offstar` も空になり **「0本すべてOK」** と表示していた。
# 公開直後はキューが空になるので、平常時はほぼ常に空振りのOKを出し続ける＝典型的な「対象0件＝合格」。
# 対象が無いときは OK ではなく **STALE（未検査）** と言う。
_queue_files = sorted(glob.glob(os.path.join(ROOT, "drafts/queue/*.md")))
_offstar = []
for _f in _queue_files:
    _b = os.path.basename(_f)[:-3]
    _t = open(_f, encoding="utf-8").read()
    _m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", _t, re.S) if "re" in dir() else None
    _body = _m.group(1) if _m else _t
    if not any(w in _body for w in _TOYAMA_WORDS):
        _offstar.append(_b)
if not _queue_files:
    add("R18 North Star整合", "STALE",
        "公開キューが空＝**検査対象なし**（0本を『すべてOK』と表示しない）。次の記事を投函したら判定される")
elif _offstar:
    add("R18 North Star整合", "STALE",
        f"**公開キュー**の記事で本文に富山/高岡/氷見/北陸/立山が0件 {len(_offstar)}本(例:{_offstar[0][:26]}…)"
        " → 一次観察を1段落入れるか、EN/Xの地域タグを外す")
else:
    add("R18 North Star整合", "OK", f"公開キュー{len(_queue_files)}本すべて本文に富山圏の記述あり（地域タグの根拠がある）")

# R13 制御ファイルの追跡: thumbnails/ は .gitignore 済なので、_verified.txt / _no_auto.txt は
# `git add -f` されていないと **codeの手元にしか存在しない**。実際 _no_auto.txt は管理外のままで、
# ランナーにもcoworkにも届かず「意図的な無サムネ」が一度も効いていなかった
# （獅子舞の誤サムネが8回復活した真因）。設定ではなく機構として毎回確認する。
import subprocess as _sp
# 2026-09-22: _backfill_attempts.json を追加。thumbnails/ は .gitignore 済なので
# -f で追跡しないと**次のrunに残らず、毎回先頭の同じ数件を試し続ける**（実際そうなっていた）。
_ctl = ["CDO/outputs/note_publisher/thumbnails/_verified.txt",
        "CDO/outputs/note_publisher/thumbnails/_no_auto.txt",
        # 2026-09-21 追加。作った当日に git add -f を忘れ、コンテナ内にしか無い状態だった。
        "CDO/outputs/note_publisher/thumbnails/_rejected_hashes.tsv",
        "CDO/outputs/note_publisher/thumbnails/_backfill_attempts.json",
        # 2026-09-23 追加。R2d の「採用済みどうしの共有は監査済みか」を持つ台帳。
        # これも -f で追跡しないと、次のセッションで7組がまた未監査に戻る。
        "CDO/outputs/note_publisher/thumbnails/_shared_ok.tsv"]
try:
    _tracked = set(_sp.run(["git", "ls-files"] + _ctl, cwd=ROOT, capture_output=True,
                           text=True, timeout=20).stdout.split())
except Exception:
    _tracked = set(_ctl)   # gitが使えない環境では判定しない（誤報を出さない）
_untracked = [c for c in _ctl if c not in _tracked]
# ★2026-09-23 追加: **末尾に改行が無いと、次の追記が最終行にくっつく**。
# 実際この日、_verified.txt の最後がコメント行で改行無しに終わっており、
# `echo "<stem>" >> _verified.txt` がその**コメントの続き**になって、採用登録が効かなかった。
# R32 が拾ったので公開前に気づけたが、検査が無ければ「登録したつもり」で通っていた。
# 追記で育てる台帳はこれで全部黙って壊れるので、機構として毎回見る。
# 対象は **追記で育てるテキスト台帳だけ**。_backfill_attempts.json はプログラムが
# 丸ごと書き直す JSON で、`echo >>` することがないので末尾改行は問題にならない。
_nonl = []
for _c in _ctl:
    if not _c.endswith((".txt", ".tsv")):
        continue
    _p = os.path.join(ROOT, _c)
    try:
        with open(_p, "rb") as _fh:
            _fh.seek(-1, 2)
            if _fh.read(1) != b"\n":
                _nonl.append(_c)
    except OSError:
        pass          # 無い/空のファイルは追記事故が起きないので対象外
if _untracked:
    add("R13 制御ファイル追跡", "BROKEN",
        f"git管理外 {len(_untracked)}件({os.path.basename(_untracked[0])}) → "
        "`git add -f` しないとランナー/coworkに届かず、無サムネ指定も検証済み指定も効かない")
elif _nonl:
    add("R13 制御ファイル追跡", "BROKEN",
        f"**末尾に改行が無い台帳 {len(_nonl)}件**({os.path.basename(_nonl[0])}) → "
        "次の `echo >> ` が最終行にくっついて、登録したつもりが効かない（2026-09-23 に実際に起きた）")
else:
    add("R13 制御ファイル追跡", "OK", f"制御ファイル {len(_ctl)}件（" + " / ".join(os.path.basename(c) for c in _ctl) + "）はすべて追跡下・末尾改行あり")

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
