import sys, glob
import numpy as np
from osgeo import gdal
for pat in sys.argv[1:]:
    for f in sorted(glob.glob(pat)):
        ds = gdal.Open(f)
        if ds is None:
            print(f, "UNREADABLE"); continue
        a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
        ok = np.isfinite(a) & (a > 0)
        pct = 100*ok.mean()
        med = 10*np.log10(np.median(a[ok])) if ok.any() else float("nan")
        print(f"{f:28s} valid {pct:5.1f}%  median {med:6.1f} dB")
