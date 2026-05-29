"""
run_pipeline.py — 毎日3本を通しで実行（高岡note自動投稿）

フロー（1日分）:
  01 本日の3トピック選定（重複なし）
  → 各トピックについて:
       02 記事生成（Claude）
       03 実写サムネ生成（画像API）
       04 note へ公開（既定は下書きまで。--publish で公開操作）

使い方:
  python run_pipeline.py            # 3本を下書きまで生成（安全既定）
  python run_pipeline.py --publish  # 公開まで（要セッション・要承認運用）

毎日自動化する場合は cron / launchd で 1日1回起動する。
"""

import sys
import datetime
from importlib import import_module

select = import_module("01_select_topics")
article = import_module("02_generate_article")
thumb = import_module("03_generate_thumbnail")
publish = import_module("04_publish_note")


def main(do_publish: bool):
    date = datetime.date.today().isoformat()
    todays = select.select_today(n=3)
    print(f"=== {date} 本日の3トピック: {[t['topic_id'] for t in todays]} ===")

    for t in todays:
        print(f"\n--- {t['topic_id']} ({t['angle']}) ---")
        art_path = article.generate(t["topic_id"], t["angle"], date)
        try:
            thumb_path = thumb.generate(art_path)
        except Exception as e:
            print(f"[warn] サムネ生成失敗（記事は生成済）: {e}")
            thumb_path = None
        if do_publish:
            publish.publish(art_path, thumb_path, headless=True)
        else:
            print("[skip] 公開はスキップ（--publish で実行）。")

    print(f"\n=== 完了: {len(todays)} 本 ===")


if __name__ == "__main__":
    main(do_publish="--publish" in sys.argv)
