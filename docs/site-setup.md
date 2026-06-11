# 英語SEOサイト 有効化チェックリスト（env 実値設定）

build.py は以下を **GitHub repo Variables** から読む（`Settings → Secrets and variables → Actions → Variables`）。
入れれば機能ON、未設定なら build.py が安全に省略する。値は pages.yml 経由で配線済み。

| Variable | 用途 | 取得 | 状態 |
|---|---|---|---|
| `SITE_BASE_URL` | canonical/OG/内部リンクの基底URL | **Pagesが自動採用**（pages.yml）。独自ドメイン使用時のみ手動上書き | ✅自動 |
| `JALAN_URL` | じゃらんアフィリ(宿) | **build.py 既定で実リンク稼働中**（a8mat=1CCUH0…）。差替時のみ設定 | ✅稼働 |
| `SITE_NAME` | サイト名 | 任意（既定 "Hidden Hokuriku"） | 任意 |
| `KLOOK_URL` | Klookアフィリ(JRパス/体験・海外読者向け) | **要登録**: klook affiliate → 生成リンク | ⬜要アカウント |
| `BOOKING_URL` | Booking.com/Agodaアフィリ(宿・海外) | **要登録**: partner center → 生成リンク | ⬜要アカウント |
| `PAID_GUIDE_URL` | 有料ガイドの購入URL | note有料記事 or Gumroad に出品後のURL | ⬜要出品 |
| `NEWSLETTER_URL` | メール登録 | Substack/Buttondown 作成後のURL | ⬜要アカウント |
| `ANALYTICS_DOMAIN` | アクセス解析(Plausible) | Plausible にサイト追加後のドメイン文字列 | ⬜要アカウント |

## いま有効なもの（口座不要）
- **SITE_BASE_URL（自動）** と **じゃらんアフィリ（既定で稼働）** は設定不要で既に効く。

## オーナーが順に作ると有効化される（推奨順）
1. Plausible 登録 → `ANALYTICS_DOMAIN`（まず計測。無料枠/トライアルあり）
2. Klook affiliate 登録 → `KLOOK_URL`（海外読者の予約=収益の本命）
3. Substack/Buttondown → `NEWSLETTER_URL`（所有リスト化）
4. 有料ガイド出品(note/Gumroad) → `PAID_GUIDE_URL`
5. Booking/Agoda → `BOOKING_URL`

## 設定後
変更を main に push（or Actions の "Deploy English SEO site" を手動実行）すれば反映。
