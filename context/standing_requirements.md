# 恒常要件レジストリ（standing requirements）

> **なぜこれが必要か**：要件が「途中から実行されなくなる」根本原因は、**要件を記憶（STATE/docs）に書いた時点で"満たした"と誤認し、実際に動いている証拠(observable)を誰も検証しないから**。
> このレジストリは「動き続けねばならないこと」を1か所に集め、各要件に**実行された証拠(observable)**を紐づける。
> 毎日の点検で `python3 ops/check_requirements.py` を走らせ、**証拠が更新されていない要件を必ず owner に提示する**（静かに止まる→毎日アラームに変える）。

## 根本原因（自責での診断・2026-09-01）

1. **「手配＝完了」の誤認**：code が実行できない要件（A1＝note/X投稿等）を「ツール作成＋cowork発注」した時点で done 扱い。実行はcowork/owner側なのに、実行確認のループが無い。
2. **証拠を検証しない**：「記憶に書いた＝機能」ではない（STATE148で自認）。observable を定期検証していなかった。
3. **発注が fire-and-forget**：ops/inbox に出して放置→ open が27件堆積。締め・再送のSLAが無い。
4. **点検スコープが狭い**：日次点検は「新着cowork報告」中心で、恒常要件全体の生存を見ていない。
5. **新要件が旧要件を押しのける**：最新の指示に注意が集中し、古い恒常要件を再浮上させる仕組みが無い。
6. **A7＝セッション揮発**：CronCre 等はコンテナ破棄で消える。恒久は「日次点検＋STATE」だけ。

## 対策＝この台帳 + check_requirements.py + 日次点検の必須ステップ化

- 各要件に **observable（実行された機械的証拠）** を定義。
- 毎点検で checker を実行し、**OK以外（STALE/BROKEN/BLOCKED）を owner に提示**。
- 発注は「open のまま放置しない」＝ checker が古い open を警告。

---

## 要件一覧

| # | 要件 | 実行主体 | observable（証拠） | 目安cadence | 現状 | blocker |
|---|------|---------|-------------------|------------|------|--------|
| R1 | note記事の継続公開 | cowork(auto-publish) | drafts/published/ の最新note記事の日付 | 数日以内 | ✅ | — |
| R2 | 実写サムネ取得 | GitHub Action | CDO/.../thumbnails/*.jpg の最新 | 記事公開に追随 | ✅ | — |
| R3 | 英語SEOページ(3点セット) | code | apps/toyama-guide/en-*.html 総数(増加) | 新記事ごと | ✅ | — |
| R4 | クロスポスト素材(3点セット) | code | 2026-08-25_crosspost_… の更新日 | 新記事ごと | ✅ | — |
| R5 | **note→X 自動投稿** | cowork(note_to_x) | **ops/logs/x_posted.tsv の行数** | 公開ごと | ❌**BROKEN(0)** | **owner: X APIキー** |
| R6 | note コメント自動返信（新着＋**過去記事の全件棚卸し**） | cowork取得+code下書き | ops/comments/replies.tsv の POSTED ＋ backlog_targets.tsv の swept割合 | コメント発生時／棚卸しは一度全件 | ⏸ 空・棚卸し0/78 | cowork: note-login取得＝過去記事の全件スイープ（owner再確認要件2026-09-02） |
| R7 | 有料note導線の差し込み | cowork | cowork日次報告(有料導線) | 日次 | ✅ 誤失敗の根本修正済(R10) | — |
| R8 | 日次点検の生存 | code(点検トリガー) | context/STATE.md 最終更新の鮮度 | 日次 | ✅ | — |
| R9 | ops指示の滞留防止 | code | ops/inbox の open 件数(過多で警告) | 常時 | ✅ (open 2件・2026-09-01棚卸し) | — |
| R10 | 有料フッター差し込みの健全性 | code修正+cowork | append_paid_footer.py に結果行修正(対象0本でも結果行) | — | ✅ 根本修正・実機検証済 | 新記事付与のみ要manifest再生成+有人--apply検証 |
| R11 | sitemap 鮮度(SEO) | code | 全 toyama en ページが sitemap.xml に掲載 | 新記事ごと | ✅ 全掲載 | — |

> **凡例**：✅OK ／ ⚠️注意 ／ ❌BROKEN(動くべきなのにゼロ) ／ ⏸未着手(入力待ち) ／ BLOCKED(owner/cowork の前提待ち)

## 運用ルール（これで「途中でやめ」を防ぐ）

1. **毎日の点検で checker 必須**：`python3 ops/check_requirements.py` を実行し、非OKを owner に1行で提示。
2. **BROKEN/BLOCKED は放置しない**：owner 前提待ち(X APIキー等)は「これが要件停止の原因」と明示して owner に判断を仰ぐ。
3. **新要件を足したら、この台帳に observable を1行追加**（証拠が定義できない要件は"完了"にしない）。
4. **「手配した」で done にしない**：observable が動くまでは in-progress。
