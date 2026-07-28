# 被リンク先ファインダー v2 — recent / 低回答スレ優先（探索クエリ集）

- **作成**: 2026-07-28 / CMO（code）
- **背景（cowork 2026-07-28_001報告）**: Quoraはログイン復活済だが、batch3対象トピックの**実在スレは全て古く飽和**（トップ回答300〜627upvote・19回答超）。新規アカで飽和スレに埋没リンクを差すのは (a)可視性ほぼ0 (b)被リンク価値ほぼ0 (c)スパム/BANリスク。→ **詰まりは「良質な鮮度スレの不在」**。
- **本ファイルの目的**: 「人気（＝飽和）スレ」でなく **recent（新しい）× 低回答数（先頭を取れる）× high-intent（具体質問）** のスレだけを surface する探索手順とクエリを提供。worker/owner が**手動で1回だけ**投稿する運用は不変（自動投稿しない・A5厳守）。
- **判定しきい値（この条件を満たすスレだけ投稿対象）**:
  - 投稿日 **30日以内**（できれば7日以内）
  - 既存回答/コメント **5件未満**（0〜2件が理想＝最初の良回答になれる）
  - 質問が **具体的**（漠然とした"underrated Japan"でなく、ルート/所要/パス/行き方など）
  - リンク先ページと**質問が直結**（無関係な質問に貼らない）

---

## A. Quora — 鮮度＋低回答の探し方

Quoraは「新着×低回答」で直接ソートしにくいので、**Googleの時間フィルタ＋site:検索**で新しい質問を surface し、Quora内で回答数を目視確認する二段構え。

### A-1. Google経由で新しいQuora質問を拾う（推奨）
Google検索 → ツール → 期間指定「1か月以内」/「1週間以内」で以下を実行：
```
site:quora.com Toyama when to visit
site:quora.com "Tateyama" alpine route open OR dates OR direction
site:quora.com Takaoka OR Himi Japan itinerary
site:quora.com Shirakawa-go OR Gokayama from Toyama OR Takaoka OR Kanazawa
site:quora.com Kurobe gorge OR dam OR trolley
site:quora.com "off the beaten path" Japan Hokuriku OR "Sea of Japan"
site:quora.com Japan 2 weeks itinerary "add" OR "worth" central OR Toyama
```
- ヒットしたら質問ページを開き、**回答数と最新性**を確認。5回答未満なら候補。
- 「Answer」ボタンが目立つ＝未回答/低回答の合図。飽和（19回答・数百upvote）は**捨てる**。

### A-2. Quora内の「Questions」タブ活用
Quoraのトピック（Travel in Japan / Toyama Prefecture 等）で **Questions** タブ→未回答（"0 answers"表示）を優先。Spaceの新着質問も低回答が多い。

### A-3. 投稿ルール（Quora）
- 新規/低karmaアカは**初週リンク控えめ**。まず**リンク無しの良回答を2〜3本**投げて信頼を作ってから、関連質問にだけリンク1本。
- 1回答＝導線1本。本文で十分な価値を出し、末尾に「詳しくは」で1リンク。

---

## B. Reddit — 週次スレ＋sort=new＋低コメント

Redditは**検索URLで new ソート**が効くので、鮮度探索はQuoraより機械的にできる。

### B-1. new ソートの検索URL（そのまま開ける）
```
https://www.reddit.com/r/JapanTravel/search/?q=Toyama&sort=new&restrict_sr=1
https://www.reddit.com/r/JapanTravelTips/search/?q=Toyama&sort=new&restrict_sr=1
https://www.reddit.com/r/JapanTravel/search/?q=Tateyama%20alpine&sort=new&restrict_sr=1
https://www.reddit.com/r/JapanTravel/search/?q=Shirakawago%20OR%20Gokayama&sort=new&restrict_sr=1
https://www.reddit.com/r/JapanTravelTips/search/?q=Kanazawa%20itinerary&sort=new&restrict_sr=1
https://www.reddit.com/r/JapanTravel/search/?q=Kurobe&sort=new&restrict_sr=1
```
- **コメント0〜3件**の新しい質問を優先（先頭回答＝可視性が高い）。
- 数百upvote・数十コメントの人気スレは**捨てる**（埋没）。

### B-2. 週次/定期スレ（毎回リセット＝常に新鮮）
- r/JapanTravel と r/JapanTravelTips の **Weekly/Daily質問メガスレ**に、その週の実際の質問へ回答。megathreadは自己宣伝規約が比較的ゆるく、鮮度も常に高い。
- 「itinerary check」系スレで富山/立山/白川郷が絡む行程に、実用一文＋（信頼構築後に）リンク1本。

### B-3. 投稿ルール（Reddit・厳守）
- **9:1ルール**（自己宣伝以外の貢献9：宣伝1）。新規/低karmaのgithub.ioリンクは自動削除されやすい→**まずリンク無しで価値本文**、karma/信頼ができてからリンク。
- 各subのルール（self-promo禁止/フレア必須等）をスレ投稿前に確認。無関係スレに貼らない。

---

## C. 運用フロー（worker/owner・1日5〜10分）

1. **探索**: A-1（Google時間フィルタ）とB-1（Reddit new）を上から実行。しきい値（30日以内・5回答未満・具体・直結）を満たすスレだけを**3〜5件**メモ。
2. **選別**: リンク先ページ（batch3の9本＝`quora_reddit_batch3_newpages_EN.md`）と直結する質問だけ残す。
3. **投稿**: 用意済みドラフト（品質良好）を、相手の文脈に**一文だけ**合わせて手動投稿。Quora/Redditとも**まずは価値本文中心・リンクは信頼構築後**。1スレ1リンク。
4. **記録**: 投稿したURL・日付・リンク先を `ops/outbox` かこの項の下に追記（同じスレへの重複投稿防止）。
5. **禁止**: 自動一括投稿・飽和スレへの埋没リンク・無関係スレ・"世界唯一"等の誇張（A5）・fake完了宣言。

---

## D. 見つからない日の代替（無風を作らない）

鮮度スレが0の日は、リンク投下を**無理にしない**（スパム化を避ける）。代わりに：
- Redditの週次スレに**リンク無しの良回答**を1本（信頼貯金＝将来のリンクが通る土台）。
- Pinterest/自サイト内部リンク等、規約リスクの低い導線を回す（`EN/outputs/2026-07-01_世界配布キット_Reddit_Pinterest_Forums.md` 参照）。
- 「今日は適地なし」を正直に記録（fake完了宣言はしない＝A5）。

---

## メモ
- 本v2は「探し方」の再設計。**投稿ドラフト自体は既存**（`quora_reddit_batch3_newpages_EN.md` 9本・品質良好）で不足なし＝課題は"投稿先の鮮度"だけだった。
- 自動化は現状しない（Quora/Redditの規約・BANリスク・A5より、手動1回投稿が安全）。将来スクリプト化するなら「Google site:検索の時間フィルタ結果を収集→回答数を目視verifyしてから提示」の**読み取り専用collector**までに留める（自動投稿はしない）。
