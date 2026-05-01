#!/usr/bin/env python3
"""
auto_gen_articles.py — Claude API Batches で SEO記事を一括生成

使い方:
  python3 auto_gen_articles.py          # 全トピックを生成
  python3 auto_gen_articles.py --dry    # トピック一覧だけ表示

必要環境変数:
  ANTHROPIC_API_KEY

コスト: claude-haiku-4-5 + Batches API → 通常の約5%のコスト
"""

import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

REPO      = Path(__file__).parent
OUTPUT_DIR = REPO / "CMO" / "outputs"
SESSIONS  = REPO / ".sessions"
STATE_FILE = SESSIONS / "article_gen_state.json"

TODAY = date.today().isoformat()

# ── 生成するSEO記事トピック（キーワード × 検索意図）─────────────────
TOPICS = [
    {
        "id": "seo_01",
        "keyword": "フリーランス 確定申告 いくらから",
        "title": "フリーランスの確定申告はいくらから必要？20万円の壁を完全解説",
        "tags": "#確定申告 #フリーランス #副業 #節税 #20万円",
        "template_cta": "フリーランス収支管理スプレッドシート（¥980）",
    },
    {
        "id": "seo_02",
        "keyword": "在宅ワーク 初心者 稼げる",
        "title": "在宅ワーク初心者が最初に稼げる仕事5選【2026年・実績あり】",
        "tags": "#在宅ワーク #副業 #フリーランス #初心者 #クラウドワークス",
        "template_cta": "フリーランス収支管理スプレッドシート（¥980）",
    },
    {
        "id": "seo_03",
        "keyword": "副業 バレない 会社員",
        "title": "会社員の副業がバレない3つの方法と、バレたときの対処法",
        "tags": "#副業 #会社員 #バレない #住民税 #確定申告",
        "template_cta": "フリーランス収支管理スプレッドシート（¥980）",
    },
    {
        "id": "seo_04",
        "keyword": "クラウドワークス 始め方 登録",
        "title": "クラウドワークス始め方ガイド【登録〜初受注まで画像付きで解説】",
        "tags": "#クラウドワークス #副業 #在宅ワーク #フリーランス",
        "template_cta": "CrowdWorks応募文テンプレート",
    },
    {
        "id": "seo_05",
        "keyword": "ランサーズ クラウドワークス 違い",
        "title": "ランサーズとクラウドワークスの違い5つ——初心者はどちらを選ぶべきか",
        "tags": "#ランサーズ #クラウドワークス #副業 #フリーランス",
        "template_cta": "フリーランス収支管理スプレッドシート（¥980）",
    },
    {
        "id": "seo_06",
        "keyword": "Googleスプレッドシート 家計簿 テンプレ",
        "title": "Googleスプレッドシートで家計簿を自動化する方法【無料テンプレ付き】",
        "tags": "#Googleスプレッドシート #家計簿 #節約 #副業 #テンプレート",
        "template_cta": "フリーランス収支管理スプレッドシート（¥980）",
    },
    {
        "id": "seo_07",
        "keyword": "SNS運用代行 料金 相場",
        "title": "SNS運用代行の料金相場は？【依頼側・受注側 両方の視点で解説】",
        "tags": "#SNS運用 #副業 #Instagram #フリーランス #料金",
        "template_cta": "SNS投稿カレンダーテンプレート（¥680）",
    },
    {
        "id": "seo_08",
        "keyword": "Instagram 投稿 頻度 フォロワー増やす",
        "title": "Instagramの投稿頻度とフォロワーの関係——週何回投稿すべきか",
        "tags": "#Instagram #SNS運用 #フォロワー #副業 #集客",
        "template_cta": "SNS投稿カレンダーテンプレート（¥680）",
    },
    {
        "id": "seo_09",
        "keyword": "Excel スキル 副業 活かす",
        "title": "Excelスキルを副業に活かす5つの方法【月5万円の実例あり】",
        "tags": "#Excel #副業 #スキル #クラウドワークス #データ入力",
        "template_cta": "フリーランス収支管理スプレッドシート（¥980）",
    },
    {
        "id": "seo_10",
        "keyword": "高岡 観光 日帰り 東京から",
        "title": "東京から高岡へ日帰り旅行は可能？【新幹線・モデルコース・費用まとめ】",
        "tags": "#高岡市 #富山観光 #日帰り旅行 #北陸旅行 #新幹線",
        "template_cta": "高岡市 完全ガイドマガジン（¥4,980）",
    },
]

SYSTEM_PROMPT = """あなたはSEOに強いnoteライターです。
読者に本当に役立つ記事を書いてください。

## 記事の要件
- 文字数：2000〜3000文字
- 構成：## 見出し で適切にセクション分け
- 冒頭：読者の悩みに共感する書き出し（体験談風）
- 本文：具体的な数字・事例・手順を含む
- 末尾：テンプレート/マガジンへの自然な誘導（CTAテキスト指定あり）
- タグ行で終わる

## 文体
- 一人称は「私」
- 体験談を交えた親近感のある文体
- 「です・ます」調
- 小見出しは ## を使用
- リストは - で表記

## 禁止事項
- 嘘の情報・誇張
- 「〜と思います」の多用
- 過度な自己PRや押し売り表現"""


def load_env():
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"generated": {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def build_user_prompt(topic: dict) -> str:
    return f"""以下のSEOキーワードで記事を書いてください。

## 対象キーワード
{topic['keyword']}

## 記事タイトル
{topic['title']}

## CTA（記事末尾に自然に入れる）
「{topic['template_cta']}」へ誘導する文言を最後に入れてください。
URLは「[購入ページへ]」というプレースホルダーにしてください。

## タグ（記事の最後の行）
{topic['tags']}

それでは記事を書いてください。"""


def run_batch(client: anthropic.Anthropic, topics: list) -> str:
    requests = [
        Request(
            custom_id=t["id"],
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(t)}],
            ),
        )
        for t in topics
    ]

    batch = client.messages.batches.create(requests=requests)
    print(f"  バッチ作成: {batch.id}")
    return batch.id


def wait_for_batch(client: anthropic.Anthropic, batch_id: str, timeout: int = 600) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        batch = client.messages.batches.retrieve(batch_id)
        status = batch.processing_status
        processed = batch.request_counts.processing
        succeeded = batch.request_counts.succeeded

        print(f"  [{int(time.time()-start)}s] {status} — 処理中: {processed}, 完了: {succeeded}")

        if status == "ended":
            return True
        time.sleep(10)

    print("  ⚠️  タイムアウト")
    return False


def save_results(client: anthropic.Anthropic, batch_id: str, topics: list, state: dict):
    topic_map = {t["id"]: t for t in topics}
    saved = []

    for result in client.messages.batches.results(batch_id):
        topic = topic_map.get(result.custom_id)
        if not topic:
            continue

        if result.result.type == "succeeded":
            msg  = result.result.message
            body = next((b.text for b in msg.content if b.type == "text"), "")
            fname = f"{TODAY}_{result.custom_id}_note記事.md"
            fpath = OUTPUT_DIR / fname
            fpath.write_text(body, encoding="utf-8")

            state["generated"][result.custom_id] = {
                "file": fname,
                "title": topic["title"],
                "keyword": topic["keyword"],
                "date": TODAY,
            }
            saved.append(topic["title"])
            print(f"  ✅ 保存: {fname}")
        else:
            print(f"  ❌ 失敗 [{result.custom_id}]: {result.result}")

    save_state(state)
    return saved


def run(dry: bool = False):
    load_env()
    print("━" * 50)
    print("  記事一括生成 (Claude Batches API)")
    print("━" * 50)

    if dry:
        print("\n  生成予定トピック:")
        for i, t in enumerate(TOPICS, 1):
            print(f"  {i:2}. {t['title']}")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY が未設定です")
        print("  .env に ANTHROPIC_API_KEY=sk-ant-... を追加してください")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    state  = load_state()
    done   = set(state["generated"].keys())

    pending = [t for t in TOPICS if t["id"] not in done]
    if not pending:
        print("  全トピック生成済みです")
        return

    print(f"\n  生成対象: {len(pending)}本（生成済: {len(done)}本）")

    batch_id = run_batch(client, pending)

    print("\n  完了を待機中…")
    if not wait_for_batch(client, batch_id):
        print("  バッチIDを保存して後で確認してください:", batch_id)
        return

    print("\n  結果を保存中…")
    saved = save_results(client, batch_id, pending, state)

    print(f"\n{'━'*50}")
    print(f"  完了: {len(saved)}本生成")
    for title in saved:
        print(f"  ✅ {title[:50]}")
    print("━" * 50)


if __name__ == "__main__":
    run(dry="--dry" in sys.argv)
