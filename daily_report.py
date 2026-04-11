"""
daily_report.py — 日次進捗レポート（リスクゼロ・読み取りのみ）

毎朝 8:00 に cron から自動実行される。
外部APIへのアクセスは一切行わない。ローカルファイルの状態を集計するだけ。

実行方法:
  python3 daily_report.py
"""

import json
from datetime import datetime, date
from pathlib import Path

REPO_DIR = Path(__file__).parent
PIPELINE_OUTPUT_DIR = REPO_DIR / "projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/outputs"
TEMPLATE_DIST_DIR   = REPO_DIR / "projects/2026-04-08_月30万自動化/C_テンプレ販売/dist"
SESSION_DIR         = REPO_DIR / "projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/.sessions"
BOOTH_SESSION_FILE  = REPO_DIR / ".sessions/booth_session.json"
LOG_DIR             = REPO_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def check_sessions():
    """ログインセッション状態"""
    results = {}
    results["crowdworks"] = (SESSION_DIR / "crowdworks_session.json").exists()
    results["lancers"]    = (SESSION_DIR / "lancers_session.json").exists()
    results["booth"]      = BOOTH_SESSION_FILE.exists()
    return results


def check_templates():
    """C柱 テンプレートファイル状態"""
    files = {
        "vol1_freelance_cashflow.xlsx": "フリーランス収支管理",
        "vol2_sns_calendar.xlsx":       "SNS投稿カレンダー",
    }
    results = {}
    for fname, label in files.items():
        p = TEMPLATE_DIST_DIR / fname
        if p.exists():
            mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y/%m/%d")
            results[label] = {"ready": True, "updated": mtime}
        else:
            results[label] = {"ready": False, "updated": None}
    return results


def check_pipeline_outputs():
    """D柱 パイプライン出力状態"""
    if not PIPELINE_OUTPUT_DIR.exists():
        return {"total_apps": 0, "go_count": 0, "today_count": 0, "estimated_revenue": 0, "last_run": None}

    app_files = sorted(PIPELINE_OUTPUT_DIR.glob("*_applications.json"))
    eval_files = sorted(PIPELINE_OUTPUT_DIR.glob("*_evaluated.json"))

    total_apps = 0
    go_count   = 0
    today_count = 0
    estimated_revenue = 0
    last_run = None

    today_str = date.today().isoformat()

    for f in app_files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if last_run is None or mtime > last_run:
            last_run = mtime
        try:
            apps = json.loads(f.read_text(encoding="utf-8"))
            total_apps += len(apps)
            for app in apps:
                if app.get("verdict") == "GO":
                    go_count += 1
                    estimated_revenue += app.get("estimated_price_jpy", 0)
                if f.stem.startswith(today_str.replace("-", "")):
                    today_count += 1
        except Exception:
            pass

    # 今日の評価ファイルも確認
    if today_count == 0 and eval_files:
        latest = eval_files[-1]
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        if mtime.date() == date.today():
            try:
                evals = json.loads(latest.read_text(encoding="utf-8"))
                today_count = len(evals)
            except Exception:
                pass

    last_run_str = last_run.strftime("%Y/%m/%d %H:%M") if last_run else "未実行"
    return {
        "total_apps": total_apps,
        "go_count": go_count,
        "today_count": today_count,
        "estimated_revenue": estimated_revenue,
        "last_run": last_run_str,
    }


def estimate_booth_revenue():
    """
    BOOTH売上の推計（APIなし・手動ログ方式）
    logs/booth_sales.json に手動入力されたデータを読む
    """
    sales_file = LOG_DIR / "booth_sales.json"
    if not sales_file.exists():
        # 初期ファイルを作成（手動入力用テンプレ）
        template = {
            "_comment": "BOOTHの管理画面を見て手動で更新してください",
            "_url": "https://manage.booth.pm/items",
            "last_updated": "",
            "sales": []
        }
        sales_file.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"total": 0, "this_month": 0, "count": 0}

    try:
        data = json.loads(sales_file.read_text(encoding="utf-8"))
        sales = data.get("sales", [])
        this_month = date.today().strftime("%Y-%m")
        monthly = sum(s.get("amount", 0) for s in sales if s.get("date", "").startswith(this_month))
        total = sum(s.get("amount", 0) for s in sales)
        return {"total": total, "this_month": monthly, "count": len(sales)}
    except Exception:
        return {"total": 0, "this_month": 0, "count": 0}


def main():
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    today = date.today()

    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📊 日次進捗レポート  {now}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # セッション状態
    sessions = check_sessions()
    print("\n【ログインセッション】")
    print(f"  CrowdWorks : {'✅ 有効' if sessions['crowdworks'] else '❌ 未設定'}")
    print(f"  ランサーズ : {'✅ 有効' if sessions['lancers'] else '❌ 未設定'}")
    print(f"  BOOTH      : {'✅ 有効' if sessions['booth'] else '❌ 未設定'}")

    if not sessions["crowdworks"] and not sessions["lancers"]:
        print("  ⚠️  D柱が動きません → python3 pipeline/00_session_setup.py を実行")

    # C柱: テンプレート
    templates = check_templates()
    print("\n【C柱: テンプレート販売】")
    for label, info in templates.items():
        if info["ready"]:
            print(f"  ✅ {label} (更新: {info['updated']})")
        else:
            print(f"  ❌ {label} → python3 generate_products.py を実行")

    booth_sales = estimate_booth_revenue()
    print(f"  売上（今月）: ¥{booth_sales['this_month']:,}  累計: ¥{booth_sales['total']:,}  件数: {booth_sales['count']}件")
    print(f"  ※ 売上記録: logs/booth_sales.json に手動で入力してください")

    # D柱: パイプライン
    pipeline = check_pipeline_outputs()
    print("\n【D柱: 自動受注パイプライン】")
    print(f"  最終実行     : {pipeline['last_run']}")
    print(f"  総応募数     : {pipeline['total_apps']}件")
    print(f"  GO案件数     : {pipeline['go_count']}件")
    print(f"  推計売上見込み: ¥{pipeline['estimated_revenue']:,}")

    if pipeline["last_run"] == "未実行":
        print("  ⚠️  パイプライン未実行 → ./start.sh を実行 または cron 設定を確認")

    # 月次目標進捗
    target = 300_000
    booth_rev  = booth_sales["this_month"]
    pipeline_rev = pipeline["estimated_revenue"]
    total_est  = booth_rev + pipeline_rev
    progress   = min(int(total_est / target * 100), 100)

    print("\n【月次目標進捗】")
    bar_filled = progress // 5
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    print(f"  ¥300,000目標  [{bar}] {progress}%")
    print(f"  BOOTH売上(確定)  : ¥{booth_rev:,}")
    print(f"  D柱売上見込み    : ¥{pipeline_rev:,}")
    print(f"  合計             : ¥{total_est:,} / ¥{target:,}")

    # 今日のアクションリスト
    print("\n【今日のアクション】")
    actions = []

    if not sessions["crowdworks"] and not sessions["lancers"]:
        actions.append("🔑 D柱セッション設定: python3 pipeline/00_session_setup.py")

    if not sessions["booth"]:
        actions.append("🔑 BOOTHセッション設定: python3 C_テンプレ販売/auto_booth_publish.py")

    not_ready = [l for l, i in templates.items() if not i["ready"]]
    if not_ready:
        actions.append(f"📄 テンプレート生成: python3 generate_products.py")

    if pipeline["go_count"] > 0:
        actions.append(f"📝 応募: {pipeline['go_count']}件のGO案件に応募ボタンを押す（start.shが自動でブラウザを開きます）")

    if booth_sales["count"] == 0 and sessions["booth"]:
        actions.append("🛒 BOOTH出品: 管理画面で下書きを「公開」にする → https://manage.booth.pm/items")

    if not actions:
        actions.append("✅ 特になし（パイプラインが自動稼働中）")

    for action in actions:
        print(f"  → {action}")

    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")


if __name__ == "__main__":
    main()
