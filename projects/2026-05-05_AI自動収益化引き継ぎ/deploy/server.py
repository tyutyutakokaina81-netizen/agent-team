"""ai-auto iPhone 連携用ミニ HTTP サーバー（Python 標準ライブラリのみ）。

エンドポイント:
    GET  /health                  → {"ok": true, "dry_run": ...}
    GET  /kpi                     → KPI 集計を JSON で返す
    GET  /outputs                 → outputs/ の最新ファイル一覧（最大50件）
    GET  /outputs/<filename>      → 指定ファイルの本文（text/plain）
    GET  /schedule                → 当日の schedule.json
    POST /publish                 → published.csv に1行追記
                                    JSON body: {"kind":"note","url":"...","title":"...","revenue":0}
    POST /dry-run                 → DRY_RUN を切り替え（.env の DRY_RUN を更新）
                                    JSON body: {"value":"0"} or {"value":"1"}

認証: 環境変数 AI_AUTO_TOKEN を設定し、リクエストに ?token=xxx か Authorization: Bearer xxx を付ける。
未設定時は 127.0.0.1 からのみ受け付け（外部アクセス不可）。

起動: python3 server.py [--port 8765] [--bind 127.0.0.1]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import published

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"
SCHEDULE = BASE / "schedule.json"
ENV = BASE / ".env"

OUTPUTS_LIMIT = 50


def _token() -> str | None:
    return os.environ.get("AI_AUTO_TOKEN") or None


def _authorized(handler: BaseHTTPRequestHandler, query: dict) -> bool:
    expected = _token()
    if expected is None:
        return handler.client_address[0] in ("127.0.0.1", "::1")
    if query.get("token", [None])[0] == expected:
        return True
    auth = handler.headers.get("Authorization", "")
    return auth == f"Bearer {expected}"


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_text(handler: BaseHTTPRequestHandler, status: int, text: str,
               content_type: str = "text/plain; charset=utf-8") -> None:
    body = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _kpi_text() -> str:
    result = subprocess.run(
        ["python3", str(BASE / "kpi.py")], capture_output=True, text=True, timeout=10,
    )
    return result.stdout or result.stderr


def _list_outputs() -> list[dict]:
    if not OUT.exists():
        return []
    files = sorted(OUT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {"name": p.name, "size": p.stat().st_size, "mtime": int(p.stat().st_mtime)}
        for p in files[:OUTPUTS_LIMIT] if p.is_file()
    ]


def _read_output(filename: str) -> str | None:
    p = (OUT / filename).resolve()
    if BASE not in p.parents:
        return None
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def _toggle_dry_run(value: str) -> str:
    if value not in ("0", "1"):
        raise ValueError("value は '0' か '1'")
    if not ENV.exists():
        ENV.write_text(f"DRY_RUN={value}\n", encoding="utf-8")
        return f"DRY_RUN={value}（.env を新規作成）"
    lines = ENV.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("DRY_RUN="):
            new_lines.append(f"DRY_RUN={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"DRY_RUN={value}")
    ENV.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return f"DRY_RUN={value}（.env を更新）"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: N802
        pass

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        query = parse_qs(url.query)

        if url.path == "/health":
            _send_json(self, 200, {
                "ok": True,
                "dry_run": os.environ.get("DRY_RUN", "1"),
                "auth": "token" if _token() else "loopback-only",
            })
            return

        if not _authorized(self, query):
            _send_json(self, 401, {"error": "unauthorized"})
            return

        if url.path == "/kpi":
            _send_text(self, 200, _kpi_text())
            return

        if url.path == "/outputs":
            _send_json(self, 200, _list_outputs())
            return

        if url.path.startswith("/outputs/"):
            name = url.path[len("/outputs/"):]
            text = _read_output(name)
            if text is None:
                _send_json(self, 404, {"error": "not found"})
                return
            _send_text(self, 200, text, "text/markdown; charset=utf-8")
            return

        if url.path == "/schedule":
            if SCHEDULE.exists():
                _send_text(self, 200, SCHEDULE.read_text(encoding="utf-8"),
                           "application/json; charset=utf-8")
            else:
                _send_json(self, 404, {"error": "schedule.json なし"})
            return

        _send_json(self, 404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if not _authorized(self, query):
            _send_json(self, 401, {"error": "unauthorized"})
            return

        body = self._read_body()

        if url.path == "/publish":
            try:
                published.append(
                    body["kind"], body["url"], body["title"], int(body.get("revenue", 0))
                )
                _send_json(self, 200, {"ok": True})
            except (KeyError, ValueError) as e:
                _send_json(self, 400, {"error": str(e)})
            return

        if url.path == "/dry-run":
            try:
                msg = _toggle_dry_run(str(body.get("value", "")))
                _send_json(self, 200, {"ok": True, "message": msg})
            except ValueError as e:
                _send_json(self, 400, {"error": str(e)})
            return

        _send_json(self, 404, {"error": "not found"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--bind", default="127.0.0.1",
                        help="LAN公開なら 0.0.0.0、ローカルのみは 127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    auth = "token認証" if _token() else "loopbackのみ"
    print(f"ai-auto server: http://{args.bind}:{args.port}  ({auth})")
    print(f"endpoints: /health /kpi /outputs /outputs/<name> /schedule  POST /publish /dry-run")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
