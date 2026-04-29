#!/usr/bin/env python3
"""
auto_affiliate.py — アフィリエイトリンク自動挿入（¥0）

note記事・X投稿のキーワードに対してアフィリエイトリンクを自動挿入。
じゃらん・楽天トラベル・Amazon（全て無料参加可能）。

新規記事が生成されるたびに実行される。
"""

import json
import re
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
OUTPUTS_DIR = REPO / "CMO" / "outputs"
AFFILIATE_LOG = SESSIONS / "affiliate_log.json"

# ─── アフィリエイトリンク設定 ─────────────────────────────────
# 実際のアフィリエイトID取得後にここを更新する（無料登録）
# じゃらん: https://af.moshimo.com/af/c/click?pc=...
# 楽天トラベル: https://hb.afl.rakuten.co.jp/hgc/...

AFFILIATE_LINKS = {
    # じゃらん（高岡市 宿泊検索）
    "じゃらん_高岡": {
        "url": "https://www.jalan.net/yw/yw501004.do?screenId=UWW3001&rootCd=26&dateUnixtime=&adultNum=2&checkinDay=&checkinMonth=&checkinYear=&nightsNum=1&searchKeyword=高岡市",
        "text": "【じゃらん】高岡市の宿泊を探す",
        "keywords": ["宿泊", "ホテル", "旅館", "1泊", "宿", "泊"],
    },
    # 楽天トラベル（高岡市）
    "楽天トラベル_高岡": {
        "url": "https://travel.rakuten.co.jp/yado/toyama/takaoka/?f_teikei=portal&f_flg=PORTAL",
        "text": "【楽天トラベル】高岡市のホテルを比較する",
        "keywords": ["宿泊", "ホテル", "旅館", "1泊", "宿", "泊", "温泉"],
    },
    # 北陸新幹線（交通）
    "えきねっと_新幹線": {
        "url": "https://www.eki-net.com/top/reserve/Top.aspx",
        "text": "【えきねっと】北陸新幹線の予約",
        "keywords": ["新幹線", "交通", "アクセス", "東京から", "移動"],
    },
    # レンタカー
    "じゃらん_レンタカー": {
        "url": "https://www.jalan.net/rentacar/rst/LstPrd.aspx?pPrefectureCD=16&pAreaCD=1601",
        "text": "【じゃらん】富山・高岡のレンタカーを探す",
        "keywords": ["レンタカー", "車", "ドライブ", "自動車"],
    },
    # Amazonプライム（旅行書籍誘導）
    "Amazon_北陸旅行": {
        "url": "https://amzn.to/3northrikutravel",  # 要実際のASIN
        "text": "【Amazon】北陸旅行ガイドブックを見る",
        "keywords": ["旅行本", "ガイドブック", "観光案内"],
    },
}


# ─── リンク挿入ロジック ──────────────────────────────────────

def find_insertion_point(lines: list, keywords: list) -> int:
    """キーワードに関連する最後の見出し直後の行番号を返す"""
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw in line:
                # その段落の末尾を探す
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].startswith("##") or lines[j].startswith("---"):
                        return j
    return -1  # 末尾に追加


def insert_affiliate_links(content: str, article_path: Path) -> tuple[str, int]:
    """記事内容にアフィリエイトリンクを挿入"""
    lines = content.split("\n")
    inserted = 0
    already_has = set()

    # 既にリンクが入っているか確認
    for line in lines:
        for link_id, info in AFFILIATE_LINKS.items():
            if info["url"] in line or info["text"] in line:
                already_has.add(link_id)

    # キーワードに基づいて挿入
    inserts_to_do = []
    for link_id, info in AFFILIATE_LINKS.items():
        if link_id in already_has:
            continue
        for kw in info["keywords"]:
            if kw in content:
                inserts_to_do.append((link_id, info))
                break

    if not inserts_to_do:
        return content, 0

    # 記事末尾の「---」の前にまとめて挿入
    insert_section = [
        "",
        "---",
        "",
        "## 高岡旅行の準備に",
        "",
    ]
    for link_id, info in inserts_to_do[:3]:  # 最大3リンク
        insert_section.append(f"- [{info['text']}]({info['url']})")
        inserted += 1

    insert_section.append("")

    # 末尾の「---」の直前に挿入
    new_lines = []
    inserted_flag = False
    for i, line in enumerate(lines):
        # ハッシュタグ行の直前に挿入
        if not inserted_flag and line.startswith("**#") or (not inserted_flag and i == len(lines) - 5):
            new_lines.extend(insert_section)
            inserted_flag = True
        new_lines.append(line)

    if not inserted_flag:
        new_lines.extend(insert_section)

    return "\n".join(new_lines), inserted


# ─── 処理対象ファイル検索 ─────────────────────────────────────

def load_log() -> dict:
    if AFFILIATE_LOG.exists():
        return json.loads(AFFILIATE_LOG.read_text())
    return {"processed": {}}


def save_log(log: dict):
    AFFILIATE_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def find_note_articles() -> list[Path]:
    """outputs配下のnote記事を全て返す"""
    articles = list(OUTPUTS_DIR.glob("*_note記事.md"))
    articles += list(OUTPUTS_DIR.glob("*_有料note記事.md"))
    return articles


# ─── メイン ──────────────────────────────────────────────────

def run():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  アフィリエイトリンク自動挿入")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    log = load_log()
    articles = find_note_articles()
    total_inserted = 0

    for art_path in articles:
        mtime = art_path.stat().st_mtime
        logged_mtime = log["processed"].get(str(art_path), 0)

        if mtime <= logged_mtime:
            continue  # 変更なし → スキップ

        print(f"\n  [{art_path.name}]")
        content = art_path.read_text(encoding="utf-8")
        new_content, count = insert_affiliate_links(content, art_path)

        if count > 0:
            art_path.write_text(new_content, encoding="utf-8")
            print(f"  ✅ {count}件のアフィリエイトリンクを挿入")
            total_inserted += count
        else:
            print("  — 挿入対象なし（キーワード不一致）")

        log["processed"][str(art_path)] = mtime

    save_log(log)

    print(f"\n  合計挿入: {total_inserted}件")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
