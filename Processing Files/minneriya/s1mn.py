import sys, os, csv, io, subprocess, urllib.parse, urllib.request, datetime
tag, date = sys.argv[1], sys.argv[2]
TRACK = "19"
W,S,E,N,X,Y = 80.82,7.95,81.02,8.10,800,600
wkt = f"POLYGON(({W} {S}, {E} {S}, {E} {N}, {W} {N}, {W} {S}))"
d1 = (datetime.date.fromisoformat(date)+datetime.timedelta(days=1)).isoformat()
q = urllib.parse.urlencode({"dataset":"OPERA-S1","processingLevel":"RTC","intersectsWith":wkt,
    "start":date,"end":d1,"maxResults":100,"output":"csv"})
txt = urllib.request.urlopen("https://api.daac.asf.alaska.edu/services/search/param?"+q, timeout=90).read().decode()
rows = [r for r in csv.DictReader(io.StringIO(txt)) if r["Path Number"]==TRACK and date.replace("-","") in r["Granule Name"]]
rows = [r for r in rows if not any(x in r["URL"] for x in sys.argv[3:])]
print(len(rows), "bursts on Track", TRACK)
env = dict(os.environ, GDAL_HTTP_COOKIEFILE=os.path.expanduser("~/.urs_cookies"),
    GDAL_HTTP_COOKIEJAR=os.path.expanduser("~/.urs_cookies"), GDAL_DISABLE_READDIR_ON_OPEN="YES",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.h5")
for pol in ("VV","VH"):
    out = f"mn_s1_{tag}_{pol.lower()}.tif"
    if os.path.exists(out): continue
    srcs = ["/vsicurl/"+r["URL"].replace(".h5", f"_{pol}.tif") for r in rows]
    cmd = ["gdalwarp","-q","-overwrite","-t_srs","EPSG:4326","-te",str(W),str(S),str(E),str(N),
           "-ts",str(X),str(Y),"-r","bilinear","-dstnodata","nan","-ot","Float32"] + srcs + [out]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(pol, "ok" if r.returncode==0 else "FAILED: "+r.stderr[:400])
