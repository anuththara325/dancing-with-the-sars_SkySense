import os, sys, shutil
from PIL import Image
src, prefix, dst = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(dst, exist_ok=True)
tot = 0
for f in sorted(os.listdir(src)):
    p = os.path.join(src, f)
    if f.endswith(".png"):
        o = os.path.join(dst, f"{prefix}_{f[:-4]}.webp")
        Image.open(p).save(o, "WEBP", quality=88, method=6); tot += os.path.getsize(o)
    elif f.endswith((".json", ".csv")):
        shutil.copy(p, os.path.join(dst, f"{prefix}_{f}"))
print(prefix, "webp total %.1f MB" % (tot/1e6))
