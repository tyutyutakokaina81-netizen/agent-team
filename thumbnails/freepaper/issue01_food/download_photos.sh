#!/bin/bash
# フリーペーパー食特集 写真ダウンロードスクリプト
# 出典: Wikimedia Commons (CC BY-SA)
# 実行方法: bash ~/agent-team/thumbnails/freepaper/issue01_food/download_photos.sh

set -e
DEST="$(dirname "$0")"
echo "保存先: $DEST"

download() {
  local filename="$1"
  local url="$2"
  if [ -f "$DEST/$filename" ]; then
    echo "✅ 既存: $filename"
  else
    echo "⬇️  取得中: $filename"
    curl -L -o "$DEST/$filename" "$url" --progress-bar
    echo "✅ 完了: $filename"
  fi
}

# 表紙
download "cover_seafood.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Grilled_sea_food_%285040774703%29.jpg/960px-Grilled_sea_food_%285040774703%29.jpg"

# [写真1] 白えび代替 (Acetes japonicus from Japan)
download "photo01_shiraebi.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Acetes_japonicus_01_bottle_from_Japan.JPG/960px-Acetes_japonicus_01_bottle_from_Japan.JPG"

# [写真2] ノドグロ (Doederleinia berycoides)
download "photo02_nodoguro.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Doederleinia_berycoides_in_the_market_1.jpg/960px-Doederleinia_berycoides_in_the_market_1.jpg"

# [写真3] ホタルイカ酢味噌 ← 既取得済み
download "photo03_hotaruika.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Boiled_firefly_squids%2C_with_vinegared_miso.jpg/960px-Boiled_firefly_squids%2C_with_vinegared_miso.jpg"

# [写真4] フクラギ照り焼き代替 (焼き鯖)
download "photo04_fukuragi.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/7/7a/Baked_Mackereel.jpg"

# [写真5] 紅ずわいがに
download "photo05_kani.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Food_%2831639964480%29.jpg/960px-Food_%2831639964480%29.jpg"

# [写真6] バイ貝 ← 既取得済み (thumbnails/baigai.jpg より)

# [写真7] 昆布じめ
download "photo07_kobujime.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Kobu_Jime_%28Sashimi_Marinated_on_Kombu_Seaweed%29_%285094935513%29.jpg/960px-Kobu_Jime_%28Sashimi_Marinated_on_Kombu_Seaweed%29_%285094935513%29.jpg"

# [写真8] へしこ
download "photo08_heshiko.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Heshiko_2024-03_ac_%281%29.jpg/960px-Heshiko_2024-03_ac_%281%29.jpg"

# [写真9] いかの黒造り代替 (焼きいか)
download "photo09_squid.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/20240503_Grilled_Squid_Restaurant_MeGusto_anagoria.jpg/960px-20240503_Grilled_Squid_Restaurant_MeGusto_anagoria.jpg"

# [写真10] かぶら寿司 ← 既取得済み (thumbnails/kaburazushi.jpg より)

# [写真11] 干物代替 (日本の魚)
download "photo11_himono.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Japanese_butterfish.jpg/960px-Japanese_butterfish.jpg"

# [写真12] 塩蔵わかめ ← 既取得済み (thumbnails/wakame.jpg より)

# [写真13] 昆布
download "photo13_kombu.jpg" \
  "https://upload.wikimedia.org/wikipedia/commons/9/99/Dried_Kombu.jpg"

echo ""
echo "=== 完了 ==="
ls -la "$DEST"/*.jpg | awk '{print $5, $9}'
