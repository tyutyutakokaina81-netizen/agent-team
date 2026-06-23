# AI自動化サポート — ランディングページ（HP）

単一 `index.html`（依存ゼロ）。AI自動化代行の公開用ホームページ＝営業の送り先。

## 中身
ヒーロー／課題／サービス（月額¥50K・¥100K・¥200K）／なぜ任せられるか（自社実証）／
はじめ方3ステップ／FAQ／無料サンプルCTA／免責。スマホ対応。A4(PIIなし)・A5(成果保証なし)順守。

## 公開前に差し替える（owner）
- `【連絡先メールをここに】` `【連絡先】` `【屋号 / Kai Arata】` を実際の値に。
- メールCTAは `mailto:` 。問い合わせフォームを使うならリンク先を差し替え。

## 無料で公開する方法（どれか）
1. **GitHub Pages（推奨・無料）**
   - リポジトリ Settings → Pages → Source: `Deploy from a branch` → `main` / フォルダ指定、
     または `apps/ai-agency-hp/index.html` を公開用ブランチ/ディレクトリに配置。
   - 既存 `.github/workflows/pages.yml` は `tavern.html` を公開する設定。HPを正面に出すなら
     pages.yml の対象をこの `index.html` に変える（owner/cowork が調整）。
2. **Netlify / Cloudflare Pages（無料枠）**：このフォルダをドラッグ&ドロップで即公開。
3. **note/サイトに本文として**：内容をコピーして掲載（体裁は簡略化）。

## 使い方（営業導線）
HP（公開）→ 「無料サンプル依頼」→ owner/cowork が受領 → 相手の実業務で個別サンプルを code が作成 → 月額契約。
