"""
check_booth_sales.py — BOOTH売上を随時チェック（Playwright）

やること:
  1. 保存済みBOOTHセッションで管理画面にアクセス
  2. 注文履歴・売上金額を取得
  3. 新規売上があればログに記録
  4. 振込口座未登録の通知が出ていたら BANK_ACCOUNT_REQUIRED フラグを立てる
     → 口座登録自体は手動で行う（自動化しない）

実行方法:
  python3 check_booth_sales.py

cron（30分ごと）:
  */30 * * * * python3 /path/to/check_booth_sales.py >> /path/to/logs/booth_sales.log 2>&1
"""

import json
import time
from datetime import datetime
from pathlib import Path

REPO_DIR          = Path(__file__).parent
SESSION_FILE      = REPO_DIR / ".sessions" / "booth_session.json"
LOG_DIR           = REPO_DIR / "logs"
SALES_FILE        = LOG_DIR / "booth_sales.json"
ALERT_FILE        = LOG_DIR / "booth_alerts.json"
LOG_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# データ管理
# ─────────────────────────────────────────────

def load_sales() -> dict:
    if SALES_FILE.exists():
        try:
            return json.loads(SALES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sales": [], "last_checked": None, "total_revenue": 0}


def save_sales(data: dict):
    SALES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_alerts() -> list:
    if ALERT_FILE.exists():
        try:
            return json.loads(ALERT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_alerts(alerts: list):
    ALERT_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────
# BOOTH スクレイピング
# ─────────────────────────────────────────────

def scrape_booth_sales() -> dict:
    """
    BOOTHの管理画面から売上情報を取得する。
    returns: {
        "orders": [...],
        "total_revenue": int,
        "bank_account_required": bool,  ← 口座未登録通知が出ているか
        "error": str | None,
    }
    """
    if not SESSION_FILE.exists():
        return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": "セッション未設定"}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": "playwright未インストール"}

    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    orders = []
    total_revenue = 0
    bank_account_required = False
    error = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=100)
            context = browser.new_context(
                storage_state=storage,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # ── 注文履歴ページ ──
            page.goto("https://manage.booth.pm/orders", timeout=20000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            time.sleep(1)

            # 振込口座未登録の通知を検出（自動入力はしない）
            for notice_sel in [
                "[class*='bank']", "[class*='payment_account']",
                "a[href*='payment_account']",
                "*:has-text('振込先')", "*:has-text('口座登録')", "*:has-text('口座未登録')",
            ]:
                try:
                    el = page.query_selector(notice_sel)
                    if el and el.is_visible():
                        bank_account_required = True
                        break
                except Exception:
                    pass

            # ログイン確認
            if "sign_in" in page.url or "login" in page.url:
                error = "セッション期限切れ（再ログインが必要）"
                browser.close()
                return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": error}

            # 注文行を取得
            for row_sel in [
                "tr.order", ".order-row", "[class*='order__row']",
                "table tbody tr", ".c-ordersTable__row",
            ]:
                rows = page.query_selector_all(row_sel)
                if rows:
                    for row in rows[:50]:  # 最大50件
                        try:
                            text = row.inner_text()
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            if not lines:
                                continue
                            # 金額を抽出（¥数字 パターン）
                            import re
                            amounts = re.findall(r"[¥￥][\d,]+", text)
                            amount = 0
                            if amounts:
                                amount = int(amounts[0].replace("¥", "").replace("￥", "").replace(",", ""))

                            # 日付を抽出
                            dates = re.findall(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", text)
                            order_date = dates[0] if dates else ""

                            # 注文IDを抽出
                            order_ids = re.findall(r"#\d+|\d{8,}", text)
                            order_id = order_ids[0] if order_ids else f"row_{len(orders)}"

                            orders.append({
                                "id": order_id,
                                "date": order_date,
                                "amount": amount,
                                "raw": lines[0][:60] if lines else "",
                            })
                            total_revenue += amount
                        except Exception:
                            pass
                    if orders:
                        break

            # 売上サマリーページも確認
            page.goto("https://manage.booth.pm/stats", timeout=15000)
            try:
                page.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass

            # 合計売上金額をより正確に取得
            for total_sel in [
                "[class*='total_sales']", "[class*='totalSales']",
                "[class*='revenue']", ".stats-total",
                "*:has-text('売上合計')", "*:has-text('累計売上')",
            ]:
                try:
                    el = page.query_selector(total_sel)
                    if el:
                        import re
                        text = el.inner_text()
                        m = re.search(r"[\d,]+", text)
                        if m:
                            v = int(m.group().replace(",", ""))
                            if v > total_revenue:
                                total_revenue = v
                            break
                except Exception:
                    pass

            browser.close()

    except Exception as e:
        error = str(e)

    return {
        "orders": orders,
        "total_revenue": total_revenue,
        "bank_account_required": bank_account_required,
        "error": error,
    }


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def main():
    now = datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M")

    print(f"\n[{now_str}] BOOTH売上チェック開始...")

    # 既存データ読み込み
    data = load_sales()
    alerts = load_alerts()
    prev_revenue = data.get("total_revenue", 0)
    known_ids = {s.get("id") for s in data.get("sales", [])}

    # スクレイピング実行
    result = scrape_booth_sales()

    if result["error"]:
        print(f"  ⚠️  エラー: {result['error']}")
        if result["error"] == "セッション期限切れ（再ログインが必要）":
            alert = {
                "type": "session_expired",
                "message": "BOOTHセッション期限切れ。再ログインが必要です。\n  → python3 projects/2026-04-08_月30万自動化/C_テンプレ販売/auto_booth_publish.py",
                "time": now_str,
                "resolved": False,
            }
            if not any(a.get("type") == "session_expired" and not a.get("resolved") for a in alerts):
                alerts.append(alert)
                save_alerts(alerts)
                print(f"  🚨 アラート追加: {alert['message']}")
        data["last_checked"] = now_str
        save_sales(data)
        return

    # 新規注文の検出
    new_orders = []
    for order in result["orders"]:
        if order["id"] not in known_ids:
            new_orders.append(order)
            data["sales"].append({**order, "detected_at": now_str})
            known_ids.add(order["id"])

    # 売上更新
    if result["total_revenue"] > prev_revenue:
        diff = result["total_revenue"] - prev_revenue
        print(f"  🎉 新規売上: +¥{diff:,}  累計: ¥{result['total_revenue']:,}")
    elif new_orders:
        print(f"  🎉 新規注文: {len(new_orders)}件")
    else:
        print(f"  → 変化なし（累計: ¥{result['total_revenue']:,}）")

    data["total_revenue"] = result["total_revenue"]
    data["last_checked"] = now_str
    save_sales(data)

    # 口座未登録アラート（自動入力はしない・手動対応を促す）
    if result["bank_account_required"]:
        already_alerted = any(
            a.get("type") == "bank_account_required" and not a.get("resolved")
            for a in alerts
        )
        if not already_alerted:
            alert = {
                "type": "bank_account_required",
                "message": (
                    "⚠️  BOOTH振込口座が未登録です。売上を受け取るために手動で登録してください。\n"
                    "  → https://manage.booth.pm/payment_accounts"
                ),
                "time": now_str,
                "resolved": False,
            }
            alerts.append(alert)
            save_alerts(alerts)
            print(f"\n  {'='*50}")
            print(f"  🚨 ACTION REQUIRED（手動対応）")
            print(f"  {alert['message']}")
            print(f"  {'='*50}\n")

    # 未解決アラートの表示
    unresolved = [a for a in alerts if not a.get("resolved")]
    if unresolved:
        print(f"\n  未対応アラート: {len(unresolved)}件")
        for a in unresolved:
            print(f"    [{a['time']}] {a['message'].splitlines()[0]}")

    print(f"  ✅ 完了 → {SALES_FILE}")


if __name__ == "__main__":
    main()
