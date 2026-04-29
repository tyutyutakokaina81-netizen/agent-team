#!/usr/bin/env python3
"""
auto_youtube_produce.py — 架空女子アナウンサーによる富山観光YouTube動画を自動生成

パイプライン:
  1. 台本 → セリフ分割
  2. VOICEVOX（無料）で音声生成
  3. 背景画像 + アナウンサー画像をFFmpegで合成
  4. 字幕テロップをFFmpegで焼き込み
  5. 最終MP4を出力

前提:
  brew install ffmpeg
  VOICEVOXアプリを起動しておく（http://localhost:50021）
  pip install requests pillow
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# ── 設定 ──────────────────────────────────────────────
REPO = Path(__file__).parent
OUTPUT_DIR = REPO / "CMO" / "outputs" / "youtube_videos"
ASSET_DIR = REPO / "CMO" / "assets" / "announcer"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)

VOICEVOX_URL = "http://localhost:50021"
SPEAKER_ID = 8          # 春日部つむぎ=8 / 四国めたん=2 / ずんだもん=3
ANNOUNCER_IMG = ASSET_DIR / "ai_takaoka_main.png"  # キャラ立ち絵
SLIDE_DURATION = 5      # 1枚の画像の表示秒数（音声長に合わせて自動調整）
VIDEO_SIZE = "1280x720" # YouTube HD

# ── 台本データ（シーン分割）──────────────────────────────
SCRIPTS = [
    {
        "scene": "オープニング",
        "bg": "takaoka_overview.jpg",
        "text": "みなさん、こんにちは！富山・高岡市観光ガイドへようこそ。私は高岡ナビゲーターのアイです。今日は、まだ世界が知らない「本物の日本」をご案内します！",
    },
    {
        "scene": "瑞龍寺",
        "bg": "zuiryuji.jpg",
        "text": "最初にご紹介するのは、国宝・瑞龍寺。江戸時代初期に建てられた禅宗のお寺で、山門・仏殿・法堂が国宝に指定されています。春夏秋冬、季節のライトアップも絶景ですよ。",
    },
    {
        "scene": "高岡大仏",
        "bg": "daibutsu.jpg",
        "text": "次は、高岡大仏！奈良・鎌倉と並ぶ日本三大仏のひとつです。しかも入場無料！さらに台座の中に入れるんです。回廊には仏画も飾られていて、見どころたっぷりです。",
    },
    {
        "scene": "金屋町",
        "bg": "kanayamachi.jpg",
        "text": "続いては金屋町。400年前から続く鋳物の町です。石畳の路地に千本格子の家並みが続いて、まるでタイムスリップしたような気分になれます。工房では職人さんの仕事も見学できますよ。",
    },
    {
        "scene": "グルメ",
        "bg": "takaoka_food.jpg",
        "text": "お腹が空いたら、高岡コロッケ！市内40店舗で買えて、1個100円くらい。歩きながら食べるのが地元流です。それから氷見うどん、1751年から続く手延べうどんも絶品です！",
    },
    {
        "scene": "アクセス・締め",
        "bg": "shinkansen.jpg",
        "text": "東京から北陸新幹線で約2時間、金沢からは30分で行けます。人混みが少なくて、本物の日本をゆっくり楽しめる高岡市。ぜひ、次の旅先に選んでみてください！チャンネル登録もよろしくお願いします！",
    },
]


# ── VOICEVOX 音声生成 ──────────────────────────────────
def check_voicevox():
    try:
        r = requests.get(f"{VOICEVOX_URL}/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def text_to_speech(text: str, speaker: int, output_path: Path) -> bool:
    try:
        # 音声クエリ生成
        r = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": speaker},
            timeout=30,
        )
        r.raise_for_status()
        query = r.json()

        # 話速・音程調整
        query["speedScale"] = 1.1
        query["pitchScale"] = 0.02
        query["intonationScale"] = 1.2

        # 音声合成
        r2 = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker},
            json=query,
            timeout=60,
        )
        r2.raise_for_status()
        output_path.write_bytes(r2.content)
        return True
    except Exception as e:
        print(f"  ⚠️ VOICEVOX エラー: {e}")
        return False


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return SLIDE_DURATION


# ── 背景画像生成（プレースホルダー）──────────────────────────
def create_placeholder_bg(scene_name: str, output_path: Path, size="1280x720"):
    """背景画像がない場合のプレースホルダーをFFmpegで生成"""
    w, h = size.split("x")
    colors = {
        "オープニング": "0x1a3a5c",
        "瑞龍寺": "0x2d4a1e",
        "高岡大仏": "0x4a3520",
        "金屋町": "0x3d2a1a",
        "グルメ": "0x4a1e35",
        "アクセス・締め": "0x1a2a4a",
    }
    color = colors.get(scene_name, "0x1a1a2e")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={color}:size={w}x{h}:rate=1",
        "-vframes", "1", str(output_path)
    ], capture_output=True)


def create_title_overlay(scene_name: str, output_path: Path, bg_path: Path, size="1280x720"):
    """シーン名テキストを背景に焼き込む"""
    subprocess.run([
        "ffmpeg", "-y", "-i", str(bg_path),
        "-vf", (
            f"drawtext=text='{scene_name}':fontsize=60:fontcolor=white:bold=1:"
            f"x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        str(output_path)
    ], capture_output=True)


# ── テロップ付き動画クリップ生成 ──────────────────────────
def create_clip(scene: dict, audio_path: Path, bg_path: Path,
                output_path: Path, duration: float):
    # 字幕（20文字折り返し）
    words = scene["text"]
    lines = [words[i:i+20] for i in range(0, len(words), 20)]
    subtitle = "\n".join(lines[:3])
    subtitle_safe = subtitle.replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")

    # キャラクター画像がある場合はオーバーレイ合成
    if ANNOUNCER_IMG.exists():
        # 入力: 背景 + キャラ画像 + 音声
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg_path),
            "-loop", "1", "-i", str(ANNOUNCER_IMG),
            "-i", str(audio_path),
            "-filter_complex", (
                "[0:v]scale=1280:720[bg];"
                "[1:v]scale=400:-1[char];"
                "[bg][char]overlay=820:220[v1];"
                f"[v1]drawtext=text='{subtitle_safe}':"
                f"fontsize=34:fontcolor=white:borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=h-120:line_spacing=12[vout]"
            ),
            "-map", "[vout]", "-map", "2:a",
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(output_path),
        ]
    else:
        # キャラ画像なし（背景+字幕のみ）
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-vf", (
                f"scale=1280:720,"
                f"drawtext=text='{subtitle_safe}':"
                f"fontsize=34:fontcolor=white:borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=h-120:line_spacing=12"
            ),
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(output_path),
        ]
    subprocess.run(cmd, capture_output=True)


# ── クリップ結合 ──────────────────────────────────────
def concat_clips(clip_paths: list, output_path: Path):
    list_file = output_path.parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p}'" for p in clip_paths), encoding="utf-8"
    )
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy", str(output_path),
    ], capture_output=True)
    list_file.unlink(missing_ok=True)


# ── メイン ──────────────────────────────────────────
def produce(title: str = "高岡市観光ガイド"):
    timestamp = time.strftime("%Y%m%d_%H%M")
    out_dir = OUTPUT_DIR / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  YouTube動画生成: {title}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # VOICEVOX 確認
    use_voicevox = check_voicevox()
    if not use_voicevox:
        print("⚠️  VOICEVOXが起動していません。サイレント動画を生成します。")
        print("   起動: VOICEVOXアプリを開いてから再実行してください")
        print("   ダウンロード: https://voicevox.hiroshiba.jp/")

    clip_paths = []

    for i, scene in enumerate(SCRIPTS, 1):
        print(f"\n[{i}/{len(SCRIPTS)}] {scene['scene']}")

        # 背景画像（実素材があれば使用、なければプレースホルダー）
        bg_src = ASSET_DIR / scene["bg"]
        bg_work = out_dir / f"bg_{i:02d}.jpg"
        if bg_src.exists():
            import shutil
            shutil.copy(bg_src, bg_work)
        else:
            create_placeholder_bg(scene["scene"], bg_work)
            print(f"  📷 プレースホルダー背景生成（実写真: {ASSET_DIR / scene['bg']}）")

        # 音声生成
        audio_path = out_dir / f"audio_{i:02d}.wav"
        duration = SLIDE_DURATION

        if use_voicevox:
            ok = text_to_speech(scene["text"], SPEAKER_ID, audio_path)
            if ok:
                duration = get_audio_duration(audio_path) + 0.5
                print(f"  🎙️  音声生成完了 ({duration:.1f}秒)")
            else:
                use_voicevox = False

        if not use_voicevox:
            # サイレント音声（無音）
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", str(duration), "-c:a", "aac", str(audio_path)
            ], capture_output=True)

        # 動画クリップ生成
        clip_path = out_dir / f"clip_{i:02d}.mp4"
        create_clip(scene, audio_path, bg_work, clip_path, duration)
        clip_paths.append(clip_path)
        print(f"  🎬 クリップ生成完了")

    # 全クリップ結合
    final_path = OUTPUT_DIR / f"{timestamp}_{title}.mp4"
    print(f"\n結合中...")
    concat_clips(clip_paths, final_path)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ✅ 完成: {final_path}")
    print(f"  サイズ: {final_path.stat().st_size // 1024}KB" if final_path.exists() else "  ❌ 生成失敗")
    print(f"\n  次: YouTube Studioにアップロード")
    print(f"  https://studio.youtube.com/")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return final_path


if __name__ == "__main__":
    produce()
