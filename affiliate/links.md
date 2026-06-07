# アフィリエイトリンク管理

note 記事に埋め込むアフィリエイトリンクの正本。
新しいリンクは下に追記式で記録し、削除はしない（過去記事の整合性のため）。

最終更新: 2026-06-07

---

## 稼働中

### A8.net / じゃらんnet

- **a8mat コード**: `1CCUH0+929KAA+14CS+64RJ5`
- **URL テンプレート**:
  ```
  https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=<URLエンコード済みじゃらんURL>
  ```

#### 主要エリア URL（生成済み）

| エリア | a8ejpredirect 値 | 完成リンク |
|---|---|---|
| 氷見 | `https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160025%2F` | `https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160025%2F` |
| 高岡 | `https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160006%2F` | `https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160006%2F` |
| 富山全体 | `https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160000%2F` | `https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160000%2F` |

#### 使い回しテンプレート（記事末尾用）

```markdown
---

### 旅の宿を探す（PR）

- 氷見の宿: https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160025%2F
- 高岡の宿: https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160006%2F
- 富山全体: https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160000%2F
```

---

## 未設定

### 楽天アフィリエイト / 楽天トラベル

- 状態: **未設定**
- 必要作業: https://affiliate.rakuten.co.jp/ でログイン → リンク生成
- 担当: オーナー（Chrome セッション要・Cowork 経由でも可）
- 想定用途: 楽天経由のホテル予約導線（じゃらんと並列で出すと CVR が分散しないか要 A/B）

### Booking.com / Stay22（推奨）

- 状態: **未設定（Stay22 を推奨）**
- 経緯: Awin Japan が **2026-06-30 で終了** → CJ Affiliate 経由は不要
- 推奨: [Stay22](https://stay22.com/) のホワイトラベルウィジェット（複数 OTA を集約）
- 想定用途: 海外読者向けの英語セクション末尾に設置

---

## 運用ルール

1. **アフィリエイトリンクは記事末尾の独立セクションに置く**（本文埋め込みは避ける）
2. **「PR」「広告」表記を必ず付ける**（景表法・ステマ規制対応）
3. **同一記事で複数 ASP のリンクを並べない**（CVR 分散・読者の選択疲れ）
4. **じゃらんリンクは現状の標準**：迷ったらじゃらん。地域 URL は上記表から選ぶ
5. **新規 ASP 追加時はこのファイルに必ず追記**
6. **コード/URL のローテーション時は旧コードも履歴として残す**（過去記事の追跡用）

---

## 公開済み記事への埋め込み状況（2026-06-07 時点）

Cowork セッションから引き継いだ情報（[`docs/cowork-handoff.md`](../docs/cowork-handoff.md) 参照）。

| 記事 ID | じゃらんリンク |
|---|---|
| n75868bbf7284 ひろゆきも泊まった、氷見の民宿 | ✅ |
| n17af1e4f1a80 ドラえもんの作者の故郷へ | ❌ |
| n512b2f5438c8 金沢に来たら、1日だけ高岡に | ✅ |
| nc3a37b9e7a37 北陸新幹線で新高岡に途中下車 | ✅ |
| naaa94948b05a 能登に行くなら、氷見から | ✅ |
| ncaa0329ab69e 立山黒部から富山に降りたら | ❌ |
| n13dc3d1baec8 高岡は日本で一番知られていない | ✅ |
| nd00d4f786b86 ニセコに飽きたなら北陸へ | ❌ |
| nb2f7f6fab31d 雷が呼ぶ魚、氷見の寒ブリ | ✅ |

未付与の3本（ドラえもん／立山黒部／ニセコ）は次回更新時に高岡 or 富山リンクを追加検討。
