#!/usr/bin/env python3
"""docs/unpublished_candidates.md を再生成する（公開してよい候補だけに厳選）。

除外するもの:
  1. タイトル重複（registry_check）— 既公開と同名
  2. 題材重複（topic_conflict）— 既公開と同じ題材（タイトル違いでも）
  3. 非記事ファイル — 本文ブロックが無い / ファイル名が サムネ・プロンプト・テンプレ 等
  4. 候補どうしの題材重複 — 先に採った候補と同題材の後続は落とす（同一題材の複数公開を防ぐ）

publish_to_note.py のゲート関数を流用するので、判定基準は公開時ゲートと完全一致。
"""
import re
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

# playwright 不要（ゲート関数のみ使う）
_fake = types.ModuleType("playwright.sync_api"); _fake.sync_playwright = None
sys.modules.setdefault("playwright", types.ModuleType("playwright"))
sys.modules.setdefault("playwright.sync_api", _fake)
import importlib.util
spec = importlib.util.spec_from_file_location("pub", HERE / "publish_to_note.py")
pub = importlib.util.module_from_spec(spec); spec.loader.exec_module(pub)

THUMBS = HERE / "thumbnails"
JUNK_NAME = re.compile(r"(サムネ|プロンプト|テンプレ|下書き|メモ|_ボツ|_没|README)")


def title_and_has_body(md: Path):
    """(title, has_body) を返す。抽出不能や本文なしは (None, False)。"""
    text = md.read_text(encoding="utf-8")
    tm = re.search(r"メイン.*?\n```\n(.+?)\n```", text, re.S) or \
        re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    bm = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    if not tm or not bm:
        return None, False
    title = tm.group(1).strip().splitlines()[0].strip()
    body = bm.group(1).strip()
    return title, (len(body) >= 200)  # 200字未満は記事とみなさない


def main():
    rows, skipped = [], {"title": 0, "topic": 0, "nonarticle": 0, "self": 0}
    picked_titles = []  # 既に候補採用したタイトル（候補どうしの題材重複判定用）

    for md in sorted((REPO / "CMO" / "outputs").glob("*_note記事_*.md")):
        if JUNK_NAME.search(md.name):
            skipped["nonarticle"] += 1; continue
        title, has_body = title_and_has_body(md)
        if not title or not has_body:
            skipped["nonarticle"] += 1; continue
        if pub.registry_check(title):
            skipped["title"] += 1; continue
        if pub.topic_conflict(title):
            skipped["topic"] += 1; continue
        # 候補どうしの題材重複（先勝ち）
        new_tok = pub._topic_tokens(title)
        if any(new_tok & pub._topic_tokens(pt) for pt in picked_titles):
            skipped["self"] += 1; continue
        picked_titles.append(title)
        thumb = any((THUMBS / f"{md.stem}.{e}").exists() for e in ("jpg", "jpeg", "png", "webp", "JPG", "PNG"))
        rows.append((md.name, title, thumb))

    out = [
        "# 未公開バックログ候補（厳選・自動生成）",
        "",
        "> 生成: `python3 CDO/outputs/note_publisher/build_unpublished_candidates.py`",
        "> 除外済み: タイトル重複 / 題材重複(既公開・候補間) / 非記事(本文なし/サムネ/プロンプト等)。",
        "> 公開時は publish_to_note.py の題材ゲートが最終確認する（二重の安全）。",
        f"> 除外内訳: タイトル重複{skipped['title']} / 題材重複{skipped['topic']} / "
        f"候補間題材重複{skipped['self']} / 非記事{skipped['nonarticle']}",
        "",
        "| ファイル | タイトル | サムネ |",
        "|---|---|---|",
    ]
    for name, title, thumb in rows:
        out.append(f"| {name} | {title} | {'✅' if thumb else '—'} |")
    (REPO / "docs" / "unpublished_candidates.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"候補 {len(rows)}本を書き出し（サムネ済 {sum(1 for r in rows if r[2])}本）")
    print(f"除外: {skipped}")


if __name__ == "__main__":
    main()
