import sys, numpy as np
from osgeo import gdal
gdal.UseExceptions()
pre, tag = sys.argv[1], sys.argv[2]
ds = gdal.Open(f"{pre}_{tag}_hvhv.tif"); a = ds.GetRasterBand(1).ReadAsArray().astype("float32")
m = np.isfinite(a) & (a > 0)
last = np.array([np.where(m[r])[0].max() if m[r].any() else -1 for r in range(a.shape[0])])
rows = np.where((last > 200) & (last < a.shape[1] - 5))[0]
print(pre, tag, "rows with a real right edge:", len(rows), "of", a.shape[0])
for off in [0, 5, 10, 20, 30, 40, 60, 80, 100, 150, 250]:
    print("  %3d px from the edge: median HV %.1f dB" % (off, 10*np.log10(np.median([a[r, last[r]-off] for r in rows])))) if len(rows) else None
