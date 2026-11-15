import sys, os, json, subprocess, datetime
tag, date = sys.argv[1], sys.argv[2]
W,S,E,N,X,Y = 80.45,5.9,80.75,6.1,1200,800
d1 = (datetime.date.fromisoformat(date)+datetime.timedelta(days=1)).isoformat()
body = json.dumps({"collections":["sentinel-2-l2a"],"bbox":[W,S,E,N],"datetime":f"{date}T00:00:00Z/{d1}T00:00:00Z","limit":10})
out = subprocess.run(["curl","-s","-X","POST","https://earth-search.aws.element84.com/v1/search",
    "-H","Content-Type: application/json","-d",body],capture_output=True,text=True).stdout
feats = json.loads(out).get("features",[])
print(len(feats),"items")
for f in feats:
    print(f["id"], "cloud", f["properties"].get("eo:cloud_cover"))
if feats:
    href = feats[0]["assets"]["visual"]["href"]
    res = subprocess.run(["gdalwarp","-q","-overwrite","-t_srs","EPSG:4326","-te",str(W),str(S),str(E),str(N),
        "-ts",str(X),str(Y),"-r","bilinear","/vsicurl/"+href,f"mt_s2_{tag}.tif"],capture_output=True,text=True)
    print("clip", "ok" if res.returncode==0 else res.stderr[:300])
