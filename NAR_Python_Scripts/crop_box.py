#!/usr/bin/env python3
"""Crop a Google Earth Pro screenshot to the study rectangle drawn by the KML, save as JPG.
Usage: python3 crop_box.py <image or folder> [out_dir] [--color yellow|red|cyan|magenta|white]
                           [--inset N] [--manual x0,y0,x1,y1]"""
import sys, os, glob
import numpy as np
from PIL import Image

args = [x for x in sys.argv[1:]]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
color  = opt("--color", "yellow")
inset  = int(opt("--inset", "4"))
manual = opt("--manual", None)
if not args:
    sys.exit(__doc__)
src = args[0]
if len(args) > 1:
    out_dir = args[1]
elif os.path.isdir(src):
    out_dir = os.path.join(src, "cropped")
else:
    out_dir = os.path.dirname(src) or "."
os.makedirs(out_dir, exist_ok=True)

RULES = {
    "yellow":  lambda r, g, b: (r > 190) & (g > 190) & (b < 110),
    "red":     lambda r, g, b: (r > 190) & (g < 70) & (b < 70),
    "cyan":    lambda r, g, b: (r < 90) & (g > 190) & (b > 190),
    "magenta": lambda r, g, b: (r > 190) & (g < 90) & (b > 190),
    "white":   lambda r, g, b: (r > 235) & (g > 235) & (b > 235),
}
if color not in RULES:
    sys.exit(f"--color must be one of {list(RULES)}")

def edges(count, frac=0.35):
    if count.max() == 0:
        return None
    idx = np.where(count >= frac * count.max())[0]
    return (idx.min(), idx.max()) if idx.size and idx.max() - idx.min() > 20 else None

def crop_one(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    if manual:
        x0, y0, x1, y1 = map(int, manual.split(","))
    else:
        m = RULES[color](a[:, :, 0], a[:, :, 1], a[:, :, 2])
        cols, rows = edges(m.sum(axis=0)), edges(m.sum(axis=1))
        if cols is None or rows is None:
            print(f"  {os.path.basename(path)}: no {color} box found, skipped "
                  f"(try --color red, or --manual x0,y0,x1,y1)")
            return
        (x0, x1), (y0, y1) = cols, rows
        x0, y0, x1, y1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + "_crop.jpg")
    im.crop((x0, y0, x1, y1)).save(out, "JPEG", quality=95)
    print(f"  {os.path.basename(path)}: box x {x0}-{x1}, y {y0}-{y1} -> {out} ({x1 - x0}x{y1 - y0} px)")

files = sorted(glob.glob(os.path.join(src, "*.jpg")) + glob.glob(os.path.join(src, "*.jpeg")) +
               glob.glob(os.path.join(src, "*.png"))) if os.path.isdir(src) else [src]
files = [f for f in files if not f.endswith("_crop.jpg")]
print(f"{len(files)} image(s), outline colour {color}")
for f in files:
    crop_one(f)
