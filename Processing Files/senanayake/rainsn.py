import csv, datetime as dt
lines = open("power_senanayake.csv").read().splitlines()
i = [k for k, l in enumerate(lines) if l.startswith("YEAR")][0]
rows = []
for r in csv.DictReader(lines[i:]):
    d = dt.date(int(r["YEAR"]), 1, 1) + dt.timedelta(int(r["DOY"]) - 1)
    rows.append((d, max(float(r["PRECTOTCORR"]), 0.0)))
with open("web_senanayake/rain.csv", "w") as f:
    f.write("date,mm,mm_3day\n")
    for k, (d, mm) in enumerate(rows):
        f.write("%s,%.1f,%.1f\n" % (d, mm, sum(x for _, x in rows[max(0, k-2):k+1])))
passes = [dt.date(2026, m, d) for m, d in [(6,20),(7,2),(7,14),(7,26),(8,19),(8,31),(9,12),(9,24),(10,6),(10,18)]]
print("rain (mm) between consecutive NISAR passes, and 3 days before each pass")
for a, b in zip(passes[:-1], passes[1:]):
    print(a, "->", b, "%.1f" % sum(x for d, x in rows if a < d <= b), "| 3 days before:", "%.1f" % sum(x for d, x in rows if b - dt.timedelta(2) <= d <= b))
