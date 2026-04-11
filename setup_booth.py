"""
setup_booth.py — BOOTHセッション設定 → 即出品まで一発完了
"""
import json
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "booth_session.json"
SESSION_FILE.parent.mkdir(exist_ok=True)

print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  BOOTH セッション設定")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("\nブラウザのコンソール（F12→Console）で以下を実行してコピー:")
print("  document.cookie.split(';').find(c=>c.includes('_booth_session'))?.split('=').slice(1).join('=')")
print()

cookie = input("値をここに貼り付けてEnter: ").strip()

if not cookie:
    print("❌ 入力がありません")
    exit(1)

SESSION_FILE.write_text(json.dumps({"cookie": cookie}), encoding="utf-8")
print(f"\n✅ セッション保存完了")
print("\n出品を開始します...")

import subprocess, sys
result = subprocess.run(
    [sys.executable, str(Path(__file__).parent / "booth_requests.py"), "--publish"],
    cwd=Path(__file__).parent
)
