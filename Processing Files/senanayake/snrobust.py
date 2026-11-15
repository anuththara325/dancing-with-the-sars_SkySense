import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
tags = ["jul02","aug31","sep12","oct06"]
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
hv = {t: rd(f"sn_{t}_hvhv.tif") for t in tags}
cm0 = np.logical_and.reduce([np.isfinite(hv[t]) & (hv[t] > 1e-4) for t in tags])
pa = (0.24/960*111.32*np.cos(np.radians(7.285))) * (0.27/1080*110.57)
scl, scl8 = rd("sn_s2scl_jun25.tif"), rd("sn_s2scl_sep08.tif")
print("edge px | valid km2 | outline km2 | HV-dark inside outline %: jul02 aug31 sep12 oct06 | dark outside km2: jul02 aug31 sep12 oct06 | optical share 8 Sep %")
for E in [50, 100, 150, 200, 250]:
    cm = cm0.copy()
    for r in range(cm.shape[0]):
        c = np.where(cm0[r])[0]
        if len(c): cm[r, c.max()-E+1:] = False
    fp = (scl == 6) & cm
    ins, out = [], []
    for t in tags:
        z = np.where(cm, hv[t], 0).astype("float32"); w = cm.astype("float32")
        s = 10*np.log10(np.maximum(uniform_filter(z, 5) / np.maximum(uniform_filter(w, 5), 1e-6), 1e-8))
        d = (s < -22) & cm; ins.append(100*d[fp].mean()); out.append((d & ~fp).sum()*pa)
    clear = np.isin(scl8, [4,5,6]) & fp
    print("%3d | %.0f | %.1f | %s | %s | %.1f" % (E, cm.sum()*pa, fp.sum()*pa, " ".join("%.1f" % x for x in ins), " ".join("%.1f" % x for x in out), 100*((scl8 == 6) & clear).sum()/clear.sum()))
