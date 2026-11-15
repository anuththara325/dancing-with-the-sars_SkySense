#!/usr/bin/env python3
"""One graph per track: green-pixel intensity (line 1) and daily rainfall (line 2).
Usage: python3 plot_green_rain.py <green_stats.csv> <giovanni_rain.csv> [column]"""
import sys, csv, datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md

green_csv, rain_csv = sys.argv[1], sys.argv[2]
col = sys.argv[3] if len(sys.argv) > 3 else "G_mean"
labels = {"G_mean": "green pixel intensity (mean, 0-255)", "G_median": "green pixel intensity (median, 0-255)",
          "green_pct": "green pixels (% of scene)", "HV_mean_dB": "HV of green pixels (dB)"}

rain = []
for r in csv.reader(open(rain_csv)):
    if len(r) < 2 or "/" not in r[0]:
        continue
    try:
        m, d, y = map(int, r[0].strip().split("/")); v = float(r[1])
    except ValueError:
        continue
    if v > -9999:
        rain.append((dt.date(y, m, d), v))

rows = list(csv.DictReader(open(green_csv)))
for track, name in (("T084A", "Ascending (track 084, 05:44)"), ("T048D", "Descending (track 048, 18:34)")):
    pts = sorted((dt.date.fromisoformat(r["date"]), float(r[col])) for r in rows
                 if r["track"] == track and r[col] not in ("", "None"))
    if not pts:
        continue
    fig, ax1 = plt.subplots(figsize=(11, 4.8))
    ax2 = ax1.twinx()
    ax2.plot([d for d, _ in rain], [v for _, v in rain], color="#7F93A8", lw=1.2, label="daily rainfall (mm/day)")
    ax1.plot([d for d, _ in pts], [v for _, v in pts], color="#2DB800", lw=2.2, marker="o", ms=7,
             label=labels.get(col, col), zorder=5)
    ax1.set_zorder(ax2.get_zorder() + 1); ax1.patch.set_visible(False)
    ax1.set_ylabel(labels.get(col, col), color="#2DB800")
    ax2.set_ylabel("rainfall (mm/day)", color="#7F93A8")
    ax1.axvspan(dt.date(2026, 7, 27), dt.date(2026, 8, 10), color="#eeeeee", zorder=0)
    ax1.text(dt.date(2026, 7, 28), ax1.get_ylim()[1], "NISAR\ndata gap", fontsize=8, color="#777777", va="top")
    ax1.xaxis.set_major_locator(md.MonthLocator()); ax1.xaxis.set_major_formatter(md.DateFormatter("%b %Y"))
    ax1.grid(axis="y", color="#eeeeee")
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    ax1.set_title(f"Nawalapitiya {name}: green pixel intensity and rainfall", loc="left")
    fig.text(0.01, 0.01, "Rainfall: GPM IMERG Late daily (Giovanni). Green: NISAR GCOV composite (R=HH, G=HV, B=HH/HV).",
             fontsize=7.5, color="#777777")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = f"green_rain_{track}.png"
    fig.savefig(out, dpi=150); plt.close(fig)
    print("saved", out)
