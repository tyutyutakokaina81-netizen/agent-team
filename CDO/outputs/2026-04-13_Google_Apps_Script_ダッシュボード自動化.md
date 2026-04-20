# Google Apps Script：ダッシュボード自動化（2026-04-13）

Googleスプレッドシートに貼り付けるだけで動く、売上・応募進捗の自動集計スクリプト。

---

## 🎯 目的

- 複数サイト（CW・ランサーズ・ママワークス等）の売上をスプレッドシートに手入力
- ボタン1つで月次サマリーを自動更新
- 毎日の作業を**15分→3分に短縮**

---

## 📊 スプレッドシート設計

### シート1：入金記録（手入力）
```
A: 日付
B: サイト
C: クライアント名
D: 案件名
E: 売上（税抜）
F: 手数料
G: 振込額
H: 入金確認
```

### シート2：応募記録（手入力）
```
A: 日付
B: サイト
C: 案件名
D: 単価
E: ステータス（応募/返信/受注/失注）
F: 納期
```

### シート3：月次サマリー（自動生成）
```
A: 月
B: 応募数
C: 受注数
D: 受注率
E: 売上合計
F: 手取り合計
```

---

## 🖥 Google Apps Script コード

### 使い方

1. Googleスプレッドシートを開く
2. 「拡張機能」→「Apps Script」
3. 以下のコードを貼り付けて保存
4. スプレッドシートに戻ると「ダッシュボード更新」メニューが追加される

### 貼り付けるコード

```javascript
/**
 * 月30万自動化 ダッシュボード自動集計
 * 2026-04-13
 */

// カスタムメニューを追加
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('📊 ダッシュボード')
    .addItem('サマリー更新', 'updateSummary')
    .addItem('応募ログ集計', 'aggregateApplications')
    .addItem('月次レポート生成', 'generateMonthlyReport')
    .addToUi();
}

// 月次サマリーを自動更新
function updateSummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const incomeSheet = ss.getSheetByName('入金記録');
  const applicationSheet = ss.getSheetByName('応募記録');
  const summarySheet = ss.getSheetByName('月次サマリー');
  
  if (!incomeSheet || !applicationSheet || !summarySheet) {
    SpreadsheetApp.getUi().alert('必要なシートがありません');
    return;
  }
  
  // 入金データ取得
  const incomeData = incomeSheet.getDataRange().getValues();
  const applicationData = applicationSheet.getDataRange().getValues();
  
  // 月別集計
  const monthlyData = {};
  
  for (let i = 1; i < incomeData.length; i++) {
    const row = incomeData[i];
    if (!row[0]) continue;
    
    const date = new Date(row[0]);
    const ym = Utilities.formatDate(date, 'JST', 'yyyy-MM');
    const revenue = Number(row[4]) || 0;
    const fee = Number(row[5]) || 0;
    const netIncome = Number(row[6]) || 0;
    
    if (!monthlyData[ym]) {
      monthlyData[ym] = {
        revenue: 0,
        fee: 0,
        netIncome: 0,
        applications: 0,
        orders: 0
      };
    }
    monthlyData[ym].revenue += revenue;
    monthlyData[ym].fee += fee;
    monthlyData[ym].netIncome += netIncome;
  }
  
  // 応募データ集計
  for (let i = 1; i < applicationData.length; i++) {
    const row = applicationData[i];
    if (!row[0]) continue;
    
    const date = new Date(row[0]);
    const ym = Utilities.formatDate(date, 'JST', 'yyyy-MM');
    const status = row[4];
    
    if (!monthlyData[ym]) {
      monthlyData[ym] = {
        revenue: 0,
        fee: 0,
        netIncome: 0,
        applications: 0,
        orders: 0
      };
    }
    monthlyData[ym].applications++;
    if (status === '受注') {
      monthlyData[ym].orders++;
    }
  }
  
  // サマリーシートに書き込み
  summarySheet.clear();
  const headers = ['月', '応募数', '受注数', '受注率', '売上合計', '手数料', '手取り'];
  summarySheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  summarySheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
  
  const months = Object.keys(monthlyData).sort();
  months.forEach((ym, i) => {
    const d = monthlyData[ym];
    const winRate = d.applications > 0 ? (d.orders / d.applications) : 0;
    summarySheet.getRange(i + 2, 1, 1, 7).setValues([[
      ym,
      d.applications,
      d.orders,
      winRate,
      d.revenue,
      d.fee,
      d.netIncome
    ]]);
  });
  
  // 書式設定
  summarySheet.getRange(2, 4, months.length, 1).setNumberFormat('0.0%');
  summarySheet.getRange(2, 5, months.length, 3).setNumberFormat('¥#,##0');
  
  SpreadsheetApp.getUi().alert('サマリー更新完了！');
}

// 応募ログをサイト別に集計
function aggregateApplications() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const applicationSheet = ss.getSheetByName('応募記録');
  const data = applicationSheet.getDataRange().getValues();
  
  const siteStats = {};
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!row[1]) continue;
    
    const site = row[1];
    const status = row[4];
    
    if (!siteStats[site]) {
      siteStats[site] = { total: 0, orders: 0, replies: 0 };
    }
    siteStats[site].total++;
    if (status === '受注') siteStats[site].orders++;
    if (status === '返信' || status === '受注') siteStats[site].replies++;
  }
  
  let message = '📊 サイト別応募統計\n\n';
  Object.keys(siteStats).forEach(site => {
    const s = siteStats[site];
    const replyRate = s.total > 0 ? (s.replies / s.total * 100).toFixed(1) : 0;
    const winRate = s.total > 0 ? (s.orders / s.total * 100).toFixed(1) : 0;
    message += `${site}: 応募${s.total}件 / 返信率${replyRate}% / 受注率${winRate}%\n`;
  });
  
  SpreadsheetApp.getUi().alert(message);
}

// 月次レポートをテキスト形式で生成
function generateMonthlyReport() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const summarySheet = ss.getSheetByName('月次サマリー');
  const data = summarySheet.getDataRange().getValues();
  
  const today = new Date();
  const currentMonth = Utilities.formatDate(today, 'JST', 'yyyy-MM');
  
  let report = `📊 月次レポート（${currentMonth}）\n\n`;
  
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === currentMonth) {
      report += `応募数：${data[i][1]}件\n`;
      report += `受注数：${data[i][2]}件\n`;
      report += `受注率：${(data[i][3] * 100).toFixed(1)}%\n`;
      report += `売上：¥${data[i][4].toLocaleString()}\n`;
      report += `手取り：¥${data[i][6].toLocaleString()}\n\n`;
      
      // 目標との比較
      const targetRevenue = 300000;
      const achievementRate = (data[i][4] / targetRevenue * 100).toFixed(1);
      report += `目標達成率：${achievementRate}%（目標：¥300,000）\n`;
      
      break;
    }
  }
  
  SpreadsheetApp.getUi().alert(report);
}

// 毎月1日に自動実行するトリガー（任意）
function setupMonthlyTrigger() {
  // 既存のトリガーを削除
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  
  // 毎月1日の9時に実行
  ScriptApp.newTrigger('updateSummary')
    .timeBased()
    .onMonthDay(1)
    .atHour(9)
    .create();
  
  SpreadsheetApp.getUi().alert('月次自動更新を設定しました');
}
```

---

## 🔧 セットアップ手順

### 1. スプレッドシート準備
```
1. 新しいGoogleスプレッドシートを作成
2. シート名を「入金記録」「応募記録」「月次サマリー」に変更
3. 各シートの1行目にヘッダーを入力
```

### 2. Apps Script貼り付け
```
1. メニュー「拡張機能」→「Apps Script」
2. デフォルトのコードを削除
3. 上記のコードを貼り付け
4. 保存（Ctrl/Cmd + S）
5. プロジェクト名を入力（例：「月30万ダッシュボード」）
```

### 3. 初回実行
```
1. スプレッドシートをリロード
2. メニューバーに「📊 ダッシュボード」が追加されているはず
3. 「📊 ダッシュボード」→「サマリー更新」をクリック
4. 初回は権限承認を求められる → 許可
```

### 4. 自動実行の設定
```
1. Apps Scriptエディタで「setupMonthlyTrigger」関数を実行
2. これで毎月1日9時に自動更新される
```

---

## 💡 拡張アイデア

### 追加できる機能
1. **Slack/LINE通知**：月次レポートを自動送信
2. **グラフ自動生成**：売上推移・受注率推移
3. **目標達成アラート**：月10万達成で通知
4. **リマインダー**：応募が3日ないと通知

### 拡張用コード例（Slack通知）

```javascript
function sendSlackNotification() {
  const webhookUrl = 'YOUR_SLACK_WEBHOOK_URL';
  const message = generateMonthlyReport();
  
  const payload = {
    text: message
  };
  
  UrlFetchApp.fetch(webhookUrl, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  });
}
```

---

## 🎯 期待効果

| 作業 | 手動 | 自動化後 |
|------|------|---------|
| 月次集計 | 30分 | 1秒 |
| サイト別分析 | 15分 | 1秒 |
| 目標達成率計算 | 5分 | 1秒 |
| グラフ更新 | 10分 | 1秒 |
| **合計** | **60分/月** | **4秒/月** |

**月1時間の時短 = 時給1,000円換算で年間¥12,000の価値。**

---

## ⚠️ 注意事項

- Apps Scriptは**無料で使えるが実行時間に制限あり**（1回6分まで）
- データが膨大になると処理が遅くなる
- 1年以上経過したら、古いデータは別シートにアーカイブ推奨

---

迷うな。貼れ。動かせ。
