#!/bin/zsh
# send_outreach.sh — 営業メールをまずdry-run（送信せず全文確認）。Macで実行。
# 使い方:
#   bash scripts/send_outreach.sh            # SEO代行の文面でdry-run
#   bash scripts/send_outreach.sh sns        # SNS代行の文面でdry-run
set -e
cd "$(dirname "$0")/.."
SVC="${1:-seo}"
CSV="CSO/outputs/targets.csv"

# targets.csv は見込み客データ(PII)のため git管理外。無ければ雛形を自動生成する。
if [ ! -f "$CSV" ]; then
  echo "== targets.csv が無いので雛形を自動生成します（PIIのためローカルのみ・gitには載せない） =="
  python3 CSO/outputs/send_outreach_gmail.py --template
  echo
fi

echo "== 送り先リスト($CSV) =="
cat "$CSV"
echo
echo "== ⚠️ example行のままなら、実在の見込み客に差し替えてから送ること =="
echo

echo "== 営業メール dry-run（送信しません・全文プレビュー） =="
python3 CSO/outputs/send_outreach_gmail.py --service "$SVC" --dry-run

cat <<'EOM'

------------------------------------------------------------
▶ 本送信する手順（中身を確認してから）:
  1) CSO/outputs/targets.csv を実在の見込み客に差し替え（知人・取引先を優先）
  2) Gmailアプリパスワードを設定:
       export GMAIL_ADDR="you@gmail.com"
       export GMAIL_APP_PW="16桁のアプリパスワード"
  3) まず5件だけ送る（5分間隔・スパム化回避）:
       python3 CSO/outputs/send_outreach_gmail.py --service seo --limit 5
  4) 送信後の記録（任意）: git add -A && git commit -m "営業送信ログ" && git push
------------------------------------------------------------
EOM
