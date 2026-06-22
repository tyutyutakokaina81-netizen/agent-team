#!/usr/bin/env python3
"""
guard_checks.py — 完全自動AI会社の無人ガーディアン（監視体制の中核）

設計思想:
- LLMを一切呼ばない決定論的チェックのみ（API従量課金ゼロ・GitHub Actions無料枠で動く）
- 2026-06-12インシデント（重複/テスト/未来日付記事を404本公開・台帳乖離）の再発防止が目的
- 「番人」: 公開前/コミット時に機械的に異常を検出して止める or 警告する

チェック項目:
  1. 未来日付記事    : CMO/outputs に「今日より未来の日付」のファイルがないか（誤公開の温床）
  2. 重複記事        : 同一タイトル（日付違い）が複数ないか
  3. テスト記事      : test/てすと/サンプル/dummy 等の混入がないか
  4. 台帳整合        : CMO/outputs の各記事が CMO/_index.md に記載されているか
  5. センシティブ流出 : 請求書/契約書/顧客PII 等の実ファイルがコミット対象に紛れていないか

終了コード: 0=異常なし / 1=要注意(警告) / 2=重大(公開ブロック推奨)
使い方:    python3 ops/auto_company/guard_checks.py [--strict]
"""
import os
import re
import sys
import datetime
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CMO_OUTPUTS = os.path.join(REPO, "CMO", "outputs")
CMO_INDEX = os.path.join(REPO, "CMO", "_index.md")

DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
TEST_TOKENS = ("test", "てすと", "テスト", "サンプル", "sample", "dummy", "ダミー")
SENSITIVE_NAME = re.compile(r"(請求書|契約書|invoice|contract|顧客名簿|個人情報|マイナンバー)", re.IGNORECASE)
# 個人特定情報(PII)の機械的ヒント: 番地・丁目など（市レベルはOK）
PII_HINT = re.compile(r"\d+丁目|\d+番地|\d+-\d+-\d+\s*(?:番|号)?")

warnings = []
errors = []


def w(msg):
    warnings.append(msg)


def e(msg):
    errors.append(msg)


def list_md(d):
    if not os.path.isdir(d):
        return []
    return [f for f in os.listdir(d) if f.endswith(".md")]


def file_date(name):
    m = DATE_RE.search(name)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def check_future_dates(today):
    for f in list_md(CMO_OUTPUTS):
        d = file_date(f)
        if d and d > today:
            e(f"未来日付記事: {f}（今日={today}）→ 誤公開の温床。日付を確認")


def check_duplicates():
    # タイトル部分（日付と種別プレフィックスを除いた本体）で重複検出
    titles = defaultdict(list)
    for f in list_md(CMO_OUTPUTS):
        body = re.sub(r"^\d{4}-\d{2}-\d{2}_note記事_", "", f)
        body = re.sub(r"\.md$", "", body)
        titles[body].append(f)
    for title, files in titles.items():
        if len(files) > 1:
            w(f"重複タイトル({len(files)}件): 「{title}」→ " + ", ".join(sorted(files)))


def check_test_articles():
    for f in list_md(CMO_OUTPUTS):
        low = f.lower()
        if any(t in low or t in f for t in TEST_TOKENS):
            e(f"テスト/サンプル混入の疑い: {f} → 公開対象から除外")


def check_ledger_coverage():
    if not os.path.isfile(CMO_INDEX):
        w("CMO/_index.md が見つからない → 台帳整合チェックをスキップ")
        return
    with open(CMO_INDEX, encoding="utf-8") as fh:
        ledger = fh.read()
    missing = []
    for f in list_md(CMO_OUTPUTS):
        # ファイル名 or 日付+タイトル断片が台帳に出てくるか
        body = re.sub(r"\.md$", "", f)
        if f not in ledger and body not in ledger:
            missing.append(f)
    if missing:
        w(f"台帳未記載 {len(missing)}件（先頭5件）: " + ", ".join(sorted(missing)[:5]))


def check_sensitive():
    # research/ や outputs/ にセンシティブ実ファイルが紛れていないか（テンプレ/設計は除外）
    for root, _dirs, files in os.walk(REPO):
        if "/.git" in root or "/node_modules" in root:
            continue
        for f in files:
            if SENSITIVE_NAME.search(f) and not re.search(r"(テンプレ|template|設計|サンプル様式|プロンプト|prompt|note記事|reddit|_x_|footer)", f):
                rel = os.path.relpath(os.path.join(root, f), REPO)
                w(f"センシティブ名のファイル: {rel} → 実データなら .gitignore 管理に")


def main():
    strict = "--strict" in sys.argv
    today = datetime.date.today()

    check_future_dates(today)
    check_duplicates()
    check_test_articles()
    check_ledger_coverage()
    check_sensitive()

    print("=" * 60)
    print(f"監視ガーディアン guard_checks  ({today})")
    print("=" * 60)
    if errors:
        print(f"\n🛑 重大 {len(errors)}件:")
        for m in errors:
            print(f"  - {m}")
    if warnings:
        print(f"\n⚠️  警告 {len(warnings)}件:")
        for m in warnings:
            print(f"  - {m}")
    if not errors and not warnings:
        print("\n✅ 異常なし。収益ループは安全に回せる状態。")

    if errors:
        return 2
    if warnings and strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
