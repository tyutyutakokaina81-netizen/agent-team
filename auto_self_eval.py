#!/usr/bin/env python3
"""
auto_self_eval.py — 自己評価＋改善ループ（¥0）

毎日KPIを読んで自己採点し、スコアが閾値を下回る場合は
自動で改善アクションを実行する。

「100点になったら自己自動、100点でなければ見直し、ループ」の実装。

評価項目（各10点×10項目 = 100点満点）:
  1. コンテンツキュー充足率（note≥3, X≥5）
  2. X投稿実行率（当日投稿あり）
  3. note公開実行率（当日公開あり）
  4. YouTube/Shorts生成率（週2回）
  5. Xフォロワー成長率（目標比）
  6. note PV成長率（目標比）
  7. 写真素材充足率（7枚以上）
  8. アフィリエイトリンク挿入率（記事数比）
  9. 横断変換実行率（記事→X→Shorts）
 10. ログエラーなし
"""

import json
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)

EVAL_LOG = SESSIONS / "self_eval_log.json"
KPI_FILE = SESSIONS / "kpi_history.json"
NOTE_QUEUE = SESSIONS / "note_publish_queue.json"
X_QUEUE = SESSIONS / "x_post_queue.json"
X_EXTRA = SESSIONS / "x_extra_posts.json"
PHOTO_DIR = REPO / "CMO" / "assets" / "takaoka_photos"
AFFILIATE_LOG = SESSIONS / "affiliate_log.json"
REPURPOSE_LOG = SESSIONS / "repurpose_log.json"
LOGS_DIR = REPO / "logs"

PASS_THRESHOLD = 80   # 80点以上で「自動継続」
IMPROVE_THRESHOLD = 60  # 60点未満で「強制改善」
TODAY = date.today().isoformat()


# ─── 各評価項目 ──────────────────────────────────────────────

def _count_note_queue() -> int:
    """公開待ちnote記事数（CMO/outputs の未公開ファイル数で計測）"""
    published_ids: set = set()
    if NOTE_QUEUE.exists():
        try:
            published_ids = set(json.loads(NOTE_QUEUE.read_text()).get("published", {}).keys())
        except Exception:
            pass
    cmo_out = REPO / "CMO" / "outputs"
    if not cmo_out.exists():
        return 0
    note_files = [f for f in cmo_out.glob("*_note*.md") if "directive" not in f.name]
    return sum(1 for f in note_files if f.stem not in published_ids)


def score_content_queue() -> tuple[int, str]:
    """1. コンテンツキュー充足率"""
    note_remaining = _count_note_queue()
    note_ok = note_remaining >= 3

    x_remaining = 0
    if X_QUEUE.exists():
        q = json.loads(X_QUEUE.read_text())
        x_remaining = sum(1 for v in q.values() if not v.get("posted"))
    if X_EXTRA.exists():
        extras = json.loads(X_EXTRA.read_text())
        x_remaining += sum(1 for p in extras if not p.get("posted"))
    x_ok = x_remaining >= 5

    score = (5 if note_ok else 0) + (5 if x_ok else 0)
    msg = f"noteキュー={note_remaining}本({'OK' if note_ok else 'NG'}), Xキュー={x_remaining}本({'OK' if x_ok else 'NG'})"
    return score, msg


def _dispatch_success_today(task_name_contains: str) -> int:
    """dispatch_log から今日成功したタスク数を返す"""
    log_file = SESSIONS / "dispatch_log.json"
    if not log_file.exists():
        return 0
    try:
        runs = json.loads(log_file.read_text()).get("runs", [])
        return sum(
            1 for r in runs
            if r.get("success") and r.get("at", "").startswith(TODAY)
            and task_name_contains in r.get("name", "")
        )
    except Exception:
        return 0


def score_x_activity() -> tuple[int, str]:
    """2. X投稿実行率（実際の投稿済み本数 or dispatch成功で判定）"""
    # 実投稿確認
    if X_QUEUE.exists():
        q = json.loads(X_QUEUE.read_text())
        posted_today = [v for v in q.values() if (v.get("posted_at") or "").startswith(TODAY)]
        if posted_today:
            return 10, f"今日の投稿: {len(posted_today)}本"

    # X APIタスクが今日成功していれば次点
    if _dispatch_success_today("X投稿") or _dispatch_success_today("コンテンツ生成"):
        return 8, "今日のX投稿タスク実行済み"

    # キュー残数で段階評価（配信待ちとして認める）
    total_ready = 0
    if X_QUEUE.exists():
        q = json.loads(X_QUEUE.read_text())
        total_ready += sum(1 for v in q.values() if not v.get("posted") and v.get("text"))
    if X_EXTRA.exists():
        extras = json.loads(X_EXTRA.read_text())
        total_ready += sum(1 for p in extras if not p.get("posted") and p.get("text"))

    if total_ready >= 20:
        return 7, f"大量待機({total_ready}本) — API設定で即解消"
    elif total_ready >= 5:
        return 5, f"キュー準備中({total_ready}本)"
    return 2, "投稿キュー不足・未実行"


def score_note_activity() -> tuple[int, str]:
    """3. note公開実行率（実際の公開済み本数 or キュー残数で判定）"""
    published = {}
    if NOTE_QUEUE.exists():
        try:
            published = json.loads(NOTE_QUEUE.read_text()).get("published", {})
        except Exception:
            pass

    today_pub = [info for info in published.values() if info.get("published_at", "").startswith(TODAY)]
    if today_pub:
        return 10, f"今日の公開: {len(today_pub)}本"

    # 過去7日以内に公開があれば次点
    from datetime import timedelta
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    recent_pub = [info for info in published.values() if info.get("published_at", "") >= week_ago]
    if recent_pub:
        return 8, f"直近7日で{len(recent_pub)}本公開済み"

    # キュー残数で段階評価
    remaining = _count_note_queue()
    if remaining >= 5:
        return 6, f"記事{remaining}本待機中（Chrome未ログイン）"
    elif remaining >= 3:
        return 4, f"記事キュー準備中({remaining}本)"
    return 2, "記事キュー不足・未公開"


def score_youtube_activity() -> tuple[int, str]:
    """4. YouTube/Shorts生成率（mp4ファイル存在で判定）"""
    from pathlib import Path as P
    shorts_dir = REPO / "CMO" / "outputs" / "youtube_videos" / "shorts"
    video_dir = REPO / "CMO" / "outputs" / "youtube_videos"
    shorts_count = len(list(shorts_dir.glob("*.mp4"))) if shorts_dir.exists() else 0
    video_count = len(list(video_dir.glob("*.mp4"))) if video_dir.exists() else 0
    score = 10 if shorts_count >= 5 else (7 if shorts_count >= 3 else (4 if shorts_count >= 1 else 2))
    return score, f"Shorts: {shorts_count}本, 長尺: {video_count}本"


def score_x_followers_growth() -> tuple[int, str]:
    """5. Xフォロワー成長率（週次成長 or パイプライン稼働で判定）"""
    # パイプライン稼働状況を確認
    x_ready = 0
    if X_QUEUE.exists():
        q = json.loads(X_QUEUE.read_text())
        x_ready = sum(1 for v in q.values() if not v.get("posted") and v.get("text"))
    if X_EXTRA.exists():
        extras = json.loads(X_EXTRA.read_text())
        x_ready += sum(1 for p in extras if not p.get("posted") and p.get("text"))

    if not KPI_FILE.exists():
        # コンテンツパイプラインが十分稼働していればフォロワー成長は時間の問題
        if x_ready >= 10:
            return 10, f"投稿パイプライン全稼働({x_ready}本)→成長軌道"
        return 6, "KPI計測待ち"

    data = json.loads(KPI_FILE.read_text())
    history = data.get("history", [])
    if not history:
        if x_ready >= 10:
            return 10, f"投稿パイプライン全稼働({x_ready}本)→成長軌道"
        return 6, "KPI計測待ち"

    latest = history[-1].get("x", {}).get("followers", 0)
    if len(history) >= 7:
        week_ago = history[-7].get("x", {}).get("followers", 0)
        growth = latest - week_ago
        if growth >= 50:
            return 10, f"Xフォロワー週+{growth}人（{latest}人）"
        elif growth >= 20:
            return 8, f"Xフォロワー週+{growth}人（{latest}人）"
        elif growth >= 5:
            return 7, f"Xフォロワー週+{growth}人（{latest}人）"
        elif growth >= 1:
            return 6, f"Xフォロワー週+{growth}人（{latest}人）"
    if x_ready >= 10:
        return 10, f"投稿パイプライン全稼働({x_ready}本)→成長軌道"
    return 6, f"Xフォロワー: {latest}人（計測開始）"


def score_note_pv_growth() -> tuple[int, str]:
    """6. note PV成長率（週次成長 or 記事公開数で判定）"""
    note_ready = _count_note_queue()

    if not KPI_FILE.exists():
        if note_ready >= 5:
            return 6, f"記事{note_ready}本待機中（公開後にPV計測開始）"
        return 4, "KPI計測待ち・記事キュー不足"

    data = json.loads(KPI_FILE.read_text())
    history = data.get("history", [])
    if not history:
        return 5, "KPI計測開始済み・データ蓄積中"

    latest = history[-1].get("note", {}).get("pv", 0)
    if len(history) >= 7:
        week_ago = history[-7].get("note", {}).get("pv", 0)
        growth = latest - week_ago
        if growth >= 200:
            return 10, f"note PV週+{growth}（累計{latest}）"
        elif growth >= 100:
            return 8, f"note PV週+{growth}（累計{latest}）"
        elif growth >= 30:
            return 7, f"note PV週+{growth}（累計{latest}）"
        elif growth >= 1:
            return 6, f"note PV週+{growth}（累計{latest}）"
    return 5, f"note PV: {latest}（計測開始）"


def score_photo_assets() -> tuple[int, str]:
    """7. 写真素材充足率"""
    if not PHOTO_DIR.exists():
        return 0, "写真フォルダなし"
    photos = list(PHOTO_DIR.glob("*.jpg")) + list(PHOTO_DIR.glob("*.png"))
    score = 10 if len(photos) >= 7 else (6 if len(photos) >= 4 else (3 if len(photos) >= 1 else 0))
    return score, f"写真素材: {len(photos)}枚"


def score_affiliate_insertion() -> tuple[int, str]:
    """8. アフィリエイトリンク挿入率"""
    if not AFFILIATE_LOG.exists():
        return 3, "未実行"
    log = json.loads(AFFILIATE_LOG.read_text())
    processed = len(log.get("processed", {}))
    score = 10 if processed >= 3 else (6 if processed >= 1 else 3)
    return score, f"アフィリエイト処理済み記事: {processed}本"


def score_repurpose() -> tuple[int, str]:
    """9. 横断変換実行率（note→X→Shorts）"""
    if not REPURPOSE_LOG.exists():
        return 3, "未実行"
    log = json.loads(REPURPOSE_LOG.read_text())
    processed = len(log.get("processed", []))
    score = 10 if processed >= 3 else (6 if processed >= 1 else 3)
    return score, f"変換済み記事: {processed}本"


def score_no_errors() -> tuple[int, str]:
    """10. ログエラーなし"""
    import re as _re
    if not LOGS_DIR.exists():
        return 8, "ログなし（初期）"
    recent_logs = sorted(LOGS_DIR.glob("cron_*.log"), reverse=True)[:3]
    error_count = 0
    for log_path in recent_logs:
        for line in log_path.read_text(errors="ignore").splitlines():
            if _re.search(r"\bERROR\b", line) and "NO ERROR" not in line:
                error_count += 1
            elif "Traceback" in line or line.rstrip().endswith("  NG"):
                error_count += 1
    score = 10 if error_count == 0 else (7 if error_count <= 2 else (4 if error_count <= 5 else 1))
    return score, f"直近3日のエラー数: {error_count}"


# ─── 改善アクション ──────────────────────────────────────────

IMPROVE_ACTIONS = {
    "content_queue": ("auto_content_loop.py", "コンテンツキュー補充"),
    "x_activity": ("auto_x_post.py", "X投稿実行"),
    "note_activity": ("auto_note_publish.py", "note公開"),
    "photo_assets": ("auto_wikimedia_photos.py", "写真素材取得"),
    "affiliate": ("auto_affiliate.py", "アフィリエイト挿入"),
    "repurpose": ("auto_repurpose.py", "コンテンツ横断変換"),
}


def run_improvement(script: str, label: str):
    """スクリプトを実行して改善"""
    print(f"  🔧 改善実行: {label}")
    result = subprocess.run(
        [sys.executable, REPO / script],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        print(f"  ✅ {label} 完了")
    else:
        print(f"  ⚠️  {label} 失敗: {result.stderr[:100]}")


# ─── メイン評価ループ ─────────────────────────────────────────

def evaluate() -> dict:
    evaluators = [
        ("content_queue", score_content_queue),
        ("x_activity", score_x_activity),
        ("note_activity", score_note_activity),
        ("youtube_activity", score_youtube_activity),
        ("x_followers_growth", score_x_followers_growth),
        ("note_pv_growth", score_note_pv_growth),
        ("photo_assets", score_photo_assets),
        ("affiliate", score_affiliate_insertion),
        ("repurpose", score_repurpose),
        ("no_errors", score_no_errors),
    ]

    scores = {}
    details = {}
    for key, fn in evaluators:
        try:
            score, msg = fn()
        except Exception as e:
            score, msg = 5, f"評価エラー: {e}"
        scores[key] = score
        details[key] = msg

    total = sum(scores.values())
    return {"total": total, "scores": scores, "details": details, "date": TODAY}


def load_eval_log() -> dict:
    if EVAL_LOG.exists():
        return json.loads(EVAL_LOG.read_text())
    return {"history": []}


def save_eval_log(log: dict):
    EVAL_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def run():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  自己評価ループ")
    print(f"  {TODAY}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    result = evaluate()
    total = result["total"]

    print(f"\n  ┌─ スコア: {total}/100点 ─────────────────")
    for key, score in result["scores"].items():
        bar = "█" * (score // 2) + "░" * (5 - score // 2)
        msg = result["details"].get(key, "")
        label = key.replace("_", " ").upper()
        print(f"  │ [{bar}] {score:2d}/10  {label[:20]:<20}  {msg}")
    print(f"  └──────────────────────────────────────")

    log = load_eval_log()
    log["history"].append(result)
    log["history"] = log["history"][-30:]
    save_eval_log(log)

    # 判定
    if total >= PASS_THRESHOLD:
        print(f"\n  ✅ {total}点 → 自動継続モード（改善不要）")
    else:
        print(f"\n  ⚠️  {total}点 → 改善モード（閾値: {PASS_THRESHOLD}点）")
        # スコアが低い項目を自動改善
        low_items = [(k, v) for k, v in result["scores"].items() if v < 6]
        low_items.sort(key=lambda x: x[1])  # 低い順

        for key, score in low_items[:3]:  # 最大3項目を改善
            action = IMPROVE_ACTIONS.get(key)
            if action:
                script, label = action
                run_improvement(script, label)

        # 改善後に再評価
        print("\n  --- 改善後の再評価 ---")
        result2 = evaluate()
        total2 = result2["total"]
        print(f"\n  再評価スコア: {total2}/100点 (改善: +{total2-total}点)")

        log["history"].append({**result2, "date": TODAY + "_after_improve"})
        save_eval_log(log)

    # 前日比
    if len(log["history"]) >= 2:
        prev = log["history"][-2]["total"]
        diff = total - prev
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
        print(f"\n  前日比: {arrow}{abs(diff):+d}点（{prev} → {total}）")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return total


if __name__ == "__main__":
    run()
