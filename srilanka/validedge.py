import numpy as np
from osgeo import gdal
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
common = None
for t in tags:
    ds = gdal.Open(f"mn_{t}_hvhv.tif"); a = ds.GetRasterBand(1).ReadAsArray()
    ok = np.isfinite(a) & (a > 0)
    r = np.where(ok.any(axis=1))[0]; c = np.where(ok.any(axis=0))[0]
    print(t, "valid %.1f%%" % (100*ok.mean()), "rows %d-%d cols %d-%d (of 600x800)" % (r[0], r[-1], c[0], c[-1]),
          "| top20%% %.0f bottom20%% %.0f left20%% %.0f right20%%  %.0f" % (100*ok[:120].mean(), 100*ok[-120:].mean(), 100*ok[:, :160].mean(), 100*ok[:, -160:].mean()))
    common = ok if common is None else common & ok
print("common valid on all 10 dates: %.1f%%" % (100*common.mean()))
