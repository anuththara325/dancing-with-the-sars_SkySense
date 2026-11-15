import sys, csv, datetime as dt, urllib.request
lon, lat, start, end, out = sys.argv[1:6]; tags = sys.argv[6].split(",")
MON = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6, jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)
url = "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=AG&longitude=%s&latitude=%s&start=%s&end=%s&format=CSV" % (lon, lat, start, end)
lines = urllib.request.urlopen(url, timeout=120).read().decode().splitlines()
i = [k for k, l in enumerate(lines) if "END HEADER" in l][0]
hdr = lines[i+1].split(","); iy, idoy, ip = hdr.index("YEAR"), hdr.index("DOY"), hdr.index("PRECTOTCORR")
rain = {}
for l in lines[i+2:]:
    p = l.split(",")
    if len(p) > ip:
        v = float(p[ip]); rain[dt.date(int(p[iy]), 1, 1) + dt.timedelta(days=int(p[idoy]) - 1)] = 0.0 if v < 0 else v
with open(out + "/rain_daily.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(["date", "rain_mm"])
    for d in sorted(rain): wr.writerow([d.isoformat(), "%.1f" % rain[d]])
ds = [dt.date(2026, MON[t[:3]], int(t[3:])) for t in tags]
print("rain between NISAR passes (mm; POWER MERRA-2 ~50 km, not a gauge):")
with open(out + "/rain.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(["from", "to", "rain_mm"])
    for a, b in zip(ds[:-1], ds[1:]):
        s = sum(v for d, v in rain.items() if a < d <= b); wr.writerow([a, b, "%.1f" % s]); print(" ", a, "->", b, "%.1f" % s)
print("last 12 days of data:", " ".join("%s:%.0f" % (d.strftime("%d%b"), rain[d]) for d in sorted(rain)[-12:]))
