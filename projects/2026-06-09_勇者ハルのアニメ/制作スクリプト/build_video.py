#!/usr/bin/env python3
# 写真3枚をアニメ調フィルタ加工 + ドラクエ風UI + チップチューンBGM + VOICEVOXアフレコ。
import json, os, wave, subprocess, glob
import numpy as np
from PIL import (Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops)
import imageio_ffmpeg

W, H, FPS = 1280, 720, 24
AUD = "/tmp/vv/audio"
MAN = json.load(open("/tmp/vv/manifest.json"))
OUT = "/home/user/agent-team/projects/2026-06-09_勇者ハルのアニメ/勇者ハルのぼうけん.mp4"
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"

up = sorted(glob.glob("/root/.claude/uploads/e9e1e32f-0213-5782-861c-60b6f918b109/*.jpeg"))
byname = lambda s: next(p for p in up if s in p)

# ---- アニメ調フィルタ（セルシェード風）----
def animeize(img):
    # 1) 強めの平滑化で“セル塗り”の面を作る（縮小→メディアン→拡大）
    small = img.resize((img.width//2, img.height//2), Image.LANCZOS)
    for _ in range(3):
        small = small.filter(ImageFilter.MedianFilter(5))
    sm = small.resize(img.size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.4))
    # 2) 色数を絞ってポスタライズ＋彩度UP
    post = sm.quantize(colors=12, method=Image.FASTOCTREE, dither=Image.Dither.NONE).convert("RGB")
    post = ImageEnhance.Color(post).enhance(1.8)
    post = ImageEnhance.Contrast(post).enhance(1.15)
    post = ImageEnhance.Brightness(post).enhance(1.05)
    # 3) 太く濃い輪郭線
    g = img.convert("L").filter(ImageFilter.GaussianBlur(0.8))
    edge = g.filter(ImageFilter.FIND_EDGES)
    line = edge.point(lambda p: 0 if p > 26 else 255)
    line = line.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MinFilter(3))
    line3 = Image.merge("RGB", (line, line, line))
    return ImageChops.multiply(post, line3)

ANIME = "/tmp/vv/anime"  # AnimeGANv2で変換済みのアニメ絵を使用
photos = {"profile": Image.open(f"{ANIME}/IMG_0851.png").convert("RGB"),
          "back":    Image.open(f"{ANIME}/IMG_0853.png").convert("RGB"),
          "front":   Image.open(f"{ANIME}/IMG_0852.png").convert("RGB")}

PIC = {0:"front",1:"profile",2:"front",3:"profile",4:"front",5:"profile",6:"back",
       7:"back",8:"front",9:"front",10:"profile",11:"front",12:"profile",13:"front",
       14:"profile",15:"profile",16:"front",17:"profile",18:"front",19:"front",
       20:"profile",21:"profile",22:"front",23:"profile",24:"profile",25:"front",
       26:"profile",27:"front",28:"profile",29:"profile",30:"front",
       31:"back",32:"profile",33:"front",34:"back",35:"back"}

def make_bg(img):
    s = max(W/img.width, H/img.height)
    r = img.resize((int(img.width*s), int(img.height*s)), Image.LANCZOS)
    x=(r.width-W)//2; y=(r.height-H)//2
    r = r.crop((x,y,x+W,y+H)).filter(ImageFilter.GaussianBlur(30))
    return Image.eval(r, lambda p: int(p*0.5))
BG = {k: make_bg(v) for k,v in photos.items()}
FGW = 540
FG = {k: v.resize((int(v.width*(H/v.height)), H), Image.LANCZOS) for k,v in photos.items()}

vig = Image.new("L",(W,H),0); vd=ImageDraw.Draw(vig)
for i in range(60):
    vd.rectangle([i*W//120,i*H//120,W-i*W//120,H-i*H//120], outline=int(110*(i/60)**2))
vig = vig.filter(ImageFilter.GaussianBlur(40))
VIG = Image.merge("RGBA",(Image.new("L",(W,H),0),)*3+(vig,))

font_sub   = ImageFont.truetype(FONT, 38)
font_name  = ImageFont.truetype(FONT, 26)
font_title = ImageFont.truetype(FONT, 76)
font_tsub  = ImageFont.truetype(FONT, 32)
CHNAME = {"narr":"", "haru":"ハル","mira":"ミラ先生","chibi":"チビ",
          "purun":"ぷるん","nemu":"ネムリン","minna":"みんな"}

def wrap(d, text, font, maxw):
    out, cur = [], ""
    for c in text:
        if d.textlength(cur+c, font=font) > maxw and cur:
            out.append(cur); cur=c
        else: cur+=c
    if cur: out.append(cur)
    return out

def ctext(d, cx, y, s, font, fill=(255,255,255), sw=4, stroke=(0,0,0)):
    w=d.textlength(s,font=font); d.text((cx-w/2,y),s,font=font,fill=fill,stroke_width=sw,stroke_fill=stroke)

BLUE=(16,28,124); WHITE=(248,248,248)
def dq_window(frame, x,y,w,h):
    d=ImageDraw.Draw(frame,"RGBA")
    d.rounded_rectangle([x,y,x+w,y+h], radius=16, fill=WHITE)
    d.rounded_rectangle([x+5,y+5,x+w-5,y+h-5], radius=12, fill=BLUE)
    d.rounded_rectangle([x+9,y+9,x+w-9,y+h-9], radius=9, outline=WHITE, width=3)

def render_frame(pic, t, text, speaker, title=None):
    z = 1.0 + 0.10*t
    fg = FG[pic]; rh=int(H*z); rw=int(fg.width*z)
    r = fg.resize((rw,rh), Image.LANCZOS)
    panx=int((rw-FGW)/2); pany=max(0,min(rh-H,int((rh-H)/2+(t-0.5)*18)))
    r = r.crop((panx,pany,panx+FGW,pany+H))
    frame = BG[pic].copy().convert("RGBA")
    frame.paste(r, ((W-FGW)//2,0))
    frame.alpha_composite(VIG)
    if title:
        dq_window(frame, 150, H//2-110, W-300, 220)
        d=ImageDraw.Draw(frame)
        ctext(d, W/2, H//2-78, title, font_title, fill=(255,236,150), sw=5)
        ctext(d, W/2, H//2+30, "〜 ゆうしゃの ぼうけん 〜", font_tsub, fill=WHITE, sw=3)
    elif text:
        wy=H-176; dq_window(frame, 60, wy, W-120, 150)
        d=ImageDraw.Draw(frame)
        if speaker and CHNAME.get(speaker):
            nx=92
            d.rounded_rectangle([nx,wy-28,nx+(len(CHNAME[speaker])*28+40),wy+14], radius=10, fill=WHITE)
            d.text((nx+20,wy-24), CHNAME[speaker], font=font_name, fill=BLUE)
        lines = wrap(d, text, font_sub, W-220)
        ty = wy+34 if len(lines)>1 else wy+52
        for ln in lines:
            d.text((100,ty), ln, font=font_sub, fill=WHITE, stroke_width=2, stroke_fill=(0,0,40)); ty+=48
    return frame.convert("RGB")

def chip(n,sr):
    sq=lambda f,tt:np.sign(np.sin(2*np.pi*f*tt))
    N={'C4':261.6,'D4':293.7,'E4':329.6,'F4':349.2,'G4':392.0,'A4':440.0,'B4':493.9,
       'C5':523.3,'D5':587.3,'E5':659.3,'G5':784.0,'R':0}
    mel=['E5','G5','A4','C5','D5','E5','G4','C5','F4','A4','G4','E5','D5','C5','D5','R']
    bass=['C4','C4','A4','A4','F4','F4','G4','G4']
    bpm=120; beat=60/bpm; out=np.zeros(n,np.float32); sp=0; i=0
    while sp<n:
        f=N[mel[i%len(mel)]]; ln=int(beat*sr); tt=np.arange(min(ln,n-sp))/sr
        env=np.minimum(1,tt/0.01)*np.exp(-tt*2.2)
        if f>0: out[sp:sp+len(tt)]+=0.10*sq(f,tt)*env
        bf=N[bass[(i//2)%len(bass)]]
        if bf>0: out[sp:sp+len(tt)]+=0.08*sq(bf/2,tt)*np.minimum(1,tt/0.02)*np.exp(-tt*1.4)
        sp+=ln; i+=1
    return out

def main():
    GAP, INTRO, OUTRO = 0.5, 3.8, 4.4
    segs=[("front",None,None,int(INTRO*FPS),"青き勇者ハルのぼうけん",None)]
    for m in MAN:
        segs.append((PIC[m["i"]], m["text"], m["ch"], int(round((m["dur"]+GAP)*FPS)), None, m["file"]))
    segs.append(("back",None,None,int(OUTRO*FPS),"おしまい",None))
    total=sum(s[3] for s in segs)
    print("frames",total,"dur",round(total/FPS,1),"s",flush=True)

    def rd(p):
        with wave.open(p,"rb") as w:
            sr=w.getframerate(); a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
            if w.getnchannels()==2: a=a.reshape(-1,2).mean(1)
        return a,sr
    SR=rd(os.path.join(AUD,MAN[0]["file"]))[1]; spf=SR/FPS
    voice=np.zeros(int(total*spf)+SR, np.float32); pf=0
    for pic,text,sp,nf,title,vf in segs:
        if vf:
            a,_=rd(os.path.join(AUD,vf)); st=int(pf*spf); en=min(st+len(a),len(voice)); voice[st:en]+=a[:en-st]
        pf+=nf
    voice=voice[:int(total*spf)]
    mix = voice + chip(len(voice),SR)
    mix = (mix/(np.max(np.abs(mix)) or 1)*0.95*32767).astype(np.int16)
    with wave.open("/tmp/vv/final_audio.wav","wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mix.tobytes())
    print("audio",round(len(mix)/SR,1),"s",flush=True)

    ff=imageio_ffmpeg.get_ffmpeg_exe()
    cmd=[ff,"-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),
         "-i","-","-i","/tmp/vv/final_audio.wav","-c:v","libx264","-preset","medium","-crf","20",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest",OUT]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    done=0
    for pic,text,sp,nf,title,vf in segs:
        for f in range(nf):
            t=f/max(1,nf-1)
            proc.stdin.write(render_frame(pic,t,text,sp,title=title).tobytes()); done+=1
        print(f"  {done}/{total}",flush=True)
    proc.stdin.close()
    err=proc.stderr.read().decode("utf-8","ignore"); rc=proc.wait()
    print("ffmpeg rc",rc)
    if rc: print(err[-1500:])
    print("OUT",OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING")

if __name__=="__main__":
    main()
