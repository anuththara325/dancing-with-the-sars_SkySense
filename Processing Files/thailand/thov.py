import numpy as np, os
from osgeo import gdal
from PIL import Image
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
W, S, E, N, X, Y = 101.2, 13.9, 101.6, 14.2, 800, 600
pa = (E-W)/X*111.32*np.cos(np.radians((S+N)/2)) * (N-S)/Y*110.57
tags = ["aug25", "sep30", "oct12"]
def rd(f):
    ds = gdal.Open(f); return ds.GetRasterBand(1).ReadAsArray().astype("float32")
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
hv = {t: rd(f"th_{t}_hvhv.tif") for t in tags}
ok = {t: np.isfinite(hv[t]) & (hv[t] > 1e-4) for t in tags}
cm = np.logical_and.reduce(list(ok.values()))
os.makedirs("overview", exist_ok=True)
print("box km2 %.0f" % (X*Y*pa))
for t in tags:
    v = ok[t]; print(t, "valid %.1f%% (%.0f km2)  HV median %.2f dB  dark HV<-22: %.0f km2 (%.1f%% of common valid)" % (100*v.mean(), v.sum()*pa, db(np.median(hv[t][v])), ((db(hv[t]) < -22) & cm).sum()*pa, 100*((db(hv[t]) < -22) & cm).sum()/max(cm.sum(), 1)))
print("common valid %.1f%% (%.0f km2)" % (100*cm.mean(), cm.sum()*pa))
print("common valid by 3x3 block (rows N->S, cols W->E), %:")
for i in range(3):
    print("  ", " ".join("%3.0f" % (100*cm[i*Y//3:(i+1)*Y//3, j*X//3:(j+1)*X//3].mean()) for j in range(3)))
def sm(a, k=5):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return db(uniform_filter(z, k)/np.maximum(uniform_filter(w, k), 1e-6))
for t in tags:
    g = np.clip((sm(hv[t]) + 26)/20, 0, 1)
    Image.fromarray(np.dstack([(g*255).astype("uint8")]*3 + [(cm*255).astype("uint8")]), "RGBA").save(f"overview/hv_{t}.png")
for t in ["sep30", "oct12"]:
    d = sm(hv[t]) - sm(hv["aug25"]); d = d - np.median(d[cm])
    rgba = np.zeros(d.shape + (4,), "uint8")
    rgba[..., 0] = (np.clip(d/6, 0, 1)*255).astype("uint8"); rgba[..., 2] = (np.clip(-d/6, 0, 1)*255).astype("uint8")
    rgba[..., 3] = ((cm & (np.abs(d) > 2))*230).astype("uint8")
    Image.fromarray(rgba, "RGBA").save(f"overview/diff_{t}_aug25.png")
    print(t, "vs aug25: darker >3 dB %.0f km2, brighter >3 dB %.0f km2" % (((d < -3) & cm).sum()*pa, ((d > 3) & cm).sum()*pa))
