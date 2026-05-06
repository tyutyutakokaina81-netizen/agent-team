# daily/ — 毎朝自動生成されるドラフト集

GitHub Actions が **毎朝 07:00 (JST)** に自動で実行され、当日分のドラフトを `daily/YYYY-MM-DD/` に生成・コミットします。

**mac セットアップは不要**。iPhone のブラウザ（または GitHub アプリ）からドラフトを開いてコピー → note アプリに貼って公開、で運用できます。

---

## 自動化されているもの

| 項目 | 自動化レベル | 備考 |
|------|------------|------|
| ドラフト生成（note / SEO記事 / 提案書 / Reddit / Shorts / CW応募文） | ✅ **完全自動**（GitHub Actions） | 7:00 JST 毎日 |
| Reddit 投稿 | ✅ **完全自動**（公式API・GitHub Actions） | 段階的有効化（後述） |
| note 公開 | ⚠ 半自動（iPhone から1タップで貼り付けまで） | 公開ボタンは人間 |
| X 投稿 | ⚠ 半自動（同上） | mac での Plan B 全自動も別途可能 |
| CrowdWorks 応募 | ⚠ 半自動（同上） | 規約厳格・自動応募は mac の Plan B のみ |

## iPhone での1分運用

1. **GitHub アプリ**を iPhone にインストール（無料）
2. このリポジトリの `daily/<最新日付>/` を開く
3. 公開したいファイル（例：`note_draft.md`）をタップ
4. **Raw** ボタン → 全選択 → コピー
5. note アプリ → 新規記事 → 貼り付け → 公開
6. （任意）公開後の URL を `published.csv` に記録

詳しい iPhone Shortcuts レシピ：`projects/2026-05-05_AI自動収益化引き継ぎ/deploy/iphone_shortcuts.md`

## ファイル一覧の意味

| ファイル名 | 用途 | 編集要否 |
|-----------|------|--------|
| `note_draft.md` | 無料note記事 | そのまま公開可 |
| `paid_note_2980.md` | 有料note ¥2,980 | claude.ai で本文を肉付け推奨 |
| `reddit_post.md` | Reddit 投稿（英語） | そのまま公開可 |
| `youtube_short.md` | YouTube Shorts 台本 | 動画素材は別途 |
| `seo_article.md` | SEO 記事の骨組み（H2/H3） | claude.ai で本文を肉付け必須 |
| `crowdworks_application_*.txt` | CW 応募文（カテゴリ別） | 案件タイトルだけ調整 |
| `proposal_sample.md` | 法人向け提案書サンプル | 案件名・予算を調整 |
| `README.md` | 当日ドラフト一覧 | — |

## ワークフロー

- 定義：`.github/workflows/daily-drafts.yml`
- 手動実行：GitHub の Actions タブ → "Daily Drafts" → "Run workflow"
- 失敗時：GitHub の通知が届く

## 関連ドキュメント

- 全体設計：`projects/2026-05-05_AI自動収益化引き継ぎ/outputs/claude_code_handover.docx`
- mac での全自動 Plan B（Web自動投稿）：`projects/2026-05-05_AI自動収益化引き継ぎ/deploy/SETUP_PROMPT.md`
- COO 運用ルール：`COO/prompt.md`
