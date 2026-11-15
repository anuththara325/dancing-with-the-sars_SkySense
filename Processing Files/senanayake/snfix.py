import numpy as np, json
from osgeo import gdal
from scipy.ndimage import uniform_filter
from PIL import Image
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
dates = {"jun20":"2026-06-20","jul02":"2026-07-02","jul14":"2026-07-14","jul26":"2026-07-26","aug19":"2026-08-19","aug31":"2026-08-31","sep12":"2026-09-12","sep24":"2026-09-24","oct06":"2026-10-06","oct18":"2026-10-18"}
s2d = {"jun25":"2026-06-25","jul25":"2026-07-25","aug19":"2026-08-19","sep08":"2026-09-08","oct03":"2026-10-03"}
EDGE = 100
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
hv = {t: rd(f"sn_{t}_hvhv.tif") for t in tags}; hh = {t: rd(f"sn_{t}_hhhh.tif") for t in tags}
cm0 = np.logical_and.reduce([np.isfinite(hv[t]) & (hv[t] > 1e-4) & np.isfinite(hh[t]) & (hh[t] > 1e-4) for t in tags])
cm = cm0.copy()
for r in range(cm.shape[0]):
    c = np.where(cm0[r])[0]
    if len(c): cm[r, c.max()-EDGE+1:] = False
pa = (0.24/960*111.32*np.cos(np.radians(7.285))) * (0.27/1080*110.57)
print("valid before %.1f km2, after removing edge strip %.1f km2" % (cm0.sum()*pa, cm.sum()*pa))
def sm(a):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return uniform_filter(z, 5) / np.maximum(uniform_filter(w, 5), 1e-6)
HH = {t: db(sm(hh[t])) for t in tags}; HV = {t: db(sm(hv[t])) for t in tags}
rh, rv = np.median(HH[tags[0]][cm]), np.median(HV[tags[0]][cm])
def ali(t): return HH[t] - np.median(HH[t][cm]) + rh, HV[t] - np.median(HV[t][cm]) + rv
a0, b0 = ali(tags[0])
lim = [np.percentile(x[cm], [2, 98]) for x in (a0, b0, a0 - b0)]
print("stretch limits dB  HH %.1f..%.1f   HV %.1f..%.1f   HH-HV %.1f..%.1f" % (*lim[0], *lim[1], *lim[2]))
st = lambda x, l: np.clip((x - l[0]) / (l[1] - l[0]), 0, 1)
for t in tags:
    a, b = ali(t)
    ch = [st(a, lim[0]), st(b, lim[1]), st(a - b, lim[2])]
    rgba = np.dstack([(c*255).astype("uint8") for c in ch] + [(cm*255).astype("uint8")])
    Image.fromarray(rgba, "RGBA").save(f"web_senanayake/nisar_{t}.png")
    if t == "aug19": print("aug19 saturation R/G/B at max: %.1f%% %.1f%% %.1f%%" % tuple(100*(c[cm] >= 0.999).mean() for c in ch))
fp = (rd("sn_s2scl_jun25.tif") == 6) & cm
print("outline (25 Jun optical water) %.1f km2" % (fp.sum()*pa))
with open("web_senanayake/timeseries.csv", "w") as f:
    f.write("date,hv_median_db,hh_median_db,hv_dark_box_km2,hv_dark_inside_pct,hv_dark_outside_km2,hv_median_inside_db\n")
    for t in tags:
        d = (HV[t] < -22) & cm
        f.write("%s,%.2f,%.2f,%.2f,%.1f,%.2f,%.2f\n" % (dates[t], db(np.median(hv[t][cm])), db(np.median(hh[t][cm])), d.sum()*pa, 100*d[fp].mean(), (d & ~fp).sum()*pa, db(np.median(hv[t][fp]))))
with open("web_senanayake/s2_timeseries.csv", "w") as f:
    f.write("date,water_km2,water_pct_of_clear_inside_outline,cloud_pct_inside_outline\n")
    for t, d in s2d.items():
        s = rd(f"sn_s2scl_{t}.tif"); clear = np.isin(s, [4,5,6]) & fp; cl = np.isin(s, [3,8,9,10]) & fp
        f.write("%s,%.2f,%.1f,%.1f\n" % (d, ((s == 6) & cm).sum()*pa, 100*((s == 6) & clear).sum()/max(clear.sum(), 1), 100*cl.sum()/fp.sum()))
json.dump({"box": [81.38, 7.15, 81.62, 7.42], "edge_strip_removed_px": EDGE, "common_valid_km2": round(float(cm.sum()*pa), 1),
           "outline_km2_25jun": round(float(fp.sum()*pa), 1), "pixel_km2": round(float(pa), 5), "dark_threshold_db": -22}, open("web_senanayake/stats.json", "w"), indent=1)
