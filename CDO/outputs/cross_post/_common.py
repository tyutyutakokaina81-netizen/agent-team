"""共通ユーティリティ：記事mdからメタ情報を取り出す。"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTICLES_DIR = REPO_ROOT / "CMO" / "outputs"


def parse_article(md_path: Path) -> dict:
    """note記事mdから主要要素を抽出する。"""
    text = md_path.read_text(encoding="utf-8")
    out = {"path": md_path, "raw": text}

    # 日本語タイトル
    m = re.search(r"メイン.*?\n```\n(.+?)\n```", text, re.S) or \
        re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    out["title_ja"] = m.group(1).strip().splitlines()[0].strip() if m else ""

    # 本文（## 本文 直下の```ブロック）
    m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    out["body_ja"] = m.group(1).strip() if m else ""

    # 英語要約（本文内の 🌏 For English readers セクション）
    m = re.search(r"🌏 For English readers.*?\n(.+?)(?=\n```|\n---|\Z)", out["body_ja"], re.S)
    out["en_summary"] = m.group(1).strip() if m else ""
    # フォールバック: 末尾の「## English …」節（```ブロック内）を英語要約として使う
    if not out["en_summary"]:
        m = re.search(r"##\s*English.*?\n+```\s*\n(.+?)\n```", text, re.S)
        out["en_summary"] = m.group(1).strip() if m else ""

    # ハッシュタグ
    m = re.search(r"##\s*ハッシュタグ.*?\n```\n(.+?)\n```", text, re.S)
    tags_line = m.group(1).strip() if m else ""
    out["tags_all"] = [t.strip() for t in re.findall(r"#\S+", tags_line)]
    out["tags_ja"] = [t for t in out["tags_all"] if re.match(r"#[　-鿿]", t)]
    out["tags_en"] = [t for t in out["tags_all"] if re.match(r"#[A-Za-z]", t)]

    # 日付（ファイル名から）
    fnm = re.match(r"(\d{4}-\d{2}-\d{2})_", md_path.name)
    out["date"] = fnm.group(1) if fnm else ""

    return out


def find_article(arg: str | None) -> Path:
    """--article 指定 or 最新を返す。"""
    if arg:
        p = Path(arg).expanduser()
        if p.is_absolute() or p.exists():
            return p
        return ARTICLES_DIR / arg
    candidates = sorted(ARTICLES_DIR.glob("*_note記事_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("記事が見つかりません")
    return candidates[0]
