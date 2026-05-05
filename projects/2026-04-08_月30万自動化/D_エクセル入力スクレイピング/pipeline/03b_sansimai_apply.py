"""
03b_sansimai_apply.py — 三姉妹AI統合エージェント方式の応募文ジェネレータ

【概要】
案件情報（手動コピペ）を入力すると、三姉妹AI（りん=技術 / しおり=リスク /
あかね=価値）の3視点で評価し、最良案件を1つ選んで応募文を生成する。

【規約準拠の設計】
- 案件取得は手動コピペ（CrowdWorks / Lancers のスクレイピングは規約NG）
- 応募送信も手動（自動応募は両プラットフォームで明示禁止）
- ANTHROPIC_API_KEY 未設定時はプロンプトを出力するのみ
  （ユーザーが Claude にコピペして使う運用に切り替わる）

【使い方】
  # 1. 案件情報を pipeline/inputs/jobs.md に貼り付ける（複数案件OK）
  #    フォーマットは pipeline/inputs/jobs.md.sample を参照
  # 2. 実行
  python3 pipeline/03b_sansimai_apply.py

  # ANTHROPIC_API_KEY を環境変数で渡せばAPIで自動生成
  # 未設定なら整形済プロンプトをstdoutと outputs/ に保存するのみ
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
PIPELINE_DIR = Path(__file__).parent
INPUT_FILE = PIPELINE_DIR / "inputs" / "jobs.md"
OUTPUT_DIR = PROJECT_DIR / "outputs"
TEMPLATE_FILE = PROJECT_DIR / "templates" / "sansimai_prompt.txt"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 2000
API_TIMEOUT_SEC = 60


def build_prompt(jobs_text: str) -> str:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    return template.replace("{{JOBS}}", jobs_text)


def call_claude(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=API_TIMEOUT_SEC) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body["content"][0]["text"]


def extract_block(text: str, begin: str, end: str) -> str:
    if begin in text and end in text:
        s = text.index(begin) + len(begin)
        e = text.index(end)
        return text[s:e].strip()
    return ""


def try_clipboard(text: str) -> str:
    candidates = [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
        ["clip.exe"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                return cmd[0]
            except subprocess.CalledProcessError:
                continue
    return ""


def main() -> int:
    if not TEMPLATE_FILE.exists():
        print(f"[ERROR] テンプレートが見つかりません: {TEMPLATE_FILE}", file=sys.stderr)
        return 1

    if not INPUT_FILE.exists():
        print(f"[ERROR] {INPUT_FILE} が存在しません。", file=sys.stderr)
        print(
            "        案件情報を貼り付けたmarkdownを置いてから再実行してください。",
            file=sys.stderr,
        )
        print(
            f"        フォーマット見本: {INPUT_FILE.with_suffix('.md.sample')}",
            file=sys.stderr,
        )
        return 1

    jobs_text = INPUT_FILE.read_text(encoding="utf-8").strip()
    if not jobs_text:
        print("[ERROR] inputs/jobs.md が空です。", file=sys.stderr)
        return 1

    prompt = build_prompt(jobs_text)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not ANTHROPIC_API_KEY:
        out_prompt = OUTPUT_DIR / f"{ts}_sansimai_prompt.md"
        out_prompt.write_text(prompt, encoding="utf-8")
        print(
            "[INFO] ANTHROPIC_API_KEY 未設定。下記プロンプトを Claude に貼り付けて使ってください。"
        )
        print(f"[保存] {out_prompt}")
        print("=" * 60)
        print(prompt)
        print("=" * 60)
        return 0

    print("[三姉妹AI] APIで応募文を生成中…")
    try:
        response = call_claude(prompt)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] HTTP {e.code}: {body}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[ERROR] API呼び出し失敗: {e}", file=sys.stderr)
        return 2

    apply_text = extract_block(response, "BEGIN_APPLY", "END_APPLY")
    meta_text = extract_block(response, "BEGIN_META", "END_META")

    if not apply_text:
        print("[WARN] BEGIN_APPLY / END_APPLY が見つかりません。応答全文を保存します。")
        apply_text = response.strip()

    out_full = OUTPUT_DIR / f"{ts}_sansimai_full.md"
    out_full.write_text(response, encoding="utf-8")

    out_apply = OUTPUT_DIR / f"{ts}_sansimai_apply.txt"
    out_apply.write_text(apply_text, encoding="utf-8")

    latest = OUTPUT_DIR / "latest_apply.txt"
    latest.write_text(apply_text, encoding="utf-8")

    clip = try_clipboard(apply_text)

    print("=" * 60)
    if meta_text:
        print("【選定情報】")
        print(meta_text)
        print("-" * 60)
    print("【応募文】")
    print(apply_text)
    print("=" * 60)
    print(f"[保存] {out_apply}")
    print(f"[全文] {out_full}")
    if clip:
        print(f"[クリップボード] {clip} でコピー完了")
    else:
        print("[クリップボード] 利用可能なツールなし（xclip/xsel/pbcopy/clip.exe）")
    print(
        "[次の手順] 案件ページで内容を確認し、人間が手動で送信してください（自動応募は規約NG）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
