# autonomous/

自立型AI "Always-On Company" のコア実装ディレクトリ。

5役職AI（CDO/CFO/CMO/CPO/CSO）が日次ループで自律稼働するための土台を置く。

## 設計ドキュメント

- `CDO/outputs/2026-04-11_autonomous_ai_spec.md` — 全体設計仕様書 v0.1
- `projects/2026-04-08_月30万自動化/brief.md` — 2026-04-11 方針転換版プロジェクトブリーフ

## 構成要素（段階的に追加）

| ファイル | 役割 | 状態 |
|---------|------|------|
| `budget_guard.mjs` | Claude API 支出の hard limit 管理（第一防衛線） | **Phase 1: 実装済** |
| `officer_runner.mjs` | 1役職ぶんのターンを実行する関数 | Phase 1: 未着手 |
| `orchestrator.mjs` | 5役職のターンを順に回すメインループ | Phase 2: 未着手 |
| `context_loader.mjs` | context/ と _index.md を読み込んで各役職に渡す | Phase 2: 未着手 |
| `memory.json` | 各役職の短期記憶（直近5ターン要約） | Phase 2: 未着手 |
| `task_queue.json` | 役職間の非同期メッセージング | Phase 2: 未着手 |

## budget_guard.mjs — 使い方

### ステータス確認
```bash
node autonomous/budget_guard.mjs status
```

### 呼び出し前の許可判定
```bash
node autonomous/budget_guard.mjs check 25   # 25円の見積もりで許可されるか
```

### トークン → 円 の見積もり
```bash
node autonomous/budget_guard.mjs simulate 1200 800 claude-haiku-4-5
```

### プログラムからの利用
```javascript
import * as budget from './autonomous/budget_guard.mjs';

// 呼び出し前
const check = await budget.canProceed({ estimate: 25 });
if (!check.allowed) {
  console.error(check.reason);
  process.exit(0); // 正常終了（失敗扱いしない）
}

// Claude API 呼び出し
// ...

// 呼び出し後
await budget.record({
  officer: 'CDO',
  model: 'claude-haiku-4-5-20251001',
  inputTokens: 1200,
  outputTokens: 800,
});
```

## hard limit 一覧

| 階層 | 上限 |
|------|------|
| 1ループあたり | ¥30 |
| 1日あたり | ¥100 |
| 1月あたり | ¥2,000 |

これらは `budget_guard.mjs` の `CONFIG` オブジェクトで集中管理。変更は Git で追跡される。

## 原則

1. **上限超過は失敗ではなく正常終了** — 呼び出し側は exit 0 で終わる
2. **全ての支出は `CFO/research/{daily,monthly}_spend.json` に Git コミット** — 透明性担保
3. **人間の介入は不要** — 暴走しない設計が全責任
