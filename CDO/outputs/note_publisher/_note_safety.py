"""公開系ツールの共通安全弁。

2026-09-24 の事故を受けて新設した。

**何が起きたか**：`set_magazine.py` が `nc7a3522ade60`（氷見牛2本目）に
`投稿する` を押し、**7月に意図して下書きへ戻した重複記事を再公開した**。
A5（重複公開）の再発で、2026-07-04 のインシデントと同じ型。

**なぜ起きたか**（2つ重なっている）:
  1. 台帳 `published_registry.json` は「非公開に戻した記事」も公開済みのまま持つ。
     台帳から作った作業リストに、実体が下書きの記事が混ざる。
  2. ボタン押下が `("更新する", "投稿する", "公開する")` の順で
     **最初に見えたものを押す**実装だった。下書きの編集画面には `更新する` が無く
     `投稿する` があるので、後付け作業のつもりで公開してしまう。

**どう塞いだか**：
  - 押すのは `更新する` だけ（= 既に公開済みの記事の保存ボタン）。
  - `更新する` が無くて `投稿する`/`公開する` しか無いときは **押さずに止める**。
    公開は後戻りできないので fail-closed にする（黙って公開するより止まる方が安い）。
  - `DO_NOT_TOUCH`（非公開に戻した／削除した記事の ID）は開く前に弾く。
"""

from __future__ import annotations

from pathlib import Path

# 台帳や作業リストに残っていても**触ってはいけない** note ID。
# 下書きに戻した重複記事・削除済み記事。ログの実測値から起こした。
DO_NOT_TOUCH: dict[str, str] = {
    "nc7a3522ade60": "氷見牛2本目=重複。2026-07-08 に下書き化（09-24 に誤って再公開＝要再取り下げ）",
    "n0443f87ce4df": "氷見牛1本目=下書き。ライブは nccce1e10499a",
    "n710f16d5c152": "じゃがいも重複=2026-08 に下書き化。ライブは nca13899b62c5",
    "n826dc4bd09ea": "「夏だけ朝」重複=下書き化済み",
    "n6c719e5bd23d": "バタバタ茶の残骸下書き。ライブは n92090a60679c",
    "n257fa3872add": "EN有料¥100の重複下書き（price300 の誤設定つき）",
    "nea8b690cde14": "削除済み",
}

SAVE_LABEL = "更新する"          # 公開済み記事を保存するボタン。これだけ押す
PUBLISH_LABELS = ("投稿する", "公開する")   # 下書きを公開するボタン。押さない


def _registry_unpublished() -> dict[str, str]:
    """台帳側の印（`"unpublished": true`）も読む。

    ここを見ておくと、**今後わたし以外が作ったツール**が台帳から作業リストを作っても、
    下書きへ戻した記事を開かずに済む。台帳が読めなければ静かに諦める（安全弁の本体は
    DO_NOT_TOUCH 側なので、台帳の不調でツールを止めない）。
    """
    import json
    import re
    out: dict[str, str] = {}
    reg = Path(__file__).resolve().parent / "published_registry.json"
    try:
        for e in json.loads(reg.read_text(encoding="utf-8")):
            if not e.get("unpublished"):
                continue
            m = re.search(r"(n[0-9a-f]{12,13})", e.get("url", "") or "")
            if m:
                out[m.group(1)] = e.get("unpublished_note") or "台帳で非公開と記録されている"
    except Exception:
        pass
    return out


def blocked_reason(nid: str) -> str:
    """触ってはいけない ID なら理由を返す。問題なければ空文字。"""
    return DO_NOT_TOUCH.get(nid) or _registry_unpublished().get(nid, "")


def save_published(page, nid: str, publish_url_tmpl: str) -> str:
    """公開済み記事の編集内容を保存する。**下書きは公開しない。**

    戻り値:
      "UPDATED:更新する"      保存できた
      "SKIP_DRAFT:..."        下書きらしいので何もしなかった（呼び出し側は done にしない）
      "UPDATE_FAIL:..."       ボタンが見つからない等
    """
    if "/publish" not in page.url:
        try:
            page.goto(publish_url_tmpl.format(nid=nid), wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)
        except Exception as e:
            return f"UPDATE_FAIL:/publish/へ行けない {str(e)[:80]}"

    # 描画が遅れているだけの可能性があるので、更新するを数回に分けて待つ
    for _ in range(6):
        try:
            btn = page.locator(f'button:has-text("{SAVE_LABEL}")').last
            if btn.is_visible(timeout=1500):
                btn.click()
                page.wait_for_timeout(4000)
                return f"UPDATED:{SAVE_LABEL}"
        except Exception:
            pass
        page.wait_for_timeout(1000)

    # ここに来た＝更新するが最後まで出なかった。投稿するがあるなら下書き。
    for label in PUBLISH_LABELS:
        try:
            if page.locator(f'button:has-text("{label}")').last.is_visible(timeout=1000):
                return (
                    f"SKIP_DRAFT:「{SAVE_LABEL}」が無く「{label}」だけがある"
                    "＝この記事は下書き。意図しない公開を避けるため押していない"
                )
        except Exception:
            continue

    return f"UPDATE_FAIL:「{SAVE_LABEL}」が見つからない"
