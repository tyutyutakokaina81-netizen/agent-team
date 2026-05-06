#!/usr/bin/env python3
"""
list_publish_targets.py — note 投稿準備の一覧表示

dist/ にある全 Vol の添付ファイル・価格・アイキャッチを1画面で確認できる。
オーナーが note 投稿作業時に「次は何を upload するか」を即把握するための一覧。

【使い方】
  python3 projects/2026-04-08_月30万自動化/今すぐ収益化/list_publish_targets.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / "C_テンプレ販売" / "dist"
EYECATCH = DIST / "eyecatch"
NOTE_PASTE = Path(__file__).parent / "note_paste.md"


def parse_paste_md() -> dict:
    """note_paste.md からタイトル・価格を抽出"""
    if not NOTE_PASTE.exists():
        return {}
    text = NOTE_PASTE.read_text(encoding="utf-8")
    blocks = re.split(r"^## (Vol\.\d+)", text, flags=re.M)[1:]
    info = {}
    for i in range(0, len(blocks), 2):
        vol = blocks[i].replace(".", "").strip()
        body = blocks[i+1] if i+1 < len(blocks) else ""
        price_m = re.search(r"\*\*💰 価格\*\*：(¥[\d,]+)", body)
        title_m = re.search(r"### タイトル.*?\n```\n(.+?)\n```", body, re.S)
        info[vol] = {
            "price": price_m.group(1) if price_m else "?",
            "title": title_m.group(1).strip() if title_m else "?",
        }
    return info


def vol_files() -> dict:
    """各 Vol の添付ファイル候補を集める"""
    result = {}
    for f in DIST.iterdir():
        if not f.name.startswith("Vol"):
            continue
        m = re.match(r"(Vol\d+)", f.name)
        if not m:
            continue
        vol = m.group(1)
        if f.is_file():
            result.setdefault(vol, []).append(f)
        elif f.is_dir():
            # Vol11 のディレクトリ：中の docx 群
            for sub in f.iterdir():
                if sub.is_file():
                    result.setdefault(vol, []).append(sub)
    return result


def main():
    info = parse_paste_md()
    files = vol_files()
    eyecatches = {p.stem: p for p in EYECATCH.glob("*.png")} if EYECATCH.exists() else {}

    vols = sorted(set(list(info.keys()) + list(files.keys())),
                  key=lambda v: int(v.replace("Vol", "")))

    print()
    print("━" * 80)
    print(f"  note 投稿準備一覧（dist/ 全 {len(vols)} Vol）")
    print("━" * 80)
    print()

    for vol in vols:
        meta = info.get(vol, {})
        print(f"┌─ {vol} {meta.get('price', '')} {'─' * (70 - len(vol) - len(meta.get('price','')))}")
        title = meta.get("title", "(タイトル未設定)")
        print(f"│ タイトル：{title}")
        eye = eyecatches.get(vol)
        print(f"│ アイキャッチ：{eye.relative_to(ROOT.parent.parent) if eye else '（なし）'}")
        attachments = files.get(vol, [])
        if attachments:
            print(f"│ 添付ファイル（{len(attachments)} 個）：")
            for f in sorted(attachments):
                rel = f.relative_to(ROOT.parent.parent)
                size_kb = f.stat().st_size // 1024
                print(f"│   - {rel} ({size_kb} KB)")
        else:
            print(f"│ 添付ファイル：（なし）")
        print(f"└{'─' * 79}")
        print()

    # サマリ
    total_files = sum(len(v) for v in files.values())
    total_eye = len(eyecatches)
    expected_revenue = sum(
        int(re.sub(r"[¥,]", "", info[v]["price"]))
        for v in vols if info.get(v, {}).get("price", "?") != "?"
    )
    print(f"添付ファイル総数：{total_files}")
    print(f"アイキャッチ画像：{total_eye}")
    print(f"全 Vol 単品合計（1本ずつ販売した場合）：¥{expected_revenue:,}")
    print()
    print("【次のオーナー作業】")
    print("  1. note にログイン")
    print("  2. note_paste.md を別タブで開く")
    print("  3. 上記の各 Vol を順番に新規記事として作成")
    print("     - タイトル / 本文 / 価格 / タグ をペースト")
    print("     - 添付ファイル・アイキャッチをアップロード")
    print("  4. 公開後、URL を brief.md の DoD 表に記録")
    print()


if __name__ == "__main__":
    main()
