import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
from PIL import Image
gdal.UseExceptions()
tags = ["jun20","jul02","jul14","jul26","aug19","aug31","sep12","sep24","oct06","oct18"]
def rd(f):
    ds = gdal.Open(f); a = ds.GetRasterBand(1).ReadAsArray().astype("float32"); return a
hv = {t: rd(f"dv_{t}_hvhv.tif") for t in tags}; hh = {t: rd(f"dv_{t}_hhhh.tif") for t in tags}
ok = {t: np.isfinite(hv[t]) & (hv[t] > 1e-4) & np.isfinite(hh[t]) & (hh[t] > 1e-4) for t in tags}
cm = np.logical_and.reduce(list(ok.values()))
pa = (0.04/480*111.32*np.cos(np.radians(27.888))) * (0.04/540*110.57)
print("valid km2 per date (cutoff 1e-4):", " ".join("%s %.2f" % (t, ok[t].sum()*pa) for t in tags))
r = np.where(cm.any(1))[0]; c = np.where(cm.any(0))[0]; h, w = cm.shape
print("common valid %.2f km2 (%.1f%% of box) rows %d-%d cols %d-%d" % (cm.sum()*pa, 100*cm.mean(), r.min(), r.max(), c.min(), c.max()))
print("valid by quadrant (NW NE / SW SE): %.0f %.0f / %.0f %.0f %%" % (100*cm[:h//2,:w//2].mean(), 100*cm[:h//2,w//2:].mean(), 100*cm[h//2:,:w//2].mean(), 100*cm[h//2:,w//2:].mean()))
db = lambda x: 10*np.log10(np.maximum(x, 1e-8))
def sm(a, k):
    z = np.where(cm, a, 0).astype("float32"); w_ = cm.astype("float32")
    return db(uniform_filter(z, k) / np.maximum(uniform_filter(w_, k), 1e-6))
H5, G5 = {t: sm(hv[t], 5) for t in tags}, {t: sm(hh[t], 5) for t in tags}
rh, rv = np.median(G5[tags[0]][cm]), np.median(H5[tags[0]][cm])
lim = [np.percentile(x[cm], [2, 98]) for x in (G5[tags[0]], H5[tags[0]], G5[tags[0]] - H5[tags[0]])]
st = lambda x, l: np.clip((x - l[0]) / (l[1] - l[0]), 0, 1)
for t in tags:
    a = G5[t] - np.median(G5[t][cm]) + rh; b = H5[t] - np.median(H5[t][cm]) + rv
    ch = [st(a, lim[0]), st(b, lim[1]), st(a - b, lim[2])]
    Image.fromarray(np.dstack([(x*255).astype("uint8") for x in ch] + [(cm*255).astype("uint8")]), "RGBA").save(f"web_devighat/nisar_{t}.png")
H9 = {t: sm(hv[t], 9) for t in tags}
print("date | median HV dB | area darker than 19 Aug by >3 dB (km2) | area brighter by >3 dB (km2) | std")
for t in tags:
    d = H9[t] - H9["aug19"]; d = d - np.median(d[cm])
    print(t, "%.2f" % db(np.median(hv[t][cm])), "%.3f" % (((d < -3) & cm).sum()*pa), "%.3f" % (((d > 3) & cm).sum()*pa), "%.2f" % d[cm].std())
d = H9["aug31"] - H9["aug19"]; d = d - np.median(d[cm])
print("key pair 19 Aug -> 31 Aug: min %.2f max %.2f std %.2f share |d|>2 dB %.2f%%" % (d[cm].min(), d[cm].max(), d[cm].std(), 100*(np.abs(d[cm]) > 2).mean()))
rgba = np.zeros(d.shape + (4,), "uint8")
rgba[..., 0] = (np.clip(d/6, 0, 1)*255).astype("uint8"); rgba[..., 2] = (np.clip(-d/6, 0, 1)*255).astype("uint8")
rgba[..., 3] = ((cm & (np.abs(d) > 2))*220).astype("uint8")
Image.fromarray(rgba, "RGBA").save("web_devighat/change_aug19_aug31.png")
