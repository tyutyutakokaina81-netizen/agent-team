# CrowdWorks 応募文テンプレート

## 入力
- 案件タイトル：{job_title}
- ジャンル：{genre_label}
- 提示単価：{rate}
- 納期希望：{deadline}

## 出力
```
はじめまして、{profile_name}と申します。

【対応可能業務】
{genre_label}

【スキル・ツール】
{genre_skills}

【作業スピード目安】
{genre_speed}

【一言】
{genre_pitch}
ご指示内容を正確に確認し、納期厳守で丁寧に作業いたします。
不明点はその都度確認させていただきます。
まずは少量・短期からでも対応可能です。
ご検討のほど、よろしくお願いいたします。
```

## 応募チェック
- [ ] 必須スキル要件と上記スキルが一致している
- [ ] 単価が `CW_MIN_HOURLY` を下回っていない
- [ ] 同一クライアントへの重複応募になっていない
- [ ] 応募後に `logs/posted_{date}_cw_{genre_slug}.log` に記録した
