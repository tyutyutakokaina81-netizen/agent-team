#!/bin/bash
# ops/use_my_photo.sh — **自分で撮った写真を、その記事の見出し画像にする**（owner の Mac で実行）
#
#   cd ~/agent-team-run && bash ops/use_my_photo.sh ~/Desktop/curry.jpg バスセンターのカレー
#
# 第1引数=写真のパス（Finder からターミナルにドラッグすると入る）／第2引数=記事名の一部
#
# なぜ（2026-10-02）:
#   お取り寄せの記事でサムネが**4巡しても決まらなかった**。原因は、フリー素材に
#   「新潟の黄色いカレー」「静岡の黒いおでん」のような**その土地のその料理**が無いこと。
#   Commons は画像の中身ではなく説明文の文字に一致するので、地名や名産品名で引くと
#   その土地の風景写真が来る（「黒はんぺん」→富士山）。
#   取り寄せた現物が手元にあるなら、**撮るのがいちばん確実で、いちばん正しい**。
#
# やること:
#   ・写真を thumbnails/<記事stem>.jpg に置く
#   ・_verified.txt に登録する（= 自動取得で上書きされなくなる）
#   ・出典を「owner own work」で記録する（= クレジット行が本文に入らない）
#   ・記事に自動取得のクレジット行が残っていたら消す
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
if [ "$#" -lt 2 ]; then
  echo "usage: bash ops/use_my_photo.sh <写真のパス> <記事名の一部>"
  echo "  例: bash ops/use_my_photo.sh ~/Desktop/curry.jpg バスセンターのカレー"
  exit 1
fi
SRC="$1"; KEY="$2"
[ -f "$SRC" ] || { echo "✗ 写真が見つかりません: $SRC"; exit 1; }
git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"

python3 - "$SRC" "$KEY" <<'PYEOF'
import glob, json, os, re, shutil, sys
src, key = sys.argv[1], sys.argv[2]
TH = "CDO/outputs/note_publisher/thumbnails"
hits = [p for p in glob.glob("CMO/outputs/*note記事*.md") if key in os.path.basename(p)]
if not hits:
    print(f"✗ 「{key}」に当たる記事がありません"); sys.exit(1)
if len(hits) > 1:
    print(f"✗ 「{key}」に {len(hits)}本 当たります。もっと絞ってください:")
    for h in hits: print("   ", os.path.basename(h)[:60])
    sys.exit(1)
stem = os.path.basename(hits[0])[:-3]
os.makedirs(TH, exist_ok=True)
dst = os.path.join(TH, stem + ".jpg")
shutil.copyfile(src, dst)
print(f"✅ 置きました: {dst}")

vf = os.path.join(TH, "_verified.txt")
cur = open(vf, encoding="utf-8").read() if os.path.exists(vf) else ""
if stem not in cur:
    with open(vf, "a", encoding="utf-8") as f:
        f.write(stem + "\n")
    print("✅ _verified.txt に登録（自動取得で上書きされません）")

pf = os.path.join(TH, "_provenance.json")
prov = json.load(open(pf, encoding="utf-8")) if os.path.exists(pf) else {}
prov[stem] = {"backend": "owner", "file": os.path.basename(src),
              "license": "owner own work", "author": "owner",
              "note": "オーナーが撮影した実物。クレジット表示は不要"}
json.dump(prov, open(pf, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("✅ 出典を『owner own work』で記録（クレジット行は本文に入りません）")

md = open(hits[0], encoding="utf-8").read()
lines = [l for l in md.split("\n") if "（見出し画像：" not in l]
if len(lines) != len(md.split("\n")):
    open(hits[0], "w", encoding="utf-8").write("\n".join(lines))
    print("✅ 記事に残っていた自動取得のクレジット行を消しました")
print(f"\n記事: {stem}")
PYEOF
RC=$?
[ "$RC" -ne 0 ] && exit "$RC"

python3 CDO/outputs/note_publisher/body_stats.py --sync CMO/outputs/*note記事*.md >/dev/null 2>&1 || true
git add -f CDO/outputs/note_publisher/thumbnails/_verified.txt \
           CDO/outputs/note_publisher/thumbnails/_provenance.json \
           CDO/outputs/note_publisher/thumbnails/*.jpg 2>/dev/null
git add -A
git diff --cached --quiet || {
  git commit -qm "thumb: オーナー撮影の写真を見出し画像に（$(date +%F_%H%M)）"
  for i in 1 2 3; do
    git push -q origin main && { echo "push しました"; break; }
    git pull --rebase -q origin main || true; sleep $((i*2))
  done
}
echo ""
echo "次: bash ops/go.sh で公開キューに入れられます"
