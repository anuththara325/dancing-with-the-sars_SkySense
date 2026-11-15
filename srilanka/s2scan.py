import json, subprocess
import numpy as np
from osgeo import gdal
gdal.UseExceptions()
body = json.dumps({"collections":["sentinel-2-l2a"],"bbox":[80.45,5.9,80.75,6.1],
    "datetime":"2026-09-01T00:00:00Z/2026-10-25T00:00:00Z","limit":100})
out = subprocess.run(["curl","-s","-X","POST","https://earth-search.aws.element84.com/v1/search",
    "-H","Content-Type: application/json","-d",body],capture_output=True,text=True).stdout
feats = sorted(json.loads(out)["features"], key=lambda f: f["id"].split("_")[2])
for f in feats:
    scl = f["assets"]["scl"]["href"]
    try:
        ds = gdal.Warp("/vsimem/scl.tif", "/vsicurl/"+scl, dstSRS="EPSG:4326",
            outputBounds=(80.45,5.9,80.75,6.1), width=300, height=200, resampleAlg="near")
        a = ds.GetRasterBand(1).ReadAsArray(); ds = None
        c = 100*np.isin(a,[3,8,9,10]).sum()/a.size
        print(f["id"], "tile %.0f%%" % f["properties"]["eo:cloud_cover"], "box %.0f%%" % c)
    except Exception as e:
        print(f["id"], "ERR", str(e)[:60])
