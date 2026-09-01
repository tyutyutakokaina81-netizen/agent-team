# X（旧Twitter）自動投稿ツール — セットアップと運用（CDO・2026-09-01）

owner の希望「2（cowork発注）＋3（自動投稿ツール）」に対応。**code は A1 で外部不可のため投稿しない**。
ツール（`ops/x_poster.py`）は **owner/cowork の環境**で動かす。

---

## いちばん大事な前提（安全・課金）

- **課金（¥0原則）**：X API の **Free tier** で運用する。Free は書き込みに**月間の上限**がある（少ない）。
  料金・上限は変動するので、**登録前に X 公式（developer.x.com）で最新を必ず確認**。上限超過や有料化が要る規模になったら **owner 判断**（当社は有料従量課金の発生源を持たない方針）。
- **機密（4系統ルール）**：認証情報は **環境変数のみ**。リポジトリ（.env含む）に**絶対置かない**。`ops/x_poster.py` はコードにキーを持たず、実行時に環境変数から読む。
- **アカウント安全（凍結回避）**：
  - 1回の実行で**1スレッドだけ**投稿（連投しない）。
  - 投稿間隔は**1日1本**目安。cron を短くしない。
  - 文面は**人がレビュー**した素材のみ（`2026-08-25_crosspost_Reddit_X_templates.md`）。
  - スパム的な同文連投・大量ハッシュタグはしない。

---

## セットアップ（owner/cowork・1回だけ）

1. **X Developer 登録** → developer.x.com でアプリ作成（Free tier）。
2. アプリの権限を **Read and Write** にする（投稿に必要）。
3. **OAuth 1.0a のユーザー認証情報**を取得：
   - API Key / API Secret（アプリの Consumer Keys）
   - Access Token / Access Token Secret（自分のアカウントで発行）
4. ライブラリ導入：`pip install tweepy`
5. 環境変数に入れる（**シェルに直書きせず、その場のみ**）：
   ```bash
   export X_API_KEY=...       X_API_SECRET=...
   export X_ACCESS_TOKEN=...  X_ACCESS_SECRET=...
   ```

## 毎回の投稿手順

```bash
cd ~/agent-team && git pull origin main
# 1) 確認（投稿しない）：先頭の未投稿スレッドと文字数を表示
python3 ops/x_poster.py
# 2) 投稿（先頭1スレッドだけ・280字超は自動で中止）
python3 ops/x_poster.py --go
# 3) 投稿されると ops/logs/x_posted.tsv に記録され、queueは自動で [POSTED] に。
git add ops/x_queue.txt ops/logs/x_posted.tsv && git commit -m "x: posted <slug>" && git push
```

## スレッドの追加

`ops/x_queue.txt` に追記する：
```
=== <slug> ===
1行目のツイート（280字以内）
2行目のツイート（スレッドにするなら続けて／返信チェーンで投稿される）
```
素材は `CMO/outputs/2026-08-25_crosspost_Reddit_X_templates.md` の X スレッドをコピペ。
※長いスレッド（コロッケ/氷見/高岡の6ツイート版）は各行280字を確認してから入れる。

## 現在キューに入っている素材（seed済み・未投稿）

- 単発4本: tap-water / new-rice / nihyakutoka / cosmos（各1ツイート）
- スレッド6本: croquette / himi / takaoka / rice-fields / two-day / august（末尾ハッシュタグは最終ツイートへ統合済）
- 計10スレッド・全ツイート280字以内で検証済み（`python3 ops/x_poster.py` で確認可）

## トラブル時

- `✗ 280字超` → 文面を分割。
- `✗ 認証情報が環境変数に無い` → export し直す。
- `✗ tweepy 未インストール` → `pip install tweepy`。
- 429/レート制限や上限到達 → Free tier の月間上限。時間を空ける／翌月まで待つ（有料化は owner 判断）。

---

**この経路の位置づけ**：X は「note＋英語SEO＋クロスポスト」の3チャネルのうちの拡散担当。
実投稿は owner/cowork 側でしか行えない（A1）。code は素材・ツール・手順の整備までを担当する。

---

# note公開 → X自動投稿 の連動（2026-09-01 実装・owner指示）

**目的**: note記事が公開されたら、対応するXスレッドを自動で投稿する（＝実質「同時投稿」）。
**実行**: note公開デーモン（cowork/Mac・A1でcode不可）の**公開成功直後**に、記事ごとに1回呼ぶ。

```bash
# 公開できた記事 basename と そのnote URL を渡す（認証は環境変数）
python3 ops/note_to_x.py --article "<公開したmd basename>" --note-url "<note記事URL>"        # DRY-RUN
python3 ops/note_to_x.py --article "<...>" --note-url "https://note.com/.../n/nXXXX" --go     # 投稿
```

- 記事名→Xスレッド slug は `ops/note_to_x.py` の KEY_MAP（彼岸花/コスモス/水道水/新米/二百十日/田んぼ/コロッケ/氷見/高岡/2日/8月）。
  **新題材を作るたびに、x_queue.txt にXスレッドを追加し、必要なら KEY_MAP にも1行足す**（3点セットのX担当）。
- **安全**: 1呼び出し=1記事=1スレッドのみ。note URLは最終ツイートへ。280字超は中止。[POSTED]で二重投稿しない。
- **複数記事が同時公開**なら、デーモンは**記事ごとに間隔を空けて**呼ぶ（連投=凍結回避）。1日の投稿数はFree tier上限内に。
- 対応スレッドが無い記事は skip（＝そのうちKEY_MAP/x_queueに追加）。

## 稼働の前提（owner）
**X API Free tier のキー4つ（環境変数）が無いと投稿できない**。キーが入るまで、この連動は DRY-RUN 相当で「何も投稿しない」＝安全に空回りする。キーが入った瞬間から note公開のたびにXへ流れる。
