/*
 * 海外読者向け収益化（国際アフィリ）共有スクリプト — 全役員合意 2026-06-25。
 *
 * 課題：英語ページの予約導線が「じゃらん(日本語)」だけ＝海外客は成約しにくい。
 * 解決：各英語記事の"意図"に合う海外向けボタン（宿/ツアー/鉄道/eSIM）を文脈別に自動表示。
 *
 * 仕組み：
 *  - 下の LINKS にURLを入れたものだけボタン表示。空なら何も出ない（壊れない・無害・冪等）。
 *  - ページのファイル名から「意図」を判定し、合うボタンだけ出す（スパムにしない＝A5）。
 *
 * ▼ owner が一度だけやる作業（無料・審査あり）：
 *   1. Travelpayouts (travelpayouts.com) に1社登録。これ1つで Booking.com(宿)・Klook/GetYourGuide(ツアー)・
 *      12Go(鉄道)・Airalo(eSIM) などのアフィリリンクがまとめて発行できる（英語・海外送金OK）。
 *   2. 各プログラムの自分のリンクを、下の LINKS の "" に貼る（or code に渡す）→ 全英語ページで一斉有効化。
 *   ※ 国内じゃらん/楽天リンクは各ページに既設のまま（併用）。これは"海外客の上積み"。
 */
(function () {
  // ★ Travelpayouts等で取得した自分のリンクをここに入れると、対応ボタンが全英語ページで有効化 ★
  var LINKS = {
    stay:  "", // 宿・ホテル（Booking.com 等）
    tours: "", // 現地ツアー・体験（Klook / GetYourGuide）
    rail:  "", // 鉄道・ジャパンレールパス（12Go 等）
    esim:  ""  // eSIM・モバイルデータ（Airalo 等）
  };

  var META = {
    stay:  { emoji: "🏨", label: "Find hotels & inns" },
    tours: { emoji: "🎫", label: "Browse tours & activities" },
    rail:  { emoji: "🚅", label: "Japan rail passes & tickets" },
    esim:  { emoji: "📶", label: "Get an eSIM for Japan" }
  };

  // ページの意図 → 出す売り物（ファイル名の一部で判定）
  var INTENT = [
    [/en-access|getting-to|vs-kanazawa/,                 ["rail", "esim", "stay"]],
    [/en-itinerary|days-2-3|how-many-days|when-to-go|spring|summer|winter/, ["stay", "tours", "rail"]],
    [/alpine|kurobe|gokayama|shomyo|daytrip|things-to-do|off-beaten|doraemon|hattori|manga/, ["tours", "stay"]],
    [/onsen|himi|takaoka|toyama-city|amaharashi/,        ["stay", "tours"]],
    // 食・その他 → 控えめに宿だけ
    [/.*/,                                               ["stay"]]
  ];

  function intentsFor(path) {
    for (var i = 0; i < INTENT.length; i++) {
      if (INTENT[i][0].test(path)) return INTENT[i][1];
    }
    return ["stay"];
  }

  function render() {
    var path = (location.pathname || "").toLowerCase();
    var keys = intentsFor(path);
    var btns = [];
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i], url = LINKS[k];
      if (url && META[k]) btns.push({ url: url, m: META[k] });
    }
    if (!btns.length) return; // 何も設定されていなければ表示しない（無害）

    var box = document.createElement("section");
    box.style.cssText = "margin:26px 0 6px;padding:16px 18px;border:1px solid #e0e8e6;border-radius:12px;background:#f3f7f6";
    var h = document.createElement("p");
    h.style.cssText = "font-weight:700;color:#1f6b58;margin:0 0 8px;font-size:16px";
    h.textContent = "Plan your Toyama trip";
    box.appendChild(h);
    for (var j = 0; j < btns.length; j++) {
      var a = document.createElement("a");
      a.href = btns[j].url; a.target = "_blank"; a.rel = "nofollow sponsored noopener";
      a.className = "aff";
      a.textContent = btns[j].m.emoji + " " + btns[j].m.label + " →";
      box.appendChild(a);
    }
    var note = document.createElement("p");
    note.style.cssText = "font-size:12px;color:#5b6a6a;margin:8px 0 0";
    note.textContent = "These are affiliate links. Prices and availability change — please check each site for the latest.";
    box.appendChild(note);

    // 関連リンク(.tag)の直前、無ければ本文末に挿入
    var anchor = document.querySelector("p.tag");
    var tags = document.querySelectorAll("p.tag");
    if (tags.length) tags[tags.length - 1].parentNode.insertBefore(box, tags[tags.length - 1]);
    else document.body.appendChild(box);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
  else render();
})();
