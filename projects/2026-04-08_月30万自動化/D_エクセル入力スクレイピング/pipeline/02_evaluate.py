"""
02_evaluate.py — 案件見極め（高精度版）
案件テキストをコピペするだけで GO / NO-GO を判定する。

使い方:
  python 02_evaluate.py                    # 対話モード（テキストを貼り付け）
  python 02_evaluate.py --file jobs.json   # 検索結果JSONから一括評価
  echo "案件テキスト" | python 02_evaluate.py  # パイプ入力
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────
# 評価プロンプト（4軸 × 詳細基準）
# ─────────────────────────────────────────────

EVAL_PROMPT = """
あなたはクラウドソーシングの案件を評価する専門家です。
以下の案件テキストを読み、4軸で採点して GO/NO-GO を判定してください。

━━━━━━━━━━━━━━━━━━━━━━━━
案件テキスト:
{job_text}
━━━━━━━━━━━━━━━━━━━━━━━━

## 評価軸と採点基準

### 軸1：技術実現性（0〜25点）
- 25点：標準的なHTML構造、静的サイト、openpyxlで処理できるExcel
- 15点：多少のJavaScriptあり、Playwrightで対応可能
- 5点：ログイン必須、CAPTCHA、Cloudflare等の強固な対策あり
- 0点：技術的に不可能（リアルタイムAPI専用、Flash等）

### 軸2：法的・規約リスク（0〜25点）
- 25点：明らかに公開情報、クライアントが対象サイトのオーナーまたは許可あり
- 15点：公開情報だが対象サイトの規約確認が必要
- 5点：個人情報・競合調査・著作物コピーの可能性あり
- 0点：明らかな違法行為（不正アクセス、個人情報の無断収集等）

### 軸3：採算性（0〜25点）
- 25点：¥10,000以上、または繰り返し受注が見込める
- 20点：¥5,000〜¥9,999
- 10点：¥2,000〜¥4,999
- 5点：¥1,000〜¥1,999
- 0点：¥1,000未満、または予算不明で低そう

### 軸4：要件明確性（0〜25点）
- 25点：入力元・出力形式・件数・納期がすべて明記されている
- 15点：主要項目は明確、細部は確認で解決できる
- 5点：要件が曖昧で大幅な追加確認が必要
- 0点：何をすべきか不明、または矛盾している

## 出力形式（JSONのみ、説明不要）

{{
  "category": "scraping" | "excel_input" | "data_processing" | "other",
  "scores": {{
    "technical": <0-25>,
    "legal": <0-25>,
    "profitability": <0-25>,
    "clarity": <0-25>
  }},
  "total": <0-100>,
  "verdict": "GO" | "CAUTION" | "NO-GO",
  "estimated_price_jpy": <数値>,
  "estimated_work_hours": <数値>,
  "hourly_rate_jpy": <時給換算>,
  "red_flags": ["懸念点1", "懸念点2"],
  "green_flags": ["優良点1", "優良点2"],
  "questions_to_ask": ["確認すべき質問1", "質問2"],
  "reason": "GO/NO-GO の主な理由（1〜2文）"
}}

## 判定基準
- GO     : total >= 70（積極的に応募）
- CAUTION: total 50〜69（質問して判断）
- NO-GO  : total < 50（見送り推奨）
"""

# ─────────────────────────────────────────────
# Claude API 呼び出し
# ─────────────────────────────────────────────

def call_claude(prompt: str, model: str = "claude-haiku-4-5-20251001") -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY が設定されていません\n"
            "export ANTHROPIC_API_KEY=sk-ant-... を実行してください"
        )
    payload = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
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
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body["content"][0]["text"]


# ─────────────────────────────────────────────
# ルールベース評価（APIキー不要のフォールバック）
# ─────────────────────────────────────────────

def _rule_based_evaluate(job_text: str, meta: dict | None = None) -> dict:
    """APIキーなしで動くルールベース評価"""
    import re
    text = job_text.lower()
    title = (meta or {}).get("title", "").lower()
    budget_text = (meta or {}).get("budget_text", "")

    # --- 軸1: 技術実現性 ---
    tech = 10  # デフォルト
    if any(k in text + title for k in ["エクセル", "excel", "csv", "スプレッドシート", "データ入力"]):
        tech = 25
    elif any(k in text + title for k in ["スクレイピング", "scraping", "データ収集", "web取得"]):
        tech = 20
    if any(k in text for k in ["captcha", "キャプチャ", "ログイン必須", "会員限定"]):
        tech = max(tech - 10, 5)

    # --- 軸2: 法的リスク ---
    legal = 15  # デフォルト
    if any(k in text for k in ["公開情報", "自社サイト", "許可", "オーナー", "委託"]):
        legal = 25
    if any(k in text for k in ["個人情報", "プライバシー", "住所", "電話番号", "メールアドレス収集"]):
        legal = 5
    if any(k in text + title for k in ["詐欺", "副業", "不正", "違法"]):
        legal = 0

    # --- 軸3: 採算性 ---
    profitability = 10
    # 金額を抽出
    amounts = re.findall(r'[¥￥]?\s*(\d[\d,]+)\s*円?', budget_text + " " + text)
    max_amount = 0
    for a in amounts:
        try:
            val = int(a.replace(",", ""))
            if val > max_amount:
                max_amount = val
        except Exception:
            pass
    if max_amount >= 10000:
        profitability = 25
    elif max_amount >= 5000:
        profitability = 20
    elif max_amount >= 2000:
        profitability = 10
    elif max_amount >= 1000:
        profitability = 5
    estimated_price = max_amount or 5000

    # --- 軸4: 要件明確性 ---
    clarity = 10
    has_count = bool(re.search(r'\d+\s*(件|行|ページ|sheet)', text))
    has_deadline = any(k in text for k in ["納期", "期限", "までに", "日以内", "締め切り"])
    has_format = any(k in text for k in ["excel", "エクセル", "csv", "json", "形式", "フォーマット"])
    clarity += (15 if has_count else 0) + (5 if has_deadline else 0) + (5 if has_format else 0)
    clarity = min(clarity, 25)

    total = tech + legal + profitability + clarity

    # 詐欺フラグ
    red_flags = []
    if any(k in text + title for k in ["海外在住", "受け取り", "転送", "送金", "LINE登録"]):
        red_flags.append("詐欺の疑い（受け取り・転送系）")
        total = 0
    if any(k in text + title for k in ["副業", "初心者歓迎", "誰でも", "簡単に稼"]):
        red_flags.append("怪しい副業案件の可能性")
        total = max(total - 20, 0)
    if (meta or {}).get("platform") == "crowdworks" and "0" == str((meta or {}).get("client_reviews", "")):
        red_flags.append("クライアントのレビュー0件")

    if total >= 70:
        verdict = "GO"
    elif total >= 50:
        verdict = "CAUTION"
    else:
        verdict = "NO-GO"

    result = {
        "category": "excel_input" if "excel" in text + title or "エクセル" in text + title else "scraping",
        "scores": {"technical": tech, "legal": legal, "profitability": profitability, "clarity": clarity},
        "total": total,
        "verdict": verdict,
        "estimated_price_jpy": estimated_price,
        "estimated_work_hours": max(1, estimated_price // 2000),
        "hourly_rate_jpy": estimated_price // max(1, estimated_price // 2000),
        "red_flags": red_flags,
        "green_flags": [k for k in ["データ入力", "エクセル", "スクレイピング", "CSV"] if k in text + title],
        "questions_to_ask": ["データの件数と納期を教えてください", "出力形式（Excel/CSV等）はありますか？"],
        "reason": f"ルールベース評価: 技術{tech}+法的{legal}+採算{profitability}+明確{clarity}={total}点",
        "evaluated_by": "rule_based",
    }
    if meta:
        result = {**meta, **result}
    result["evaluated_at"] = datetime.now().isoformat()
    result["job_text_preview"] = job_text[:100] + ("..." if len(job_text) > 100 else "")
    return result


# ─────────────────────────────────────────────
# 評価ロジック
# ─────────────────────────────────────────────

def evaluate(job_text: str, meta: dict | None = None) -> dict:
    """案件テキストを評価して結果dictを返す（API→ルールベース フォールバック）"""
    if ANTHROPIC_API_KEY:
        prompt = EVAL_PROMPT.format(job_text=job_text.strip())
        try:
            raw = call_claude(prompt)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            result = json.loads(raw[start:end])
            if meta:
                result = {**meta, **result}
            result["evaluated_at"] = datetime.now().isoformat()
            result["job_text_preview"] = job_text[:100] + ("..." if len(job_text) > 100 else "")
            return result
        except Exception:
            pass  # API失敗時はルールベースにフォールバック

    # APIキー未設定またはAPI失敗 → ルールベース評価
    return _rule_based_evaluate(job_text, meta)


def print_result(result: dict) -> None:
    """評価結果を見やすく表示する"""
    verdict = result.get("verdict", "?")
    total = result.get("total", 0)
    colors = {"GO": "✅", "CAUTION": "⚠️ ", "NO-GO": "❌"}
    icon = colors.get(verdict, "❓")

    print("\n" + "═" * 60)
    print(f"  {icon} {verdict}   スコア: {total}/100")
    print("═" * 60)

    # スコア内訳
    scores = result.get("scores", {})
    if scores:
        print(f"  技術実現性  : {'█' * (scores.get('technical', 0) // 5):<5} {scores.get('technical', 0)}/25")
        print(f"  法的リスク  : {'█' * (scores.get('legal', 0) // 5):<5} {scores.get('legal', 0)}/25")
        print(f"  採算性      : {'█' * (scores.get('profitability', 0) // 5):<5} {scores.get('profitability', 0)}/25")
        print(f"  要件明確性  : {'█' * (scores.get('clarity', 0) // 5):<5} {scores.get('clarity', 0)}/25")

    # 採算
    price = result.get("estimated_price_jpy", 0)
    hours = result.get("estimated_work_hours", 0)
    rate = result.get("hourly_rate_jpy", 0)
    if price:
        print(f"\n  想定単価: ¥{price:,}  /  工数: {hours}h  /  時給換算: ¥{rate:,}")

    # 判定理由
    print(f"\n  【判定理由】{result.get('reason', '')}")

    # 優良点
    greens = result.get("green_flags", [])
    if greens:
        print("\n  【優良点】")
        for g in greens:
            print(f"    ✓ {g}")

    # 懸念点
    reds = result.get("red_flags", [])
    if reds:
        print("\n  【懸念点】")
        for r in reds:
            print(f"    ✗ {r}")

    # 確認質問
    questions = result.get("questions_to_ask", [])
    if questions and verdict == "CAUTION":
        print("\n  【応募前に確認すべき質問】")
        for i, q in enumerate(questions, 1):
            print(f"    {i}. {q}")

    print("═" * 60)


# ─────────────────────────────────────────────
# 実行モード
# ─────────────────────────────────────────────

def interactive_mode() -> dict:
    """対話モード：案件テキストをターミナルに貼り付けて評価"""
    print("\n" + "─" * 60)
    print("  案件見極めツール（Enter×2 で評価開始）")
    print("─" * 60)
    print("案件テキストを貼り付けてください（タイトル・説明・予算・納期を含める）:")
    print()

    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break

    job_text = "\n".join(lines)
    if not job_text.strip():
        print("[エラー] テキストが空です")
        sys.exit(1)

    print("\n評価中...")
    result = evaluate(job_text)
    print_result(result)

    # 結果を保存
    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_eval.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  結果保存: {out}")
    return result


def batch_mode(file_path: str) -> list[dict]:
    """バッチモード：検索結果JSONを一括評価"""
    jobs = json.loads(Path(file_path).read_text(encoding="utf-8"))
    results = []
    go_count = caution_count = nogo_count = 0

    print(f"\n[一括評価] {len(jobs)}件")
    for i, job in enumerate(jobs, 1):
        text = job.get("description") or job.get("title") or str(job)
        print(f"  [{i}/{len(jobs)}] {job.get('title', '')[:40]}...", end=" ", flush=True)
        result = evaluate(text, meta=job)
        v = result.get("verdict", "NO-GO")
        if v == "GO": go_count += 1
        elif v == "CAUTION": caution_count += 1
        else: nogo_count += 1
        print(f"→ {v} ({result.get('total', 0)}点)")
        results.append(result)

    # サマリ
    print(f"\n結果: GO={go_count} / CAUTION={caution_count} / NO-GO={nogo_count}")

    # GO案件のみ表示
    go_jobs = [r for r in results if r.get("verdict") == "GO"]
    if go_jobs:
        print("\n▼ GO案件（応募推奨）")
        for r in sorted(go_jobs, key=lambda x: x.get("total", 0), reverse=True):
            print_result(r)

    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_evaluated.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[保存] {out}")
    return [r for r in results if r.get("verdict") in ("GO", "CAUTION")]


def run(jobs: list[dict] | None = None):
    """パイプラインから呼び出す場合"""
    if jobs is None:
        files = sorted(OUTPUT_DIR.glob("*_jobs.json"))
        if not files:
            print("[ERROR] 01_search.py を先に実行してください")
            return []
        jobs = json.loads(files[-1].read_text(encoding="utf-8"))

    results = []
    for j in jobs:
        text = j.get("description") or j.get("title", "")
        result = evaluate(text, meta=j)
        results.append(result)

    # GO/CAUTION のみ保存
    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_evaluated.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[評価完了] {len(results)}件 → {out}")

    recommended = [r for r in results if r.get("verdict") in ("GO", "CAUTION")]
    print(f"  GO: {sum(1 for r in results if r.get('verdict')=='GO')}件 / "
          f"CAUTION: {sum(1 for r in results if r.get('verdict')=='CAUTION')}件 / "
          f"NO-GO: {sum(1 for r in results if r.get('verdict')=='NO-GO')}件")
    return recommended


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        batch_mode(sys.argv[2])
    elif not sys.stdin.isatty():
        # パイプ入力
        text = sys.stdin.read()
        result = evaluate(text)
        print_result(result)
    else:
        interactive_mode()
