"""
_browser.py — オーナーの普段使い Chrome プロファイルでブラウザを起動

Google 認証を通すために、Playwright バンドル Chromium ではなく
オーナーの実 Chrome プロファイル（cookie・ログイン状態を含む）を直接使用する。

⚠️ 実行前に Chrome を完全終了すること（Chrome のプロファイルロックで起動失敗するため）

OS 別 プロファイルパス：
- macOS:  ~/Library/Application Support/Google/Chrome
- Linux:  ~/.config/google-chrome
- Windows: %LOCALAPPDATA%/Google/Chrome/User Data
"""

import os
import platform
import sys
from pathlib import Path


def _chrome_profile_root() -> Path:
    """OS 別の Chrome User Data フォルダのパス"""
    home = Path.home()
    sysname = platform.system()
    if sysname == "Darwin":  # macOS
        return home / "Library" / "Application Support" / "Google" / "Chrome"
    elif sysname == "Linux":
        return home / ".config" / "google-chrome"
    elif sysname == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "Google" / "Chrome" / "User Data" if local else home
    return home


def _check_chrome_not_running():
    """Chrome が起動中なら警告して中止"""
    try:
        import subprocess
        if platform.system() == "Darwin":
            r = subprocess.run(
                ["pgrep", "-x", "Google Chrome"],
                capture_output=True, text=True, timeout=5,
            )
        else:
            r = subprocess.run(
                ["pgrep", "-f", "google-chrome|chrome.exe"],
                capture_output=True, text=True, timeout=5,
            )
        if r.returncode == 0 and r.stdout.strip():
            print("=" * 60)
            print("⚠️  Chrome が起動中です。完全に終了してから再実行してください。")
            print("   (Chrome を終了 → Cmd+Q または右クリック → 終了)")
            print("=" * 60)
            sys.exit(1)
    except Exception:
        pass  # pgrep が無い環境などはチェックをスキップ


def open_browser(p, profile: str = "Default", headless: bool = False):
    """オーナーの普段使い Chrome プロファイルで永続コンテキストを開く。

    p: sync_playwright() コンテキストマネージャの戻り値
    profile: 使用するプロファイルディレクトリ名（"Default"／"Profile 1"／"Profile 2"...）
    返り値: BrowserContext
    """
    _check_chrome_not_running()

    profile_root = _chrome_profile_root()
    if not profile_root.exists():
        print(f"[ERROR] Chrome User Data フォルダが見つかりません: {profile_root}")
        print("        Chrome を一度起動してから再実行してください")
        sys.exit(1)

    if not (profile_root / profile).exists():
        # Default が無ければ最初に見つけたプロファイルを使う
        candidates = [d.name for d in profile_root.iterdir() if d.is_dir() and (d / "Cookies").exists()]
        if not candidates:
            print(f"[ERROR] 利用可能なプロファイルがありません: {profile_root}")
            sys.exit(1)
        profile = candidates[0]
        print(f"[INFO] Default が無いため '{profile}' を使用します")

    print(f"[ブラウザ] Chrome プロファイル: {profile_root / profile}")

    return p.chromium.launch_persistent_context(
        user_data_dir=str(profile_root),
        channel="chrome",
        headless=headless,
        viewport={"width": 1280, "height": 900},
        slow_mo=80,
        args=[
            f"--profile-directory={profile}",
            "--disable-blink-features=AutomationControlled",
        ],
    )
