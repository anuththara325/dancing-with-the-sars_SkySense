import numpy as np, os, json
from osgeo import gdal
from scipy.ndimage import uniform_filter
from PIL import Image
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
dates = {"jun20":"2026-06-20","jul02":"2026-07-02","jul14":"2026-07-14","jul26":"2026-07-26","aug19":"2026-08-19","aug31":"2026-08-31","sep12":"2026-09-12","sep24":"2026-09-24","oct06":"2026-10-06","oct18":"2026-10-18"}
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
hv = {t: rd(f"pt_{t}_hvhv.tif") for t in tags}; hh = {t: rd(f"pt_{t}_hhhh.tif") for t in tags}
cm = np.logical_and.reduce([np.isfinite(hv[t]) & (hv[t] > 1e-4) & np.isfinite(hh[t]) & (hh[t] > 1e-4) for t in tags])
pa = (0.0272/600*111.32*np.cos(np.radians(6.9378))) * (0.027/600*110.57)
def sm(a):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return uniform_filter(z, 9) / np.maximum(uniform_filter(w, 9), 1e-6)
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
HV = {t: db(sm(hv[t])) for t in tags}; HH = {t: db(sm(hh[t])) for t in tags}
medHV = np.median([HV[t] for t in tags], axis=0); medHH = np.median([HH[t] for t in tags], axis=0)
land = cm & (medHV > -19); bright = land & (medHH > -3)
print("valid %.2f km2 (%.1f%% of box) | land %.2f km2 | bright structures (HH > -3 dB) %.2f km2" % (cm.sum()*pa, 100*cm.mean(), land.sum()*pa, bright.sum()*pa))
print("pair | HV bias dB | std land | >3 dB share: land / bright / other land (%) | HH-HV diff correlation")
for a, b in list(zip(tags[:-1], tags[1:])) + [("jul14", "aug19")]:
    dv = HV[b] - HV[a]; dh = HH[b] - HH[a]
    bias = np.median(dv[land]); dv = dv - bias; dh = dh - np.median(dh[land]); ch = np.abs(dv) > 3
    print(a, "->", b, "%.2f" % bias, "%.2f" % dv[land].std(), "%.1f / %.1f / %.1f" % (100*ch[land].mean(), 100*ch[bright].mean(), 100*ch[land & ~bright].mean()), "%.2f" % np.corrcoef(dv[land], dh[land])[0, 1])
os.makedirs("web_port", exist_ok=True)
dv = HV["aug19"] - HV["jul14"]; dv = dv - np.median(dv[land])
rgba = np.zeros(dv.shape + (4,), "uint8")
rgba[..., 0] = (np.clip(dv/6, 0, 1)*255).astype("uint8"); rgba[..., 2] = (np.clip(-dv/6, 0, 1)*255).astype("uint8")
rgba[..., 3] = ((land & (np.abs(dv) > 2))*220).astype("uint8")
Image.fromarray(rgba, "RGBA").save("web_port/change_jul14_aug19.png")
print("change layer: >2 dB on land %.3f km2 (increase %.3f, decrease %.3f)" % ((land & (np.abs(dv) > 2)).sum()*pa, (land & (dv > 2)).sum()*pa, (land & (dv < -2)).sum()*pa))
with open("web_port/timeseries.csv", "w") as f:
    f.write("date,land_hv_median_db,land_hh_median_db,bright_hh_median_db\n")
    for t in tags:
        f.write("%s,%.2f,%.2f,%.2f\n" % (dates[t], db(np.median(hv[t][land])), db(np.median(hh[t][land])), db(np.median(hh[t][bright]))))
json.dump({"box": [79.8232, 6.9243, 79.8504, 6.9513], "valid_km2": round(float(cm.sum()*pa), 3), "land_km2": round(float(land.sum()*pa), 3), "bright_km2": round(float(bright.sum()*pa), 3), "pixel_km2": round(float(pa), 7), "smoothing_px": 9}, open("web_port/stats.json", "w"), indent=1)
