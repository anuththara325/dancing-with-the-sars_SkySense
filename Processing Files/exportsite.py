import os, sys, json
import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
import matplotlib.pyplot as plt
gdal.UseExceptions()
pre, out = sys.argv[1], sys.argv[2]
W, S, E, N = map(float, sys.argv[3:7])
nis, s1 = sys.argv[7].split(","), sys.argv[8].split(",")
os.makedirs(out, exist_ok=True)
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    ok = np.isfinite(a) & (a > 0)
    m = np.where(ok, a, 0.0); w = uniform_filter(ok.astype("float64"), 5)
    sm = np.where(w > 0, uniform_filter(m, 5)/np.maximum(w, 1e-9), np.nan)
    return 10*np.log10(sm), ok
def series(prefix, pa, pb, tags, label):
    D = {}; common = None
    for t in tags:
        fa, fb = f"{prefix}_{t}_{pa}.tif", f"{prefix}_{t}_{pb}.tif"
        if not (os.path.exists(fa) and os.path.exists(fb)): continue
        a, o1 = rd(fa); b, o2 = rd(fb)
        D[t] = [a, b]; ok = o1 & o2
        common = ok if common is None else common & ok
    ts = list(D); t0 = ts[0]
    print(label, "common valid %.1f%%" % (100*common.mean()))
    for t in ts:
        for i in (0, 1):
            D[t][i] -= np.nanmedian(D[t][i][common]) - np.nanmedian(D[t0][i][common])
    ch = lambda t: [D[t][0], D[t][1], D[t][0]-D[t][1]]
    lim = [np.nanpercentile(c[common], [2, 98]) for c in ch(t0)]
    for t in ts:
        c = ch(t)
        rgb = np.dstack([np.clip((c[i]-lim[i][0])/(lim[i][1]-lim[i][0]), 0, 1) for i in range(3)])
        alpha = (np.isfinite(c[0]) & np.isfinite(c[1])).astype(float)
        plt.imsave(f"{out}/{label}_{t}.png", (np.dstack([np.nan_to_num(rgb), alpha])*255).astype("uint8"))
        print("wrote", f"{label}_{t}.png")
    return ts
n = series(pre, "hhhh", "hvhv", nis, "nisar")
s = series(pre + "_s1", "vv", "vh", s1, "s1")
json.dump({"bounds_leaflet": [[S, W], [N, E]], "bbox_wsen": [W, S, E, N], "nisar": n, "sentinel1": s,
           "colour": "NISAR R=HH G=HV B=HH-HV dB (NASA SVS 5661); S1 R=VV G=VH B=VV-VH dB; stretch fixed from first date; medians aligned on common valid area"},
          open(f"{out}/manifest.json", "w"), indent=1)
