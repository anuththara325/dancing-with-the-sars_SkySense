import sys, csv, datetime as dt, numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
from PIL import Image
gdal.UseExceptions()
pre = sys.argv[1]; W, S, E, N = map(float, sys.argv[2:6]); X, Y = int(sys.argv[6]), int(sys.argv[7])
tags = sys.argv[8].split(","); ref, key = sys.argv[9], sys.argv[10]
s1 = [] if sys.argv[11] == "-" else sys.argv[11].split(","); s1ref = sys.argv[12]; out = sys.argv[13]; thr = float(sys.argv[14])
MON = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6, jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)
dstr = lambda t: dt.date(2026, MON[t[:3]], int(t[3:])).isoformat()
pa = (E-W)/X*111.32*np.cos(np.radians((S+N)/2)) * (N-S)/Y*110.57
def rd(f):
    ds = gdal.Open(f); return ds.GetRasterBand(1).ReadAsArray().astype("float32")
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
def sm(a, m, k):
    z = np.where(m, a, 0).astype("float32"); ww = m.astype("float32")
    return db(uniform_filter(z, k)/np.maximum(uniform_filter(ww, k), 1e-6))
area = lambda mask: float(mask.sum())*pa
hv = {t: rd(f"{pre}_{t}_hvhv.tif") for t in tags}; hh = {t: rd(f"{pre}_{t}_hhhh.tif") for t in tags}
ok = {t: np.isfinite(hv[t]) & (hv[t] > 1e-4) & np.isfinite(hh[t]) & (hh[t] > 1e-4) for t in tags}
cm = np.logical_and.reduce(list(ok.values()))
print("NISAR valid km2 (cutoff 1e-4):", " ".join("%s %.2f" % (t, area(ok[t])) for t in tags))
print("common valid %.2f km2 (%.1f%% of box)" % (area(cm), 100*cm.mean()))
hgt, wid = cm.shape
print("valid by quadrant NW NE / SW SE: %.0f %.0f / %.0f %.0f %%" % (100*cm[:hgt//2, :wid//2].mean(), 100*cm[:hgt//2, wid//2:].mean(), 100*cm[hgt//2:, :wid//2].mean(), 100*cm[hgt//2:, wid//2:].mean()))
H5 = {t: sm(hv[t], cm, 5) for t in tags}; G5 = {t: sm(hh[t], cm, 5) for t in tags}
rh, rv = np.median(G5[ref][cm]), np.median(H5[ref][cm])
lim = [np.percentile(x[cm], [2, 98]) for x in (G5[ref], H5[ref], G5[ref] - H5[ref])]
st = lambda x, l: np.clip((x - l[0])/(l[1] - l[0]), 0, 1)
for t in tags:
    a = G5[t] - np.median(G5[t][cm]) + rh; b = H5[t] - np.median(H5[t][cm]) + rv
    ch = [st(a, lim[0]), st(b, lim[1]), st(a - b, lim[2])]
    Image.fromarray(np.dstack([(c*255).astype("uint8") for c in ch] + [(cm*255).astype("uint8")]), "RGBA").save(f"{out}/nisar_{t}.png")
H9 = {t: sm(hv[t], cm, 9) for t in tags}
rows = []
print("NISAR | date | HV median dB | dark HV<%.0f km2 (%% of valid) | darker than %s >3 dB km2 | brighter km2" % (thr, ref))
for t in tags:
    d = H9[t] - H9[ref]; d = d - np.median(d[cm])
    dk = area((H9[t] < thr) & cm); dr = area((d < -3) & cm); br = area((d > 3) & cm)
    rows.append([t, dstr(t), "%.2f" % db(np.median(hv[t][cm])), "%.2f" % db(np.median(hh[t][cm])), "%.3f" % dk, "%.1f" % (100*dk/area(cm)), "%.3f" % dr, "%.3f" % br])
    print(" ", t, "HV %.2f  dark %.2f (%.1f%%)  darker %.3f  brighter %.3f" % (db(np.median(hv[t][cm])), dk, 100*dk/area(cm), dr, br))
with open(f"{out}/timeseries.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(["tag", "date", "hv_median_db", "hh_median_db", "dark_km2", "dark_pct", "darker_vs_ref_km2", "brighter_vs_ref_km2"]); wr.writerows(rows)
for t in dict.fromkeys([key, tags[-1]]):
    d = H9[t] - H9[ref]; d = d - np.median(d[cm])
    rg = np.zeros(d.shape + (4,), "uint8")
    rg[..., 0] = (np.clip(d/6, 0, 1)*255).astype("uint8"); rg[..., 2] = (np.clip(-d/6, 0, 1)*255).astype("uint8")
    rg[..., 3] = ((cm & (np.abs(d) > 2))*220).astype("uint8")
    Image.fromarray(rg, "RGBA").save(f"{out}/change_{t}_{ref}.png")
    print("change layer", t, "vs", ref, "std %.2f  share |d|>2 dB %.2f%%" % (d[cm].std(), 100*(np.abs(d[cm]) > 2).mean()))
if s1:
    vv = {t: rd(f"{pre}_s1_{t}_vv.tif") for t in s1}; vh = {t: rd(f"{pre}_s1_{t}_vh.tif") for t in s1}
    ok1 = {t: np.isfinite(vh[t]) & (vh[t] > 1e-4) & np.isfinite(vv[t]) & (vv[t] > 1e-4) for t in s1}
    c1 = np.logical_and.reduce(list(ok1.values()))
    print("S1 valid km2:", " ".join("%s %.2f" % (t, area(ok1[t])) for t in s1), "| common %.2f km2 (%.1f%%)" % (area(c1), 100*c1.mean()))
    V9 = {t: sm(vh[t], c1, 9) for t in s1}; r1 = []
    for t in s1:
        d = V9[t] - V9[s1ref]; d = d - np.median(d[c1])
        dk = area((V9[t] < thr) & c1); dr = area((d < -3) & c1); br = area((d > 3) & c1)
        r1.append([t, dstr(t), "%.2f" % db(np.median(vv[t][c1])), "%.2f" % db(np.median(vh[t][c1])), "%.3f" % dk, "%.1f" % (100*dk/area(c1)), "%.3f" % dr, "%.3f" % br])
        print("  S1", t, "VH %.2f  dark %.2f (%.1f%%)  darker than %s %.3f  brighter %.3f" % (db(np.median(vh[t][c1])), dk, 100*dk/area(c1), s1ref, dr, br))
    with open(f"{out}/s1_timeseries.csv", "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["tag", "date", "vv_median_db", "vh_median_db", "dark_km2", "dark_pct", "darker_vs_ref_km2", "brighter_vs_ref_km2"]); wr.writerows(r1)
