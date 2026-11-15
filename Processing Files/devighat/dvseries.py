import numpy as np, csv, datetime as dt
from osgeo import gdal
from scipy.ndimage import uniform_filter
gdal.UseExceptions()
def rd(f):
    ds = gdal.Open(f); return ds.GetRasterBand(1).ReadAsArray().astype("float32")
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
pa = (0.04/480*111.32*np.cos(np.radians(27.888))) * (0.04/540*110.57)
N = {"jun20":"2026-06-20","jul02":"2026-07-02","jul14":"2026-07-14","jul26":"2026-07-26","aug19":"2026-08-19","aug31":"2026-08-31","sep12":"2026-09-12","sep24":"2026-09-24","oct06":"2026-10-06","oct18":"2026-10-18"}
S = {"jun22":"2026-06-22","jun29":"2026-06-29","jul11":"2026-07-11","jul23":"2026-07-23","aug04":"2026-08-04","aug16":"2026-08-16","aug28":"2026-08-28","sep09":"2026-09-09","sep21":"2026-09-21","oct03":"2026-10-03","oct15":"2026-10-15"}
def run(tags, f_co, f_cr, ref, label, rows):
    co = {t: rd(f_co(t)) for t in tags}; cr = {t: rd(f_cr(t)) for t in tags}
    cm = np.logical_and.reduce([np.isfinite(co[t]) & (co[t] > 1e-4) & np.isfinite(cr[t]) & (cr[t] > 1e-4) for t in tags])
    def sm(a, k=9):
        z = np.where(cm, a, 0).astype("float32"); w = cm.astype("float32")
        return db(uniform_filter(z, k)/np.maximum(uniform_filter(w, k), 1e-6))
    R = sm(cr[ref])
    print(label, "common valid %.2f km2" % (cm.sum()*pa))
    for t in tags:
        d = sm(cr[t]) - R; d = d - np.median(d[cm])
        dark = ((d < -3) & cm).sum()*pa; bright = ((d > 3) & cm).sum()*pa
        rows.append([label, tags[t] if isinstance(tags, dict) else t, N.get(t, S.get(t)), "%.2f" % db(np.median(co[t][cm])), "%.2f" % db(np.median(cr[t][cm])), "%.3f" % dark, "%.3f" % bright])
        print(label, N.get(t, S.get(t)), "co %.2f cross %.2f dB  darker %.3f  brighter %.3f km2" % (db(np.median(co[t][cm])), db(np.median(cr[t][cm])), dark, bright))
rows = []
run(list(N), lambda t: f"dv_{t}_hhhh.tif", lambda t: f"dv_{t}_hvhv.tif", "aug19", "NISAR_HH_HV", rows)
run(list(S), lambda t: f"dv_s1_{t}_vv.tif", lambda t: f"dv_s1_{t}_vh.tif", "aug16", "S1_VV_VH", rows)
with open("web_devighat/timeseries.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["sensor","tag","date","co_median_db","cross_median_db","darker_km2_vs_ref","brighter_km2_vs_ref"])
    for r in rows: w.writerow([r[0], r[1] if False else r[1], r[2], r[3], r[4], r[5], r[6]])
# rain
lines = open("power_devighat.csv").read().splitlines()
i = [k for k, l in enumerate(lines) if "END HEADER" in l][0]
hdr = lines[i+1].split(","); iy, im, id_, ip = hdr.index("YEAR"), hdr.index("MM" if "MM" in hdr else "MO"), hdr.index("DY"), hdr.index("PRECTOTCORR")
rain = {}
for l in lines[i+2:]:
    p = l.split(",")
    v = float(p[ip]); rain[dt.date(int(p[iy]), int(p[im]), int(p[id_]))] = 0.0 if v < 0 else v
with open("web_devighat/rain_daily.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date","rain_mm"])
    for d_ in sorted(rain): w.writerow([d_.isoformat(), "%.1f" % rain[d_]])
ds_ = [dt.date.fromisoformat(v) for v in N.values()]
print("rain between NISAR passes (mm, POWER MERRA-2 ~50 km, not a gauge):")
with open("web_devighat/rain.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["from","to","rain_mm"])
    for a, b in zip(ds_[:-1], ds_[1:]):
        s = sum(v for d_, v in rain.items() if a < d_ <= b); w.writerow([a, b, "%.1f" % s]); print(a, "->", b, "%.1f" % s)
print("daily rain 20-31 Aug:", " ".join("%d:%.1f" % (d_.day, rain[d_]) for d_ in sorted(rain) if dt.date(2026,8,20) <= d_ <= dt.date(2026,8,31)))
print("total 17-26 Aug %.1f mm" % sum(v for d_, v in rain.items() if dt.date(2026,8,17) <= d_ <= dt.date(2026,8,26)))
