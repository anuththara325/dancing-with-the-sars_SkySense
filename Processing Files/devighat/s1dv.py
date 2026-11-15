import sys, os, csv, io, subprocess, urllib.parse, urllib.request
tag, date = sys.argv[1], sys.argv[2]
excl = sys.argv[3:]
W, S, E, N, X, Y = 85.114, 27.868, 85.154, 27.908, 480, 540
env = dict(os.environ)
env.pop("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", None)
env["GDAL_HTTP_COOKIEFILE"] = env["GDAL_HTTP_COOKIEJAR"] = os.path.expanduser("~/.urs_cookies")
env["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
wkt = f"POLYGON(({W} {S},{E} {S},{E} {N},{W} {N},{W} {S}))"
q = urllib.parse.urlencode({"dataset": "OPERA-S1", "processingLevel": "RTC", "intersectsWith": wkt,
                            "start": date + "T00:00:00Z", "end": date + "T23:59:59Z", "maxResults": 200, "output": "csv"})
txt = urllib.request.urlopen("https://api.daac.asf.alaska.edu/services/search/param?" + q, timeout=120).read().decode()
rows = [r for r in csv.DictReader(io.StringIO(txt)) if r["Path Number"] == "85"
        and not any(x in r["Granule Name"] for x in excl)]
print(tag, date, len(rows), "bursts")
for pol in ("VV", "VH"):
    urls = ["/vsicurl/" + r["URL"].replace(".h5", f"_{pol}.tif") for r in rows]
    out = f"dv_s1_{tag}_{pol.lower()}.tif"
    cmd = ["gdalwarp", "-overwrite", "-q", "-te", str(W), str(S), str(E), str(N), "-ts", str(X), str(Y),
           "-t_srs", "EPSG:4326", "-r", "average", "-dstnodata", "nan", "-ot", "Float32"] + urls + [out]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(pol, "ok" if r.returncode == 0 and os.path.exists(out) else "FAILED " + r.stderr[-300:])
