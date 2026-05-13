/* かいちのAI大学 — デスクトップUI 振る舞い */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);

  const input       = $('#chatInput');
  const sendBtn     = $('#sendBtn');
  const log         = $('#chatLog');
  const speech      = $('#speechBubble');
  const mood        = $('#mood');
  const msgCount    = $('#msgCount');
  const clock       = $('#clock');
  const character   = document.querySelector('.character');
  const clearBtn    = $('#clearBtn');

  let count = 1;

  /* ----------------------------------------------------
     時計：タスクバーの時刻
     ---------------------------------------------------- */
  function updateClock() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    clock.textContent = `${hh}:${mm}`;
  }
  updateClock();
  setInterval(updateClock, 30000);

  /* ----------------------------------------------------
     チャット送受信
     ---------------------------------------------------- */
  function appendMsg(role, body) {
    const wrap = document.createElement('div');
    wrap.className = `chat-msg chat-msg-${role}`;
    const from = document.createElement('div');
    from.className = 'chat-from';
    from.textContent = role === 'bot' ? 'かいち教官' : 'あなた';
    const bod = document.createElement('div');
    bod.className = 'chat-body';
    bod.textContent = body;
    wrap.appendChild(from);
    wrap.appendChild(bod);
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    count++;
    msgCount.textContent = `メッセージ: ${count}`;
  }

  /* 教官のテンプレ応答（オフラインでも遊べる用） */
  const REPLIES = [
    {
      match: /(自己紹介|あなた|誰)/,
      reply: '私はかいち教官。AI実践学部で「月30万円自動化」の講義を担当しています。よろしく。'
    },
    {
      match: /(月30万|30万|稼ぐ|収益)/,
      reply: '柱は3本。①SEOライティング代行（¥15K×20本）②SNS運用代行（¥50K×6社）③テンプレート販売。詳しくはシラバスを開いてみて下さい。'
    },
    {
      match: /(講義|今日|授業|スケジュール)/,
      reply: '今日のテーマは「テンプレート販売Vol.2 SNSコンテンツカレンダー」。配布資料は projects/ にあります。'
    },
    {
      match: /(プロンプト|chatgpt|claude)/i,
      reply: 'プロンプトは CDO/outputs/ に集約しています。team_prompt.txt は4役職での文書作成テンプレです。'
    },
    {
      match: /(料金|価格|いくら)/,
      reply: 'ランニングコストは月¥5,800（Claude Pro ¥3K + Canva ¥1.5K + M365 ¥1.3K）。サービス単価はシラバス参照。'
    },
    {
      match: /(youtube|ユーチューブ|チャンネル)/i,
      reply: '「かいちのAI大学」YouTubeで配信中。台本は CMO/outputs/ に保存しています。'
    },
    {
      match: /(ありがとう|サンクス|thanks?)/i,
      reply: 'こちらこそ。引き続き学んでいきましょう。'
    },
    {
      match: /(こんにちは|やあ|はろー|hi|hello)/i,
      reply: 'こんにちは。今日も講義を始めましょう。'
    }
  ];

  function generateReply(text) {
    for (const r of REPLIES) {
      if (r.match.test(text)) return r.reply;
    }
    return `「${text}」について、ふむ。良い質問です。
これは講義のテーマに加えておきましょう。次回までに資料を用意します。`;
  }

  /* 教官のセリフを話す（口パク） */
  function teacherSay(text) {
    speech.innerHTML = escapeHtml(text).replace(/\n/g, '<br/>');
    mood.textContent = '解説中';
    character && character.classList.add('talking');
    setTimeout(() => {
      character && character.classList.remove('talking');
      mood.textContent = '講義中';
    }, Math.min(2400, 600 + text.length * 60));
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  function send() {
    const text = (input.value || '').trim();
    if (!text) return;
    appendMsg('user', text);
    input.value = '';
    const reply = generateReply(text);
    setTimeout(() => {
      appendMsg('bot', reply);
      teacherSay(reply);
    }, 350);
  }

  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  /* クイック質問ボタン */
  document.querySelectorAll('.quick').forEach((btn) => {
    btn.addEventListener('click', () => {
      input.value = btn.dataset.q || '';
      input.focus();
      send();
    });
  });

  /* クリア */
  clearBtn.addEventListener('click', () => {
    log.innerHTML = '';
    count = 0;
    msgCount.textContent = 'メッセージ: 0';
    appendMsg('bot', '対話ログをクリアしました。新しい話題をどうぞ。');
    teacherSay('対話ログをクリアしました。');
  });

  /* ----------------------------------------------------
     ウィンドウボタン（飾り）
     ---------------------------------------------------- */
  document.querySelectorAll('.tb-btn').forEach((b) => {
    b.addEventListener('click', () => {
      const label = b.getAttribute('aria-label');
      if (label === '閉じる') {
        teacherSay('講義を閉じますか？……このボタンは飾りです。');
      } else if (label === '最大化') {
        document.body.classList.toggle('maximized');
      }
    });
  });

  /* デスクトップアイコン */
  document.querySelectorAll('.desk-icon').forEach((ic) => {
    ic.addEventListener('dblclick', () => {
      const app = ic.dataset.app;
      const messages = {
        chat:     'マイコンピュータを開きました（現在のウィンドウです）。',
        syllabus: 'シラバス：A.SEOライティング代行／B.SNS運用代行／C.テンプレート販売',
        readme:   'README — かいちのAI大学 講義室 ver 0.1.0。Enterで送信、Shift+Enterで改行です。'
      };
      const m = messages[app] || 'このアプリは準備中です。';
      teacherSay(m);
      appendMsg('bot', m);
    });
  });

  /* スタートボタン */
  document.querySelector('.start-btn').addEventListener('click', () => {
    teacherSay('スタートメニュー：File / Edit / View / Help（飾り）。');
  });

  /* 起動時にフォーカス */
  input.focus();
})();
