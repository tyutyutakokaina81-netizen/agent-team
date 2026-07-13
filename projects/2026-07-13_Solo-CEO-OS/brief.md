# brief.md — Solo CEO OS（Gumroad商品化）

## 目的
この agent-team の仕組み（6役職AI幹部＋共通ルール＋永続メモリ）を、**個人情報を全て除去した
汎用テンプレ商品**としてパッケージ化し、Gumroad で $19 販売する。オーナーが写真で設定中の
「Solo CEO OS — Run your business like a company with AI executives」を完成させるためのプロジェクト。

## ゴール
1. 買った人がダウンロードして自分の事業に使える汎用パッケージ（`product/`）
2. Gumroad販売ページ文（英語メイン＋日本語）（`sales/`）
3. 写真の設定画面をどう設定するかのガイド（`gumroad-settings-guide.md`）

## 関与役職
- **CPO**（主導）：商品設計・パッケージ構成
- **CSO / CMO**：販売ページ文
- **CDO**：汎用版のルールブック・役職プロンプト整備

## サブフォルダ構成（テーマ別を採用）
- `product/` … 納品物本体（ZIP化してGumroadにアップロードする対象）
- `sales/` … 販売ページコピー（EN / JA）
- `gumroad-settings-guide.md` … 設定ガイド
- 理由：役職別より「納品物 / 販売 / 運用」の機能単位で分けた方が、出品作業に直結して自然。

## 重要な制約（厳守）
- **`product/` には実事業データを一切入れない。** 高岡・note・オーナー個人情報・STATE.mdの実内容は
  混入禁止（PII方針A4）。汎用テンプレのみ。
- 実際のGumroadアップロード・公開はオーナーがブラウザで手動（コンテナから外部到達不可・制約A1）。

## 状態
- 2026-07-13：product一式・sales(EN/JA)・設定ガイド 作成完了。ZIP（Solo-CEO-OS-v1.0.zip）とカバー案(cover.svg)も作成しオーナーへ送付済み。
- 2026-07-13：集客キット（launch/faq.md・social-posts.md・launch-plan.md）作成完了。出品と投稿はオーナー作業待ち。

## 集客キット（launch/）
- `faq.md` … 購入前FAQ（EN=商品ページ／JA=note）
- `social-posts.md` … X英語スレ/単発・Reddit・X日本語スレ（そのまま貼れる完成稿・`{LINK}`置換）
- `launch-plan.md` … Day0〜Week1の3ステップ・見る指標

## 次アクション（オーナー側）
1. `product/` を `Solo-CEO-OS-v1.0.zip` に圧縮 → Gumroadの Content にアップロード
2. `sales/gumroad_page_EN.md`（または JA）の本文を Description に貼る
3. サムネ作成（組織図デザイン）→ Cover に設定
4. `gumroad-settings-guide.md` の通りに各トグルを設定 → 公開前チェック3点 → 公開
