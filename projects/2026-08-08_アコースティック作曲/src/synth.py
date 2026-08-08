#!/usr/bin/env python3
"""Render 'Aurora, Slowly' (ehon-style acoustic post-rock) to a stereo WAV.
Mirrors the browser Web Audio composition: Karplus-Strong guitar arpeggio,
ambient pad, glockenspiel bells, falsetto lead, deep convolution reverb,
with a 静->動 (quiet->grand) build."""
import numpy as np, wave, struct, json, sys

SR = 44100
BPM = 76.0
beat = 60.0 / BPM
barLen = beat * 4
rng = np.random.default_rng(7)

SEMI = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
        'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def freq(n):
    name = n[:-1]; octv = int(n[-1])
    s = SEMI[name] + (octv+1)*12
    return 440.0 * 2**((s-69)/12.0)

V = {
 'D':    ["D3","A3","D4","F#4","A4"],
 'A':    ["A2","E3","A3","C#4","E4"],
 'Bm7':  ["B2","F#3","A3","D4","F#4"],
 'Gmaj7':["G2","D3","F#3","B3","D4"],
 'G':    ["G2","D3","G3","B3","D4"],
}
PAD = {'D':["D3","F#3","A3"],'A':["A2","C#3","E3"],'Bm7':["B2","D3","F#3"],
       'Gmaj7':["G2","B2","D3","F#3"],'G':["G2","B2","D3"]}
BASS = {'D':"D2",'A':"A2",'Bm7':"B1",'Gmaj7':"G2",'G':"G2"}
MEL = [("F#4",4),("D4",2),("B4",2),("A4",4),("C#5",2),("E5",2),
       ("D5",2),("F#4",2),("B4",4),("F#4",2),("A4",2),("E4",3),("D4",1)]

SONG = [
 dict(tag="Intro",  intn=.12, inst=True,  bars=["D","Gmaj7","D","Gmaj7"]),
 dict(tag="Build I", intn=.40, bars=["D","A","Bm7","Gmaj7"]),
 dict(tag="Build II",intn=.66, bars=["D","A","Bm7","Gmaj7"]),
 dict(tag="Climax",  intn=1.0, climax=True, bars=["Bm7","G","D","A","Bm7","G","D","A"]),
 dict(tag="Outro",   intn=.28, fade=True, bars=["Gmaj7","D","Gmaj7","D"]),
]
PAT = [0,3,2,4,1,3,2,4,1,4,2,3,0,4,2,3]

nbars = sum(len(s["bars"]) for s in SONG)
totalDur = nbars*barLen + 3.4
N = int(totalDur*SR) + SR
# per-layer dry mixes
guit = np.zeros(N); padb = np.zeros(N); bell = np.zeros(N); lead = np.zeros(N)
drums = np.zeros(N); bass = np.zeros(N); elec = np.zeros(N)

def add(buf, start, sig):
    i = int(start*SR); j = min(len(buf), i+len(sig))
    if i < 0: return
    buf[i:j] += sig[:j-i]

def ks(f, dur, gain):
    """Karplus-Strong plucked string, block-vectorized."""
    Np = max(2, int(round(SR/f)))
    total = int(dur*SR)
    nb = total//Np + 2
    seg = rng.uniform(-1,1,Np)          # initial noise burst
    damp = 0.996 - min(f,700)/700*0.006
    out = np.empty(nb*Np)
    out[:Np] = seg
    prev_last = seg[-1]
    for k in range(1, nb):
        s = out[(k-1)*Np:k*Np]
        shifted = np.empty(Np); shifted[0] = prev_last; shifted[1:] = s[:-1]
        nseg = damp*0.5*(s + shifted)
        out[k*Np:(k+1)*Np] = nseg
        prev_last = s[-1]
    out = out[:total]
    # pluck amplitude envelope (fast attack, natural decay already in KS, add taper)
    env = np.ones(total)
    a = int(0.006*SR); env[:a] = np.linspace(0,1,a)
    r = int(0.05*SR); env[-r:] *= np.linspace(1,0,r)
    return out*env*gain

def osc_saw(f, t):  # naive saw
    return 2.0*(f*t - np.floor(0.5 + f*t))
def osc_tri(f, t):
    return 2.0/np.pi*np.arcsin(np.sin(2*np.pi*f*t))

def pad_note(names, dur, gain):
    t = np.arange(int(dur*SR))/SR
    sig = np.zeros(len(t))
    for nm in names:
        f = freq(nm)
        for det, amp in ((1.0,0.5),(1.003,0.35),(0.997,0.3)):
            sig += amp*np.sin(2*np.pi*f*det*t)/len(names)
            sig += 0.12*np.sin(2*np.pi*2*f*det*t)/len(names)
    env = np.ones(len(t))
    a = int(0.9*SR); env[:a] = np.linspace(0,1,a)
    r = int(1.0*SR); env[-r:] *= np.linspace(1,0,r)
    return sig*env*gain

def bell_note(f, gain):
    dur = 1.8; t = np.arange(int(dur*SR))/SR
    sig = (np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*2.76*f*t)
           + 0.12*np.sin(2*np.pi*5.4*f*t))
    env = np.exp(-t*3.0)
    return sig*env*gain

def lead_note(f, dur, gain):
    t = np.arange(int(dur*SR))/SR
    vib = 1.0 + 0.006*np.sin(2*np.pi*5.2*t)
    ph = 2*np.pi*f*np.cumsum(vib)/SR
    sig = 0.6*(2/np.pi*np.arcsin(np.sin(ph))) + 0.4*(2/np.pi*np.arcsin(np.sin(ph*1.003)))
    env = np.ones(len(t))
    a = int(0.28*SR); env[:a] = np.linspace(0,1,a)
    r = int(0.4*SR); env[-r:] *= np.linspace(1,0,r)
    return sig*env*gain

# ---- rock layer: drums / bass / distorted electric ----
def kick(gain, dur=0.30):
    t=np.arange(int(dur*SR))/SR
    f=45+(120-45)*np.exp(-t*45)
    ph=2*np.pi*np.cumsum(f)/SR
    sig=np.sin(ph)*np.exp(-t*8) + np.exp(-t*200)*0.6
    return sig*gain

def snare(gain, dur=0.22):
    t=np.arange(int(dur*SR))/SR
    noise=rng.uniform(-1,1,len(t))*np.exp(-t*22)
    tone=np.sin(2*np.pi*185*t)*np.exp(-t*30)*0.5
    return (noise*0.8+tone)*gain

def hat(gain, dur=0.05):
    t=np.arange(int(dur*SR))/SR
    n=rng.uniform(-1,1,len(t)); n=np.diff(n,prepend=0.0)   # high emphasis
    return n*np.exp(-t*90)*gain

def crash(gain, dur=1.5):
    t=np.arange(int(dur*SR))/SR
    n=rng.uniform(-1,1,len(t)); n=np.diff(n,prepend=0.0)
    return n*np.exp(-t*3.5)*gain

def bass_note(f, dur, gain):
    t=np.arange(int(dur*SR))/SR
    sig=np.tanh((2/np.pi*np.arcsin(np.sin(2*np.pi*f*t)))*1.8)  # driven triangle
    env=np.ones(len(t)); a=int(0.005*SR); env[:a]=np.linspace(0,1,a)
    r=int(min(0.05,dur*0.3)*SR); env[-r:]*=np.linspace(1,0,r)
    return sig*env*gain

def elec_chord(root_f, dur, gain):
    t=np.arange(int(dur*SR))/SR
    sig=osc_saw(root_f,t)+osc_saw(root_f*2**(7/12),t)+osc_saw(root_f*2,t)
    sig=np.tanh(sig*3.0)                                   # distortion
    k=np.ones(9)/9.0; sig=np.convolve(sig,k,mode="same")   # tame the fizz
    env=np.ones(len(t)); a=int(0.02*SR); env[:a]=np.linspace(0,1,a)
    r=int(0.12*SR); env[-r:]*=np.linspace(1,0,r)
    return sig*env*gain

# ---- schedule ----
b = 0
for s in SONG:
    intn = s["intn"]
    for ci, ch in enumerate(s["bars"]):
        t0 = b*barLen
        voic = [freq(x) for x in V[ch]]
        dense = 16 if intn > 0.55 else 8
        step = barLen/dense
        gGain = 0.12 + intn*0.16
        for i in range(dense):
            fi = PAT[i % len(PAT)] % len(voic)
            accent = 1.5 if i==0 else (1.12 if i%4==0 else 1.0)
            jitter = rng.uniform(0,0.006)
            add(guit, t0 + i*step + jitter,
                ks(voic[fi], beat*(1.4 if intn>0.55 else 1.9), gGain*accent))
        if intn > 0.25:
            add(padb, t0, pad_note(PAD[ch], barLen*1.02, 0.05+intn*0.14))
        if intn > 0.6:
            add(bell, t0, bell_note(voic[-1]*2, 0.16*intn))
            if intn > 0.9:
                add(bell, t0+beat*2.5, bell_note(voic[-2]*2, 0.13))
        if s.get("fade"):
            add(bell, t0+beat*1.5, bell_note(voic[-1]*2, 0.10*intn))

        # ---- rock layer (enters from Build II) ----
        tag = s["tag"]; root = freq(BASS[ch])
        if tag == "Build I":
            add(bass, t0, bass_note(root, beat*4*0.95, 0.30))
        elif tag == "Build II":
            add(bass, t0, bass_note(root, beat*2*0.95, 0.40))
            add(bass, t0+beat*2, bass_note(root, beat*2*0.95, 0.40))
            add(drums, t0, kick(0.7)); add(drums, t0+beat*2, kick(0.7))
            add(drums, t0+beat*2, snare(0.38))
            for k in range(8): add(drums, t0+k*(beat/2), hat(0.09))
        elif tag == "Climax":
            for k in range(8): add(bass, t0+k*(beat/2), bass_note(root, beat*0.5*0.95, 0.5))
            add(drums, t0, kick(0.95)); add(drums, t0+beat*2, kick(0.95))
            add(drums, t0+beat*2.5, kick(0.7))
            add(drums, t0+beat*1, snare(0.6)); add(drums, t0+beat*3, snare(0.6))
            for k in range(16): add(drums, t0+k*(beat/4), hat(0.16 if k%2==0 else 0.11))
            if ci in (0,4): add(drums, t0, crash(0.4))
        elif s.get("fade"):
            add(bass, t0, bass_note(root, beat*4*0.95, 0.26))
            if ci==0: add(drums, t0, kick(0.5))
        b += 1
    if s.get("climax"):
        mt = (b-len(s["bars"]))*barLen
        for nn, bl in MEL:
            add(lead, mt+0.02, lead_note(freq(nn), beat*bl*1.02, 0.20))
            mt += beat*bl

# ---- mix: dry + convolution reverb ----
predry = (guit*1.0 + padb*0.7 + bell*0.8 + lead*0.75
          + drums*0.95 + bass*1.0)
prewet = (guit*0.5 + padb*1.0 + bell*0.9 + lead*1.0
          + drums*0.12 + bass*0.08)

def make_ir(seed, decay=2.2, dur=2.6):
    r = np.random.default_rng(seed)
    n = int(dur*SR)
    ir = r.uniform(-1,1,n) * (1-np.arange(n)/n)**decay
    ir /= np.max(np.abs(ir))
    return ir*0.5

def fftconv(x, ir):
    n = len(x)+len(ir)-1
    NF = 1 << int(np.ceil(np.log2(n)))
    y = np.fft.irfft(np.fft.rfft(x,NF)*np.fft.rfft(ir,NF), NF)[:len(x)]
    return y

irL = make_ir(11); irR = make_ir(29)
wetL = fftconv(prewet, irL); wetR = fftconv(prewet, irR)

masterDry, masterWet = 0.85, 0.5
L = predry*masterDry + wetL*masterWet
R = predry*masterDry + wetR*masterWet

peak = max(np.max(np.abs(L)), np.max(np.abs(R)), 1e-9)
g = 0.94/peak
L *= g; R *= g
# soft global fade in/out edges
fi = int(0.15*SR); L[:fi]*=np.linspace(0,1,fi); R[:fi]*=np.linspace(0,1,fi)
fo = int(1.5*SR); L[-fo:]*=np.linspace(1,0,fo); R[-fo:]*=np.linspace(1,0,fo)

stereo = np.empty(len(L)*2)
stereo[0::2] = L; stereo[1::2] = R
pcm = (stereo*32767).astype('<i2')

out = "/tmp/claude-0/-home-user-agent-team/af0ffba2-d9ce-5973-bf9d-744a93585c07/scratchpad/aurora.wav"
with wave.open(out,'w') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("WROTE", out, "dur=%.1fs"%(len(L)/SR))
