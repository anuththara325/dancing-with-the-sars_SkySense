import csv, datetime as dt
rows = open("power_minneriya.csv").read().splitlines()
i = [k for k, l in enumerate(rows) if "END HEADER" in l][0]
rain = {}
for r in csv.DictReader(rows[i+1:]):
    d = dt.date(int(r["YEAR"]), 1, 1) + dt.timedelta(days=int(r["DOY"]) - 1); v = float(r["PRECTOTCORR"])
    rain[d] = v if v >= 0 else 0.0
passes = ["2026-06-20","2026-07-02","2026-07-14","2026-07-26","2026-08-19","2026-08-31","2026-09-12","2026-09-24","2026-10-06","2026-10-18"]
P = [dt.date.fromisoformat(p) for p in passes]
s = lambda a, b: sum(rain.get(a + dt.timedelta(days=k), 0) for k in range((b - a).days + 1))
out = ["date,mm_since_prev_pass,mm_prev3d,mm_prev7d"]
print("date        since_prev  prev3d  prev7d")
for k, d in enumerate(P):
    sp = s(P[k-1], d - dt.timedelta(days=1)) if k else float("nan")
    r3 = s(d - dt.timedelta(days=3), d - dt.timedelta(days=1)); r7 = s(d - dt.timedelta(days=7), d - dt.timedelta(days=1))
    print(d, "%9.1f %8.1f %7.1f" % (sp, r3, r7)); out.append(f"{d},{sp:.1f},{r3:.1f},{r7:.1f}")
open("web_minneriya/rain.csv", "w").write("\n".join(out))
print("wettest days:", sorted(((v, str(k)) for k, v in rain.items()), reverse=True)[:6])
