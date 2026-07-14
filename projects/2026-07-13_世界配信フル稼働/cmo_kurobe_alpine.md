# CMO 作業ログ：黒部ダム新規ページ ＋ アルペンルート予約強化

- 作成：2026-07-14 / CMO
- North Star：高岡・氷見・富山を海外個人旅行者に読ませる
- 発注元：CAO `cao_en_seo_gap.md` の最優先ギャップ2件
- 制約遵守：¥0 / A4（番地・地区名なし、市/村レベルまで）/ A5（放水期間・料金・運行は断定回避、"varies by year / check official"で逃げ）/ 著作権配慮 / リンク切れ厳禁（実在ファイルのみ）

## タスクA：新規 `apps/toyama-guide/en-kurobe-dam.html`

- 既存 `en-alpine.html` のHTML構造を完全クローン（head/canonical/og/robots/twitter・JSON-LD・analytics.js include・affiliates.js・lang/tagヘッダー・.aff/.pr/.muted等CSSクラス・reader-follow-block・note CTA形式）。
- canonical / og:url = `https://tyutyutakokaina81-netizen.github.io/agent-team/toyama/en-kurobe-dam.html`。og:image は命名規則に沿い `og/en-kurobe-dam.png`（画像はオーナー/cloud生成前提・A2）。
- 内容（英語 約900語）：観光放水（late June〜mid-Oct を目安として提示・断定せず「年により変動、公式で確認」）／見どころ表（クレスト歩き・展望台の石段・黒部湖の遊覧船・建設の歴史）／立山黒部アルペンルート内での位置づけ（黒部ダムは長野側の端＝富山側からは縦断ほぼ全行程）／行き方（富山側 vs 長野側 Ogizawa の正直比較＝ダム目的なら長野側が速く安い）／所要目安（全縦断は丸1日）。
- 住人トーン：「地元なら黒部ダム目的の旅行者は長野側へ回す」等の一次的視点を挿入。峡谷（Kurobe Gorge）との混同注意も明記。
- A5対策：放水日程・遊覧船・料金・区間はすべて「seasonal / vary by year / confirm on official」で断定回避。免責 .muted 段落を末尾に設置。
- 内部リンク（実在確認済・全OK）：en-alpine, en-alpine-cost, en-how-many-days, en-takaoka, en-kurobe-gorge, en-murodo, en-kurobe-vs-tateyama, en-when-to-go の**コンテンツ8ページ**＋ナビ（index, en）。末尾 note CTA（¥100 EN: note.com/safe_canna441/n/nba958ccd6cb8）1本。
- 検証：html/head/body タグ各1対1で対応・壊れなし。リンク先10本すべて実在ファイル。

## タスクB：既存 `en-alpine.html` 強化（"how to book Alpine Route tickets"）

- 「Riding it from Toyama」セクション直後に**予約フローの具体段落を1つ加筆**（本文構造は非破壊・既存段落は温存）。
- 追加内容：オンライン予約でケーブルカー区間の日時指定・方向別の通し券購入／Web予約は数週間前に開始・春の雪壁期が最も早く埋まる→日程確定なら早めに／正確な開始時期・timed slot・発券方法は季節変動＝公式で確認（A5断定回避）。既存 `en-alpine-cost.html`（費用・2026日程・予約）への内部リンク追加。
- 検証：タグ対応維持・en-alpine-cost.html 実在。

## 事実検証ノート

- ✅ 確実：黒部ダムはアルペンルートの長野側端に位置し、富山側からはほぼ全縦断が必要（既存 `en-alpine-cost.html` の区間順記述と整合：…Kurobeko→Kurobe Dam crest→Ogizawa[長野側]）。日本一高いダム。
- ⚠️ 要確認：観光放水期間（本文は「late June〜mid-Oct・年により変動・公式確認」と明示逃げ）。CAOメモの 6/26–10/15 も `[要確認:日付]` 扱い。遊覧船・展望台石段数・料金も断定せず。→ A5順守。
- 出典系（CAO WebSearch 2026-07-14）：japan.travel/en/spot/1422, japan-guide.com/e/e7554.html, alpen-route.com/en。

## 成果

- 作成：`apps/toyama-guide/en-kurobe-dam.html`（新規）
- 強化：`apps/toyama-guide/en-alpine.html`（予約段落＋内部リンク加筆）
- sitemap.xml は未編集（code が追加）。commit は未実施（code がまとめて push）。
