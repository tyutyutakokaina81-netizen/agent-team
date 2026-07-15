#!/usr/bin/env python3
"""依存ゼロ(標準ライブラリのみ)で「議事録＋要件メモ → 提案書draft(md)」を生成する。

B2B受託の中核フック「商談30分後に提案書が届くと顧客が驚く」(かいち動画5)を worker が回すための穴埋めスクリプト。
テンプレ(template_proposal.md)の {{key}} を req.txt の値で差し替え、下書きmdを出力する。
外部依存なし(pandoc/APIを使わない=¥0)。EN/build_epub.py と同じ「自作・標準ライブラリのみ」方針。

使い方:
  python3 gen_proposal.py --minutes minutes.txt --req req.txt --out proposal_draft.md
  # --template を省略すると同ディレクトリの template_proposal.md を使う

req.txt の書式:
  key: value            # 1行1項目。'#' 以降はコメント。値内の \\n は改行に展開。
  # 空行・コメント行は無視。同じ key が複数回あれば後勝ち。

安全設計:
  - 埋まらなかった {{key}} は 【未入力: key】 として残す(=壊さず抜けを可視化)。
  - 末尾に「未入力一覧」と「⚑要ファクトチェック件数」を自動追記(人間チェックを促す)。
  - 議事録は原本を触らず、pain_points が未指定なら議事録の箇条書き行から素案を補う。
"""
import argparse
import re
from pathlib import Path


def parse_req(text: str) -> dict:
    """req.txt(key: value) を dict に。'#'コメント除去、値内 \\n を改行へ。"""
    data = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        # 行頭がコメント/空行はスキップ
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        # 値末尾のインラインコメントを除去(値に # を含めたい場合は非対応=シンプル優先)
        val = val.split("#", 1)[0].strip()
        val = val.replace("\\n", "\n")
        if key:
            data[key] = val
    return data


def extract_bullets(minutes: str, limit: int = 6) -> str:
    """議事録テキストから箇条書き/短文の一次情報を素案として抽出(pain_points 補完用)。"""
    bullets = []
    for raw in minutes.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^[-*・]\s*(.+)$", line)
        if m:
            bullets.append(m.group(1).strip())
        elif len(line) <= 60 and ("課題" in line or "困" in line or "問題" in line):
            bullets.append(line)
        if len(bullets) >= limit:
            break
    if not bullets:
        return "  - （議事録から自動抽出できず。人間が現状整理を記入してください）"
    return "\n".join(f"  - {b}" for b in bullets)


def fill(template: str, data: dict):
    """テンプレの {{key}} を data で差し替え。未入力keyの一覧も返す。"""
    missing = []

    def repl(m):
        key = m.group(1).strip()
        if key in data and data[key] != "":
            return data[key]
        missing.append(key)
        return f"【未入力: {key}】"

    filled = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", repl, template)
    return filled, missing


def main():
    ap = argparse.ArgumentParser(description="議事録＋要件 → 提案書draft(md)")
    here = Path(__file__).resolve().parent
    ap.add_argument("--template", default=str(here / "template_proposal.md"))
    ap.add_argument("--minutes", required=True, help="商談議事録テキスト")
    ap.add_argument("--req", required=True, help="要件メモ(key: value)")
    ap.add_argument("--out", required=True, help="出力先md")
    args = ap.parse_args()

    template = Path(args.template).read_text(encoding="utf-8")
    minutes = Path(args.minutes).read_text(encoding="utf-8")
    data = parse_req(Path(args.req).read_text(encoding="utf-8"))

    # 必須5要素の確認(曖昧input禁止)
    required5 = ["industry", "scale", "issue", "goal", "budget"]
    lacking5 = [k for k in required5 if not data.get(k)]

    # pain_points 未指定なら議事録から素案を補完
    if not data.get("pain_points"):
        data["pain_points"] = extract_bullets(minutes)

    filled, missing = fill(template, data)

    fc_count = filled.count("⚑要ファクトチェック")
    footer = ["\n\n---\n\n## 生成メモ（納品前に削除）\n"]
    if lacking5:
        footer.append(
            "> ⚠️ 必須5要素の未入力: "
            + ", ".join(lacking5)
            + " ← 埋めてから生成し直すこと（曖昧inputは刺さらない）。\n"
        )
    else:
        footer.append("> 必須5要素（業種/規模/課題/ゴール数字/予算感）: すべて入力済み。\n")
    uniq_missing = sorted(set(missing))
    footer.append(f"> 未入力プレースホルダ {len(uniq_missing)}件: "
                  + (", ".join(uniq_missing) if uniq_missing else "なし") + "\n")
    footer.append(f"> ⚑要ファクトチェック {fc_count}件: 人間が一次情報で裏取りしてから納品する（A5／落とし穴①）。\n")
    footer.append("> A評価でも即納品しない。実行体力・資金・PII(A4)を一度重ねる（落とし穴②）。\n")

    out = Path(args.out)
    out.write_text(filled + "".join(footer), encoding="utf-8")

    print(f"[gen_proposal] wrote {out}")
    print(f"  必須5要素の未入力: {lacking5 if lacking5 else 'なし'}")
    print(f"  未入力プレースホルダ: {len(uniq_missing)}件")
    print(f"  ⚑要ファクトチェック: {fc_count}件")


if __name__ == "__main__":
    main()
