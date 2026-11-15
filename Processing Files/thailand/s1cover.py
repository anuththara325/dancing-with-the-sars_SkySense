import csv, io, urllib.request, urllib.parse
W,S,E,N = 101.38,14.00,101.46,14.08
pts = [(W,S),(E,S),(W,N),(E,N),((W+E)/2,(S+N)/2)]
sets = []
for lon,lat in pts:
    q = urllib.parse.urlencode({"dataset":"OPERA-S1","processingLevel":"RTC",
        "intersectsWith":f"POINT({lon} {lat})","start":"2026-09-20","end":"2026-10-20","output":"csv"})
    txt = urllib.request.urlopen("https://api.daac.asf.alaska.edu/services/search/param?"+q, timeout=120).read().decode()
    rows = list(csv.DictReader(io.StringIO(txt)))
    sets.append({(r["Path Number"], r["Ascending or Descending?"]) for r in rows})
    print(f"{lon:.3f},{lat:.3f}: {sorted(sets[-1])}")
print("\nCOVER ALL 5 POINTS:", sorted(set.intersection(*sets)))
