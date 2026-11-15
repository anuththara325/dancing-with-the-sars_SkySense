import sys, numpy as np
from osgeo import gdal
gdal.UseExceptions()
pre = sys.argv[1]
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
masks = []
for t in tags:
    ds = gdal.Open(f"{pre}_{t}_hvhv.tif"); a = ds.GetRasterBand(1).ReadAsArray()
    m = np.isfinite(a) & (a > 0); masks.append(m)
    r = np.where(m.any(1))[0]; c = np.where(m.any(0))[0]
    h, w = m.shape; k = int(0.2 * h); j = int(0.2 * w)
    print(t, "valid %.1f%%" % (100 * m.mean()), "rows", r.min(), r.max(), "cols", c.min(), c.max(),
          "| top %.0f bottom %.0f left %.0f right %.0f %%" % (100*m[:k].mean(), 100*m[-k:].mean(), 100*m[:, :j].mean(), 100*m[:, -j:].mean()))
cm = np.logical_and.reduce(masks)
print("common valid %.1f%%" % (100 * cm.mean()), "size", cm.shape)
h, w = cm.shape
print("valid by quadrant (NW NE / SW SE): %.0f %.0f / %.0f %.0f %%" % (
    100*cm[:h//2,:w//2].mean(), 100*cm[:h//2,w//2:].mean(), 100*cm[h//2:,:w//2].mean(), 100*cm[h//2:,w//2:].mean()))
