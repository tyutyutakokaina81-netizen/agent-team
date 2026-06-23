#!/usr/bin/env python3
"""
jobs.py — クラウドソーシング受託案件のパイプライン管理（受注→制作→納品→入金）。

依存ゼロ（標準ライブラリのみ）。A1（ネット不可）でも回る。
応募・客対応・納品アップロードは人、制作・品質チェックは code/agent。

案件は 受託/{inbox,wip,delivered}/ に1ファイル=1案件のMarkdownで保存。
ヘッダ（先頭の「- key: value」行）を正規表現で読む（yaml依存なし）。

使い方:
  python3 tools/jobs.py new --type 記事 --title "経費管理の記事" --budget 5000 --deadline 2026-06-30 --platform ランサーズ
  python3 tools/jobs.py list
  python3 tools/jobs.py show 2026-06-23_001
  python3 tools/jobs.py start   2026-06-23_001
  python3 tools/jobs.py deliver 2026-06-23_001 --file 受託/wip/2026-06-23_001_記事.md
  python3 tools/jobs.py done    2026-06-23_001 --paid 5000
"""
import argparse, re, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "受託"
INBOX, WIP, DELIV = BASE / "inbox", BASE / "wip", BASE / "delivered"
FOLDERS = {"inbox": INBOX, "wip": WIP, "delivered": DELIV}


def _today():
    return datetime.date.today().isoformat()


def _find(job_id):
    """全フォルダから job_id のファイルを探して (path, status) を返す。"""
    for status, folder in FOLDERS.items():
        for p in folder.glob(f"{job_id}_*.md"):
            return p, status
    return None, None


def _read_header(path):
    h = {}
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
        # ヘッダ末尾（最初の空行 or 見出し前）に挿入
        ins = 0
        for i, ln in enumerate(lines):
            if ln.startswith("- "):
                ins = i + 1
        lines.insert(ins, f"- {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _next_id():
    today = _today()
    n = 0
    for folder in FOLDERS.values():
        for p in folder.glob(f"{today}_*.md"):
            m = re.match(rf"{today}_(\d+)_", p.name)
            if m:
                n = max(n, int(m.group(1)))
    return f"{today}_{n+1:03d}"


def cmd_new(a):
    INBOX.mkdir(parents=True, exist_ok=True)
    jid = _next_id()
    safe_title = re.sub(r"[/\\\s]+", "_", a.title)[:40]
    path = INBOX / f"{jid}_{a.type}.md"
    path.write_text(
        f"""# 受託案件 {jid} — {a.title}

- id: {jid}
- type: {a.type}
- platform: {a.platform}
- title: {a.title}
- budget: {a.budget}
- deadline: {a.deadline}
- status: inbox
- paid: 0
- created: {_today()}

## 発注者の要件（ここに案件詳細を貼る）
（コピペ：文字数・トーン・納期・参考URL・NG事項 など）

## 制作メモ / 成果物リンク
""",
        encoding="utf-8",
    )
    print(f"✅ 受注カード作成: {path.relative_to(ROOT)}")
    print("   → 発注者の要件を本文に貼り、`jobs.py start {0}` で制作開始。".format(jid))


def cmd_list(a):
    rows = []
    paid_total = 0
    for status in ("inbox", "wip", "delivered"):
        for p in sorted(FOLDERS[status].glob("*.md")):
            h = _read_header(p)
            if not h.get("id"):
                continue
            paid = int(h.get("paid", "0") or 0)
            paid_total += paid
            rows.append((h.get("id"), status, h.get("type", "?"),
                         h.get("budget", "?"), paid, h.get("deadline", "?"),
                         h.get("title", "")[:30]))
    if not rows:
        print("案件なし。`jobs.py new ...` で受注カードを作成。")
        return
    print(f"{'ID':16} {'状態':9} {'種別':8} {'予算':>7} {'入金':>7} {'納期':11} 件名")
    print("-" * 80)
    for r in rows:
        print(f"{r[0]:16} {r[1]:9} {r[2]:8} {str(r[3]):>7} {r[4]:>7} {r[5]:11} {r[6]}")
    print("-" * 80)
    FIXED = 5800
    state = "🟢黒字" if paid_total >= FIXED else "🔴未達"
    print(f"今月までの入金累計: ¥{paid_total}  / 固定費¥{FIXED} → {state}"
          f"（あと¥{max(0, FIXED - paid_total)}で黒字）")


def cmd_show(a):
    path, status = _find(a.id)
    if not path:
        sys.exit(f"見つかりません: {a.id}")
    print(path.read_text(encoding="utf-8"))


def _move(path, dest_folder, new_status):
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest = dest_folder / path.name
    path.rename(dest)
    _set_header(dest, "status", new_status)
    return dest


def cmd_start(a):
    path, status = _find(a.id)
    if not path:
        sys.exit(f"見つかりません: {a.id}")
    dest = _move(path, WIP, "wip")
    print(f"▶️  制作開始（wipへ）: {dest.relative_to(ROOT)}")
    print("   code/agent が成果物を作成 → `python3 tools/quality_check.py` でチェック → deliver。")


def cmd_deliver(a):
    path, status = _find(a.id)
    if not path:
        sys.exit(f"見つかりません: {a.id}")
    if a.file:
        _set_header(path if status != "wip" else path, "deliverable", a.file)
    dest = _move(path, DELIV, "delivered")
    if a.file:
        _set_header(dest, "deliverable", a.file)
    print(f"📦 納品準備OK（deliveredへ）: {dest.relative_to(ROOT)}")
    print("   人が発注者へ納品（コピペ/添付）→ 入金後 `jobs.py done {0} --paid 金額`。".format(a.id))


def cmd_done(a):
    path, status = _find(a.id)
    if not path:
        sys.exit(f"見つかりません: {a.id}")
    _set_header(path, "paid", str(a.paid))
    _set_header(path, "status", "paid")
    print(f"💰 入金記録: {a.id} = ¥{a.paid}")
    cmd_list(a)


def main(argv):
    ap = argparse.ArgumentParser(description="受託案件パイプライン")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new"); p.set_defaults(f=cmd_new)
    p.add_argument("--type", required=True, help="記事/翻訳/編集翻訳/資料/商品説明/議事録 等")
    p.add_argument("--title", required=True)
    p.add_argument("--budget", default="?")
    p.add_argument("--deadline", default="?")
    p.add_argument("--platform", default="?")

    p = sub.add_parser("list"); p.set_defaults(f=cmd_list)
    p = sub.add_parser("show"); p.set_defaults(f=cmd_show); p.add_argument("id")
    p = sub.add_parser("start"); p.set_defaults(f=cmd_start); p.add_argument("id")
    p = sub.add_parser("deliver"); p.set_defaults(f=cmd_deliver); p.add_argument("id"); p.add_argument("--file", default=None)
    p = sub.add_parser("done"); p.set_defaults(f=cmd_done); p.add_argument("id"); p.add_argument("--paid", type=int, required=True)

    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except BrokenPipeError:
        sys.exit(0)
