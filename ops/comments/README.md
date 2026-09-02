# note コメント自動返信パイプライン（owner指示・2026-09-01）

owner『自動返信して』。**owner は個々のコメントに触らない**が、A5(定型/誤爆NG)とブランドを守るため
「code が下書き・cowork が取得/投稿・危険なものだけ自動保留」の3ステージ構成にする。

> ⚠️ **code は note に投稿・閲覧できない（A1）**。取得と投稿は cowork（ログイン済みブラウザ/Playwright）。
> code の担当は **返信文の自動生成（A5準拠の個別文）** と **危険判定**。

## 3ステージ（owner ハンズオフ）

1. **取得（cowork・定期）**：note の各記事の**新着コメント**を取得し `ops/comments/pending.tsv` に追記（既取得はスキップ＝dedup）。投稿はしない。
2. **下書き（code・毎点検で自動）**：`pending.tsv` の未処理行を読み、**1件ずつ個別に返信を生成**して `ops/comments/replies.tsv` に書く。返信ガイドライン(`CMO/outputs/2026-08-16_note返信ガイドライン.md`)の型＝温かく1〜3文・「てつ」の声・A5厳守・**英語コメントは英語**・A4厳守・定型コピペ禁止。
3. **投稿（cowork・定期）**：`replies.tsv` の `status=READY` のみ投稿し、`POSTED`＋URLに更新。`HOLD*` は投稿しない。

## 危険判定＝自動で HOLD（投稿しない・owner確認へ）

code は下書き時に次を検出したら `status` を HOLD にして**返信文を作らない/仮置きにする**：
- `HOLD-criticism` … 批判・苦情・炎上の芽（防衛的返信は逆効果。owner が個別判断）
- `HOLD-spam` … 宣伝・スパム・無関係リンク（スルー推奨）
- `HOLD-uncertain` … 事実確認が要る質問で、確証がない（A5＝憶測で断定しない）
- `HOLD-sensitive` … 政治/宗教/論争/個人情報を含む
- `HOLD-nonJP-nonEN` … 日英以外の言語（誤訳リスク）

→ HOLD は日次点検で owner に一覧提示。owner がGO/文面修正したら READY に変える。

## TSV フォーマット

`pending.tsv`（cowork が追記）:
```
comment_id	article	author	lang	text	fetched_at
```
`replies.tsv`（code が書く／cowork が投稿後に更新）:
```
comment_id	article	lang	status	reply_text	posted_url	updated_at
```
- `status`: READY / POSTED / HOLD-criticism / HOLD-spam / HOLD-uncertain / HOLD-sensitive / HOLD-nonJP-nonEN
- **dedup**：同じ comment_id は二重に処理・投稿しない（両TSVで一意）。

## 安全・運用

- **kill-switch**：`ops/comments/PAUSE` ファイルがあれば cowork は取得も投稿も止める。
- **レート**：投稿は1回の実行で最大5件・間隔を空ける（凍結/スパム判定回避）。
- **記録**：投稿URLは replies.tsv と ops/logs へ。全件 git に残す（監査可能）。
- **A4**：住所/番地/私的情報を書かない・聞き出さない（市/県まで）。

## 位置づけ
「自動」だが**無検閲の全投稿ではない**＝praise/簡単な質問は自動で返し、リスクのある少数だけ人へ回す。
これがブランド保護(A5上位)と自動化の両立点。


## Stage0：過去記事の全件棚卸し（owner再確認要件・2026-09-02）

owner『過去記事に返信していないものを調べて、返信していなければ返信して』。**一度きりの全件パス**。

- 対象一覧＝`ops/comments/backlog_targets.tsv`（公開78件・article / note_id_or_url / swept / comments_found / unreplied_found）。
- cowork：各記事のコメント欄を開き**全コメント**（新着に限らない）を確認。
  - 既に当方が返信済み → `replies.tsv` に `status=POSTED` で記録（＝二度と触らない・dedup）。
  - 未返信 → `pending.tsv` に追記（→ code が下書き → READY → cowork 投稿）。
  - 記事ごとに `backlog_targets.tsv` の `swept=YES`・件数を記入して push。
- 進捗は `check_requirements.py` の R6 が `過去記事棚卸し N/78` として表示。全件YESで棚卸し完了。
- note_id 空欄の記事は、note アカウントの記事一覧から辿る（code は一部URLを未把握）。
