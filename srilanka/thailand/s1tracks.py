import csv, io, urllib.request, urllib.parse, collections
W,S,E,N = 101.38,14.00,101.46,14.08
poly = f"POLYGON(({W} {S},{E} {S},{E} {N},{W} {N},{W} {S}))"
q = urllib.parse.urlencode({"dataset":"OPERA-S1","processingLevel":"RTC","intersectsWith":poly,
    "start":"2026-06-20","end":"2026-10-31","output":"csv"})
txt = urllib.request.urlopen("https://api.daac.asf.alaska.edu/services/search/param?"+q, timeout=180).read().decode()
rows = list(csv.DictReader(io.StringIO(txt)))
by = collections.defaultdict(lambda: collections.defaultdict(int))
for r in rows:
    k = (r["Path Number"], r["Ascending or Descending?"][:4])
    by[k][r["Start Time"][:10]] += 1
for k in sorted(by):
    d = by[k]
    print(f"\nTrack {k[0]} {k[1]}: {len(d)} dates, bursts/date = {sorted(set(d.values()))}")
    print("  ", " ".join(x[5:] for x in sorted(d)))
