# AIを「インターン」から「会社」に変えたら、ひとり事業が回り出した

ひとりで事業をやっていると、肩書きが日替わりどころか分単位で変わる。午前中はコピーを書くマーケ担当、昼は価格で悩む経理、夕方は問い合わせに返す営業。全部を自分ひとりで、全部中途半端に、一日中やっている。

AIに頼ればいい、と誰もが言う。私もそう思って、毎日ChatGPTやClaudeに話しかけていた。でも返ってくるのは、賢いけれど昨日のことを何も覚えていない何でも屋だった。今日また事業の前提を説明し直す。また同じトーンのブレた文章が出てくる。便利なのに、なぜか散らかったままだった。

原因は途中で気づいた。**AIに「担当」と「記憶」が無かった**のだ。

---

## 組織図を一枚、渡してみた

やったことはシンプルだ。AIに向かって「手伝って」と言うのをやめて、**会社の組織図を渡した**。

CEOは私。その下に6人の幹部を置いた。

- **CMO** — 集客と共感の担当。数字より「人の心が動くか」で書く
- **CPO** — 商品担当。「受講者がゴールに着けるか」だけを見る
- **CFO** — 財務担当。価格と数字を絶対に曖昧にしない
- **CSO** — 営業担当。反論に、信頼を壊さずに応える
- **CDO** — 技術担当。面倒を自動化し、必要なら新しい役職を「採用」する
- **CAO** — 分析担当。「先月なぜ伸びたか」を言葉にする

面白いのは、この6人が**わざと意見を食い違わせる**ことだ。CMOが強気の価格をつけると、CFOが「その根拠は？」と突っ込む。CMOが盛った表現を、CPOが「これは削ろう」と切る。

ひとりで考えていると、都合のいい結論に一直線に走ってしまう。役職を分けると、その途中に「待った」がかかる。**摩擦こそが狙い**だった。本物の経営会議で起きているのは、たぶんこれと同じことだ。最後に決めるのは、いつも私だけれど。

---

## 効いたのは「記憶ファイル」だった

役職分けよりも効果が大きかったのは、地味な工夫のほうだった。

`STATE.md` という一枚のテキストファイルを作り、AIがセッションの最初に必ずそれを読むようにした。事業の中身、いま進めている案件、決めたこと、次にやること。全部そこに書いてある。

これで、**二度と事業を説明し直さなくてよくなった**。

昨日の決定が今日に引き継がれる。「価格は¥980ではなく¥490にした、参入障壁を下げるため」——そういう判断の理由まで残る。ツールをまたいでも、日をまたいでも、会社としての記憶が途切れない。

派手さは無い。でも、ひとり事業でいちばん消耗するのは「毎回ゼロから説明すること」だと、この一枚が教えてくれた。

---

## 仕組みごと、渡せる形にした

しばらく自分の事業で回してみて、これは自分だけの工夫にしておくにはもったいないと思った。

そこで、**役職の定義・共通ルール・記憶ファイルの雛形**を一式にまとめて、ClaudeやChatGPTのフォルダに入れるだけで動く形にした。名前は **Solo CEO OS**。コードは要らない。セットアップは30分。中身は全部、私が実際に毎日使っているものの、個人情報を抜いた汎用版だ。

「ひとりのカオス」を、「ひとりの会社」に変えるためのOS。もし今、私が数か月前と同じように散らかっているなら、いちばん欲しかったのはこれだと思う。

商品ページはこちら（¥2,000相当・買い切り）：{LINK}

---

### English summary

I run a business alone, and for months my AI assistant was a brilliant amnesiac — helpful every day, but starting from zero every day. The fix turned out to be organizational, not technical: I gave the AI an org chart of six executives (marketing, product, finance, sales, ops, analytics), each with its own lane and a mandate to disagree with the others, plus a single memory file it reads at the start of every session. The disagreement surfaces trade-offs I used to skip; the memory means I never re-explain my business. I packaged the whole setup — roles, shared rules, memory template — as **Solo CEO OS**, a drop-in folder for Claude or ChatGPT. No code, 30-minute setup. It won't run your business for you. It gives your one-person business the structure of a company so you run it far better.

---

### 事実検証ノート（公開前にオーナーが確認）
- ✅ 確実：本文の体験（役職分け・STATE.md運用・摩擦の効用）は自分の運用に基づく一次記述。
- ⚠️ 要確認：`{LINK}` は Gumroad 出品後の実URLに差し替える。価格表記（¥2,000相当）は公開時のレート／設定価格に合わせる。
- ⚠️ 要確認：価格例「¥980→¥490」は説明用の一般例。実際の自社価格を書く場合は事実に合わせる。
- 諸説あり：「本物の経営会議で起きているのはこれと同じ」は比喩・私見。断定を避けた表現にしてある。
- 注意：個人特定情報（地区名・実売上額など）は記載していない（PII方針遵守）。
