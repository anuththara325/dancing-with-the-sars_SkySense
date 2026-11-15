import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter, label, binary_dilation
import matplotlib.pyplot as plt
gdal.UseExceptions()
def hv(t):
    ds = gdal.Open(f"mt_{t}_hvhv.tif"); a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    return 10*np.log10(uniform_filter(a, 5))
a, b = hv("sep12"), hv("oct18")
lab, n = label(a < -18); ids = [i for i in np.unique(lab[-1, :]) if i != 0]
land = ~binary_dilation(np.isin(lab, ids), iterations=6)
m = land & (b < -22) & (a > -20)
l2, n2 = label(m); sizes = np.bincount(l2.ravel())
keep = np.isin(l2, np.where(sizes >= 10)[0]) & (l2 > 0)
px = (0.3/1200*111.32*np.cos(np.radians(6.0))) * (0.2/800*110.57)
print("newly dark before filter %.2f km2, after patch filter %.2f km2" % (m.sum()*px, keep.sum()*px))
img = np.zeros(keep.shape + (4,), "uint8"); img[keep] = (0, 229, 255, 220)
plt.imsave("web_matara/change_sep12_oct18.png", img)
