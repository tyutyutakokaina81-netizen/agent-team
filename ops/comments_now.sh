#!/bin/bash
# いま来ているコメントを取りに行く（見直しも含めて全記事）。
# 読み取りだけ。note 側は変更しない。
set -e
cd "$(dirname "$0")/.."

# ★2026-10-07: **自分で最新を取り込む**。
#   これまでは「git pull && bash ops/xxx.sh」と二つ並べて渡していたが、
#   手元に未コミットの変更があると pull が止まり、スクリプトまで届かなかった（実際に起きた）。
#   --autostash は手元の変更を退避→取り込み→戻す、まで自動でやる（消さない）。
git pull --rebase --autostash origin main || echo "⚠️ git pull に失敗。手元のまま続行します"
echo "=== 1/3 通知欄から拾う（1ページで済む・いちばん速い）==="
# 2026-10-07: オーナーが「コメントきてる」と気づくのは通知欄。そこを見れば、
#   どの記事に来たかに関係なく1ページで分かる。237本の巡回は取りこぼし確認用に残す。
python3 CDO/outputs/note_publisher/fetch_comments_from_notifications.py --go || \
  echo "⚠️ 通知欄から取れなかった。保存した実物が push されるので、そのまま報告してください"
echo ""
echo "=== 2/3 念のため全記事も巡回する（見直し込み）==="
python3 CDO/outputs/note_publisher/fetch_note_comments.py --rescan --limit 0 --debug
echo ""
echo "=== 3/3 仕分け ==="
python3 ops/draft_comment_replies.py --write || true
echo ""
echo "=== commit & push ==="
git add -A ops/comments 2>/dev/null || true
git commit -q -m "comments: 取得結果（$(date +%Y-%m-%d_%H%M)）" 2>/dev/null \
  && (git pull --rebase --autostash -q origin main || true) && git push -u origin main 2>&1 | tail -1 || echo "新しいコメントは無し"
echo ""
echo "※ 本文が取れなかった記事があれば、保存HTMLも一緒に push されます。"
echo "   その場合は『コメントきてる』ともう一度言ってください。保存HTMLから返信文を書きます。"

echo ""
echo "================ 取れたコメント ================"
python3 - <<'PYEOF'
import csv, os
f = os.path.join("ops", "comments", "pending.tsv")
rows = []
if os.path.exists(f):
    with open(f, encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if r and not r[0].startswith("comment_id"):
                rows.append(r)
if not rows:
    print("0件。通知欄にコメントが見えているのにここが0なら、")
    print("ops/comments/_debug/notifications.txt を Claude に貼ってください（画面の実物です）")
else:
    print(f"{len(rows)}件。この下の行をそのまま Claude に貼れば、返信文を書きます。")
    print("-" * 56)
    for r in rows:
        who = r[2] if len(r) > 2 else "?"
        lang = r[3] if len(r) > 3 else "?"
        text = r[4] if len(r) > 4 else ""
        art = r[1] if len(r) > 1 else ""
        print(f"[{lang}] {who} / {art}")
        print(f"    {text}")
    print("-" * 56)
PYEOF
