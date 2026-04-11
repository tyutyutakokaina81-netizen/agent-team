#!/usr/bin/env python3
"""
mac_auto_cookie.py — ChromeのCookieDBから直接BOOTHセッションを自動取得
browser-cookie3 を使用（HttpOnly対応・DevTools不要）
"""
import sys
import json
import subprocess
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "booth_session.json"
SESSION_FILE.parent.mkdir(exist_ok=True)


def install_deps():
    print("📦 パッケージをインストール中...")
    for cmd in [
        [sys.executable, "-m", "pip", "install", "browser-cookie3",
         "requests", "--break-system-packages", "-q"],
        [sys.executable, "-m", "pip", "install", "browser-cookie3",
         "requests", "-q"],
    ]:
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0:
            print("  ✅ インストール完了")
            return
    print("  ⚠️  インストール失敗。pip3 を試みます...")
    subprocess.run(["pip3", "install", "browser-cookie3", "requests", "-q"])


def get_cookies():
    try:
        import browser_cookie3
    except ImportError:
        install_deps()
        try:
            import browser_cookie3
        except ImportError:
            print("❌ browser-cookie3 のインポートに失敗しました")
            return None

    print("🔍 ChromeからBOOTHクッキーを取得中...")
    print("   ※ キーチェーンのアクセス許可ダイアログが出たら「許可」してください")
    print()

    try:
        jar = browser_cookie3.chrome(domain_name='.booth.pm')
        cookies = {c.name: c.value for c in jar}

        if not cookies:
            # Safariも試す
            print("  Chrome: クッキーなし → Safariを試します...")
            jar = browser_cookie3.safari(domain_name='.booth.pm')
            cookies = {c.name: c.value for c in jar}

        if not cookies:
            print("❌ booth.pm のクッキーが見つかりません")
            print()
            print("  対処法: BOOTHにログインしてから再実行してください")
            print("  https://booth.pm → ログイン → このスクリプトを再実行")
            return None

        print(f"  ✅ {len(cookies)}個のクッキーを取得しました")
        for name in list(cookies.keys())[:5]:
            print(f"     {name}: {cookies[name][:30]}...")

        # セッションクッキー文字列を組み立て
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        return cookie_str

    except PermissionError:
        print("❌ Chromeのクッキーファイルへのアクセスが拒否されました")
        print("   Chromeを閉じてから再実行してみてください")
        return None
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  BOOTH クッキー自動取得（Mac版）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    cookie_str = get_cookies()
    if not cookie_str:
        sys.exit(1)

    # 保存
    SESSION_FILE.write_text(
        json.dumps({"cookie": cookie_str}, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n  ✅ セッション保存: {SESSION_FILE}")

    # 出品実行
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  出品を開始します...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "booth_requests.py")],
        cwd=Path(__file__).parent
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
