# Cowork → Code 全重要事項引き継ぎ（2026-06-07）

> Cowork セッションから Claude Code セッションへの一括引き継ぎ。
> 内容は Cowork セッション時点でオーナーが共有した情報を verbatim で保持する。
> 古くなった項目は決定ログ追記式で更新し、この本文は履歴として残す。

## プロジェクト概要

- **オーナー**: てつ（藤森哲司 / @safe_canna441）
- **ゴール**: 高岡・氷見・富山を世界に発信する旅行ライターとして国際SEOで集客
- **主戦場**: note.com（https://note.com/safe_canna441）
- **フェーズ**: フェーズ2（国内＋海外への閲覧数拡大）

## 記事戦略

- **入口キーワード**: ドラえもん / 金沢 / 北陸新幹線 / 能登 / ひろゆき などで未知の読者を高岡へ誘導
- **日本語**: 自然な日本語文体（1,800〜2,200字）
- **英語セクション**: 翻訳ではなく独立した travel writing（150〜250 words）
  - "from Kanazawa" フレーム（金沢から30分の day trip）
  - "skip the crowds" / "barely any foreign tourists"
  - "This is the Japan most tourists never see"
  - アクセス情報必須（JR氷見線・新幹線等）

## 公開済み記事（2026-06-07 完了分）

| ID | タイトル | 状態 |
|---|---|---|
| n75868bbf7284 | ひろゆきも泊まった、氷見の民宿 | 公開済み＋じゃらんリンク |
| n17af1e4f1a80 | ドラえもんの作者の故郷へ | 公開済み |
| n512b2f5438c8 | 金沢に来たら、1日だけ高岡に | 公開済み＋じゃらんリンク |
| nc3a37b9e7a37 | 北陸新幹線で新高岡に途中下車 | 公開済み＋じゃらんリンク |
| naaa94948b05a | 能登に行くなら、氷見から | 公開済み＋じゃらんリンク |
| ncaa0329ab69e | 立山黒部から富山に降りたら | 公開済み |
| n13dc3d1baec8 | 高岡は日本で一番知られていない | 公開済み＋じゃらんリンク |
| nd00d4f786b86 | ニセコに飽きたなら北陸へ | 公開済み |
| nb2f7f6fab31d | 雷が呼ぶ魚、氷見の寒ブリ（鰤起こし） | 公開済み＋じゃらんリンク |

## 英語セクション刷新済み記事

- 白えびせんべい記事 → travel writing スタイルに更新完了
- 氷見干物記事 → "from Kanazawa" フレームで更新完了

## アフィリエイト設定

| ASP | プログラム | コード/状態 |
|---|---|---|
| A8.net | じゃらんnet | `a8mat=1CCUH0+929KAA+14CS+64RJ5` |
| 楽天アフィリエイト | 楽天トラベル | 未設定（affiliate.rakuten.co.jp でログイン要） |
| Booking.com | Stay22（代替） | Awin Japan 6/30 終了のため CJ は不要 |

### じゃらんアフィリエイトURL形式

```
https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=[URLエンコード済みじゃらんURL]
```

- 氷見エリア: `&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160025%2F`
- 高岡エリア: `&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160006%2F`
- 富山全体: `&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160000%2F`

## 未対応の残課題

1. **CrowdWorks Konatsu.F スカウト**: 「富山県の高校制服に関する調査」¥330 → 未返信（CrowdWorks で要確認）
2. **X 破損ツイート削除**: https://x.com/FujimoriTe27067/status/2063118974821577192 → 手動削除必要
3. **楽天アフィリエイト**: affiliate.rakuten.co.jp でのログイン・リンク生成が未完
4. **万葉線記事**: Daily takaoka blog セッションで下書き完成済み → 公開承認待ち
5. **過去記事の英語セクション刷新**: 残り多数（白えびせんべい・氷見干物以外）

## note.com API情報

- エンドポイント: `PUT /api/v1/text_notes/{数値ID}`
- 認証: `credentials: 'include'`（ブラウザセッション必須 → Chrome 拡張経由のみ可）
- 1日10記事の更新制限あり（JST 深夜リセット）

## Code への期待役割（新ワークフロー）

1. `drafts/YYYY-MM-DD-タイトル.md` に記事下書きを生成
2. `ops/inbox/` に公開指示 YAML を投入
3. Cowork が pickup して note.com に公開
4. アフィリエイトリンクの追加・英語セクション生成は Code で下書き → Cowork が API 投入

---

## 引き継ぎ後の Code 側アクション（追記）

このファイル受領時点での Code 側の動き：

- 受領した内容をそのまま `docs/cowork-handoff.md` として commit
- 既存の方針（`docs/role-division.md`）と矛盾しないか確認 → 矛盾なし
- 英語セクションの方針（travel writing 150〜250 words / "from Kanazawa" フレーム）は
  既往の英語要約方針より具体的 → 今後の執筆で優先採用
- `context/STATE.md` には別途「決定ログ」追記で本引き継ぎへのリンクを残す

---

## 追記（2026-06-12・code）：6/11 大量削除の復旧と「直接指示」フォールバック規程

- **事象**：6/11 18:22「自動バックアップ」コミット（5d328a8）が ops/・docs/・workflows・CDO/CAO成果物・サムネを大量削除。
  オーナー所見では「code に指示できない状態だったため cowork へ直接指示 → 古い作業ツリーのまま commit」が原因の可能性が高い。
- **復旧（6/12）**：ops/ 一式・本ファイル・cowork設計書3本・サムネ生成マスター・note_publisher最新版・
  記事対応サムネ169枚・CAO成果物・AGENTS.md・note-thumbnails.yml を `14f4eda` から復元。
  未復旧（要オーナー判断）：audit.yml / og-images.yml / worker-integrate.yml / .claude/settings.json の差分。
- **指示の現況**：過去指示は全て `superseded` として `ops/processed/` へ移動。
  **有効なのは `ops/inbox/2026-06-12_002_code_cowork.yaml` のみ**
  （inbox 残りの `*_code_worker.yaml` 2件は外部ワーカー向け別レーン・cowork対象外）。
- **フォールバック規程（code 不在時に cowork へ直接指示する場合）**：
  ①作業前に必ず pull ②`git add -A` 禁止・触ったファイルのみ add ③実施内容を ops/outbox に1枚残す
  ④破壊的操作はオーナー明示承認必須。詳細は 2026-06-12_002 の「0-b」参照。
- **6/12 ストック再配分**：記事11本のファイル名日付を変更（EN素材9ファイル・サムネ11枚も連動）。最新構成は `context/STATE.md`。
