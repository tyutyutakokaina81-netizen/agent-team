#!/usr/bin/env python3
"""
retainers.py — B2B英語発信代行のリテーナー(継続課金)管理。jobs.py の発展形。

狙い：3〜5社の「社別 × 月次サイクル × 納品状況 × 継続課金」を1コマンドで把握し、
1社あたりの管理の手間を最小化する。依存ゼロ(標準ライブラリのみ)・A1(ネット不可)でも回る。

設計思想（jobs.py と揃える）:
  - 1社=1フォルダ `clients/<id>/`。社の固定情報は `clients/<id>/client.md` の
    ヘッダ（先頭の「- key: value」行）に持つ。正規表現で読む（yaml依存なし）。
  - 月次サイクルは `clients/<id>/monthly/<YYYY-MM>/cycle.md` の1ファイル=1サイクル。
    ステータス：planning → in-progress → review → delivered → invoiced → paid。
  - 金額(請求・入金)はヘッダに数値で持つが、**請求書・契約・PIIは clients/ ごと .gitignore**
    （CFO/CSO の outputs と同じ扱い。client.md のテンプレも実名はオーナーが入れる）。

使い方:
  python3 tools/retainers.py add  --id himi-inn --plan silver --fee 80000
  python3 tools/retainers.py open --id himi-inn --month 2026-07     # 今月サイクルを起票
  python3 tools/retainers.py list                                   # 全社×当月の状況一覧
  python3 tools/retainers.py show --id himi-inn                     # 1社の履歴
  python3 tools/retainers.py set  --id himi-inn --month 2026-07 --status review
  python3 tools/retainers.py check --id himi-inn --month 2026-07    # 当月成果物を quality_check に通す
  python3 tools/retainers.py invoice --id himi-inn --month 2026-07  # 請求済みに
  python3 tools/retainers.py paid    --id himi-inn --month 2026-07 --amount 80000

注意：
  - 実名・住所・媒体URL等のPIIは client.md に書かず〔　〕で残す（A4）。
  - clients/ は .gitignore 推奨（顧客情報）。雛形(.template)のみ追跡。
"""
import argparse, re, sys, subprocess, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENTS = ROOT / "clients"

# 月次サイクルの状態遷移（順序＝進捗の度合い）
FLOW = ["planning", "in-progress", "review", "delivered", "invoiced", "paid"]
# プラン別の月次納品ノルマ（A_高単価B2Bパッケージ.md の3プランと整合）
PLAN_QUOTA = {
    "bronze": {"記事": 2, "SNS": 8,  "サイト更新": 1, "fee": 60000},
    "silver": {"記事": 3, "SNS": 10, "サイト更新": 2, "fee": 80000},
    "gold":   {"記事": 4, "SNS": 12, "サイト更新": 0, "fee": 100000},  # サイト随時=0は「都度」の意
}
FIXED = 5800  # 月固定費（黒字判定の閾値・jobs.py と同じ思想）


def _today():
    return datetime.date.today().isoformat()


def _this_month():
    return datetime.date.today().strftime("%Y-%m")


def _read_header(path):
    h = {}
    if not path.exists():
        return h
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"-\s*([A-Za-z_]+):\s*(.*)$", ln)
        if m:
            h[m.group(1)] = m.group(2).strip()
    return h


def _set_header(path, key, value):
    lines = path.read_text(encoding="utf-8").splitlines()
    done = False
    for i, ln in enumerate(lines):
        if re.match(rf"-\s*{key}:\s*", ln):
            lines[i] = f"- {key}: {value}"
            done = True
            break
    if not done:
        ins = 0
        for i, ln in enumerate(lines):
            if ln.startswith("- "):
                ins = i + 1
        lines.insert(ins, f"- {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _client_dir(cid):
    return CLIENTS / cid


def _cycle_path(cid, month):
    return _client_dir(cid) / "monthly" / month / "cycle.md"


def cmd_add(a):
    d = _client_dir(a.id)
    if (d / "client.md").exists():
        sys.exit(f"既に存在: {a.id}")
    for sub in ("brief", "style", "monthly", "delivered"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    quota = PLAN_QUOTA.get(a.plan, PLAN_QUOTA["silver"])
    fee = a.fee or quota["fee"]
    (d / "client.md").write_text(
        f"""# クライアント {a.id}

- id: {a.id}
- plan: {a.plan}
- fee: {fee}
- status: active
- since: {_today()}
- channels: 〔記入：運用媒体カテゴリ（SNS種別/自社サイト/予約サイト 等。URLは書かない）〕
- contact: 〔記入：窓口担当・連絡手段（メール/チャット）〕

## 業種・提供物（市レベル・カテゴリのみ。実名/住所/地区名 禁止＝A4）
〔記入：業種カテゴリ（宿/飲食/体験/物販）と提供物の概要〕

## NG情報（出してはいけない情報）
〔記入：住所詳細・個人名・非公開メニュー・価格非開示 等〕

## メモ
- 月次ノルマ（{a.plan}）：記事{quota['記事']}本 / SNS{quota['SNS']}本 / サイト更新{quota['サイト更新']}回
""",
        encoding="utf-8",
    )
    # スタイルガイドの雛形（quality_check のクライアント別 当て込みに使う）
    (d / "style" / "style.md").write_text(
        f"""# {a.id} スタイルガイド（トンマナ／語彙／禁止語）

- ban_extra: 〔この社で特に避けたい語をカンマ区切り。例：超激安,完全保証〕
- tone: 〔語り口：落ち着いた/カジュアル/丁寧 等〕

## 表記ルール
- ローマ字／英訳の固有名詞の綴り（確定したものを列挙）
- 言ってよい表現 / 言ってはいけない表現（A5：成果保証NG）

## NG語（この社固有・A5標準語に追加で機械検査したいもの）
（retainers.py check が ban_extra を quality_check に渡す想定。1行1語でもよい）
""",
        encoding="utf-8",
    )
    print(f"✅ クライアント追加: clients/{a.id}/  (plan={a.plan} fee=¥{fee})")
    print(f"   → client.md / style/style.md の〔　〕を埋め、`retainers.py open --id {a.id}` で当月起票。")


def cmd_open(a):
    month = a.month or _this_month()
    cdir = _client_dir(a.id)
    if not (cdir / "client.md").exists():
        sys.exit(f"クライアント未登録: {a.id}（先に add）")
    cp = _cycle_path(a.id, month)
    if cp.exists():
        sys.exit(f"既に起票済: {a.id} {month}")
    cp.parent.mkdir(parents=True, exist_ok=True)
    plan = _read_header(cdir / "client.md").get("plan", "silver")
    q = PLAN_QUOTA.get(plan, PLAN_QUOTA["silver"])
    cp.write_text(
        f"""# 月次サイクル {a.id} / {month}

- id: {a.id}
- month: {month}
- plan: {plan}
- status: planning
- fee: {_read_header(cdir / 'client.md').get('fee', q['fee'])}
- invoiced: 0
- paid: 0
- opened: {_today()}

## 今月のノルマ（{plan}）チェック
- [ ] 英語記事 {q['記事']}本
- [ ] 英語SNS投稿 {q['SNS']}本
- [ ] サイト/LP英語更新 {q['サイト更新']}回
- [ ] 英語FAQ・問い合わせ返信テンプレ（随時）
- [ ] 月次レポート 1本

## 成果物リンク（delivered/ 配下のファイル名を列挙）

## 確認・修正の往復（契約上：月1回まとめ確認／修正1往復まで）
""",
        encoding="utf-8",
    )
    print(f"📋 月次サイクル起票: clients/{a.id}/monthly/{month}/cycle.md (status=planning)")


def _all_client_ids():
    if not CLIENTS.exists():
        return []
    return sorted([p.name for p in CLIENTS.iterdir()
                   if p.is_dir() and (p / "client.md").exists()])


def cmd_list(a):
    month = a.month or _this_month()
    ids = _all_client_ids()
    if not ids:
        print("クライアントなし。`retainers.py add --id <id> --plan silver` で登録。")
        return
    paid_total = 0
    mrr = 0
    print(f"== 当月 {month} のリテーナー状況 ==")
    print(f"{'ID':16} {'plan':7} {'月額':>8} {'当月状態':12} {'請求':>8} {'入金':>8}")
    print("-" * 70)
    for cid in ids:
        ch = _read_header(_client_dir(cid) / "client.md")
        if ch.get("status") != "active":
            continue
        fee = int(ch.get("fee", "0") or 0)
        mrr += fee
        cyc = _read_header(_cycle_path(cid, month))
        st = cyc.get("status", "未起票")
        inv = int(cyc.get("invoiced", "0") or 0)
        pd = int(cyc.get("paid", "0") or 0)
        paid_total += pd
        print(f"{cid:16} {ch.get('plan','?'):7} {fee:>8} {st:12} {inv:>8} {pd:>8}")
    print("-" * 70)
    state = "🟢黒字" if paid_total >= FIXED else "🔴未達"
    print(f"MRR(継続課金合計)=¥{mrr}  当月入金=¥{paid_total} / 固定費¥{FIXED} → {state}")
    print(f"¥300K目標まで: あと¥{max(0, 300000 - mrr)}（MRRベース）")


def cmd_show(a):
    cdir = _client_dir(a.id)
    if not (cdir / "client.md").exists():
        sys.exit(f"未登録: {a.id}")
    print((cdir / "client.md").read_text(encoding="utf-8"))
    mdir = cdir / "monthly"
    if mdir.exists():
        print("\n== 月次サイクル履歴 ==")
        for m in sorted(mdir.iterdir()):
            h = _read_header(m / "cycle.md")
            print(f"  {h.get('month','?'):9} status={h.get('status','?'):12} "
                  f"請求¥{h.get('invoiced','0')} 入金¥{h.get('paid','0')}")


def cmd_set(a):
    if a.status not in FLOW:
        sys.exit(f"status は {FLOW} のいずれか")
    cp = _cycle_path(a.id, a.month)
    if not cp.exists():
        sys.exit(f"サイクル未起票: {a.id} {a.month}（先に open）")
    _set_header(cp, "status", a.status)
    print(f"🔄 {a.id} {a.month} → status={a.status}")


def cmd_check(a):
    """当月 delivered/ 配下の成果物を quality_check.py に通す（クライアント別NG語も適用）。"""
    cdir = _client_dir(a.id)
    deliv = cdir / "delivered" / a.month
    qc = ROOT / "tools" / "quality_check.py"
    if not deliv.exists():
        sys.exit(f"成果物フォルダなし: {deliv}（delivered/{a.month}/ に納品前原稿を置く）")
    files = sorted(str(p) for p in deliv.glob("*.md"))
    if not files:
        sys.exit(f"成果物が空: {deliv}")
    # クライアント別 追加NG語（style.md の ban_extra）をユーザに見せる（quality_check本体は共通語のみ）
    ban = _read_header(cdir / "style" / "style.md").get("ban_extra", "")
    print(f"== quality_check（A4/A5）: {a.id} {a.month} の {len(files)}本 ==")
    if ban:
        print(f"  ※ この社の追加NG語（style.md ban_extra）: {ban}  ← grep等で別途確認")
    # --reader（読者に出す原稿）として厳格に検査
    rc = subprocess.call([sys.executable, str(qc), "--reader", *files])
    if rc == 0:
        print("✅ 規則チェック合格。`retainers.py set --status delivered` に進める。")
    else:
        print("🔴 違反あり。是正してから delivered にすること。")
    return rc


def cmd_invoice(a):
    cp = _cycle_path(a.id, a.month)
    if not cp.exists():
        sys.exit(f"サイクル未起票: {a.id} {a.month}")
    fee = _read_header(cp).get("fee", "0")
    _set_header(cp, "invoiced", fee)
    _set_header(cp, "status", "invoiced")
    print(f"🧾 請求記録: {a.id} {a.month} = ¥{fee}（請求書実体はCFO管理・gitignore）")


def cmd_paid(a):
    cp = _cycle_path(a.id, a.month)
    if not cp.exists():
        sys.exit(f"サイクル未起票: {a.id} {a.month}")
    _set_header(cp, "paid", str(a.amount))
    _set_header(cp, "status", "paid")
    print(f"💰 入金記録: {a.id} {a.month} = ¥{a.amount}")
    cmd_list(a)


def main(argv):
    ap = argparse.ArgumentParser(description="リテーナー(継続課金)管理 — jobs.pyの発展形")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add"); p.set_defaults(f=cmd_add)
    p.add_argument("--id", required=True)
    p.add_argument("--plan", default="silver", choices=list(PLAN_QUOTA))
    p.add_argument("--fee", type=int, default=0, help="未指定ならプラン標準額")

    p = sub.add_parser("open"); p.set_defaults(f=cmd_open)
    p.add_argument("--id", required=True); p.add_argument("--month", default=None)

    p = sub.add_parser("list"); p.set_defaults(f=cmd_list); p.add_argument("--month", default=None)

    p = sub.add_parser("show"); p.set_defaults(f=cmd_show); p.add_argument("--id", required=True)

    p = sub.add_parser("set"); p.set_defaults(f=cmd_set)
    p.add_argument("--id", required=True); p.add_argument("--month", required=True)
    p.add_argument("--status", required=True)

    p = sub.add_parser("check"); p.set_defaults(f=cmd_check)
    p.add_argument("--id", required=True); p.add_argument("--month", required=True)

    p = sub.add_parser("invoice"); p.set_defaults(f=cmd_invoice)
    p.add_argument("--id", required=True); p.add_argument("--month", required=True)

    p = sub.add_parser("paid"); p.set_defaults(f=cmd_paid)
    p.add_argument("--id", required=True); p.add_argument("--month", required=True)
    p.add_argument("--amount", type=int, required=True)

    a = ap.parse_args(argv)
    return a.f(a) or 0  # check は違反時に rc=1 を返す（CI/コミット前ゲートに使える）


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:
        sys.exit(0)
