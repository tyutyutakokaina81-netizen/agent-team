#!/usr/bin/env python3
# AnimeGANv2 (animegan2-pytorch) で写真3枚を本物のアニメ絵に変換して保存。
import glob, numpy as np, torch
from PIL import Image

UP = sorted(glob.glob("/root/.claude/uploads/e9e1e32f-0213-5782-861c-60b6f918b109/*.jpeg"))
OUTDIR = "/tmp/vv/anime"
import os; os.makedirs(OUTDIR, exist_ok=True)

print("loading AnimeGANv2 generator (face_paint_512_v2) ...", flush=True)
import sys; sys.path.insert(0, "/tmp/vv/animegan")
from model import Generator
model = Generator()
model.load_state_dict(torch.load("/tmp/vv/animegan/face_paint_512_v2.pt", map_location="cpu"))
model.eval()

def to_tensor(img):
    a = np.asarray(img.convert("RGB")).astype(np.float32)/127.5 - 1.0
    return torch.from_numpy(a).permute(2,0,1).unsqueeze(0)

def to_pil(t):
    a = (t.squeeze(0).permute(1,2,0).clamp(-1,1).numpy()+1)*127.5
    return Image.fromarray(a.astype("uint8"))

def fit32(img, longest=720):
    w,h = img.size; s = longest/max(w,h)
    nw,nh = max(32,int(round(w*s/32))*32), max(32,int(round(h*s/32))*32)
    return img.resize((nw,nh), Image.LANCZOS)

for p in UP:
    name = [k for k in ("IMG_0851","IMG_0852","IMG_0853") if k in p][0]
    img = Image.open(p).convert("RGB")
    inp = fit32(img, 720)
    with torch.no_grad():
        out = model(to_tensor(inp))
    res = to_pil(out).resize(img.size, Image.LANCZOS)
    res.save(f"{OUTDIR}/{name}.png")
    print("done", name, res.size, flush=True)
print("ALL DONE", flush=True)
