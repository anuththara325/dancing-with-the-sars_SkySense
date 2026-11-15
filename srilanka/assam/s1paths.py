import sys, io, csv, urllib.parse, urllib.request, collections
W, S, E, N = map(float, sys.argv[1:5]); start, end = sys.argv[5], sys.argv[6]
wkt = f"POLYGON(({W} {S},{E} {S},{E} {N},{W} {N},{W} {S}))"
q = urllib.parse.urlencode({"dataset": "OPERA-S1", "processingLevel": "RTC", "intersectsWith": wkt,
                            "start": start + "T00:00:00Z", "end": end + "T23:59:59Z", "maxResults": 500, "output": "csv"})
txt = urllib.request.urlopen("https://api.daac.asf.alaska.edu/services/search/param?" + q, timeout=120).read().decode()
d = collections.defaultdict(set); b = collections.defaultdict(int)
for r in csv.DictReader(io.StringIO(txt)):
    k = (r["Path Number"], r.get("Ascending or Descending?", "?"))
    d[k].add(r.get("Start Time", r.get("Acquisition Date", ""))[:10]); b[k] += 1
for k in sorted(d):
    print("path", k[0], k[1], len(d[k]), "dates:", sorted(d[k]), "bursts:", b[k])
