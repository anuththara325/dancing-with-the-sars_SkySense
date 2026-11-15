import datetime as dt, csv, sys, os
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SM_FILE   = sys.argv[1] if len(sys.argv) > 1 else "soil_moisture_ampara.csv"
RAIN_FILE = sys.argv[2] if len(sys.argv) > 2 else "rain_ampara.csv"
OUT       = sys.argv[3] if len(sys.argv) > 3 else "."
WIN = 1                                     # AMSR2 mean over pass day +/- 1 day

def load(f):
    d = {}
    for l in open(f):
        p = [s.strip() for s in l.split(",")]
        try:
            v = float(p[1])
            if v > -9000: d[dt.date.fromisoformat(p[0][:10])] = v
        except (ValueError, IndexError): pass
    return d
sm, rain = load(SM_FILE), load(RAIN_FILE)

# NISAR descending T120D: HH on fixed HH-dominant pixels, HV box mean (dB)
HH = {"20260622": -8.43, "20260704": -9.05, "20260716": -9.12, "20260821": -7.77, "20260902": -8.70,
      "20260914": -8.07, "20260926": -8.48, "20261008": -7.60, "20261020": -7.33}
HV = {"20260622": -12.46, "20260704": -12.84, "20260716": -12.91, "20260821": -12.33, "20260902": -12.65,
      "20260914": -12.43, "20260926": -12.58, "20261008": -12.07, "20261020": -11.93}
QP = {"20260821", "20260902", "20260914", "20260926"}

rows = []
for d in sorted(HH):
    D = dt.datetime.strptime(d, "%Y%m%d").date()
    v = [sm[D + dt.timedelta(k)] for k in range(-WIN, WIN + 1) if D + dt.timedelta(k) in sm]
    rows.append(dict(date=d, D=D, HH=HH[d], HV=HV[d], SM=np.mean(v) if v else np.nan, n_sm=len(v),
                     rain1=rain.get(D, 0.0), qp=d in QP))
with open(os.path.join(OUT, "nisar_vs_amsr2_soilmoisture.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["date", "mode", "HH_dB", "HV_dB", "AMSR2_SM_3day", "n_AMSR2_obs", "rain_pass_day_mm"])
    for r in rows: w.writerow([r["date"], "quad-pol" if r["qp"] else "dual-pol", r["HH"], r["HV"],
                               round(r["SM"], 1), r["n_sm"], round(r["rain1"], 1)])

def corr(a, b):
    a, b = np.array(a, float), np.array(b, float); ok = np.isfinite(a) & np.isfinite(b)
    return np.corrcoef(a[ok], b[ok])[0, 1]
SMv = [r["SM"] for r in rows]
rHH, rHV = corr(SMv, [r["HH"] for r in rows]), corr(SMv, [r["HV"] for r in rows])
dual = [r for r in rows if not r["qp"]]
rHHd = corr([r["SM"] for r in dual], [r["HH"] for r in dual])
print(f"r(AMSR2 SM, HH) = {rHH:.2f}   r(AMSR2 SM, HV) = {rHV:.2f}   dual-pol only HH: {rHHd:.2f} (n={len(dual)})")

# ---------- figure 1: time series ----------
sd = sorted(sm); sv = np.array([sm[d] for d in sd])
full = [sd[0] + dt.timedelta(i) for i in range((sd[-1] - sd[0]).days + 1)]
roll = [np.mean([sm[x] for x in sm if abs((x - d).days) <= 3]) for d in full]
rd = sorted(rain)

fig, (a1, a2) = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"height_ratios": [1, 1.3]})
a1.bar(rd, [rain[d] for d in rd], width=1, color="steelblue", alpha=.6, label="GPM IMERG rain (mm/day)")
a1.set_ylabel("Rain (mm/day)"); a1.legend(loc="upper left"); a1.grid(alpha=.3)
a1.set_title("Ampara 2026: rainfall, AMSR2 soil moisture and NISAR L-band backscatter (track 120 descending)")

a2.scatter(sd, sv, s=12, color="saddlebrown", alpha=.5, label="AMSR2 soil moisture (daily)")
a2.plot(full, roll, color="saddlebrown", lw=2, label="AMSR2 7-day mean")
a2.set_ylabel("AMSR2 volumetric soil moisture (%)", color="saddlebrown")
b2 = a2.twinx()
dd = [r["D"] for r in rows]
b2.plot(dd, [r["HH"] for r in rows], "s-", color="red", lw=2, label="NISAR HH (dB)")
b2.plot(dd, [r["HV"] + 4 for r in rows], "o-", color="green", lw=2, label="NISAR HV + 4 dB (offset for display)")
for r in rows:
    if r["qp"]: b2.axvspan(r["D"] - dt.timedelta(days=1), r["D"] + dt.timedelta(days=1), color="grey", alpha=.2)
b2.set_ylabel("NISAR backscatter (dB)")
h1, l1 = a2.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
a2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9); a2.grid(alpha=.3)
a2.text(0.99, 0.02, "grey = NISAR quad-pol dates", transform=a2.transAxes, ha="right", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "soilmoisture_timeseries.png"), dpi=150); plt.close()

# ---------- figure 2: scatter ----------
fig, axs = plt.subplots(1, 2, figsize=(13, 5.5))
for ax, key, col, rr in ((axs[0], "HH", "red", rHH), (axs[1], "HV", "green", rHV)):
    X = np.array(SMv); Y = np.array([r[key] for r in rows]); ok = np.isfinite(X)
    for r, x, y in zip(rows, X, Y):
        ax.scatter(x, y, s=80, color="grey" if r["qp"] else col, edgecolor="k", zorder=3)
        ax.annotate(r["D"].strftime("%d %b"), (x, y), textcoords="offset points", xytext=(5, 4), fontsize=8)
    k, c = np.polyfit(X[ok], Y[ok], 1); xs = np.linspace(X[ok].min(), X[ok].max(), 20)
    ax.plot(xs, k * xs + c, "k--", lw=1, label=f"slope {k:.3f} dB per % SM")
    ax.set_xlabel("AMSR2 soil moisture, 3-day mean around pass (%)"); ax.set_ylabel(f"NISAR {key} (dB)")
    ax.set_title(f"NISAR {key} vs AMSR2 soil moisture:  r = {rr:.2f}, n = {ok.sum()}"); ax.legend(); ax.grid(alpha=.3)
fig.suptitle("Ampara 2026 - grey points = quad-pol mode", fontsize=11)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "soilmoisture_scatter.png"), dpi=150); plt.close()
print("saved nisar_vs_amsr2_soilmoisture.csv, soilmoisture_timeseries.png, soilmoisture_scatter.png")
