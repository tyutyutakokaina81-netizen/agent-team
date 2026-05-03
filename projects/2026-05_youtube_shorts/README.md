# 2026-05_youtube_shorts — 富山×海外バズ狙い ショートシリーズ

**作成日**: 2026-05-03
**プロジェクト責任**: CMO（撮影・投稿）／ CDO（プロンプト・自動化支援）
**目的**: 富山の知られざる素材5本を、英語テロップ × 日本語ナレーションで海外視聴者に届ける
**尺**: 30秒/本（縦型 9:16）

---

## 🚨 運用ルール（必読）

### AGENT_RULES.md 適用ルール

| ルール番号 | 内容 | このプロジェクトでの運用 |
|----------|------|----------------------|
| **R3（1日1テーマ）** | 1日に1つのテーマだけ進める | **撮影は1日1本まで**。当日に2本撮らない。編集も1本ずつ。 |
| **R5（既存資産を先に確認）** | 新規作成より既存活用 | 撮影前に Desktop の `takaoka_shorts_*.mp4` の流用可否を確認 |
| **R1（費用ゼロ）** | API課金しない | BGMはYouTube Audio Library / Audio Library YT 等の無料源のみ使用 |
| **R4（戦略膨張禁止）** | 新シリーズを増やしすぎない | 5本完走するまで他のショート企画を立ち上げない |
| **R8（短く・実行優先）** | 議論より実行 | 台本を完璧にしすぎず、まず Day 1 を撮ってから調整 |

### 撮影スケジュール（1日1本）

| Day | Episode | 撮影地 | 備考 |
|-----|---------|-------|------|
| Day 1 | 01_takaoka_buddha | 高岡大仏前・商店街 | コロッケは個包装俯瞰でも可 |
| Day 2 | 02_firefly_squid | 滑川市・市場/水族館 | 発光カットは許諾要 |
| Day 3 | 03_toyama_black | 西町大喜（要許諾） | 食事中に撮影 |
| Day 4 | 04_kobujime | 自宅キッチン or 市場 | 仕込み→完成は2回に分割 |
| Day 5 | 05_takaoka_bronze | 金屋町の工房（要許諾） | 工房側都合優先 |

---

## 📁 フォルダ構造

```
2026-05_youtube_shorts/
├── SCRIPTS.md                ← 全5本の台本（マスター）
├── README.md                 ← このファイル
├── 01_takaoka_buddha/        ← Episode 1 素材・編集ファイル
├── 02_firefly_squid/         ← Episode 2 素材・編集ファイル
├── 03_toyama_black/          ← Episode 3 素材・編集ファイル
├── 04_kobujime/              ← Episode 4 素材・編集ファイル
└── 05_takaoka_bronze/        ← Episode 5 素材・編集ファイル
```

各サブフォルダの推奨内訳:

```
0X_xxx/
├── raw/         ← 撮って出し（編集前の素材）
├── edit/        ← Premiere/CapCut/Canva の編集プロジェクト
├── audio/       ← BGM・SE
├── thumbnails/  ← サムネ案
└── final.mp4    ← 投稿版
```

---

## 🎯 海外バズ狙いの設計原則

1. **冒頭3秒で "Wait, what?" を起こす** — 数字 or 意外性で英語テロップを打つ
2. **ナレーションは日本語のまま** — "本物感" を演出（吹き替えしない）
3. **英語テロップは画面中央〜下1/3** — 縦型で読みやすく
4. **架空の店名は禁止**（Episode 03 の「西町大喜」のみ実在店舗）
5. **概要欄に Medium 記事リンク**（EN/FR）を必ず貼る
6. **シリーズ感を出す** — 各動画の最後に "Episode X of 5" のテロップ＆Pinnedコメントで他話誘導

---

## 📖 参考リンク

- 台本本体: [SCRIPTS.md](./SCRIPTS.md)
- AGENT_RULES.md: [../../AGENT_RULES.md](../../AGENT_RULES.md)
- プロジェクト一覧: [../_index.md](../_index.md)
- Medium 記事 EN: https://medium.com/@tyutyu.tako.kaina81/doraemon-lives-in-takaoka-a-locals-view-712c66ceb922
- Medium 記事 FR: https://medium.com/@tyutyu.tako.kaina81/doraemon-vit-à-takaoka-le-regard-dun-habitant-ab3cfed5d224

---

## ✅ 進捗チェック（更新する）

- [x] 2026-05-03 SCRIPTS.md 作成（事実検証 web_search 完了）
- [x] 2026-05-03 フォルダ構造作成
- [x] 2026-05-03 projects/_index.md 登録
- [ ] Day 1: Ep01 高岡大仏 撮影
- [ ] Day 1: Ep01 編集・投稿
- [ ] Day 2: Ep02 ホタルイカ 撮影
- [ ] Day 2: Ep02 編集・投稿
- [ ] Day 3: Ep03 富山ブラック 撮影（要許諾）
- [ ] Day 3: Ep03 編集・投稿
- [ ] Day 4: Ep04 昆布締め 撮影
- [ ] Day 4: Ep04 編集・投稿
- [ ] Day 5: Ep05 高岡銅器 撮影（要許諾）
- [ ] Day 5: Ep05 編集・投稿
- [ ] 5本完走後、まとめ動画（横型）作成
