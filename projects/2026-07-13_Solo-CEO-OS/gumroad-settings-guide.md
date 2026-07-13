# Gumroad 設定ガイド — Solo CEO OS（写真の画面の設定方法）

送ってもらった商品編集画面の各設定を、この商品に合わせてどう設定すべきか。上から順に。

## 価格（Amount）
- **$19 のままでOK。** デジタル商品の衝動買い価格として妥当。
- **「Allow customers to pay what they want」＝ ON にするのは任意。**
  - ONにすると「$19以上で好きな額」にできる。応援買いで単価が上がることがある一方、
    $19未満に見せられない。**初期は OFF（固定$19）で明快に**、様子を見てから検討でよい。
- **「Allow customers to pay in installments」＝ OFF。** $19の少額商品に分割は不要。
- **「Automatically apply discount code」＝ OFF。** ローンチ時に手動クーポンを配る方が効く。

## バージョン（Versions / Add version）
- **今は追加しなくてよい（v1.0単品でOK）。**
- 将来「無印$19 / Pro$39（記入例つき・追加役職テンプレ同梱）」の2段にしたくなったら、
  ここで version を足す。まずは1本で売って反応を見る。

## 設定（Settings）
- **「Limit product sales」＝ OFF。** デジタルなので在庫制限は不要。
  （※「ローンチ100本限定」みたいな演出をやる時だけON）
- **「Allow customers to choose a quantity」＝ OFF。** 個人利用ライセンスを1つ売る商品なので、
  数量選択はむしろ混乱のもと。
- **「Publicly show the number of sales」**
  - 販売数が少ないうち＝**OFF**（0や1が見えると逆効果）。
  - 数字が伸びてきたら**ON**にして社会的証明に使う。

## そのほか、写真に写っていないが必ずやること
1. **Content（納品物）**：`product/` フォルダを **ZIP**にして商品ファイルとしてアップロード。
   - ZIP名の例：`Solo-CEO-OS-v1.0.zip`
2. **Cover（サムネ）**：販売ページ文中の「サムネ方針」を参照（組織図デザイン）。
3. **Description（説明文）**：`sales/gumroad_page_EN.md` の本文を貼る（海外向け）。
   日本語で売るなら `gumroad_page_JA.md`。
4. **Product name / URL**：`Solo CEO OS — Run your business like a company, with AI executives`
5. **Receipt / Content 内メッセージ**：購入後に「まず README → QUICKSTART の順で」と一言添える。

## 公開前チェック（3点）
- [ ] ZIPを解凍して中身が壊れていないか、自分で一度開く
- [ ] 説明文の価格表記（$19）と実際の設定価格が一致しているか
- [ ] 個人情報・高岡関連・実事業データがZIPに混入していないか（**汎用版のみ**であること）
