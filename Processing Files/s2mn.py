import os, sys, json, subprocess, datetime
os.environ.pop("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", None); os.environ.pop("GDAL_DISABLE_READDIR_ON_OPEN", None)
import numpy as np
from osgeo import gdal
gdal.UseExceptions()
tag, date = sys.argv[1], sys.argv[2]
W, S, E, N, X, Y = 80.82, 7.95, 81.02, 8.10, 800, 600
d1 = (datetime.date.fromisoformat(date) + datetime.timedelta(days=1)).isoformat()
body = json.dumps({"collections": ["sentinel-2-l2a"], "bbox": [W, S, E, N], "datetime": f"{date}T00:00:00Z/{d1}T00:00:00Z", "limit": 20})
out = subprocess.run(["curl", "-s", "-X", "POST", "https://earth-search.aws.element84.com/v1/search", "-H", "Content-Type: application/json", "-d", body], capture_output=True, text=True).stdout
feats = [f for f in json.loads(out)["features"] if f["id"].endswith("_0_L2A")]
print(date, len(feats), "tiles:", [f["id"].split("_")[1] + " %.0f%%" % f["properties"]["eo:cloud_cover"] for f in feats])
kw = dict(dstSRS="EPSG:4326", outputBounds=(W, S, E, N), width=X, height=Y, srcNodata=0, dstNodata=0)
g = gdal.Warp(f"mn_s2_{tag}.tif", ["/vsicurl/" + f["assets"]["visual"]["href"] for f in feats], resampleAlg="bilinear", **kw); g = None
ds = gdal.Warp("", ["/vsicurl/" + f["assets"]["scl"]["href"] for f in feats], format="MEM", resampleAlg="near", **kw)
a = ds.GetRasterBand(1).ReadAsArray()
print("  box cloud+shadow %.0f%%  nodata %.0f%%  clear %.0f%%" % (100*np.isin(a, [3, 8, 9, 10]).mean(), 100*(a == 0).mean(), 100*np.isin(a, [4, 5, 6]).mean()))
