#!/usr/bin/env python3
"""
auto_job_hunt.py — 案件自動サーチ＋応募文生成（requests版・参照用）

※ サーバー環境では CrowdWorks が HTTP 403 を返すため動作しません。
※ Mac/Playwright版は auto_job_apply.py を使用してください。

1. requestsでクラウドワークス公開案件を検索（ログイン不要）
2. ルールベース評価でGO/CAUTION/NO-GOを判定
3. テンプレート応募文を自動生成
4. 結果をJSONと人間可読テキストで出力

実行: python3 auto_job_hunt.py
Macで確認: .sessions/job_applications_YYYYMMDD.txt を開く
"""

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).parent
OUTPUT_DIR = REPO / "projects" / "2026-04-08_月30万自動化" / "D_エクセル入力スクレイピング" / "outputs"
SESSIONS = REPO / ".sessions"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")

KEYWORDS = [
    "データ入力",
    "エクセル入力",
    "スクレイピング",
    "データ収集",
    "CSV作成",
    "Excel作業",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
}


# ─── 案件検索 ─────────────────────────────────────────────────

def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [HTTP error] {url}: {e}")
        return ""


def search_crowdworks(keyword: str) -> list[dict]:
    enc = urllib.parse.quote(keyword)
    url = f"https://crowdworks.jp/public/jobs/search?order=new&keyword={enc}"
    html = fetch_html(url)
    if not html:
        return []

    jobs = []
    seen = set()

    # 案件URLパターン: /public/jobs/数字
    for m in re.finditer(r'href="(/public/jobs/(\d+))"', html):
        path, job_id = m.group(1), m.group(2)
        if job_id in seen:
            continue
        seen.add(job_id)

        full_url = f"https://crowdworks.jp{path}"

        # タイトルをURLの前後テキストから推定
        pos = m.start()
        surrounding = html[max(0, pos-300):pos+300]
        title_m = re.search(r'<[^>]*class="[^"]*job[^"]*"[^>]*>([^<]{5,80})<', surrounding)
        if not title_m:
            title_m = re.search(r'>([^<]{10,60})</a>', surrounding)
        title = title_m.group(1).strip() if title_m else f"案件 #{job_id}"
        title = re.sub(r'\s+', ' ', title)

        # 予算テキスト
        budget_m = re.search(r'([\d,]+)\s*円', surrounding)
        budget_text = budget_m.group(0) if budget_m else ""

        jobs.append({
            "id": job_id,
            "title": title,
            "url": full_url,
            "platform": "crowdworks",
            "keyword": keyword,
            "budget_text": budget_text,
            "found_at": datetime.now().isoformat(),
        })

    return jobs[:8]


def search_all() -> list[dict]:
    all_jobs = []
    seen_ids = set()

    print(f"\n  検索キーワード: {len(KEYWORDS)}件")
    for kw in KEYWORDS:
        print(f"  [{kw}] 検索中...", end=" ", flush=True)
        jobs = search_crowdworks(kw)
        new = [j for j in jobs if j["id"] not in seen_ids]
        for j in new:
            seen_ids.add(j["id"])
            all_jobs.append(j)
        print(f"{len(new)}件")
        time.sleep(1.5)

    return all_jobs


# ─── ルールベース評価 ──────────────────────────────────────────

def evaluate(job: dict) -> dict:
    text = (job.get("title", "") + " " + job.get("budget_text", "")).lower()

    # 技術実現性
    tech = 10
    if any(k in text for k in ["エクセル", "excel", "csv", "データ入力", "スプレッドシート"]):
        tech = 25
    elif any(k in text for k in ["スクレイピング", "scraping", "データ収集"]):
        tech = 20
    if any(k in text for k in ["captcha", "ログイン必須", "会員限定"]):
        tech = max(tech - 10, 5)

    # 法的リスク
    legal = 20
    if any(k in text for k in ["個人情報", "プライバシー", "住所収集", "電話番号収集"]):
        legal = 5
    if any(k in text for k in ["詐欺", "不正", "違法"]):
        legal = 0

    # 採算性
    amounts = re.findall(r'(\d[\d,]+)', job.get("budget_text", ""))
    max_amt = max([int(a.replace(",", "")) for a in amounts if int(a.replace(",", "")) > 100], default=0)
    profitability = 25 if max_amt >= 10000 else (20 if max_amt >= 5000 else (10 if max_amt >= 2000 else 8))
    estimated_price = max_amt or 5000

    # 要件明確性
    clarity = 15

    total = tech + legal + profitability + clarity

    # 詐欺フィルタ
    red_flags = []
    if any(k in text for k in ["海外在住", "受け取り代行", "転送", "送金"]):
        red_flags.append("詐欺の疑い")
        total = 0

    verdict = "GO" if total >= 70 else ("CAUTION" if total >= 50 else "NO-GO")

    return {
        **job,
        "scores": {"technical": tech, "legal": legal, "profitability": profitability, "clarity": clarity},
        "total": total,
        "verdict": verdict,
        "estimated_price_jpy": estimated_price,
        "red_flags": red_flags,
        "evaluated_at": datetime.now().isoformat(),
    }


# ─── 応募文生成 ────────────────────────────────────────────────

def make_application(job: dict) -> str:
    title = job.get("title", "")
    text = title.lower()

    if "スクレイピング" in text or "データ収集" in text:
        skill = "PythonによるWebスクレイピング・データ収集"
        method = "対象サイトの構造を事前に確認し、正確にデータを収集いたします。"
    elif any(k in text for k in ["エクセル", "excel", "csv"]):
        skill = "Excel・Pythonを使ったデータ処理・入力作業"
        method = "入力後に必ずダブルチェックを行い、正確な成果物をお届けします。"
    else:
        skill = "データ入力・収集作業"
        method = "丁寧・正確に対応いたします。"

    return f"""はじめまして。{skill}を得意としております。

ご依頼の内容を拝見しました。{method}

納期は厳守いたします。作業前に不明点があれば必ず確認してから進めますので、安心してお任せください。ぜひご検討のほどよろしくお願いいたします。"""


# ─── メイン ──────────────────────────────────────────────────

def run():
    print("━" * 50)
    print("  案件自動サーチ & 応募文生成")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 50)

    # 検索
    jobs = search_all()
    print(f"\n  取得: {len(jobs)}件")

    if not jobs:
        print("  案件が見つかりませんでした（ネットワーク確認）")
        return

    # 評価
    results = [evaluate(j) for j in jobs]
    go_jobs = [r for r in results if r["verdict"] == "GO"]
    caution_jobs = [r for r in results if r["verdict"] == "CAUTION"]

    print(f"\n  GO: {len(go_jobs)}件 / CAUTION: {len(caution_jobs)}件 / NO-GO: {len(results)-len(go_jobs)-len(caution_jobs)}件")

    # 応募文生成（GO + CAUTION）
    apply_list = []
    for job in sorted(go_jobs + caution_jobs, key=lambda x: x["total"], reverse=True):
        entry = {
            **job,
            "application_text": make_application(job),
            "apply_url": job["url"],
        }
        apply_list.append(entry)

    # JSON保存
    json_path = OUTPUT_DIR / f"{TODAY}_applications.json"
    json_path.write_text(json.dumps(apply_list, ensure_ascii=False, indent=2))

    # 人間可読テキスト保存（Mac側で確認用）
    txt_path = SESSIONS / f"job_applications_{TODAY}.txt"
    lines = [
        "═" * 60,
        f"  案件リスト & 応募文  {datetime.now().strftime('%Y-%m-%d')}",
        f"  GO: {len(go_jobs)}件 / CAUTION: {len(caution_jobs)}件",
        "═" * 60,
        "",
        "【手順】",
        "  1. 下記URLをブラウザで開く",
        "  2. 応募文をコピーして貼り付け",
        "  3. 応募ボタンを押す",
        "",
    ]

    for i, job in enumerate(apply_list, 1):
        lines += [
            f"─── [{i}] {job['verdict']} {job['total']}点 ───────────────────────",
            f"タイトル: {job['title']}",
            f"URL    : {job['url']}",
            f"想定単価: ¥{job['estimated_price_jpy']:,}",
            f"キーワード: {job.get('keyword', '')}",
            "",
            "【応募文】",
            job["application_text"],
            "",
        ]
        if job.get("red_flags"):
            lines.append(f"⚠ 注意: {', '.join(job['red_flags'])}")
            lines.append("")

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    # ターミナル出力
    print()
    for job in apply_list[:5]:
        icon = "✅" if job["verdict"] == "GO" else "⚠️ "
        print(f"  {icon} [{job['total']}点] {job['title'][:40]}")
        print(f"      ¥{job['estimated_price_jpy']:,}  {job['url']}")
        print()

    print(f"\n  応募文 → {txt_path}")
    print(f"  JSON  → {json_path}")
    print("\n  ▶ Mac側: .sessions/job_applications_{TODAY}.txt を開いてURLに応募")
    print("━" * 50)

    return apply_list


if __name__ == "__main__":
    run()
