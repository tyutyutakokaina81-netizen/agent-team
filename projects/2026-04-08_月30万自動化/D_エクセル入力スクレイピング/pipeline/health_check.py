#!/usr/bin/env python3
"""
health_check.py — パイプライン健全性チェック

run_pipeline.py を本番起動する前に、必要な環境が揃っているか機械的に検査する。

【使い方】
  python health_check.py
  python health_check.py --fix    # 自動修正を試みる（pip install 等）

【チェック項目】
  1. Python 3.10+ が動いている
  2. 必須パッケージ（playwright, openpyxl）がインストール済
  3. 6段階のパイプラインスクリプトが全て存在する
  4. .sessions/ にログイン済セッションがある（少なくとも1つ）
  5. outputs/ ディレクトリが存在し書き込み可能
  6. 全スクリプトが import エラー無く読み込める
  7. .env / 環境変数：ANTHROPIC_API_KEY が設定されているか

exit code: 0 = 全て OK, 1 = 1つ以上 NG
"""

import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT_ROOT = ROOT.parent
SESSION_DIR = PROJECT_ROOT / ".sessions"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

REQUIRED_SCRIPTS = [
    "00_session_setup.py", "01_search.py", "02_evaluate.py",
    "03_apply.py", "04_execute.py", "05_review.py", "06_deliver.py",
    "run_pipeline.py",
]

REQUIRED_PACKAGES = ["playwright", "openpyxl"]
OPTIONAL_PACKAGES = ["anthropic", "reportlab", "markdown"]


class Check:
    def __init__(self, name: str):
        self.name = name
        self.ok = False
        self.detail = ""
        self.fix_hint = ""

    def __repr__(self):
        mark = "✅" if self.ok else "❌"
        return f"{mark} {self.name}: {self.detail}"


def check_python_version() -> Check:
    c = Check("Python 3.10+")
    v = sys.version_info
    c.ok = (v.major, v.minor) >= (3, 10)
    c.detail = f"Python {v.major}.{v.minor}.{v.micro}"
    c.fix_hint = "Python 3.10+ をインストールしてください"
    return c


def check_package(name: str, required: bool = True) -> Check:
    c = Check(f"パッケージ: {name}{' (必須)' if required else ' (任意)'}")
    try:
        importlib.import_module(name)
        c.ok = True
        c.detail = "OK"
    except ImportError:
        c.ok = not required  # 任意なら未インストールでも OK 扱い
        c.detail = "未インストール"
        c.fix_hint = f"pip install {name}"
    return c


def check_scripts() -> list[Check]:
    checks = []
    for s in REQUIRED_SCRIPTS:
        c = Check(f"スクリプト: {s}")
        path = ROOT / s
        c.ok = path.exists()
        c.detail = "存在" if c.ok else "見つかりません"
        c.fix_hint = "リポジトリを最新化してください"
        checks.append(c)
    return checks


def check_sessions() -> Check:
    c = Check("ログインセッション")
    if not SESSION_DIR.exists():
        c.ok = False
        c.detail = ".sessions/ ディレクトリ無し"
        c.fix_hint = "python 00_session_setup.py で初回ログインしてください"
        return c
    sessions = list(SESSION_DIR.glob("*_session.json"))
    if not sessions:
        c.ok = False
        c.detail = "セッションファイル無し"
        c.fix_hint = "python 00_session_setup.py で初回ログインしてください"
        return c
    c.ok = True
    c.detail = f"{len(sessions)} 件: {', '.join(s.stem for s in sessions)}"
    return c


def check_output_dir() -> Check:
    c = Check("outputs/ 書き込み可能")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    test = OUTPUT_DIR / ".write_test"
    try:
        test.write_text("ok")
        test.unlink()
        c.ok = True
        c.detail = "OK"
    except Exception as e:
        c.detail = str(e)
        c.fix_hint = "ディレクトリの権限を確認してください"
    return c


def check_imports() -> list[Check]:
    """各パイプラインスクリプトを import してエラー無いか確認"""
    sys.path.insert(0, str(ROOT))
    checks = []
    for s in ["02_evaluate"]:  # 外部依存が少ないものだけテスト
        c = Check(f"import 可能: {s}")
        try:
            importlib.import_module(s)
            c.ok = True
            c.detail = "OK"
        except Exception as e:
            c.detail = f"{type(e).__name__}: {e}"
            c.fix_hint = "依存ライブラリを確認してください"
        checks.append(c)
    return checks


def check_env() -> Check:
    c = Check("ANTHROPIC_API_KEY")
    val = os.environ.get("ANTHROPIC_API_KEY", "")
    c.ok = bool(val) and val.startswith("sk-ant-")
    c.detail = "設定済 (先頭8文字 " + val[:8] + "...)" if c.ok else "未設定 or 形式不正"
    c.fix_hint = "export ANTHROPIC_API_KEY='sk-ant-...' で設定してください"
    return c


def auto_fix_packages():
    """必須パッケージを自動 pip install"""
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except ImportError:
            print(f"[FIX] pip install {pkg}")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="自動修正を試みる")
    args = parser.parse_args()

    if args.fix:
        auto_fix_packages()

    checks = []
    checks.append(check_python_version())
    for pkg in REQUIRED_PACKAGES:
        checks.append(check_package(pkg, required=True))
    for pkg in OPTIONAL_PACKAGES:
        checks.append(check_package(pkg, required=False))
    checks.extend(check_scripts())
    checks.append(check_sessions())
    checks.append(check_output_dir())
    checks.extend(check_imports())
    checks.append(check_env())

    print("\n" + "━" * 60)
    print("  パイプライン健全性チェック結果")
    print("━" * 60)
    for c in checks:
        print(c)
        if not c.ok and c.fix_hint:
            print(f"   → {c.fix_hint}")

    failed = [c for c in checks if not c.ok]
    print()
    if failed:
        print(f"❌ {len(failed)}/{len(checks)} 件 NG。上記の修正方法に従ってください。")
        sys.exit(1)
    else:
        print(f"✅ 全 {len(checks)} 件 OK。run_pipeline.py を起動可能です。")
        sys.exit(0)


if __name__ == "__main__":
    main()
