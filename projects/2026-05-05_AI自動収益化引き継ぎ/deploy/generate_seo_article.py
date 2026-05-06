"""SEO記事の骨組み生成（L2の主柱・¥10〜30K案件用）。

3,000字想定の構成案＋本文の雛形を outputs/ に書き出す。
本文は無料Web AI（claude.ai / gemini）で肉付けする前提。
prompts/polish_prompts.md の SEO展開プロンプトとセットで使う。

例:
    python3 generate_seo_article.py "地方副業 始め方"
    python3 generate_seo_article.py "AI 文章生成 ツール" --intent commercial
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

OUT = Path.home() / "ai-auto" / "outputs"

INTENT_GUIDE = {
    "info": ("情報収集型", "知りたい・理解したい読者向け。手順・比較・解説を中心に。"),
    "commercial": ("購入検討型", "比較したい読者向け。料金・機能・選び方を中心に。"),
    "transactional": ("行動直前型", "今すぐやりたい読者向け。手順・チェックリスト・即効性。"),
    "navigational": ("指名検索型", "特定サービス目当て。公式情報＋使い方の補足。"),
}


def build(keyword: str, *, intent: str = "info", target_chars: int = 3000) -> str:
    intent_label, intent_desc = INTENT_GUIDE.get(intent, INTENT_GUIDE["info"])
    return f"""# SEO記事 骨組み：{keyword}

## メタ情報
- 主キーワード：{keyword}
- 検索意図：{intent_label}（{intent_desc}）
- 想定字数：{target_chars}字
- 想定読了時間：{target_chars // 600}分
- 推奨タイトル文字数：28〜32字

## タイトル候補（3案・無料Web AIで膨らませる）
1. 【{datetime.now().year}年版】{keyword}の始め方｜失敗しない3ステップ
2. {keyword}を実際にやってみた｜初心者がつまずく5つのポイント
3. {keyword}とは？プロが教える選び方と注意点

## メタディスクリプション（120字以内）
{keyword}について、基礎から実践までを網羅。よくある失敗例と回避策、初心者でも今日から始められる手順を、実例とともに解説します。

## 構成（H2/H3）

### H2-1：{keyword}とは｜まず押さえる前提（500字目安）
- H3：定義と背景
- H3：今注目される3つの理由

### H2-2：{keyword}の始め方｜5ステップ（800字目安）
- H3：ステップ1 — 準備
- H3：ステップ2 — 環境構築
- H3：ステップ3 — 最初の一歩
- H3：ステップ4 — 継続のコツ
- H3：ステップ5 — 振り返りと改善

### H2-3：{keyword}でよくある失敗3選（500字目安）
- H3：失敗1 — 完璧主義
- H3：失敗2 — 情報収集だけで止まる
- H3：失敗3 — 数字を見ない

### H2-4：{keyword}を続けるための仕組み化（600字目安）
- H3：日次ルーチンの作り方
- H3：週次レビューの型
- H3：月次の振り返り

### H2-5：まとめ｜今日からできる一歩（200字目安）
- 行動を1つだけ提案

## 内部リンク候補
- 関連記事「{keyword} ツール 比較」
- 関連記事「{keyword} 初心者 失敗例」

## 外部リンク候補（信頼性UP）
- 公式統計・公的機関データを1つ
- 業界調査レポート1つ

## 想定検索キーワード（共起語）
- {keyword} 始め方
- {keyword} 初心者
- {keyword} 失敗
- {keyword} ツール
- {keyword} おすすめ

----

## 本文（無料Web AIで肉付けする領域）

無料Web AI（claude.ai / gemini）に以下を貼り付けて展開してください：

```
あなたはSEOライターです。下記の構成に沿って、{target_chars}字程度の本文を執筆してください。
- 主キーワード「{keyword}」を自然に4〜6回挿入
- 各H2の下にH3を3つずつ展開
- 一文は40字以内、段落は3行以内
- 体験談・具体例を1つ以上含める
- 結論は最初と最後の両方に配置（PREP法）

[ここに上記の構成（H2/H3）を貼る]
```

出力をこのファイルの「## 本文（ここから）」以下に貼り戻して納品。

## 本文（ここから）

（無料Web AIの出力を貼る）
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="SEO記事の骨組み生成")
    parser.add_argument("keyword", help="主キーワード")
    parser.add_argument("--intent", default="info", choices=sorted(INTENT_GUIDE))
    parser.add_argument("--chars", type=int, default=3000)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe = args.keyword.replace("/", "_").replace(" ", "_")[:40]
    path = OUT / f"{today}_seo_article_{safe}.md"
    path.write_text(build(args.keyword, intent=args.intent, target_chars=args.chars), encoding="utf-8")
    print(f"生成完了: {path}")
    print(f"次：claude.ai に prompts/polish_prompts.md の『SEO展開』を貼って肉付けする")


if __name__ == "__main__":
    main()
