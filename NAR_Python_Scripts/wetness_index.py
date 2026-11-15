#!/usr/bin/env python3
"""
wetness_index.py  -  Dancing with the SARs / SkySense

Per-pixel NISAR wetness index (0 = this pixel's driest pass, 1 = its wettest pass),
compared with daily rain, plus a "slow-drying" map.

Idea:
  1. For every pixel, take HH (or HV) on all pass dates.
  2. Scale each pixel between its own dry and wet reference:
         W = (HH - HH_dry) / (HH_wet - HH_dry), clipped to 0..1
     (dry = 2nd-lowest pass, wet = 2nd-highest pass, so one odd date cannot set the scale).
     This removes terrain brightness: a bright slope and a dark field both run 0..1.
  3. "Drying-test" passes = little rain in the 3 days before the pass, but real rain in
     the 4-14 days before it. On those dates:
         fast-drying pixel -> W already back near 0
         slow-drying pixel -> W still high
     Retention = mean W on the drying-test passes -> colour classes.

Usage (WSL, in ~/nisar, next to per_pixel_rain.py):
  python3 -u wetness_index.py \
      --dir  ~/nisar/DataSet/Nawalapitiya/Ascending_RGB \
      --rain ~/nisar/DataSet/Nawalapitiya/Rainfall.csv \
      --site Nawalapitiya --out ~/nisar/DataSet/Nawalapitiya/results/wetness_asc

Options: --channel HH|HV, --smooth 11 (pixels, linear boxcar), --block 25 (average blocks
instead), --min-range 0.6 (dB; smaller dry-wet range = "no clear change").
"""
import argparse, csv, glob, os, re, sys, warnings
from datetime import date, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import per_pixel_rain as ppr   # same folder: reuses reading, smoothing, offsets

warnings.simplefilter("ignore", RuntimeWarning)

DRY3_MAX = 6.0      # mm in the 3 days before the pass
WET4_14_MIN = 50.0  # mm in days 4-14 before the pass
# Classes are RELATIVE to the scene: lowest third of retention = "dries faster than typical",
# highest third = "stays wet longer than typical". The absolute edges are printed.


def rain_sum(rain, d, first, last):
    """Sum of rain on days d-last .. d-first (pass day excluded when first >= 1)."""
    return float(np.nansum([rain.get(d - timedelta(days=i), np.nan) for i in range(first, last + 1)]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--rain", required=True)
    ap.add_argument("--site", default="site")
    ap.add_argument("--out", default=None)
    ap.add_argument("--channel", default="HH", choices=["HH", "HV"])
    ap.add_argument("--smooth", type=int, default=11)
    ap.add_argument("--block", type=int, default=1)
    ap.add_argument("--min-range", type=float, default=0.6)
    ap.add_argument("--no-offset", action="store_true")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(os.path.expanduser(a.dir), "*_db.tif")))
    out = os.path.expanduser(a.out or os.path.join(a.dir, "wetness"))
    os.makedirs(out, exist_ok=True)
    rain = ppr.read_giovanni_csv(os.path.expanduser(a.rain))

    meta = []
    for f in files:
        m = re.search(r"(T\d{3}[AD])_(\d{8})_db\.tif$", os.path.basename(f))
        if m:
            s = m.group(2)
            meta.append((f, m.group(1), s, date(int(s[:4]), int(s[4:6]), int(s[6:]))))
    tracks = {t for _, t, _, _ in meta}
    if len(tracks) != 1 or len(meta) < 6:
        sys.exit(f"Need >= 6 dates of one track, found {len(meta)} dates, tracks {tracks}")
    track = tracks.pop()
    key = a.channel
    tag = f"{a.site}_{track}_{key}" + (f"_b{a.block}" if a.block > 1 else "")

    # ---- load
    stack, geo0, dates = [], None, []
    for f, tr, s, d in meta:
        bands, geo = ppr.read_bands(f)
        if geo0 is None:
            geo0 = geo
        elif geo[0] != geo0[0] or geo[2:] != geo0[2:]:
            sys.exit(f"{f} is not on the same grid as the first file")
        arr = ppr.pick(bands, key, 0 if key == "HH" else 1)
        off = 0.0
        if not a.no_offset and tr in ppr.OFFSETS and s in ppr.OFFSETS[tr]["dates"]:
            off = ppr.OFFSETS[tr][key]
        arr = ppr.block_db(arr, a.block) if a.block > 1 else ppr.boxcar_db(arr, a.smooth)
        stack.append(arr + off)
        dates.append(d)
    stack = np.stack(stack).astype(np.float32)
    geo = ppr.block_geo(geo0, a.block)
    n = len(dates)

    # ---- quality mask (same rules as per_pixel_rain)
    mean = np.nanmean(stack, 0)
    good = np.isfinite(mean) & np.isfinite(stack).all(0)
    if key == "HH":
        good &= (mean < ppr.LAYOVER_DB) & (mean > -15.0)   # -15 dB: open water (reservoir)
    else:
        good &= mean > ppr.SHADOW_DB

    # ---- 0..1 wetness index per pixel
    srt = np.sort(np.where(good, stack, np.nan), axis=0)
    dry, wet = srt[1], srt[n - 2]                 # 2nd lowest / 2nd highest
    rng = wet - dry
    changing = good & (rng >= a.min_range)
    with np.errstate(divide="ignore", invalid="ignore"):
        W = np.clip((stack - dry) / rng, 0, 1)
    W[:, ~changing] = np.nan

    # ---- rain per pass
    r1 = np.array([rain.get(d, np.nan) for d in dates])
    r3 = np.array([rain_sum(rain, d, 1, 3) for d in dates])
    r7 = np.array([rain_sum(rain, d, 1, 7) for d in dates])
    r414 = np.array([rain_sum(rain, d, 4, 14) for d in dates])
    test = (r3 <= DRY3_MAX) & (r414 >= WET4_14_MIN)
    print(f"{a.site} {track} {key}: {n} dates; usable {good.mean() * 100:.1f}%, "
          f"changing (range >= {a.min_range} dB) {changing.mean() * 100:.1f}%; "
          f"median dry->wet range {np.nanmedian(rng[good]):.2f} dB")
    boxW = [float(np.nanmean(w)) for w in W]
    for i, d in enumerate(dates):
        print(f"  {d}  W(box mean)={boxW[i]:.2f}  rain3={r3[i]:6.1f}  rain4-14={r414[i]:6.1f}  rain7={r7[i]:6.1f}"
              + ("   <- drying test" if test[i] else ""))
    have_ret = bool(test.sum())
    if not have_ret:
        print("  (no drying-test passes: retention / drying-class maps skipped - they are not used in the pitch anyway)")
    print(f"  r(box W, rain7) = {np.corrcoef(boxW, r7)[0, 1]:+.2f}")

    # ---- retention = mean W on drying-test passes
    if have_ret:
        ret = np.nanmean(W[test], 0)
        ret[~changing] = np.nan
    else:
        ret = np.full(W.shape[1:], np.nan, np.float32)
    e1, e2 = np.nanpercentile(ret, [33.3, 66.7]) if have_ret else (np.nan, np.nan)
    CLASS_EDGES = (e1, e2)
    if have_ret: print(f"  retention tertile edges: {e1:.2f}, {e2:.2f}")
    cls = np.full(ret.shape, np.nan, np.float32)
    cls[good] = 0
    ok = np.isfinite(ret)
    cls[ok & (ret < CLASS_EDGES[0])] = 1
    cls[ok & (ret >= CLASS_EDGES[0]) & (ret < CLASS_EDGES[1])] = 2
    cls[ok & (ret >= CLASS_EDGES[1])] = 3

    # ---- write rasters
    if have_ret:
        ppr.write_tif(f"{out}/{tag}_retention.tif", ret.astype(np.float32), geo)
        ppr.write_tif(f"{out}/{tag}_drying_class.tif", cls, geo)
    for i, d in enumerate(dates):
        ppr.write_tif(f"{out}/{tag}_W_{d:%Y%m%d}.tif", W[i].astype(np.float32), geo)

    # ---- figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    wcmap = plt.get_cmap("YlGnBu")      # pale = dry, dark blue = wet
    if have_ret:
        ppr.save_png(f"{out}/{tag}_retention.png", ret,
                     f"{a.site} {track} {key}: wetness kept on drying days (0 = dried out, 1 = still wet)",
                     "YlGnBu", 0, 1, "retention (mean wetness on drying-test passes)")
        ppr.save_png(f"{out}/{tag}_drying_class.png", cls,
                     f"{a.site} {track} {key}: how fast the ground dries after rain",
                     ListedColormap(["#d9d9d9", "#fdae61", "#66bd63", "#2166ac"]), -0.5, 3.5, "",
                     ticks=[0, 1, 2, 3],
                     ticklabels=["no clear change", "dries faster than typical", "typical", "stays wet longer"])

    # per-date frames + grid + animation
    frames = []
    for i, d in enumerate(dates):
        fig, ax = plt.subplots(figsize=(5, 5 * W.shape[1] / W.shape[2] + 0.9), dpi=120)
        ax.imshow(np.ma.masked_invalid(W[i]), cmap=wcmap, vmin=0, vmax=1, interpolation="nearest")
        ax.set_axis_off()
        ax.set_title(f"{a.site} {key} wetness  {d:%d %b %Y}\nrain previous 7 days: {r7[i]:.0f} mm"
                     + ("  (drying test)" if test[i] else ""), fontsize=9)
        fig.tight_layout()
        p = f"{out}/{tag}_W_{d:%Y%m%d}.png"
        fig.savefig(p, facecolor="white")
        plt.close(fig)
        frames.append(p)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3 * W.shape[1] / W.shape[2] + 0.6), dpi=120)
    for i, ax in enumerate(np.ravel(axs)):
        ax.set_axis_off()
        if i < n:
            im = ax.imshow(np.ma.masked_invalid(W[i]), cmap=wcmap, vmin=0, vmax=1, interpolation="nearest")
            ax.set_title(f"{dates[i]:%d %b}  ({r7[i]:.0f} mm)" + (" *" if test[i] else ""), fontsize=8)
    fig.colorbar(im, ax=axs, fraction=0.02, pad=0.01, label="wetness index (0 dry - 1 wet)")
    fig.suptitle(f"{a.site} {track} {key}: per-pixel wetness index  (* = drying-test pass)", fontsize=10)
    fig.savefig(f"{out}/{tag}_W_grid.png", facecolor="white")
    plt.close(fig)
    try:
        from PIL import Image
        ims = [Image.open(p).convert("RGB") for p in frames]
        ims[0].save(f"{out}/{tag}_W_animation.gif", save_all=True, append_images=ims[1:], duration=900, loop=0)
        ims[0].save(f"{out}/{tag}_W_animation.webp", save_all=True, append_images=ims[1:], duration=900, loop=0, quality=80)
    except Exception as e:
        print("  (animation skipped:", e, ")")

    # day-by-day rain with box wetness
    days = [dates[0] - timedelta(days=10) + timedelta(days=i)
            for i in range((dates[-1] - dates[0]).days + 11)]
    fig, ax = plt.subplots(figsize=(9, 3.4), dpi=150)
    ax.bar(days, [rain.get(d, np.nan) for d in days], width=1.0, color="#9ecae1", label="daily rain (mm)")
    ax.set_ylabel("daily rain (mm)")
    ax2 = ax.twinx()
    ax2.plot(dates, boxW, "o-", color="#08306b", label=f"{key} wetness index (box mean)")
    for d, t in zip(dates, test):
        if t:
            ax2.plot(d, boxW[dates.index(d)], "s", ms=10, mfc="none", mec="#d7301f")
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("wetness index 0-1")
    ax.set_title(f"{a.site} {track}: daily rain vs NISAR {key} wetness (red squares = drying-test passes)", fontsize=9)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(f"{out}/{tag}_rain_vs_wetness.png")
    plt.close(fig)

    # ---- tables
    with open(f"{out}/{tag}_dates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "box_mean_W", "rain_pass_day_mm", "rain3_mm", "rain4_14_mm", "rain7_mm", "drying_test"])
        for i, d in enumerate(dates):
            w.writerow([d.isoformat(), round(boxW[i], 3), round(r1[i], 1), round(r3[i], 1),
                        round(r414[i], 1), round(r7[i], 1), bool(test[i])])
    c = cls[good]
    summ = {"site": a.site, "track": track, "channel": key, "block": a.block, "smooth": a.smooth,
            "n_dates": n, "drying_test_dates": " ".join(f"{d:%Y%m%d}" for d, t in zip(dates, test) if t),
            "median_range_dB": round(float(np.nanmedian(rng[good])), 2),
            "median_retention": round(float(np.nanmedian(ret)), 3) if have_ret else "",
            "tertile_edges": f"{CLASS_EDGES[0]:.3f} {CLASS_EDGES[1]:.3f}" if have_ret else "",
            "pct_fast": round(float(np.mean(c == 1) * 100), 1),
            "pct_medium": round(float(np.mean(c == 2) * 100), 1),
            "pct_slow": round(float(np.mean(c == 3) * 100), 1),
            "pct_no_clear_change": round(float(np.mean(c == 0) * 100), 1),
            "r_boxW_rain7": round(float(np.corrcoef(boxW, r7)[0, 1]), 3)}
    with open(f"{out}/{tag}_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ))
        w.writeheader()
        w.writerow(summ)
    print(f"\nDone -> {out}\n  {summ}")


if __name__ == "__main__":
    main()
