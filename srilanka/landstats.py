import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter, label, binary_dilation
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
def hv(t):
    ds = gdal.Open(f"mt_{t}_hvhv.tif"); a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    return 10*np.log10(uniform_filter(a, 5))
H = {t: hv(t) for t in tags}
lab, n = label(H["sep12"] < -18)
ids = [i for i in np.unique(lab[-1, :]) if i != 0]
sea = np.isin(lab, ids)
sea = binary_dilation(sea, iterations=6)
land = ~sea
px = (0.3/1200*111.32*np.cos(np.radians(6.0))) * (0.2/800*110.57)
print("land fraction %.0f%%" % (100*land.mean()))
base = (H["sep12"] < -22) & land
print("tag     land HV<-22 km2   new vs 12 Sep   gone vs 12 Sep")
for t in tags:
    w = (H[t] < -22) & land
    print(f"{t:6s} {w.sum()*px:12.2f} {(w&~base).sum()*px:14.2f} {(base&~w).sum()*px:14.2f}")
