#!/usr/bin/env python3
"""見出し画像のクレジット行を、_provenance.json から**機械的に**生成・検証する。

なぜ必要か（2026-09-11）:
Wikimedia Commons の写真には CC BY / CC BY-SA のものがあり、**表示（attribution）が義務**になる。
これまで `_provenance.json` に backend しか残していなかったため可否を判断できず、
出典を記録するようにした直後に **CC BY-SA 3.0 / 4.0 の写真を2枚**採用していたことが判明した。
「あとで気づいて書く」ではなく、記事本文に入っているかを毎回機械で確かめる。

- CC0 / Public domain … クレジット不要（書いても害はない）
- CC BY / CC BY-SA / CC BY-ND 等 … **クレジット必須**

使い方:
  python3 CDO/outputs/note_publisher/thumb_credit.py --line <記事.md>    # 必要なクレジット行を表示
  python3 CDO/outputs/note_publisher/thumb_credit.py --apply <記事.md>   # 本文末尾に無ければ挿入
  python3 CDO/outputs/note_publisher/thumb_credit.py --check <記事.md...># 不足を一覧（0件なら終了0）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROV = ROOT / "CDO/outputs/note_publisher/thumbnails/_provenance.json"
CREDIT_MARK = "（見出し画像："
# 表示義務のないライセンス（これ以外はクレジットを要求する）
NO_ATTRIB = ("cc0", "public domain", "pd-", "no restrictions")
# CC BY 系はライセンス本文へのリンクが要求される。よく出るものだけ持つ（未知なら名前のみ表示）。
LICENSE_URLS = {
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
    "CC BY-SA 2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
}


def load_prov() -> dict:
    try:
        return json.loads(PROV.read_text(encoding="utf-8"))
    except Exception:
        return {}


def needs_credit(license_name: str | None) -> bool:
    if not license_name:
        return False          # 素性不明は判定しない（誤ったクレジットを書かない）
    low = license_name.lower()
    return not any(k in low for k in NO_ATTRIB)


def credit_line(stem: str, prov: dict) -> str | None:
    """クレジットが要るなら1行を返す。要らない／情報が無いなら None。"""
    v = prov.get(stem)
    if not isinstance(v, dict) or not needs_credit(v.get("license")):
        return None
    fname = re.sub(r"^File:", "", v.get("file", "")).replace("_", " ")
    author = v.get("author") or "不明"
    page = v.get("descpage") or "https://commons.wikimedia.org/"
    lic = v["license"]
    # CC BY / CC BY-SA は「ライセンスへのリンク」を求めるので URL を添える（CQO指摘・提案10）。
    url = LICENSE_URLS.get(lic.strip())
    lic_txt = f"{lic}（{url}）" if url else lic
    return f"（見出し画像：{fname} ／ 撮影 {author} ／ {lic_txt} ／ 出典 {page}）"


def has_credit(text: str) -> bool:
    return CREDIT_MARK in text


def body_block(text: str):
    """`## 本文` 直下のコードブロックの (開始, 終了) 位置を返す。"""
    m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    return (m.start(1), m.end(1)) if m else None


def apply_credit(path: Path) -> str:
    prov = load_prov()
    text = path.read_text(encoding="utf-8")
    line = credit_line(path.stem, prov)
    if line is None:
        return "クレジット不要（CC0/PD、または素性の記録なし）"
    if has_credit(text):
        return "既にクレジット行あり"
    span = body_block(text)
    if not span:
        return "本文ブロックが見つからない"
    s, e = span
    new = text[:e] + "\n\n" + line + text[e:]
    path.write_text(new, encoding="utf-8")
    return f"挿入: {line}"


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    mode, files = args[0], args[1:]
    prov = load_prov()
    missing = 0
    for f in files:
        p = Path(f)
        if mode == "--apply":
            print(f"  {p.name}: {apply_credit(p)}")
        else:
            line = credit_line(p.stem, prov)
            text = p.read_text(encoding="utf-8")
            if line is None:
                print(f"  -   {p.name}: クレジット不要")
            elif has_credit(text):
                print(f"  OK  {p.name}: クレジットあり")
            else:
                missing += 1
                print(f"  NG  {p.name}: **クレジットが必要なのに無い** → {line}")
    if mode == "--check":
        print(f"=== 結果: クレジット不足 {missing} 件 ===")
        return 1 if missing else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
