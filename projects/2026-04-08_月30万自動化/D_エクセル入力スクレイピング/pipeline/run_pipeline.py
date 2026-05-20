"""
run_pipeline.py — パイプライン統合実行

【人手が必要なのは2回だけ】
  ① 初回セットアップ時のログイン（00_session_setup.py）
  ② 応募ボタンのクリック（案件ページを自動で開くので押すだけ）
  ③ 納品ボタンのクリック（納品ファイルを添付して押すだけ）

【自動で実行されること】
  - 案件検索・詳細取得（01_search.py）
  - 案件評価・スコアリング（02_evaluate.py）
  - 応募文生成・ブラウザ表示（03_apply.py）
  - 作業実行（04_execute.py）
  - 念査（05_review.py）
  - 納品文生成・ブラウザ表示（06_deliver.py）

使い方:
  python run_pipeline.py search      # 検索→評価→応募文生成まで
  python run_pipeline.py deliver <job_json> <output_file>  # 受注後の実行→納品
"""

import json
import sys
import webbrowser
from importlib import import_module
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
SESSION_DIR = Path(__file__).parent.parent / ".sessions"

# ─────────────────────────────────────────────
# フェーズ1：検索 → 評価 → 応募文生成
# ─────────────────────────────────────────────

def phase1_search_to_apply(category: str = "data_entry"):
    search   = import_module("01_search")
    evaluate = import_module("02_evaluate")
    apply_   = import_module("03_apply")

    print("\n" + "━"*60)
    print(f"  PHASE 1: 案件検索 → 評価 → 応募文生成（category={category}）")
    print("━"*60)

    # セッション確認
    sessions_ok = [
        p for p in ["crowdworks", "lancers"]
        if (SESSION_DIR / f"{p}_session.json").exists()
    ]
    if not sessions_ok:
        print("[ERROR] セッション未設定です")
        print("  python 00_session_setup.py を先に実行してください")
        return

    print(f"  使用プラットフォーム: {', '.join(sessions_ok)}")

    # 検索
    print("\n[STEP 1/3] 案件検索中...")
    jobs = search.run(sessions_ok, category=category)
    if not jobs:
        print("[中断] 案件が見つかりませんでした")
        return

    # 評価
    print(f"\n[STEP 2/3] 案件評価中（{len(jobs)}件）...")
    recommended = []
    for i, job in enumerate(jobs, 1):
        text = job.get("description") or job.get("title", "")
        print(f"  [{i}/{len(jobs)}] {job.get('title','')[:35]}...", end=" ", flush=True)
        result = evaluate.evaluate(text, meta=job)
        v = result.get("verdict", "NO-GO")
        score = result.get("total", 0)
        print(f"→ {v} ({score}点)")
        if v in ("GO", "CAUTION"):
            recommended.append(result)

    if not recommended:
        print("\n[中断] 推奨案件がありませんでした（全件 NO-GO）")
        return

    go_jobs = [j for j in recommended if j.get("verdict") == "GO"]
    print(f"\n  結果: GO={len(go_jobs)}件 / CAUTION={len(recommended)-len(go_jobs)}件")

    # 応募文生成
    print(f"\n[STEP 3/3] 応募文生成中（{len(recommended)}件）...")
    applications = apply_.run(recommended)

    # 応募URLをブラウザで自動オープン（ユーザーが応募ボタンを押すだけ）
    print("\n" + "━"*60)
    print("  ✅ 準備完了！以下のURLで応募ボタンを押してください")
    print("━"*60)
    for i, app in enumerate(applications, 1):
        verdict = app.get("verdict", "")
        icon = "✅" if verdict == "GO" else "⚠️ "
        print(f"\n  [{i}] {icon} {app.get('title','')[:40]}")
        print(f"       URL: {app.get('url','')}")
        print(f"       スコア: {app.get('total',0)}点 | 想定: ¥{app.get('estimated_price_jpy',0):,}")
        print(f"       応募文（コピペして貼り付け）:")
        print(f"       {'─'*40}")
        for line in app.get("application_text", "").split("\n"):
            print(f"       {line}")

    # ブラウザで上位3件を自動オープン
    top = sorted(applications, key=lambda x: x.get("total", 0), reverse=True)[:3]
    print(f"\n  上位{len(top)}件のURLをブラウザで開きます...")
    for app in top:
        if app.get("url"):
            webbrowser.open(app["url"])

    print("\n  応募完了後、受注したら以下を実行してください:")
    print("  python run_pipeline.py deliver")


# ─────────────────────────────────────────────
# フェーズ2：作業実行 → 念査 → 納品準備
# ─────────────────────────────────────────────

def phase2_execute_to_deliver(job: dict | None = None, output_file: str | None = None):
    execute  = import_module("04_execute")
    review   = import_module("05_review")
    deliver  = import_module("06_deliver")

    print("\n" + "━"*60)
    print("  PHASE 2: 作業実行 → 念査 → 納品準備")
    print("━"*60)

    # 案件情報の取得
    if job is None:
        files = sorted(OUTPUT_DIR.glob("*_applications.json"))
        if not files:
            print("[ERROR] 応募情報ファイルが見つかりません")
            return
        apps = json.loads(files[-1].read_text(encoding="utf-8"))
        go_apps = [a for a in apps if a.get("verdict") == "GO"]
        if not go_apps:
            go_apps = apps

        print("\n受注した案件を選んでください:")
        for i, app in enumerate(go_apps[:5], 1):
            print(f"  [{i}] {app.get('title','')[:50]}")
        try:
            idx = int(input("\n番号を入力: ")) - 1
            job = go_apps[idx]
        except (ValueError, IndexError):
            print("[ERROR] 無効な選択です")
            return

    # 作業実行
    print(f"\n[STEP 1/3] 作業実行: {job.get('title','')[:40]}")
    result_file = execute.run(job)
    if not result_file:
        print("[ERROR] 作業実行に失敗しました")
        return

    # 念査
    print("\n[STEP 2/3] 念査（品質チェック）中...")
    review_result = review.run(result_file)
    passed = review_result.get("passed", False)

    if not passed:
        high_issues = [i for i in review_result.get("issues", []) if i.get("severity") == "high"]
        if high_issues:
            print("[中断] 重大な品質問題が検出されました。手動確認が必要です。")
            for issue in high_issues:
                print(f"  ❌ {issue.get('column','')}: {issue.get('detail','')}")
            return
        print("  ⚠️  軽微な問題あり（続行します）")

    # 納品準備
    print("\n[STEP 3/3] 納品準備中...")
    summary = deliver.run(job, Path(result_file), review_result)

    # 納品URLをブラウザで自動オープン
    job_url = job.get("url", "")
    if job_url:
        print(f"\n  納品ページを開きます: {job_url}")
        print("  ファイルを添付して納品ボタンを押してください")
        webbrowser.open(job_url)

    print("\n  ✅ 納品準備完了！ブラウザでファイルを添付して送信してください。")
    return summary


# ─────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # CLI 引数を分解：[cmd] [--category writing|data_entry] [その他]
    raw_args = sys.argv[1:]
    category = "data_entry"
    if "--category" in raw_args:
        idx = raw_args.index("--category")
        category = raw_args[idx + 1]
        raw_args = raw_args[:idx] + raw_args[idx + 2:]
    cmd = raw_args[0] if raw_args else "search"

    if cmd == "search":
        phase1_search_to_apply(category=category)
    elif cmd == "deliver":
        job_file = raw_args[1] if len(raw_args) > 1 else None
        out_file = raw_args[2] if len(raw_args) > 2 else None
        job = json.loads(Path(job_file).read_text()) if job_file else None
        phase2_execute_to_deliver(job, out_file)
    elif cmd == "setup":
        setup = import_module("00_session_setup")
        setup.check_sessions()
    else:
        print("使い方:")
        print("  python run_pipeline.py setup                       # セッション状態確認")
        print("  python run_pipeline.py search                      # 検索→評価→応募文生成（D：データ入力）")
        print("  python run_pipeline.py search --category writing   # 検索→評価→応募文生成（A：ライティング）")
        print("  python run_pipeline.py deliver                     # 受注後の実行→納品")
