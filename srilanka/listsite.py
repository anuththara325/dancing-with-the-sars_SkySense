import csv, io, re, json, sys, urllib.parse, urllib.request
from collections import defaultdict

SITES = {
 "matara":    ("POLYGON((80.45 5.9, 80.75 5.9, 80.75 6.1, 80.45 6.1, 80.45 5.9))", "2026-06-15", "2026-10-20", "2026-06-25", "2026-10-20"),
 "minneriya": ("POLYGON((80.82 7.95, 81.02 7.95, 81.02 8.10, 80.82 8.10, 80.82 7.95))", "2026-06-15", "2026-10-20", "2026-06-25", "2026-10-20"),
 "colombo":   ("POLYGON((79.8232 6.9243, 79.8504 6.9243, 79.8504 6.9513, 79.8232 6.9513, 79.8232 6.9243))", "2026-06-15", "2026-10-20", "2026-07-01", "2026-08-31"),
}
name = sys.argv[1]
wkt, ns, ne, ss, se = SITES[name]

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nisar-check"}), timeout=90).read().decode()

def asf(params):
    return list(csv.DictReader(io.StringIO(get("https://api.daac.asf.alaska.edu/services/search/param?" + urllib.parse.urlencode(params)))))

print(f"################ {name}")
try:
    rows = asf({"dataset": "NISAR", "processingLevel": "GCOV", "intersectsWith": wkt, "start": ns, "end": ne, "maxResults": 500, "output": "csv"})
    names = sorted({r.get("Granule Name", "") for r in rows if "_PR_GCOV_" in r.get("Granule Name", "") and "P05023" in r.get("Granule Name", "")})
    print(f"--- NISAR GCOV PR/P05023: {len(names)} scenes")
    for n in sorted(names, key=lambda x: x.split("_")[11]):
        p = n.split("_")
        print(f"NISAR {p[11][:8]} track {p[5]} frame {p[7]} {p[6]} {p[9]} flag {p[14]}  {n}")
except Exception as ex:
    print("NISAR search failed:", ex)
try:
    rows = asf({"dataset": "OPERA-S1", "processingLevel": "RTC", "intersectsWith": wkt, "start": ss, "end": se, "maxResults": 2000, "output": "csv"})
    by = defaultdict(int)
    for r in rows:
        m = re.search(r"_(\d{8})T", r.get("Granule Name", ""))
        if m:
            by[(m.group(1), r.get("Path Number", "?"), r.get("Flight Direction", "?"))] += 1
    print(f"--- Sentinel-1 OPERA RTC: {len(rows)} bursts")
    for k in sorted(by):
        print(f"S1 {k[0]} track {k[1]} {k[2]} {by[k]} bursts")
except Exception as ex:
    print("Sentinel-1 search failed:", ex)
flt = (f"Collection/Name eq 'SENTINEL-2' and contains(Name,'MSIL2A') and "
       f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}') and "
       f"ContentDate/Start gt {ss}T00:00:00.000Z and ContentDate/Start lt {se}T00:00:00.000Z")
url = ("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?" +
       urllib.parse.urlencode({"$filter": flt, "$orderby": "ContentDate/Start asc", "$top": 200, "$expand": "Attributes"}, quote_via=urllib.parse.quote))
try:
    data = json.loads(get(url))["value"]
    print(f"--- Sentinel-2 L2A: {len(data)} scenes")
    for p in data:
        cc = next((a["Value"] for a in p.get("Attributes", []) if a["Name"] == "cloudCover"), None)
        tile = re.search(r"_T(\d{2}[A-Z]{3})_", p["Name"])
        print("S2", p["ContentDate"]["Start"][:10], tile.group(1) if tile else "?", f"cloud {cc:.0f}%" if cc is not None else "cloud ?")
except Exception as ex:
    print("Sentinel-2 search failed:", ex)
