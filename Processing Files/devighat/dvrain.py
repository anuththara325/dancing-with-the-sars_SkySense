import csv, datetime as dt
lines = open("power_devighat.csv").read().splitlines()
i = [k for k, l in enumerate(lines) if "END HEADER" in l][0]
hdr = lines[i+1].split(","); iy, idoy, ip = hdr.index("YEAR"), hdr.index("DOY"), hdr.index("PRECTOTCORR")
rain = {}
for l in lines[i+2:]:
    p = l.split(",")
    if len(p) <= ip: continue
    v = float(p[ip]); d_ = dt.date(int(p[iy]), 1, 1) + dt.timedelta(days=int(p[idoy]) - 1)
    rain[d_] = 0.0 if v < 0 else v
print("days", len(rain), min(rain), max(rain), "missing(-999):", sum(1 for l in lines[i+2:] if l.split(",")[ip].startswith("-999")))
with open("web_devighat/rain_daily.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date","rain_mm"])
    for d_ in sorted(rain): w.writerow([d_.isoformat(), "%.1f" % rain[d_]])
N = ["2026-06-20","2026-07-02","2026-07-14","2026-07-26","2026-08-19","2026-08-31","2026-09-12","2026-09-24","2026-10-06","2026-10-18"]
S = ["2026-06-22","2026-06-29","2026-07-11","2026-07-23","2026-08-04","2026-08-16","2026-08-28","2026-09-09","2026-09-21","2026-10-03","2026-10-15"]
def between(ds, name, fn):
    ds = [dt.date.fromisoformat(x) for x in ds]
    with open(fn, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["from","to","rain_mm"])
        print("rain between", name, "passes (mm; POWER MERRA-2 ~50 km, not a gauge):")
        for a, b in zip(ds[:-1], ds[1:]):
            s = sum(v for d_, v in rain.items() if a < d_ <= b); w.writerow([a, b, "%.1f" % s]); print(" ", a, "->", b, "%.1f" % s)
between(N, "NISAR", "web_devighat/rain.csv")
between(S, "Sentinel-1", "web_devighat/rain_s1.csv")
print("daily rain 17-31 Aug:", " ".join("%d:%.1f" % (d_.day, rain[d_]) for d_ in sorted(rain) if dt.date(2026,8,17) <= d_ <= dt.date(2026,8,31)))
print("total 17-26 Aug %.1f mm; 27-31 Aug %.1f mm" % (sum(v for d_, v in rain.items() if dt.date(2026,8,17) <= d_ <= dt.date(2026,8,26)), sum(v for d_, v in rain.items() if dt.date(2026,8,27) <= d_ <= dt.date(2026,8,31))))
