#!/usr/bin/env python3
"""
auto_youtube_shorts.py — 高岡市観光 YouTube Shorts 自動生成

縦型 720x1280 / 60秒以内 / テロップ中央大文字
Shorts はアルゴリズムで外部に推薦→バズの起点
"""

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent
OUTPUT_DIR = REPO / "CMO" / "outputs" / "youtube_videos" / "shorts"
ASSET_DIR = REPO / "CMO" / "assets" / "announcer"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Shorts 台本（フック→本題→CTA の3部構成）──────────────
SHORTS = [
    {
        "id": "s1_daibutsu_free",
        "hook": "日本三大仏\nが無料って\n知ってた？",
        "scenes": [
            {"bg": "0x1a2a4a", "text": "富山県・高岡市\n高岡大仏\n奈良・鎌倉と並ぶ日本三大仏", "sec": 5},
            {"bg": "0x2a1a0a", "text": "鎌倉大仏: ¥300\n奈良大仏: ¥600\n\n高岡大仏: ¥0", "sec": 6},
            {"bg": "0x0a2a1a", "text": "しかも台座の中に入れる\n回廊には仏画\n先代大仏のお顔も", "sec": 5},
            {"bg": "0x1a1a3a", "text": "東京から\n新幹線2時間\nフォロー&チャンネル登録↑", "sec": 4},
        ],
    },
    {
        "id": "s2_kyoto_vs",
        "hook": "京都より\nここに行けば\nよかった",
        "scenes": [
            {"bg": "0x3a1a1a", "text": "京都の有名な禅寺\n拝観料¥1,000\n休日: 行列1時間", "sec": 5},
            {"bg": "0x1a3a1a", "text": "富山・高岡 瑞龍寺\n拝観料¥500\n国宝3棟\n平日: ほぼ貸し切り", "sec": 6},
            {"bg": "0x1a1a3a", "text": "高岡大仏\n日本三大仏\n¥0", "sec": 4},
            {"bg": "0x2a2a1a", "text": "金屋町\n400年続く鋳物の石畳\n入場¥0", "sec": 4},
            {"bg": "0x1a2a3a", "text": "全部ある\nでも誰も来ない\n→ 今がチャンス", "sec": 4},
        ],
    },
    {
        "id": "s3_takaoka_cost",
        "hook": "高岡日帰り\n全額\n¥2,450",
        "scenes": [
            {"bg": "0x1a2a1a", "text": "高岡市 日帰り旅\n全部で¥2,450", "sec": 4},
            {"bg": "0x2a1a2a", "text": "瑞龍寺 ¥500\n高岡大仏 ¥0\n金屋町 ¥0\nコロッケ ¥100×3\n氷見うどん ¥750\n万葉線 ¥800", "sec": 8},
            {"bg": "0x1a1a2a", "text": "国宝+日本三大仏+\n400年の職人街を\n¥2,450 で体験", "sec": 5},
            {"bg": "0x2a2a2a", "text": "#高岡市 #富山観光\n#隠れた名所\nフォロー↑", "sec": 3},
        ],
    },
    {
        "id": "s4_english_hidden",
        "hook": "Japan's\nBEST KEPT\nSECRET",
        "scenes": [
            {"bg": "0x1a2a4a", "text": "Takaoka City\nToyama, Japan\n← Almost no tourists", "sec": 5},
            {"bg": "0x2a3a1a", "text": "National Treasure Temple\n500 yen\n(Kyoto: 1000 yen + crowds)", "sec": 5},
            {"bg": "0x3a2a1a", "text": "One of Japan's\n3 Great Buddhas\nEntry: FREE", "sec": 5},
            {"bg": "0x1a3a3a", "text": "400-year-old\nCopper craft town\nFREE to visit", "sec": 5},
            {"bg": "0x2a1a3a", "text": "2hrs from Tokyo\nby Shinkansen\n#HiddenJapan", "sec": 4},
        ],
    },
    {
        "id": "s5_zuiryuji",
        "hook": "国宝が\n3棟ある\n無名の寺",
        "scenes": [
            {"bg": "0x0a2a0a", "text": "富山県高岡市\n瑞龍寺", "sec": 3},
            {"bg": "0x1a3a1a", "text": "国宝指定:\n山門・仏殿・法堂\n3棟すべて国宝", "sec": 5},
            {"bg": "0x0a1a0a", "text": "江戸時代初期\n1609年建立\n400年以上前の建築", "sec": 5},
            {"bg": "0x1a2a1a", "text": "京都の寺:\n常に混雑\n\n瑞龍寺:\n平日 ほぼ独り占め", "sec": 6},
            {"bg": "0x2a3a2a", "text": "入場¥500\nフォローして\n次の動画も見てね", "sec": 4},
        ],
    },
]

VOICEVOX_URL = "http://localhost:50021"
SPEAKER_ID = 8


def check_voicevox():
    try:
        import requests
        return requests.get(f"{VOICEVOX_URL}/version", timeout=3).status_code == 200
    except Exception:
        return False


def tts_openjtalk(text: str, output_path: Path) -> bool:
    try:
        import pyopenjtalk, numpy as np, wave
        x, sr = pyopenjtalk.tts(text.replace("\n", "。"), speed=1.15, half_tone=3.0)
        with wave.open(str(output_path), "w") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
            f.writeframes((x * 32767).astype(np.int16).tobytes())
        return True
    except Exception:
        return False


def make_vertical_bg(color: str, text: str, out: Path,
                     w=720, h=1280, font_size=52):
    """縦型背景＋テロップをFFmpegで生成"""
    safe = (text.replace("'", "\\'")
                .replace(":", "\\:")
                .replace("%", "\\%")
                .replace("\n", "\n"))
    # 複数行はdrawtextを行ごとに重ねる
    lines = text.split("\n")
    total_h = len(lines) * (font_size + 14)
    start_y = (h - total_h) // 2

    filters = [f"color=c={color}:size={w}x{h}:rate=30[bg]"]
    inputs = ["[bg]"]
    for i, line in enumerate(lines):
        safe_line = line.replace("'", "").replace(":", " ").replace("%", "")
        y = start_y + i * (font_size + 14)
        filters.append(
            f"drawtext=text='{safe_line}':fontsize={font_size}:"
            f"fontcolor=white:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y={y}"
        )

    # シンプルに1コマンドで
    vf_parts = []
    for i, line in enumerate(lines):
        safe_line = line.replace("'", "").replace(":", " ").replace("%", "")
        y = start_y + i * (font_size + 14)
        vf_parts.append(
            f"drawtext=text='{safe_line}':fontsize={font_size}:"
            f"fontcolor=white:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y={y}"
        )

    vf = ",".join(vf_parts) if vf_parts else "null"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:size={w}x{h}:rate=30",
        "-vf", vf,
        "-vframes", "1", str(out)
    ]
    subprocess.run(cmd, capture_output=True)


def make_hook_frame(text: str, out: Path, w=720, h=1280):
    """フックフレーム：黒背景・中央・超大文字（視聴者を止める）"""
    lines = text.split("\n")
    font_size = 90
    total_h = len(lines) * (font_size + 20)
    start_y = (h - total_h) // 2

    vf_parts = []
    for i, line in enumerate(lines):
        safe_line = line.replace("'", "").replace(":", " ").replace("%", "")
        y = start_y + i * (font_size + 20)
        vf_parts.append(
            f"drawtext=text='{safe_line}':fontsize={font_size}:"
            f"fontcolor=yellow:borderw=5:bordercolor=black:"
            f"x=(w-text_w)/2:y={y}"
        )

    vf = ",".join(vf_parts)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x000000:size={w}x{h}:rate=30",
        "-vf", vf, "-vframes", "1", str(out)
    ]
    subprocess.run(cmd, capture_output=True)


def make_clip(bg: Path, audio: Path, duration: float, out: Path):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(bg),
        "-i", str(audio),
        "-vf", "scale=720:1280",
        "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        "-pix_fmt", "yuv420p",
        str(out)
    ]
    subprocess.run(cmd, capture_output=True)


def make_silent_audio(duration: float, out: Path):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", str(duration), "-c:a", "aac", str(out)
    ], capture_output=True)


def concat(clips: list[Path], out: Path):
    lst = out.parent / "concat_list.txt"
    lst.write_text("\n".join(f"file '{c}'" for c in clips))
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(lst), "-c", "copy", str(out)
    ], capture_output=True)
    lst.unlink(missing_ok=True)


def produce_short(short: dict) -> Path:
    sid = short["id"]
    work = OUTPUT_DIR / sid
    work.mkdir(exist_ok=True)

    use_tts = check_voicevox() or True  # openjtalkフォールバック
    clips = []

    # ── フックシーン（3秒・黒背景・黄文字）────────────────
    hook_bg = work / "hook_bg.jpg"
    hook_audio = work / "hook_audio.wav"
    make_hook_frame(short["hook"], hook_bg)
    if not tts_openjtalk(short["hook"].replace("\n", ""), hook_audio):
        make_silent_audio(3.0, hook_audio)
    hook_clip = work / "clip_hook.mp4"
    make_clip(hook_bg, hook_audio, 3.0, hook_clip)
    clips.append(hook_clip)

    # ── 本題シーン ─────────────────────────────────────
    for i, scene in enumerate(short["scenes"]):
        bg = work / f"bg_{i:02d}.jpg"
        audio = work / f"audio_{i:02d}.wav"
        clip = work / f"clip_{i:02d}.mp4"

        make_vertical_bg(scene["bg"], scene["text"], bg)

        tts_text = scene["text"].replace("\n", "。")
        if not tts_openjtalk(tts_text, audio):
            make_silent_audio(float(scene["sec"]), audio)

        # 音声長に合わせて動画長を決定
        import subprocess as sp
        res = sp.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(audio)], capture_output=True, text=True)
        try:
            dur = max(float(res.stdout.strip()), float(scene["sec"]))
        except Exception:
            dur = float(scene["sec"])

        make_clip(bg, audio, dur, clip)
        clips.append(clip)

    # ── 結合 ─────────────────────────────────────────
    out_path = OUTPUT_DIR / f"{sid}.mp4"
    concat(clips, out_path)
    size = out_path.stat().st_size // 1024 if out_path.exists() else 0
    print(f"  ✅ {sid}.mp4 ({size}KB)")
    return out_path


def produce_all():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  YouTube Shorts 生成 (縦型720x1280)")
    print(f"  {len(SHORTS)}本 × バズ狙いフック構成")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    paths = []
    for s in SHORTS:
        print(f"\n[{s['id']}] hook: {s['hook'][:20].replace(chr(10),' ')}")
        p = produce_short(s)
        paths.append(p)
    print(f"\n  完成: {len(paths)}本 → {OUTPUT_DIR}")
    return paths


if __name__ == "__main__":
    produce_all()
