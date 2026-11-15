import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
hv, hh, masks = {}, {}, []
for t in tags:
    a = rd(f"sn_{t}_hvhv.tif"); b = rd(f"sn_{t}_hhhh.tif")
    masks.append(np.isfinite(a) & (a > 0) & np.isfinite(b) & (b > 0)); hv[t] = a; hh[t] = b
cm = np.logical_and.reduce(masks)
pa = (0.24/960*111.32*np.cos(np.radians(7.285))) * (0.27/1080*110.57)
print("common valid area %.1f km2 (%.1f%% of box)" % (cm.sum()*pa, 100*cm.mean()))
def sm(a):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return uniform_filter(z, 5) / np.maximum(uniform_filter(w, 5), 1e-6)
print("NISAR: date, HV-dark(<-22 dB) km2, median HV dB, median HH dB")
for t in tags:
    s = 10*np.log10(np.maximum(sm(hv[t]), 1e-8))
    print(t, "%.2f" % (((s < -22) & cm).sum()*pa), "%.1f" % (10*np.log10(np.median(hv[t][cm]))), "%.1f" % (10*np.log10(np.median(hh[t][cm]))))
print("Sentinel-2 inside same mask: date, water(SCL6) km2, cloud%, water as % of clear")
for t in ["jun25","jul25","aug19","sep08","oct03"]:
    a = rd(f"sn_s2scl_{t}.tif")
    cl = np.isin(a, [3,8,9,10]); w = (a == 6); clear = np.isin(a, [4,5,6])
    print(t, "%.2f" % ((w & cm).sum()*pa), "%.1f" % (100*(cl & cm).sum()/cm.sum()), "%.2f" % (100*(w & cm).sum()/max((clear & cm).sum(), 1)))
