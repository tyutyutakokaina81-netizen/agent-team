#!/usr/bin/env python3
# VOICEVOX engine (localhost:50021) で全台本をキャラ別に合成し、
# シーンごとの音声ファイル + duration manifest を出力する。
import json, os, time, urllib.request, urllib.parse, wave, contextlib

HOST = "http://127.0.0.1:50021"
OUT  = "/tmp/vv/audio"
os.makedirs(OUT, exist_ok=True)

# style_id 一覧（VOICEVOX標準）
V = {
    "narr":   {"id": 13, "speed": 1.0,  "pitch": 0.0},   # 青山龍星 ノーマル（語り）
    "haru":   {"id": 12, "speed": 1.07, "pitch": 0.0},   # 白上虎太郎 ふつう（少年勇者）
    "mira":   {"id": 16, "speed": 0.96, "pitch": 0.0},   # 九州そら ノーマル（賢者）
    "chibi":  {"id": 1,  "speed": 1.12, "pitch": 0.0},   # ずんだもん あまあま（年下）
    "purun":  {"id": 0,  "speed": 1.15, "pitch": 0.03},  # 四国めたん あまあま
    "nemu":   {"id": 84, "speed": 0.85, "pitch": -0.03}, # 青山龍星 しっとり（眠い魔物）
    "minna":  {"id": 8,  "speed": 1.05, "pitch": 0.0},   # 春日部つむぎ（みんな）
}

# (scene, character, text)  ※字幕にも使う
LINES = [
    ("OP",  "narr",  "朝の光が、村をやさしく照らしています。"),
    ("OP",  "narr",  "青き勇者ハルの、ぼうけん。"),
    ("1",   "narr",  "ここは、あさひの村。きょうは、大事な日です。"),
    ("1",   "mira",  "ハル。この兜は、勇者のあかし。村を、たのみますよ。"),
    ("1",   "haru",  "うん！ ぼく、勇者になる！"),
    ("1",   "narr",  "村の、えがおのかけらが、三つ、消えてしまいました。"),
    ("1",   "haru",  "みんなのえがお、ぼくが取りもどす。いってきます！"),
    ("2",   "narr",  "こうして、勇者の旅が、はじまりました。"),
    ("2",   "chibi", "わー！ あ、勇者さま？ ぼくも、つれてって！"),
    ("2",   "haru",  "いいよ。いっしょに、さがそう。"),
    ("2",   "chibi", "モンスターだ！ 気をつけて！"),
    ("2",   "purun", "ぷるん！"),
    ("2",   "narr",  "スライムのぷるんは、わるい子ではありませんでした。なかまになりました。"),
    ("2",   "minna", "えい、えい、おー！"),
    ("3",   "narr",  "ひとつめのかけらは、まよいの森の、おくにありました。"),
    ("3",   "chibi", "あれ？ また、ここ。"),
    ("3",   "purun", "ぷ、る、るん！"),
    ("3",   "narr",  "ぷるんの光が、道を、てらします。"),
    ("3",   "haru",  "あっ、あった！ ひとつめのかけらだ！"),
    ("3",   "narr",  "森に、えがおが、もどりました。"),
    ("4",   "narr",  "ふたつめは、だれもが、ねむってしまう城に、ありました。"),
    ("4",   "chibi", "みんな、ねてる。"),
    ("4",   "haru",  "ねちゃダメだ。チビ、ぷるん、しっかり！"),
    ("4",   "nemu",  "ふぁあ。だれだい、こんなに、うるさいのは。"),
    ("4",   "haru",  "かけらは、まくらの下。でも、とったら、ネムリンは、ひとりぼっち。"),
    ("4",   "haru",  "ねえ、ネムリン。ねるより、あそぼうよ！"),
    ("5",   "nemu",  "あそぶ。わたしは、ずっと、ひとりだったのに。"),
    ("5",   "minna", "えがお、えがお、あつまれ。みんなで、わらおう。"),
    ("5",   "nemu",  "たのしい。こんなの、はじめてだ。"),
    ("5",   "nemu",  "これは、きみたちの、えがおだろう。ふたつとも、もっておいき。"),
    ("5",   "narr",  "えがおのかけらが、三つ、そろいました。兜が、まばゆく光ります。"),
    ("ED",  "narr",  "勇者は、村へ、かえります。ネムリンも、いっしょに。"),
    ("ED",  "mira",  "おかえりなさい、勇者ハル。"),
    ("ED",  "haru",  "ぼうけんのあとの、おやつは、さいこう！"),
    ("ED",  "haru",  "ママ、行こう！"),
    ("ED",  "narr",  "また、あした。あたらしいぼうけんが、はじまります。おしまい。"),
]

def post(path, params=None, data=None):
    url = HOST + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=60).read()

def wait_engine():
    for _ in range(60):
        try:
            urllib.request.urlopen(HOST + "/version", timeout=3).read()
            return True
        except Exception:
            time.sleep(1)
    return False

def wav_dur(p):
    with contextlib.closing(wave.open(p, "rb")) as w:
        return w.getnframes() / w.getframerate()

def main():
    assert wait_engine(), "engine not up"
    manifest = []
    for i, (scene, ch, text) in enumerate(LINES):
        cfg = V[ch]
        q = json.loads(post("/audio_query", {"text": text, "speaker": cfg["id"]}))
        q["speedScale"] = cfg["speed"]
        q["pitchScale"] = cfg["pitch"]
        q["prePhonemeLength"] = 0.12
        q["postPhonemeLength"] = 0.45
        wav = post("/synthesis", {"speaker": cfg["id"]},
                   data=json.dumps(q).encode("utf-8"))
        fn = f"{i:02d}_{scene}_{ch}.wav"
        with open(os.path.join(OUT, fn), "wb") as f:
            f.write(wav)
        d = wav_dur(os.path.join(OUT, fn))
        manifest.append({"i": i, "scene": scene, "ch": ch, "text": text,
                         "file": fn, "dur": round(d, 3)})
        print(f"{fn}  {d:.2f}s  {text[:18]}", flush=True)
    json.dump(manifest, open("/tmp/vv/manifest.json", "w"),
              ensure_ascii=False, indent=1)
    print("TOTAL speech", round(sum(m["dur"] for m in manifest), 1), "s")

if __name__ == "__main__":
    main()
