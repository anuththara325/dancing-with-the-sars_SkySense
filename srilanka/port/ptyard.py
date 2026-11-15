import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
HV = {t: db(uniform_filter(rd(f"pt_{t}_hvhv.tif"), 9)) for t in tags}
HH = {t: db(uniform_filter(rd(f"pt_{t}_hhhh.tif"), 9)) for t in tags}
boxes = {"yardA": (slice(105, 205), slice(95, 340)), "yardB": (slice(0, 225), slice(460, 525)), "paved": (slice(0, 120), slice(360, 465)), "city": (slice(290, 470), slice(390, 560))}
print("pair | share >3 dB in HV (%): yardA / yardB / city | mean abs change HV (dB): yardA / yardB / city | HH: yardA / city share >3 dB")
for a, b in list(zip(tags[:-1], tags[1:])) + [("jul14", "aug19")]:
    dv = HV[b] - HV[a]; dh = HH[b] - HH[a]
    dv = dv - np.median(dv); dh = dh - np.median(dh)
    sh = [100*(np.abs(dv[s]) > 3).mean() for s in boxes.values()]
    mc = [np.abs(dv[s]).mean() for s in boxes.values()]
    print(a, "->", b, " / ".join("%.1f" % x for x in sh), "|", " / ".join("%.2f" % x for x in mc), "|", "%.1f / %.1f" % (100*(np.abs(dh[boxes["yardA"]]) > 3).mean(), 100*(np.abs(dh[boxes["city"]]) > 3).mean()))
