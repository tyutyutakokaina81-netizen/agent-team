/* AIツール アフィリリンク共有スクリプト。LINKS にURLを入れたものだけCTAが有効化。
   空なら何も出ない(壊れない・冪等)。owner/workerが各プログラム登録後にURLを投入。 */
(function(){
  var LINKS = {
    // program-key: "affiliate-url"（登録後に投入）
    jasper:"", copyai:"", writesonic:"", pictory:"", speechify:"", elevenlabs:"",
    tubebuddy:"", getresponse:"", koala:"", semrush:"", hostinger:"", nordvpn:"",
    surfshark:"", hubspot:"", notionai:"", descript:"", murf:"", synthesia:"", grammarly:"", perplexity:""
  };
  // data-aff="jasper" を持つ要素の href を差し込む。未設定は非表示。
  document.querySelectorAll('[data-aff]').forEach(function(el){
    var u = LINKS[el.getAttribute('data-aff')];
    if(u){ el.setAttribute('href',u); el.setAttribute('rel','sponsored nofollow noopener'); el.style.display=''; }
    else { el.style.display='none'; }
  });
})();
