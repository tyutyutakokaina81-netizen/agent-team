#!/usr/bin/env python3
"""Render an animated aurora video synced to the song's dynamics, mux with
aurora.wav via ffmpeg -> aurora.mp4.  (float32 + cheap falloff for speed)"""
import numpy as np, subprocess, wave, os, glob, sys
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

BASE = "/tmp/claude-0/-home-user-agent-team/af0ffba2-d9ce-5973-bf9d-744a93585c07/scratchpad"
WAV = f"{BASE}/aurora.wav"; OUT = f"{BASE}/aurora_fullhd.mp4"
W,H,FPS = 1920,1080,24

BPM=76.0; barLen=60.0/BPM*4; beat_v=barLen/4
SECTS=[(.12,4,"Intro"),(.40,4,"Build I"),(.66,4,"Build II"),
       (1.0,8,"Climax"),(.28,4,"Outro")]
bar_int=[]
for intn,nb,tag in SECTS:
    bar_int += [intn]*nb
nbars=len(bar_int); song_end=nbars*barLen

with wave.open(WAV) as w: dur=w.getnframes()/w.getframerate()
NF=int(dur*FPS); times=np.arange(NF)/FPS

fint=np.zeros(NF)
for i,t in enumerate(times):
    if t<song_end: fint[i]=bar_int[min(int(t//barLen),nbars-1)]
    else: fint[i]=0.28*max(0.0,1-(t-song_end)/(dur-song_end+1e-9))
ker=np.exp(-np.linspace(-2,2,21)**2); ker/=ker.sum()
fint=np.convolve(fint,ker,mode="same").astype(np.float32)
prog=np.clip(times/dur,0,1).astype(np.float32)

# static sky
yy1=np.linspace(0,1,H)
c_top=np.array([5,9,18.]); c_mid=np.array([7,19,34.]); c_bot=np.array([10,28,36.])
col=np.zeros((H,3)); m=yy1<0.6
col[m]=c_top+(c_mid-c_top)*(yy1[m]/0.6)[:,None]
col[~m]=c_mid+(c_bot-c_mid)*((yy1[~m]-0.6)/0.4)[:,None]
sky=np.repeat(col[:,None,:],W,axis=1).astype(np.float32)

rng=np.random.default_rng(3)
sx=rng.integers(0,W,90); sy=rng.integers(0,int(H*0.62),90)
sph=rng.uniform(0,6,90).astype(np.float32);
sx1=np.clip(sx+1,0,W-1); sy1=np.clip(sy+1,0,H-1)

Xg=(np.arange(W)[None,:]/W).astype(np.float32)
SPREAD=105.0; WIN=int(SPREAD*3.6)   # rows to compute around each band
bands=[]
for baseY,c in [(0.30,[111,227,199]),(0.40,[104,214,230]),(0.50,[169,156,240])]:
    cy=int(baseY*H); y0=max(0,cy-WIN); y1=min(H,cy+WIN)
    Ysub=np.arange(y0,y1)[:,None].astype(np.float32)
    bands.append((baseY,np.array(c,np.float32),y0,y1,Ysub))
Yg=np.arange(H)[:,None].astype(np.float32)
horizon=(Yg/H>0.6).astype(np.float32)
hgrad=np.clip((Yg/H-0.6)/0.4,0,1).astype(np.float32)
hmix=(hgrad*horizon).astype(np.float32)
teal=np.array([111,227,199],np.float32)

def find_font(sz):
    cands=glob.glob("/usr/share/fonts/**/*.ttf",recursive=True)+\
          glob.glob("/usr/local/lib/python3.11/dist-packages/**/*.ttf",recursive=True)
    pref=[p for p in cands if "dejavu" in p.lower()]
    for p in (pref+cands):
        try: return ImageFont.truetype(p,sz)
        except: pass
    return ImageFont.load_default()

ov=Image.new("RGBA",(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
f_t=find_font(112); f_s=find_font(44); f_sm=find_font(30)
def ctext(y,txt,font,fill):
    bb=od.textbbox((0,0),txt,font=font); tw=bb[2]-bb[0]
    od.text(((W-tw)//2,y),txt,font=font,fill=fill)
ctext(96,"Aurora, Slowly",f_t,(238,247,246,235))
ctext(236,"an acoustic post-rock piece",f_s,(180,200,205,205))
ctext(H-74,"ehon-style  ·  guitar / pad / glocken / falsetto",f_sm,(150,175,180,185))
ova=np.asarray(ov).astype(np.float32)
ov_rgb=ova[:,:,:3]; ov_a=ova[:,:,3:4]/255.0

FF=imageio_ffmpeg.get_ffmpeg_exe()
cmd=[FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
     "-i","pipe:0","-i",WAV,"-c:v","libx264","-pix_fmt","yuv420p",
     "-preset","veryfast","-crf","22","-c:a","aac","-b:a","192k","-shortest",OUT]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

for i in range(NF):
    t=float(times[i]); inten=float(fint[i]); p=float(prog[i])
    frame=sky.copy()
    # stars (vectorized)
    b=((0.4+0.5*np.sin(t*1.4+sph))*0.6+0.15)*220
    frame[sy,sx,:]+=b[:,None]; frame[sy,sx1,:]+=b[:,None]*0.5; frame[sy1,sx,:]+=b[:,None]*0.5
    # beat pulse (drums drive the aurora) — only where the kit plays
    bp=(t % barLen)/beat_v            # 0..4 within bar
    kicks=[0.0,2.0,4.0]+([2.5] if inten>0.9 else [])
    dmin=min(abs(bp-k) for k in kicks)*beat_v
    strength=0.55 if inten>0.9 else (0.32 if inten>0.5 else 0.0)
    pulse=np.exp(-dmin*15.0)*strength
    # aurora bands (cheap rational falloff, no exp), computed only in a window
    amp=0.05+0.55*inten+pulse*0.28
    for baseY,c,y0,y1,Ysub in bands:
        curve=baseY*H + np.sin(Xg*6.0+t*0.5)*26*inten + np.sin(Xg*13.0-t*0.8)*12*inten
        d=(Ysub-curve)/SPREAD
        ridge=1.0/(1.0+d*d); ridge*=ridge
        frame[y0:y1]+=ridge[:,:,None]*c*amp
    # horizon glow
    frame+=hmix[:,:,None]*teal*((0.10+0.5*p)*0.5)
    # title overlay + progress line
    frame=frame*(1-ov_a)+ov_rgb*ov_a
    px=int(p*W); frame[H-7:H-3,:px]+=teal*0.7
    np.clip(frame,0,255,out=frame)
    proc.stdin.write(frame.astype(np.uint8).tobytes())
    if i%200==0: sys.stderr.write(f"frame {i}/{NF}\n"); sys.stderr.flush()

proc.stdin.close(); proc.wait()
print("WROTE",OUT,"frames",NF,"size",os.path.getsize(OUT))
