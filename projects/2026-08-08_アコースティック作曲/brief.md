# 2026-08-08 アコースティック作曲（ehon風ポストロック）

**採用理由**: オーナー依頼「アコースティックギターで作曲して、ききたい／ehonってバンドも調べて」。
音楽制作＋バンド調査＋動画出力の複合タスクのため projects/ に切り出し（担当: CDO寄り、単発）。

## 成果物

| パス | 内容 |
|---|---|
| `output/aurora_fullhd.mp4` | **完成版**「Aurora, Slowly」フルHD 1920×1080/24fps/80秒。アコースティック主体（エレキなし）＋後半のみドラム&ベースの軽いドライブ |
| `player/aurora-slowly.html` | ブラウザ再生プレイヤー（Web Audioでギター合成・歌詞/コード表示・オーロラ演出） |
| `player/yoake-no-ehon.html` | 初稿「よあけの絵本」（やさしいフォーク版。ehon特定前の作） |
| `src/synth.py` | 音声合成（numpy: Karplus-Strongギター/pad/グロッケン/ファルセット/ドラム/ベース＋畳み込みリバーブ→WAV） |
| `src/video.py` | 映像生成（numpy+Pillow→ffmpegパイプ: オーロラが曲の静→動に連動、キックで脈打つ） |

再生成手順: `pip install numpy pillow imageio-ffmpeg` → `python3 src/synth.py` → `python3 src/video.py`
（スクリプト内の BASE パスを作業ディレクトリに合わせること）

## 曲「Aurora, Slowly」

- Key D / 4/4 / ♩=76、構成 Intro → Build I/II → Climax → Outro（静→動）
- コード: D–A–Bm7–Gmaj7 基調、Climax は Bm7–G–D–A
- レイヤー: アコギ16分アルペジオ／アンビエントpad／グロッケン／ファルセット（Climaxのみ）／深いリバーブ
- オーナー修正履歴: ①「若干ロック感」→ドラム/ベース/歪みエレキ追加 → ②「エレキがじゃま、アコースティック」→エレキ削除 → ③「ギターが強い」→ギター約-4dB・pad/歌を前に出すミックスで確定

## ehon 調査結果（事実）

- **ehon = 石川県金沢の4人組ポストロックバンド**（2013年結成）。“日本のSigur Rós”と評される。
  北欧的サウンドスケープ＋UK的叙情。ピアノ/グロッケン/オルガン/ストリングス/ブラスを使用。
- 自主制作「**In Youth EP**」（品番 EHON-1）: You Are My Sunshine / Caged Bird / Loose Hill / Pretext / Sleeping Child
- 販売: [Amazon.co.jp](https://www.amazon.co.jp/Youth-EP-ehon/dp/B00I8VEUVS) /
  [HMV](https://www.hmv.co.jp/artist_ehon_000000000555360/item_In-Youth-EP_5676872) /
  [オリコン](https://www.oricon.co.jp/prof/606320/products/1066577/1/) / 金沢のレコード店（Lykkelig 等）
- 本曲は ehon の音楽性に寄せた**オリジナル**（既存曲・歌詞は不使用）
- メモ: 金沢＝北陸。North Star（高岡・氷見・富山）圏の隣接で「北陸の地元バンド紹介」記事ネタに転用可能
