import sys, os, json, subprocess, urllib.request, numpy as np
from osgeo import gdal
gdal.UseExceptions()
tag, date = sys.argv[1], sys.argv[2]
W, S, E, N, X, Y = 85.114, 27.868, 85.154, 27.908, 480, 540
for k in ("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", "GDAL_DISABLE_READDIR_ON_OPEN", "GDAL_HTTP_COOKIEFILE", "GDAL_HTTP_COOKIEJAR"):
    os.environ.pop(k, None)
body = json.dumps({"collections": ["sentinel-2-l2a"], "bbox": [W, S, E, N],
                   "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z", "limit": 50}).encode()
req = urllib.request.Request("https://earth-search.aws.element84.com/v1/search", body, {"Content-Type": "application/json"})
feats = json.loads(urllib.request.urlopen(req, timeout=120).read())["features"]
print(tag, date, len(feats), "items:", [f["id"] for f in feats])
def mosaic(asset, out, resamp):
    srcs = ["/vsicurl/" + f["assets"][asset]["href"] for f in feats]
    subprocess.run(["gdalwarp", "-overwrite", "-q", "-te", str(W), str(S), str(E), str(N), "-ts", str(X), str(Y),
                    "-t_srs", "EPSG:4326", "-r", resamp, "-srcnodata", "0", "-dstnodata", "0"] + srcs + [out], check=True)
mosaic("visual", f"dv_s2_{tag}.tif", "average")
mosaic("scl", f"dv_s2scl_{tag}.tif", "near")
ds = gdal.Open(f"dv_s2scl_{tag}.tif"); a = ds.GetRasterBand(1).ReadAsArray()
n = a.size
cl = np.isin(a, [3, 8, 9, 10]).sum(); ok = np.isin(a, [4, 5, 6]).sum(); nod = (a == 0).sum(); wat = (a == 6).sum()
print("  nodata %.1f%%  cloud+shadow %.1f%%  clear %.1f%%  water(SCL6) %.1f%%" % (100*nod/n, 100*cl/n, 100*ok/n, 100*wat/n))
