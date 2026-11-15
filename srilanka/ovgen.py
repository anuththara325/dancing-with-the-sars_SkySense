import sys, os, numpy as np
from osgeo import gdal
from PIL import Image
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
pre = sys.argv[1]; W, S, E, N = map(float, sys.argv[2:6]); X, Y = int(sys.argv[6]), int(sys.argv[7]); tags = sys.argv[8].split(","); ref = tags[0]
pa = (E-W)/X*111.32*np.cos(np.radians((S+N)/2)) * (N-S)/Y*110.57
def rd(f):
    ds = gdal.Open(f); return ds.GetRasterBand(1).ReadAsArray().astype("float32")
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
hv = {t: rd(f"{pre}_{t}_hvhv.tif") for t in tags}
ok = {t: np.isfinite(hv[t]) & (hv[t] > 1e-4) for t in tags}
cm = np.logical_and.reduce(list(ok.values()))
os.makedirs("overview", exist_ok=True)
print("box km2 %.0f" % (X*Y*pa))
for t in tags:
    v = ok[t]; wd = (db(hv[t]) < -22) & cm
    print(t, "valid %.1f%% (%.0f km2)  HV median %.2f dB  dark HV<-22: %.0f km2 (%.1f%% of common valid)" % (100*v.mean(), v.sum()*pa, db(np.median(hv[t][v])), wd.sum()*pa, 100*wd.sum()/max(cm.sum(), 1)))
print("common valid %.1f%% (%.0f km2)" % (100*cm.mean(), cm.sum()*pa))
print("common valid by 3x3 block (rows N->S, cols W->E), %:")
for i in range(3):
    print("  ", " ".join("%3.0f" % (100*cm[i*Y//3:(i+1)*Y//3, j*X//3:(j+1)*X//3].mean()) for j in range(3)))
def sm(a, k=5):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return db(uniform_filter(z, k)/np.maximum(uniform_filter(w, k), 1e-6))
for t in tags:
    g = np.clip((sm(hv[t]) + 26)/20, 0, 1)
    Image.fromarray(np.dstack([(g*255).astype("uint8")]*3 + [(cm*255).astype("uint8")]), "RGBA").save(f"overview/{pre}_hv_{t}.png")
for t in tags[1:]:
    d = sm(hv[t]) - sm(hv[ref]); d = d - np.median(d[cm])
    rgba = np.zeros(d.shape + (4,), "uint8")
    rgba[..., 0] = (np.clip(d/6, 0, 1)*255).astype("uint8"); rgba[..., 2] = (np.clip(-d/6, 0, 1)*255).astype("uint8")
    rgba[..., 3] = ((cm & (np.abs(d) > 2))*230).astype("uint8")
    Image.fromarray(rgba, "RGBA").save(f"overview/{pre}_diff_{t}_{ref}.png")
    print(t, "vs", ref, ": darker >3 dB %.0f km2, brighter >3 dB %.0f km2" % (((d < -3) & cm).sum()*pa, ((d > 3) & cm).sum()*pa))
