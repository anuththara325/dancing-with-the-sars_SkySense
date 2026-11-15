import sys, json, subprocess, datetime
import numpy as np
from osgeo import gdal
gdal.UseExceptions()
tag, date = sys.argv[1], sys.argv[2]
W,S,E,N = 80.45,5.9,80.75,6.1
d1 = (datetime.date.fromisoformat(date)+datetime.timedelta(days=1)).isoformat()
body = json.dumps({"collections":["sentinel-2-l2a"],"bbox":[W,S,E,N],"datetime":f"{date}T00:00:00Z/{d1}T00:00:00Z","limit":10})
out = subprocess.run(["curl","-s","-X","POST","https://earth-search.aws.element84.com/v1/search","-H","Content-Type: application/json","-d",body],capture_output=True,text=True).stdout
feats = [f for f in json.loads(out)["features"] if f["id"].endswith("_0_L2A")]
f = feats[0]; print(f["id"])
kw = dict(dstSRS="EPSG:4326", outputBounds=(W,S,E,N), width=1200, height=800)
tci = gdal.Warp(f"mt_s2_{tag}.tif", "/vsicurl/"+f["assets"]["visual"]["href"], resampleAlg="bilinear", **kw)
tci = None
ds = gdal.Warp("", "/vsicurl/"+f["assets"]["scl"]["href"], format="MEM", resampleAlg="near", **kw)
a = ds.GetRasterBand(1).ReadAsArray()
sub = a[160:520, 200:680]
c = lambda x: 100*np.isin(x,[3,8,9,10]).sum()/x.size
print("whole box cloud %.0f%%   floodplain cloud %.0f%%   floodplain nodata %.0f%%" % (c(a), c(sub), 100*(sub==0).mean()))
