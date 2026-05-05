"""CrowdWorks 自動応募（Playwright・最高リスク領域）。

検索→案件詳細→応募文ペースト→送信。
タイトルから案件カテゴリ（data/writer/ai_support/consultant）を推定し、
cw_apply.build() でカテゴリ別の応募文を生成する。

現在実装している応募ガード:
  - 提案数 PROPOSAL_LIMIT 件以上はスキップ（競争率回避）
  - DAILY_APPLY_LIMIT 件で打ち切り
未実装（必要なら追加）：報酬下限・残期間・本人確認のフィルタ。
"""
from __future__ import annotations

import re

import _browser
import _scheduler
import cw_apply
import published

DAILY_APPLY_LIMIT = 3
PROPOSAL_LIMIT = 10

KEYWORD_TO_KIND = [
    (re.compile(r"(SEO|ライティング|執筆|記事)"), "writer"),
    (re.compile(r"(AI|ChatGPT|Claude|プロンプト|自動化)"), "ai_support"),
    (re.compile(r"(SNS|運用代行|Twitter|Instagram|X運用)"), "consultant"),
]

SEARCH_URLS = [
    "https://crowdworks.jp/public/jobs/search?keep_search_criteria=true&order=new&hide_expired=true&category_id=235",
    "https://crowdworks.jp/public/jobs/search?keep_search_criteria=true&order=new&hide_expired=true&category_id=240",
]

PROPOSAL_COUNT_RE = re.compile(r"応募\s*(\d+)\s*件")


def _detect_kind(title: str) -> str:
    for pattern, kind in KEYWORD_TO_KIND:
        if pattern.search(title):
            return kind
    return "data"


def _proposal_count(text: str) -> int | None:
    m = PROPOSAL_COUNT_RE.search(text)
    return int(m.group(1)) if m else None


def run() -> tuple[bool, str]:
    if _browser.is_dry():
        sample_titles = [
            "ECサイト商品データ500件入力",
            "SEO記事3000字執筆 健康ジャンル",
            "ChatGPTプロンプト作成支援",
        ]
        for t in sample_titles:
            kind = _detect_kind(t)
            body = cw_apply.build(t, kind)
            _scheduler.log(f"DRY_RUN: would apply '{t}' kind={kind} ({len(body)}字)")
        return True, f"DRY_RUN: would apply to {len(sample_titles)} jobs"

    applied = 0
    with _browser.open_browser(headless=False) as ctx:
        page = ctx.new_page()
        for search_url in SEARCH_URLS:
            if applied >= DAILY_APPLY_LIMIT:
                break
            page.goto(search_url)
            _browser.human_sleep(3, 6)

            if "/login" in page.url:
                return False, _browser.NOT_LOGGED_IN

            job_links = page.locator("a.job_link, a[href*='/public/jobs/']").all()
            for link in job_links[:10]:
                if applied >= DAILY_APPLY_LIMIT:
                    break
                title = (link.text_content() or "").strip()
                href = link.get_attribute("href") or ""
                if not title or not href:
                    continue

                kind = _detect_kind(title)
                body = cw_apply.build(title, kind)

                _browser.human_move(page)
                page.goto("https://crowdworks.jp" + href if href.startswith("/") else href)
                _browser.human_sleep(4, 8)

                proposals_el = page.locator("text=/応募 \\d+ 件/").first
                if proposals_el.count():
                    n = _proposal_count(proposals_el.text_content() or "")
                    if n is not None and n >= PROPOSAL_LIMIT:
                        continue

                apply_btn = page.locator("a:has-text('応募する'), button:has-text('応募する')").first
                if not apply_btn.count():
                    continue
                apply_btn.click()
                _browser.human_sleep(3, 6)

                _browser.human_type(page, "textarea[name='message'], textarea", body)
                _browser.human_sleep(2, 4)
                _browser.human_move(page)

                page.click("button:has-text('応募する'), input[type='submit']")
                _browser.human_sleep(4, 8)

                published.append("crowdworks", page.url, title, 0)
                _scheduler.log(f"crowdworks applied: {title} (kind={kind})")
                applied += 1

    if applied == 0:
        return False, "応募可能な案件が見つからなかった"
    return True, f"applied to {applied} jobs"


if __name__ == "__main__":
    ok, msg = run()
    print(("OK: " if ok else "FAIL: ") + msg)
