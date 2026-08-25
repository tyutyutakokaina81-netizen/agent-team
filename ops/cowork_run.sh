#!/bin/bash
# cowork 配信デーモン — オーナーのMacで実行（手動 or launchd/cron）。
# code が物理的にできない「note公開」を自動化し、★確認作業も自動化★する：
#   現ブランチを pull → キュー公開 → 全出力をログ保存 → 結果を outbox 報告 → commit & push。
# これにより、オーナーがコンソールを目視して貼り付けなくても、
# code が repo の ops/logs/ と ops/outbox/ を読んで結果を確認できる。
set -uo pipefail
cd "$(dirname "$0")/.."

BR="$(git rev-parse --abbrev-ref HEAD)"
mkdir -p ops/logs
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/publish_${TS}.log"

# 全標準出力/エラーをログにも複製（確認作業の自動化の中核）
exec > >(tee -a "$LOG") 2>&1

echo "=== publish run ${TS} (branch=${BR}) ==="
# 自己修復: 前回の未完マージ/リベースや残骸ロックがあると git 同期が全部詰まるので先に解消
find .git -name '*.lock' -delete 2>/dev/null || true
git merge --abort  2>/dev/null || true
git rebase --abort 2>/dev/null || true
git pull --rebase origin "$BR" || git pull origin "$BR" || { echo "⚠️ pull失敗→origin/${BR}へ強制同期(Macはミラー)"; git fetch origin "$BR" && git reset --hard "origin/${BR}"; }

PUB="CDO/outputs/note_publisher/publish_to_note.py"
# ★Python3.14/PEP668対策：setup.shが作る専用venvがあれば自動でそれを使う
PYBIN="python3"; [ -x "$HOME/.note_venv/bin/python" ] && PYBIN="$HOME/.note_venv/bin/python"
shopt -s nullglob
published=0
failed=0
ok_list=""
fail_list=""
thumb_fail=0
login_fail=0
fail_reasons=""

for f in drafts/queue/*.md; do
  name="$(basename "$f")"
  echo "--- 公開試行: ${name} ---"
  out="$("$PYBIN" "$PUB" --text-only --article "$f" 2>&1)"
  rc=$?
  # ★一過性のnote不調(タイムアウト/UIのちらつき等)を無人で拾い直す＝自動リトライ1回。
  #   ログイン切れ/題材重複など恒久失敗は2回目も同じく失敗し、失敗理由として報告される。
  if [ $rc -ne 0 ] && ! echo "$out" | grep -qE "重複ゲート|ログインしていない|初回ログインがまだ|有料"; then
    sleep 15
    out2="$("$PYBIN" "$PUB" --text-only --article "$f" 2>&1)"; rc=$?
    out="${out}
    [retry] ${out2}"
  fi
  echo "$out"
  # 写真サムネ未設定（=noteの既定サムネ適用）を集計。失敗ではなく情報として数える。
  if echo "$out" | grep -q "写真サムネは未設定"; then
    thumb_fail=$((thumb_fail+1))
  fi
  # ★ログイン切れ/未ログインを検知（publisherが未ログイン時に出す定型文）。無人では自動ログインできないため
  #   outboxに「要ログイン」をはっきり残し、owner が --login すべきと分かるようにする（0/N全滅の原因特定用）。
  if echo "$out" | grep -qE "ログインしていない|初回ログインがまだ"; then
    login_fail=1
  fi
  if [ $rc -eq 0 ]; then
    mkdir -p drafts/published
    git mv "$f" "drafts/published/$name" 2>/dev/null || mv "$f" "drafts/published/$name"
    published=$((published+1)); ok_list="${ok_list} ${name}"
  else
    failed=$((failed+1)); fail_list="${fail_list} ${name}"
    # ★失敗理由を1行だけ抽出（ログはgitignoreでcode側から読めないため、報告に理由を残す）。
    #   ✗/エラー/Error/重複/ログイン 等を含む代表行を拾う。無ければ末尾行。
    reason="$(echo "$out" | grep -m1 -E '✗|エラー|Error|重複ゲート|ログイン|Timeout|タイムアウト|中断' | sed 's/^[[:space:]]*//' | cut -c1-100)"
    [ -z "$reason" ] && reason="$(echo "$out" | tail -1 | cut -c1-100)"
    fail_reasons="${fail_reasons}
    - ${name}: ${reason}"
  fi
done

echo "=== summary(無料): published=${published} failed=${failed} thumb_fail=${thumb_fail} ==="

# ---- 有料note（drafts/paid_queue/*.txt = 記事パスを1行書いたポインタ） ----
# 無料キューと分離する理由：有料は取り消しがきかず単価も持つため、明示的に投函された分だけを公開する。
# 価格は記事の <!-- PAYWALL price=NNN --> を publish_paid_note.py が読む（ここでは指定しない＝二重管理を避ける）。
PAID_PUB="CDO/outputs/note_publisher/publish_paid_note.py"
paid_ok=0
paid_ng=0
paid_urls=""
for q in drafts/paid_queue/*.txt; do
  qname="$(basename "$q")"
  art="$(grep -v '^[[:space:]]*#' "$q" | grep -v '^[[:space:]]*$' | head -1 | sed 's/[[:space:]]*$//')"
  if [ -z "$art" ] || [ ! -f "$art" ]; then
    echo "--- 有料スキップ: ${qname}（記事が見つかりません: ${art:-空}）---"
    paid_ng=$((paid_ng+1)); fail_reasons="${fail_reasons}
    - ${qname}: 記事ファイルが見つかりません (${art:-空})"
    continue
  fi
  echo "--- 有料公開試行: $(basename "$art") ---"
  pout="$("$PYBIN" "$PAID_PUB" --article "$art" --publish 2>&1)"; prc=$?
  echo "$pout"
  # 公開成立の判定は定型行 PAID_PUBLISHED と終了コードの両方で行う（安全側）。
  pid="$(echo "$pout" | grep -m1 -E '^PAID_PUBLISHED' | cut -f2)"
  if [ $prc -eq 0 ] && [ -n "$pid" ]; then
    mkdir -p drafts/paid_published
    git mv "$q" "drafts/paid_published/$qname" 2>/dev/null || mv "$q" "drafts/paid_published/$qname"
    paid_ok=$((paid_ok+1))
    paid_urls="${paid_urls} https://note.com/safe_canna441/n/${pid}"
  else
    paid_ng=$((paid_ng+1))
    preason="$(echo "$pout" | grep -m1 -E '✗|安全のため公開を中止|エラー|Error|ログイン|Timeout|タイムアウト' | sed 's/^[[:space:]]*//' | cut -c1-100)"
    [ -z "$preason" ] && preason="$(echo "$pout" | tail -1 | cut -c1-100)"
    fail_reasons="${fail_reasons}
    - 有料 $(basename "$art"): ${preason}"
    echo "$pout" | grep -qE "ログインしていない|初回ログインがまだ" && login_fail=1
  fi
done
echo "=== summary(有料): published=${paid_ok} failed=${paid_ng} ==="

# outbox に結果報告（記事名つき・code が機械的に読める）
body="公開 ${published} 件 / 失敗 ${failed} 件 / 写真サムネ未設定 ${thumb_fail} 件(note既定サムネ適用)（log: ${LOG}）"
if [ $((paid_ok + paid_ng)) -gt 0 ]; then
  body="${body}
【有料note】公開 ${paid_ok} 件 / 失敗 ${paid_ng} 件"
  [ -n "$paid_urls" ] && body="${body} | URL:${paid_urls}"
fi
# ★ログイン切れ検知時は先頭に大きく警告（無人では復旧不可＝owner対応が必要）
if [ $login_fail -eq 1 ]; then
  body="⚠️【要対応】noteログイン切れ/未ログインで公開できません。owner は Mac で \`python3 CDO/outputs/note_publisher/publish_to_note.py --login\` を実行しnoteにログイン→再度公開してください。 || ${body}"
fi
[ -n "$ok_list" ]   && body="${body} | OK:${ok_list}"
[ -n "$fail_list" ] && body="${body} | NG:${fail_list}"
# ★失敗理由の明細（原因即特定用）
[ -n "$fail_reasons" ] && body="${body}
【失敗理由】${fail_reasons}"
python3 ops/process_inbox.py post --from cowork --to code --type report \
  --title "auto-publish 結果 ${TS}" --body "$body" || true

# ★報告が空でないことを必ず確認する。
#   2026-08-22〜24、outboxの報告が3日連続で0バイトになり、0/4で失敗し続けた理由が
#   丸ごと失われた（`*.log` は .gitignore 対象なのでログも残らず、原因を追えなかった）。
#   post が何らかの理由で中身を書けなかった場合に備え、bash から直接書き戻す。
newest="$(ls -t ops/outbox/*.yaml 2>/dev/null | head -1)"
if [ -z "$newest" ] || [ ! -s "$newest" ]; then
  fallback="ops/outbox/${TS}_fallback_cowork_code.yaml"
  echo "⚠️ outbox報告が空だったため、bashから直接書き出します: ${fallback}"
  {
    echo "---"
    echo "id: ${TS}_fallback"
    echo "from: cowork"
    echo "to: code"
    echo "created: $(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
    echo "priority: high"
    echo "type: report"
    echo "status: open"
    echo "title: auto-publish 結果 ${TS}（process_inbox.py が空を返したためbashで生成）"
    echo "---"
    echo ""
    echo "$body"
  } > "$fallback"
  # 空ファイルが残っているとコミット履歴が「0 insertions」で埋まり、次も見落とす
  [ -n "$newest" ] && [ ! -s "$newest" ] && rm -f "$newest"
fi

git add -A
git commit -m "cowork auto: publish ${published}/$((published+failed)) paid=${paid_ok}/$((paid_ok+paid_ng)) thumb_fail=${thumb_fail} (${TS})" || true
for i in 1 2 3 4; do
  git push origin "$BR" && break || sleep $((2**i))
done
echo "done. published=${published} failed=${failed} paid=${paid_ok}/$((paid_ok+paid_ng)) thumb_fail=${thumb_fail}  log=${LOG}"

# ---- 売る導線(sell_flow)が未完なら、ここで続けて実行する ----
# owner指示(ops/inbox/2026-08-20_003)の ¥500 有料note と入口記事が、
# 「手で叩く必要がある」というだけの理由で5日間出ないままだった。日次実行に乗せる。
# 自前で pull/commit/push するので、上の push が終わったこの位置から呼ぶ（履歴が絡まないように）。
# 冪等性は sell_flow.sh 側が持つ：プレースホルダが残っているか＝①②が未了、
# STATE の free_published= の有無＝③が未了。両方とも済んでいれば即座に何もせず終わる。
SELL_FREE="CMO/outputs/2026-08-21_note記事_AIは一度もやめましょうと言わなかった.md"
SELL_STATE="ops/.sell_flow_state"
if [ -f ops/sell_flow.sh ] && [ -f "$SELL_FREE" ]; then
  if grep -qF "<<有料noteURL>>" "$SELL_FREE" 2>/dev/null || \
     ! grep -q "^free_published=" "$SELL_STATE" 2>/dev/null; then
    echo ""
    echo "=== 売る導線(sell_flow)が未完のため続けて実行します ==="
    bash ops/sell_flow.sh --go || echo "⚠️ sell_flow が途中で止まりました（上のログに理由）"
  fi
fi

# ---- 公開済み記事への有料note導線の差し込みを、少しずつ進める ----
# 無料記事279本に対し有料への導線が4本しか無い＝作った商品が読者に見つからない。
# append_paid_footer.py は**実機未検証**（A1でcodeはnote.comに繋げない）。
# 公開中の記事を編集するので、初回は1日2本だけ流して「セレクタが当たるか」を実地で確かめる。
# 成功が2件以上たまったら1日10本へ上げる＝当たると分かってから量を出す。
FOOTER_SCRIPT="CDO/outputs/note_footer/append_paid_footer.py"
FOOTER_STATE="CDO/outputs/note_footer/.append_state.json"
if [ -f "$FOOTER_SCRIPT" ] && [ -f "CDO/outputs/note_footer/paid_footer_manifest.json" ]; then
  done_n="$(python3 -c "
import json,pathlib
p=pathlib.Path('$FOOTER_STATE')
print(len(json.loads(p.read_text()).get('done',[])) if p.exists() else 0)
" 2>/dev/null || echo 0)"
  if [ "${done_n:-0}" -ge 2 ]; then FOOTER_LIMIT=10; else FOOTER_LIMIT=2; fi
  echo ""
  echo "=== 有料note導線の差し込み（済 ${done_n} 本／今回 ${FOOTER_LIMIT} 本まで）==="
  fout="$("$PYBIN" "$FOOTER_SCRIPT" --apply --limit "$FOOTER_LIMIT" 2>&1)"
  echo "$fout"
  # ★結果を必ず報告に残す。ログは *.log で .gitignore 対象＝報告しないと結果が消える
  #   （8/22〜24に「0/4」の理由を丸ごと失ったのと同じ失敗を繰り返さない）。
  fsum="$(echo "$fout" | grep -m1 -E '^=== 結果:' || echo '結果行なし（途中で落ちた可能性）')"
  ffail="$(echo "$fout" | grep -E '^    (fail|skip)' | head -5)"
  python3 ops/process_inbox.py post --from cowork --to code --type report \
    --title "有料note導線の差し込み ${TS}" \
    --body "${fsum}（済 ${done_n} 本→今回上限 ${FOOTER_LIMIT}）
※このスクリプトは実機未検証のまま日次に載せている。失敗が続くならセレクタが当たっていない。
${ffail}" || true
  git add -A
  git commit -m "cowork: paid-footer insertion pass (${TS})" || true
  for i in 1 2 3 4; do git push origin "$BR" && break || sleep $((2**i)); done
fi
