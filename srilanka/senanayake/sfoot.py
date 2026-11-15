import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
hv = {t: rd(f"sn_{t}_hvhv.tif") for t in tags}
cm = np.logical_and.reduce([np.isfinite(hv[t]) & (hv[t] > 0) for t in tags])
pa = (0.24/960*111.32*np.cos(np.radians(7.285))) * (0.27/1080*110.57)
def sm(a):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return uniform_filter(z, 5) / np.maximum(uniform_filter(w, 5), 1e-6)
fp = (rd("sn_s2scl_jun25.tif") == 6) & cm
print("footprint = optical water on 25 Jun inside valid mask: %.1f km2" % (fp.sum()*pa))
print("NISAR inside footprint / outside footprint:  date, dark share inside %, median HV inside dB, dark km2 outside")
for t in tags:
    s = 10*np.log10(np.maximum(sm(hv[t]), 1e-8)); d = (s < -22) & cm
    print(t, "%.1f" % (100*d[fp].mean()), "%.1f" % (10*np.log10(np.median(hv[t][fp]))), "%.1f" % ((d & ~fp).sum()*pa))
print("Sentinel-2 inside footprint: date, water share % of clear pixels, cloud %")
for t in ["jun25","jul25","aug19","sep08","oct03"]:
    a = rd(f"sn_s2scl_{t}.tif"); clear = np.isin(a, [4,5,6]) & fp; cl = np.isin(a, [3,8,9,10]) & fp
    print(t, "%.1f" % (100*((a == 6) & clear).sum()/max(clear.sum(), 1)), "%.1f" % (100*cl.sum()/fp.sum()))
