#!/usr/bin/env python3
"""
auto_gen_xposts.py — Claude API Batches で X(Twitter)投稿を一括生成

使い方:
  python3 auto_gen_xposts.py          # 全テーマを生成
  python3 auto_gen_xposts.py --dry    # テーマ一覧だけ表示

必要環境変数:
  ANTHROPIC_API_KEY

コスト: claude-haiku-4-5 + Batches API → 通常の約50%のコスト
出力: CMO/outputs/YYYY-MM-DD_xposts_XX.md（各テーマ5投稿）
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

REPO       = Path(__file__).parent
OUTPUT_DIR = REPO / "CMO" / "outputs"
SESSIONS   = REPO / ".sessions"
STATE_FILE = SESSIONS / "xpost_gen_state.json"

TODAY = date.today().isoformat()

# ── 生成するX投稿テーマ（各テーマ5投稿セット）─────────────────────────
THEMES = [
    {
        "id": "x_副業_01",
        "theme": "副業で月3万円達成するまでの失敗談",
        "keyword": "#副業 #フリーランス",
        "hook": "失敗談・共感型",
        "cta": "フリーランス収支管理スプレッドシート（¥980）→ [リンク]",
    },
    {
        "id": "x_副業_02",
        "theme": "クラウドワークス初心者が最初の案件を取るコツ",
        "keyword": "#クラウドワークス #副業初心者",
        "hook": "ハウツー・具体的手順型",
        "cta": "クラウドワークス応募文テンプレート → [リンク]",
    },
    {
        "id": "x_副業_03",
        "theme": "会社員が副業を会社にバレずに続ける方法",
        "keyword": "#副業 #会社員 #バレない",
        "hook": "リスク回避・安心感型",
        "cta": "フリーランス収支管理スプレッドシート（¥980）→ [リンク]",
    },
    {
        "id": "x_副業_04",
        "theme": "Excelスキルで副業月5万円稼ぐ実例",
        "keyword": "#Excel #副業 #スキル",
        "hook": "実績・数字型",
        "cta": "フリーランス収支管理スプレッドシート（¥980）→ [リンク]",
    },
    {
        "id": "x_副業_05",
        "theme": "副業の確定申告、何もわからなかった私がやったこと",
        "keyword": "#確定申告 #副業 #フリーランス",
        "hook": "体験談・初心者共感型",
        "cta": "フリーランス収支管理スプレッドシート（¥980）→ [リンク]",
    },
    {
        "id": "x_在宅_01",
        "theme": "在宅ワーク初心者がやりがちな5つのミス",
        "keyword": "#在宅ワーク #副業初心者",
        "hook": "ミス・失敗列挙型",
        "cta": "フリーランス収支管理スプレッドシート（¥980）→ [リンク]",
    },
    {
        "id": "x_在宅_02",
        "theme": "週2時間から始めた在宅ワーク、今の収入は",
        "keyword": "#在宅ワーク #副業 #時間管理",
        "hook": "before/after・変化型",
        "cta": "フリーランス収支管理スプレッドシート（¥980）→ [リンク]",
    },
    {
        "id": "x_SNS_01",
        "theme": "Instagramのフォロワーが増えない人が見落としている1つのこと",
        "keyword": "#Instagram #SNS運用 #フォロワー",
        "hook": "意外な気づき・問題提起型",
        "cta": "SNS投稿カレンダーテンプレート（¥680）→ [リンク]",
    },
    {
        "id": "x_SNS_02",
        "theme": "SNS運用代行を受注するまでにやった3つのこと",
        "keyword": "#SNS運用代行 #副業 #フリーランス",
        "hook": "ステップ・手順型",
        "cta": "SNS投稿カレンダーテンプレート（¥680）→ [リンク]",
    },
    {
        "id": "x_高岡_01",
        "theme": "東京から高岡へ日帰りしてわかったこと",
        "keyword": "#高岡市 #富山観光 #北陸旅行",
        "hook": "体験談・旅行記型",
        "cta": "高岡市完全ガイドマガジン（¥4,980）→ [リンク]",
    },
]

SYSTEM_PROMPT = """あなたはX(Twitter)のバズ投稿が得意なSNSライターです。

## 依頼内容
1つのテーマに対して、**5つのX投稿文**を作成してください。

## 投稿の要件
- 1投稿あたり最大140文字（日本語）
- ハッシュタグは各投稿に1〜2個のみ（指定タグを使用）
- 5投稿のうち1つだけCTAを入れる（残り4つはCTAなし）
- 投稿番号を先頭に付ける（例：【1/5】）

## 投稿パターン（5投稿で多様性を持たせる）
1. 問いかけ・共感型（「〜に悩んでいませんか？」）
2. 具体的な数字・事実型（「月3万円を〇ヶ月で達成した方法」）
3. 意外な気づき型（「実は〜だった」「〜と思ったら違った」）
4. ミニリスト型（「〜の3つのコツ：①②③」）
5. CTA付き行動促進型（「〜したい方はこちら → [リンク]」）

## 文体ルール
- 一人称は「私」または省略
- 親近感のある話し言葉
- 過度な絵文字は使わない（1投稿あたり0〜1個まで）
- 「！！！」など過剰な感嘆符は禁止

## 出力形式
【1/5】（投稿文）#ハッシュタグ

【2/5】（投稿文）#ハッシュタグ

…（5つ全て）"""


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


def build_user_prompt(theme: dict) -> str:
    return f"""以下のテーマでX投稿5本セットを作成してください。

## テーマ
{theme['theme']}

## 使用するハッシュタグ
{theme['keyword']}

## 投稿フック（雰囲気の参考）
{theme['hook']}

## CTA（5投稿目に入れる）
{theme['cta']}

それでは5本の投稿を作成してください。"""


def run_batch(client: anthropic.Anthropic, themes: list) -> str:
    requests = [
        Request(
            custom_id=t["id"],
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(t)}],
            ),
        )
        for t in themes
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


def save_results(client: anthropic.Anthropic, batch_id: str, themes: list, state: dict):
    theme_map = {t["id"]: t for t in themes}
    saved = []

    for result in client.messages.batches.results(batch_id):
        theme = theme_map.get(result.custom_id)
        if not theme:
            continue

        if result.result.type == "succeeded":
            msg  = result.result.message
            body = next((b.text for b in msg.content if b.type == "text"), "")

            # ファイル名をテーマIDから生成
            safe_id = result.custom_id.replace("_", "-")
            fname = f"{TODAY}_xposts_{safe_id}.md"
            fpath = OUTPUT_DIR / fname

            # ヘッダー付きで保存
            header = f"# X投稿5本セット — {theme['theme']}\n\nキーワード: {theme['keyword']}\n生成日: {TODAY}\n\n---\n\n"
            fpath.write_text(header + body, encoding="utf-8")

            state["generated"][result.custom_id] = {
                "file": fname,
                "theme": theme["theme"],
                "keyword": theme["keyword"],
                "date": TODAY,
            }
            saved.append(theme["theme"])
            print(f"  ✅ 保存: {fname}")
        else:
            print(f"  ❌ 失敗 [{result.custom_id}]: {result.result}")

    save_state(state)
    return saved


def run(dry: bool = False):
    load_env()
    print("━" * 50)
    print("  X投稿一括生成 (Claude Batches API)")
    print("━" * 50)

    if dry:
        print("\n  生成予定テーマ:")
        for i, t in enumerate(THEMES, 1):
            print(f"  {i:2}. {t['theme']}")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY が未設定です")
        print("  .env に ANTHROPIC_API_KEY=sk-ant-... を追加してください")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    state  = load_state()
    done   = set(state["generated"].keys())

    pending = [t for t in THEMES if t["id"] not in done]
    if not pending:
        print("  全テーマ生成済みです")
        return

    print(f"\n  生成対象: {len(pending)}テーマ × 5投稿 = {len(pending)*5}投稿（生成済: {len(done)}テーマ）")

    batch_id = run_batch(client, pending)

    print("\n  完了を待機中…")
    if not wait_for_batch(client, batch_id):
        print("  バッチIDを保存して後で確認してください:", batch_id)
        return

    print("\n  結果を保存中…")
    saved = save_results(client, batch_id, pending, state)

    print(f"\n{'━'*50}")
    print(f"  完了: {len(saved)}テーマ分生成（{len(saved)*5}投稿）")
    for theme in saved:
        print(f"  ✅ {theme[:50]}")
    print("━" * 50)


if __name__ == "__main__":
    run(dry="--dry" in sys.argv)
