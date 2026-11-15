import numpy as np, json, datetime as dt
from osgeo import gdal
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
dates = {"jun20":"2026-06-20","jul02":"2026-07-02","jul14":"2026-07-14","jul26":"2026-07-26","aug19":"2026-08-19","aug31":"2026-08-31","sep12":"2026-09-12","sep24":"2026-09-24","oct06":"2026-10-06","oct18":"2026-10-18"}
s2d = {"jun25":"2026-06-25","jul25":"2026-07-25","aug19":"2026-08-19","sep08":"2026-09-08","oct03":"2026-10-03"}
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
hv = {t: rd(f"sn_{t}_hvhv.tif") for t in tags}; hh = {t: rd(f"sn_{t}_hhhh.tif") for t in tags}
cm = np.logical_and.reduce([np.isfinite(hv[t]) & (hv[t] > 0) & np.isfinite(hh[t]) & (hh[t] > 0) for t in tags])
pa = (0.24/960*111.32*np.cos(np.radians(7.285))) * (0.27/1080*110.57)
def sm(a):
    z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
    return uniform_filter(z, 5) / np.maximum(uniform_filter(w, 5), 1e-6)
fp = (rd("sn_s2scl_jun25.tif") == 6) & cm
db = lambda x: 10*np.log10(x)
with open("web_senanayake/timeseries.csv", "w") as f:
    f.write("date,hv_median_db,hh_median_db,hv_dark_box_km2,hv_dark_inside_pct,hv_dark_outside_km2,hv_median_inside_db\n")
    for t in tags:
        s = db(np.maximum(sm(hv[t]), 1e-8)); d = (s < -22) & cm
        f.write("%s,%.2f,%.2f,%.2f,%.1f,%.2f,%.2f\n" % (dates[t], db(np.median(hv[t][cm])), db(np.median(hh[t][cm])), d.sum()*pa, 100*d[fp].mean(), (d & ~fp).sum()*pa, db(np.median(hv[t][fp]))))
with open("web_senanayake/s2_timeseries.csv", "w") as f:
    f.write("date,water_km2,water_pct_of_clear_inside_outline,cloud_pct_inside_outline\n")
    for t, d in s2d.items():
        a = rd(f"sn_s2scl_{t}.tif"); clear = np.isin(a, [4,5,6]) & fp; cl = np.isin(a, [3,8,9,10]) & fp
        f.write("%s,%.2f,%.1f,%.1f\n" % (d, ((a == 6) & cm).sum()*pa, 100*((a == 6) & clear).sum()/max(clear.sum(), 1), 100*cl.sum()/fp.sum()))
json.dump({"box": [81.38, 7.15, 81.62, 7.42], "common_valid_km2": round(float(cm.sum()*pa), 1), "common_valid_pct": round(float(100*cm.mean()), 1),
           "outline_km2_25jun": round(float(fp.sum()*pa), 1), "pixel_km2": round(float(pa), 5), "dark_threshold_db": -22}, open("web_senanayake/stats.json", "w"), indent=1)
print("written")
