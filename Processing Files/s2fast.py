import json, subprocess
import numpy as np
from osgeo import gdal
from concurrent.futures import ThreadPoolExecutor
gdal.UseExceptions()
body = json.dumps({"collections":["sentinel-2-l2a"],"bbox":[80.45,5.9,80.75,6.1],
    "datetime":"2026-06-25T00:00:00Z/2026-10-25T00:00:00Z","limit":100})
out = subprocess.run(["curl","-s","-X","POST","https://earth-search.aws.element84.com/v1/search",
    "-H","Content-Type: application/json","-d",body],capture_output=True,text=True).stdout
feats = sorted(json.loads(out)["features"], key=lambda f: f["id"].split("_")[2])
print(len(feats), "scenes", flush=True)
def chk(f):
    try:
        ds = gdal.Warp("", "/vsicurl/"+f["assets"]["scl"]["href"], format="MEM", dstSRS="EPSG:4326",
            outputBounds=(80.45,5.9,80.75,6.1), width=300, height=200, resampleAlg="near")
        a = ds.GetRasterBand(1).ReadAsArray(); n = a.size
        cl = 100*np.isin(a,[3,8,9,10]).sum()/n
        nd = 100*(a==0).sum()/n
        ok = 100*np.isin(a,[4,5,6]).sum()/n
        return f["id"], f["properties"]["eo:cloud_cover"], cl, nd, ok
    except Exception as e:
        return f["id"], -1, -1, -1, -1
rows = []
with ThreadPoolExecutor(6) as ex:
    for r in ex.map(chk, feats):
        rows.append(r); print(r[0], "tile %.0f%% cloud %.0f%% nodata %.0f%% clear %.0f%%" % r[1:], flush=True)
print("--- best by clear ground ---")
for r in sorted(rows, key=lambda r: -r[4])[:12]:
    print(r[0], "clear %.0f%% cloud %.0f%% nodata %.0f%%" % (r[4], r[2], r[3]))
