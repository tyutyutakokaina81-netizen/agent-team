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

def score_content_queue() -> tuple[int, str]:
    """1. コンテンツキュー充足率"""
    note_ok = False
    x_ok = False

    if NOTE_QUEUE.exists():
        state = json.loads(NOTE_QUEUE.read_text())
        from auto_note_publish import ARTICLE_QUEUE
        published = state.get("published", {})
        remaining = sum(1 for a in ARTICLE_QUEUE if a["id"] not in published)
        note_ok = remaining >= 3

    x_remaining = 0
    if X_QUEUE.exists():
        q = json.loads(X_QUEUE.read_text())
        x_remaining = sum(1 for v in q.values() if not v.get("posted"))
    if X_EXTRA.exists():
        extras = json.loads(X_EXTRA.read_text())
        x_remaining += sum(1 for p in extras if not p.get("posted"))
    x_ok = x_remaining >= 5

    score = (5 if note_ok else 0) + (5 if x_ok else 0)
    msg = f"noteキュー={'OK' if note_ok else 'NG'}, Xキュー={x_remaining}本({'OK' if x_ok else 'NG'})"
    return score, msg


def score_x_activity() -> tuple[int, str]:
    """2. X投稿実行率（今日投稿しているか）"""
    if not X_QUEUE.exists():
        return 0, "Xキュー未作成"
    q = json.loads(X_QUEUE.read_text())
    posted_today = [v for v in q.values() if v.get("posted_at", "").startswith(TODAY)]
    score = 10 if posted_today else 3
    return score, f"今日の投稿: {len(posted_today)}本"


def score_note_activity() -> tuple[int, str]:
    """3. note公開実行率（今日公開しているか）"""
    if not NOTE_QUEUE.exists():
        return 5, "未計測（初日は5点）"
    state = json.loads(NOTE_QUEUE.read_text())
    published = state.get("published", {})
    today_pub = [info for info in published.values() if info.get("published_at", "").startswith(TODAY)]
    score = 10 if today_pub else 3
    return score, f"今日の公開: {len(today_pub)}本"


def score_youtube_activity() -> tuple[int, str]:
    """4. YouTube/Shorts生成率（今週2回）"""
    if not LOGS_DIR.exists():
        return 5, "ログフォルダなし"
    today_dt = datetime.now()
    week_start = TODAY[:8] + "0" * 2  # 簡易的な週判定
    logs = sorted(LOGS_DIR.glob("daily_auto_*.log"), reverse=True)[:7]
    youtube_runs = 0
    for log_path in logs:
        content = log_path.read_text(errors="ignore")
        if "YouTubeShorts生成" in content and "✅" in content:
            youtube_runs += 1
    score = 10 if youtube_runs >= 2 else (6 if youtube_runs >= 1 else 2)
    return score, f"今週のYouTube生成: {youtube_runs}回"


def score_x_followers_growth() -> tuple[int, str]:
    """5. Xフォロワー成長率"""
    if not KPI_FILE.exists():
        return 5, "KPIデータなし（初期値5点）"
    data = json.loads(KPI_FILE.read_text())
    history = data.get("history", [])
    if not history:
        return 5, "KPI未計測"
    latest = history[-1].get("x", {}).get("followers", 0)
    target = 100  # Month1目標
    pct = min(100, int(latest / max(target, 1) * 100))
    score = max(1, pct // 10)
    return score, f"Xフォロワー: {latest}/{target} ({pct}%)"


def score_note_pv_growth() -> tuple[int, str]:
    """6. note PV成長率"""
    if not KPI_FILE.exists():
        return 5, "KPIデータなし"
    data = json.loads(KPI_FILE.read_text())
    history = data.get("history", [])
    if not history:
        return 5, "KPI未計測"
    latest = history[-1].get("note", {}).get("pv", 0)
    target = 500
    pct = min(100, int(latest / max(target, 1) * 100))
    score = max(1, pct // 10)
    return score, f"note PV: {latest}/{target} ({pct}%)"


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
    if not LOGS_DIR.exists():
        return 8, "ログなし（初期）"
    recent_logs = sorted(LOGS_DIR.glob("daily_auto_*.log"), reverse=True)[:3]
    error_count = 0
    for log_path in recent_logs:
        content = log_path.read_text(errors="ignore")
        error_count += content.count("⚠️  ") + content.count("ERROR") + content.count("Traceback")
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
