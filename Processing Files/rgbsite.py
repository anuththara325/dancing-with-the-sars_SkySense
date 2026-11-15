import sys
import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
gdal.UseExceptions()
pre = sys.argv[1]; W,S,E,N = map(float, sys.argv[2:6])
items = [a.split(":",1) for a in sys.argv[6:]]
def rd(tag, b):
    ds = gdal.Open(f"{pre}_{tag}_{b}.tif")
    a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    ok = np.isfinite(a) & (a > 0)
    m = np.where(ok, a, 0.0)
    w = uniform_filter(ok.astype("float64"), 5)
    sm = np.where(w > 0, uniform_filter(m, 5)/np.maximum(w, 1e-9), np.nan)
    return 10*np.log10(sm), ok
D = {}
common = None
for tag, lab in items:
    hh, o1 = rd(tag, "hhhh"); hv, o2 = rd(tag, "hvhv")
    D[tag] = [hh, hv]; ok = o1 & o2
    common = ok if common is None else common & ok
t0 = items[0][0]
for tag, lab in items:
    for i in (0, 1):
        D[tag][i] = D[tag][i] - (np.nanmedian(D[tag][i][common]) - np.nanmedian(D[t0][i][common]))
def chans(tag):
    return [D[tag][0], D[tag][1], D[tag][0] - D[tag][1]]
lim = [np.nanpercentile(c[common], [2, 98]) for c in chans(t0)]
def rgb(tag):
    c = chans(tag)
    out = np.dstack([np.clip((c[i]-lim[i][0])/(lim[i][1]-lim[i][0]), 0, 1) for i in range(3)])
    return np.nan_to_num(out)
n = len(items); cols = min(5, n); rows = (n+cols-1)//cols
fig, ax = plt.subplots(rows, cols, figsize=(3.6*cols, 2.6*rows+0.9), squeeze=False)
ny, nx = D[t0][0].shape
latm = (S+N)/2
px = (E-W)/nx*111.32*np.cos(np.radians(latm)); py = (N-S)/ny*110.57
print("pixel area km2", px*py)
print(f"{'date':12s}{'HH_med':>8s}{'HV_med':>8s}{'HV<-20':>9s}{'HV<-22':>9s}{'new<-22':>9s}{'gone<-22':>9s}")
w0 = (D[t0][1] < -22) & common
for k, (tag, lab) in enumerate(items):
    a = ax[k//cols][k % cols]; a.imshow(rgb(tag), extent=[W,E,S,N]); a.set_title(lab, fontsize=9)
    a.tick_params(labelsize=6)
    hv = D[tag][1]; w = (hv < -22) & common
    print(f"{lab:12s}{np.nanmedian(D[tag][0][common]):8.1f}{np.nanmedian(hv[common]):8.1f}"
          f"{((hv<-20)&common).sum()*px*py:9.2f}{w.sum()*px*py:9.2f}{(w&~w0).sum()*px*py:9.2f}{(w0&~w).sum()*px*py:9.2f}")
for k in range(n, rows*cols): ax[k//cols][k % cols].axis("off")
fig.suptitle("False colour: R=HH, G=HV, B=HH/HV (dB difference). Credit: NASA SVS 5661. Data: NISAR GCOV provisional", fontsize=9)
plt.tight_layout(); plt.savefig(f"{pre}_rgb_grid.png", dpi=130); print("saved", f"{pre}_rgb_grid.png")
