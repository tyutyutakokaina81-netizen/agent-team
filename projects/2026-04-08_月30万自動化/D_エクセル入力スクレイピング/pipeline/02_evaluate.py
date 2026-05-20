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

# 応募禁止ルール（/応募禁止ルール.md ⑥ より抜粋）
PROHIBITION_KEYWORDS = {
    "ymyl": ["医療", "薬機", "投資勧誘", "病気", "症状", "金融商品", "クレジットカード審査"],
    "adult": ["アダルト", "成人向け", "風俗", "出会い系"],
    "scam": ["着手金", "先払い", "暗号資産", "ビットコイン", "海外在住", "受け取り代行", "LINE登録"],
    "personal_info": ["個人情報リスト", "顧客名簿", "電話番号リスト", "住所リスト"],
    "rights_transfer": ["著作権譲渡＋身分証", "著作権完全譲渡", "全権譲渡"],
    "physical": ["対面必須", "出張あり", "現地", "通勤"],
    "plagiarism": ["既存記事リライト", "コピー記事", "他サイト記事を書き換え"],
    "overseas": ["海外発注", "海外クライアント", "english only"],
}


def _check_prohibition(text: str, title: str) -> list[str]:
    """応募禁止ルールに該当するかチェック"""
    combined = (text + " " + title).lower()
    violations = []
    for category, kws in PROHIBITION_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in combined:
                violations.append(f"{category}: 「{kw}」検出")
                break
    return violations


def _rule_based_evaluate_writing(job_text: str, meta: dict | None = None) -> dict:
    """ライティング案件向けのルールベース評価"""
    import re
    text = job_text.lower()
    title = (meta or {}).get("title", "").lower()
    budget_text = (meta or {}).get("budget_text", "")
    combined = text + " " + title

    # 応募禁止ルール該当チェック（即 NO-GO）
    violations = _check_prohibition(job_text, (meta or {}).get("title", ""))
    if violations:
        result = {
            "category": "writing",
            "scores": {"theme": 0, "trust": 0, "profitability": 0, "clarity": 0},
            "total": 0,
            "verdict": "NO-GO",
            "estimated_price_jpy": 0,
            "estimated_work_hours": 0,
            "hourly_rate_jpy": 0,
            "red_flags": violations,
            "green_flags": [],
            "questions_to_ask": [],
            "reason": "応募禁止ルール該当: " + "; ".join(violations),
            "evaluated_by": "rule_based_writing",
        }
        if meta:
            result = {**meta, **result}
        result["evaluated_at"] = datetime.now().isoformat()
        return result

    # --- 軸1: テーマ適合性（0-25） ---
    theme = 15
    if any(k in combined for k in ["seo", "オウンドメディア", "ブログ記事", "コラム", "解説記事"]):
        theme = 25
    if any(k in combined for k in ["初心者歓迎", "未経験ok", "未経験可"]):
        theme = max(theme, 20)
    if any(k in combined for k in ["専門", "高度", "経験者のみ"]):
        theme = max(theme - 5, 5)

    # --- 軸2: 発注者信用性（0-25） ---
    trust = 10  # 不明時のデフォルト
    if any(k in combined for k in ["継続発注", "長期", "定期発注", "リピート"]):
        trust = 25
    elif "本人確認済" in combined or "本人確認済み" in combined:
        trust = 20
    if any(k in combined for k in ["dmで詳細", "詳しくはdm", "lineで連絡"]):
        trust = max(trust - 15, 0)

    # --- 軸3: 採算性（0-25・文字単価ベース） ---
    profitability = 10
    # 文字単価抽出
    char_rate_match = re.search(r'(\d+(?:\.\d+)?)\s*円?\s*/\s*(?:字|文字)', combined)
    char_count_match = re.search(r'(\d[\d,]*)\s*(?:字|文字)', combined)
    char_rate = 0.0
    if char_rate_match:
        char_rate = float(char_rate_match.group(1))
    if char_rate >= 2.0:
        profitability = 25
    elif char_rate >= 1.5:
        profitability = 20
    elif char_rate >= 1.0:
        profitability = 15
    elif char_rate >= 0.5:
        profitability = 5
    elif char_rate > 0:
        profitability = 0  # 0.5未満は禁止ルール

    char_count = 0
    if char_count_match:
        try:
            char_count = int(char_count_match.group(1).replace(",", ""))
        except Exception:
            pass
    estimated_price = int(char_rate * char_count) if char_rate and char_count else 0

    # --- 軸4: 要件明確性（0-25） ---
    clarity = 10
    has_keyword = any(k in combined for k in ["キーワード", "テーマ", "ジャンル"])
    has_persona = any(k in combined for k in ["読者", "ターゲット", "ペルソナ"])
    has_deadline = any(k in combined for k in ["納期", "期限", "までに", "日以内"])
    has_format = any(k in combined for k in ["構成案", "見出し", "h2", "h3", "メタディスクリプション"])
    clarity += (5 if has_keyword else 0) + (5 if has_persona else 0) + (3 if has_deadline else 0) + (2 if has_format else 0)
    clarity = min(clarity, 25)

    total = theme + trust + profitability + clarity

    # 推奨テンプレ判定（CSO 5テンプレ準拠）
    recommended_template = "①SEO汎用"
    if any(k in combined for k in ["継続", "月10本", "週2本", "長期"]):
        recommended_template = "②継続"
    elif any(k in combined for k in ["初心者歓迎", "未経験"]):
        recommended_template = "③初心者歓迎"
    elif any(k in combined for k in ["it", "ガジェット", "比較記事", "レビュー"]):
        recommended_template = "④専門"
    elif any(k in combined for k in ["ai可", "ai執筆可", "ai活用"]):
        recommended_template = "⑤AI可"

    # 競争性チェック
    red_flags = []
    apply_count_match = re.search(r'応募.*?(\d+)\s*(?:名|人|件)', combined)
    if apply_count_match:
        try:
            apply_count = int(apply_count_match.group(1))
            if apply_count > 30:
                red_flags.append(f"応募人数{apply_count}名（30名超で読まれない可能性）")
                total = max(total - 10, 0)
        except Exception:
            pass

    if char_rate and char_rate < 0.5:
        red_flags.append(f"文字単価{char_rate}円（0.5円未満は禁止ルール）")
        total = 0
    elif char_rate and char_rate < 1.0:
        red_flags.append(f"文字単価{char_rate}円（実績作り期1.0円以上推奨）")

    if any(k in combined for k in ["テストライティング無償", "無償テスト"]):
        red_flags.append("テストライティング無償（応募禁止）")
        total = 0

    green_flags = []
    if "継続" in combined or "長期" in combined:
        green_flags.append("継続案件の可能性")
    if has_persona:
        green_flags.append("読者像が明示されている")
    if char_rate >= 1.5:
        green_flags.append(f"文字単価{char_rate}円（相場以上）")

    if total >= 70:
        verdict = "GO"
    elif total >= 50:
        verdict = "CAUTION"
    else:
        verdict = "NO-GO"

    result = {
        "category": "writing",
        "scores": {
            "theme": theme,
            "trust": trust,
            "profitability": profitability,
            "clarity": clarity,
        },
        "total": total,
        "verdict": verdict,
        "estimated_price_jpy": estimated_price,
        "char_rate": char_rate,
        "char_count": char_count,
        "recommended_template": recommended_template,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "questions_to_ask": [
            "ターゲット読者の年代・属性を教えてください",
            "参考にしたい記事のURLはありますか？",
        ],
        "reason": f"ライティング評価: テーマ{theme}+信用{trust}+採算{profitability}+明確{clarity}={total}点 / テンプレ{recommended_template}",
        "evaluated_by": "rule_based_writing",
    }
    if meta:
        result = {**meta, **result}
    result["evaluated_at"] = datetime.now().isoformat()
    result["job_text_preview"] = job_text[:100] + ("..." if len(job_text) > 100 else "")
    return result


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
    """案件テキストを評価して結果dictを返す（API→ルールベース フォールバック）

    meta["search_category"] が "writing" なら writing 向けルール評価を行う。
    """
    # category 分岐（ライティング案件専用評価）
    category = (meta or {}).get("search_category", "data_entry")
    if category == "writing":
        return _rule_based_evaluate_writing(job_text, meta)

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
    return batch_mode.__wrapped__(jobs) if hasattr(batch_mode, "__wrapped__") else [
        evaluate(j.get("description") or j.get("title", ""), meta=j)
        for j in jobs
    ]


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
