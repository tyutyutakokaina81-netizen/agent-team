/*
 * 到達計測（GA4）共有スクリプト — 「世界に広まったか」を数字で見るための唯一の計器。
 * サイトは多言語SEO・じゃらん/楽天アフィリ・IndexNow まで揃っているが、解析だけが無かった。
 * これを全ページが読み込むことで、訪問者数・国・流入元(検索/SNS)・人気記事が見えるようになる。
 *
 * ▼ owner が一度だけやる作業（約3分・無料）：
 *   1. https://analytics.google.com にログイン →「管理」→「プロパティを作成」
 *   2. 「データストリーム」→「ウェブ」→ URL: https://tyutyutakokaina81-netizen.github.io/agent-team/
 *   3. 表示される「測定ID」(G-で始まる) を、このファイルの GA_ID = "" の "" に貼る（or code に渡す）
 *   → 次のデプロイで全ページの計測が始まる。GA_ID が空のあいだは何もしない（安全）。
 */
(function () {
  var GA_ID = ""; // ★ ここに G-XXXXXXXXXX を入れると全ページで計測開始 ★
  if (!GA_ID) return;
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", GA_ID);
})();
