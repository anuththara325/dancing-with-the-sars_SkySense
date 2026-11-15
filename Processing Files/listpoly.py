import sys, re, csv, io, json, subprocess, urllib.parse, urllib.request, collections
name, wkt, s, e = sys.argv[1:5]
def asf(ds, lvl):
    q = urllib.parse.urlencode({"dataset": ds, "processingLevel": lvl, "intersectsWith": wkt, "start": s, "end": e, "maxResults": 500, "output": "csv"})
    txt = urllib.request.urlopen("https://api.daac.asf.alaska.edu/services/search/param?" + q, timeout=120).read().decode()
    return list(csv.DictReader(io.StringIO(txt)))
print("######", name)
rows = [r for r in asf("NISAR", "GCOV") if "_PR_" in r["Granule Name"] and "P05023" in r["Granule Name"]]
print("--- NISAR GCOV PR/P05023:", len(rows), "scenes")
for r in sorted(rows, key=lambda r: r["Granule Name"].split("_")[11]):
    t = r["Granule Name"].split("_")
    print("NISAR", t[11][:8], "track", t[5], "frame", t[7], t[6], t[9], "flag", t[14], r["Granule Name"])
rows = asf("OPERA-S1", "RTC")
c = collections.Counter()
for r in rows:
    c[(r["Granule Name"].split("_")[4][:8], r["Path Number"], r["Ascending or Descending?"])] += 1
print("--- Sentinel-1 OPERA RTC:", len(rows), "bursts")
for (d, p, a), n in sorted(c.items()): print("S1", d, "track", p, a, n, "bursts")
nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", wkt)]
lons, lats = nums[0::2], nums[1::2]
body = json.dumps({"collections": ["sentinel-2-l2a"], "bbox": [min(lons), min(lats), max(lons), max(lats)],
                   "datetime": f"{s}T00:00:00Z/{e}T00:00:00Z", "limit": 200})
out = subprocess.run(["curl", "-s", "-X", "POST", "https://earth-search.aws.element84.com/v1/search", "-H", "Content-Type: application/json", "-d", body], capture_output=True, text=True).stdout
feats = sorted(json.loads(out)["features"], key=lambda f: f["id"].split("_")[2])
print("--- Sentinel-2 L2A (AWS):", len(feats), "scenes (cloud is tile-wide)")
for f in feats:
    p = f["id"].split("_")
    print("S2", p[2], p[1], p[3], "cloud %.0f%%" % f["properties"]["eo:cloud_cover"])
