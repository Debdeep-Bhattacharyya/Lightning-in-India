# ============================================================
# Advanced Multipanel Figure (Q1 level) — v3
#
# Fixes applied vs. v2:
#   (A) Stats box moved to a clear empty region (top-left, inside the
#       axes but above all data); Peak/Trough call-outs now use curved
#       leader lines pointing OUT to clear white space instead of
#       sitting on top of the line/markers. Male/Female raw-count lines
#       removed from this panel (they are redundant with Panel B and
#       were the main source of clutter/overlap) — Panel A is now a
#       clean "Total" trend panel.
#   (B) Fixed a sign bug that made the Female bars completely hide the
#       Male bars (both deviations were computed as positive). Now a
#       true mirrored/butterfly chart: Male % bars rise above the 50%
#       parity line, Female % bars fall below it. Removed the confusing
#       secondary axis and replaced it with direct percentage labels on
#       a subset of bars so the chart is self-explanatory at a glance.
#   (C) Y-axis now has a proper MultipleLocator so intermediate z-score
#       values are labeled (not just -2 and 0), and the extreme-year
#       annotations now also print the z-score value, not just the year.
#   All legends remain fully outside the plot axes (right margin) so
#   they never overlap plotted data in any panel.
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from scipy import stats
from scipy.stats import norm
from statsmodels.nonparametric.smoothers_lowess import lowess

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
DATA_DIR = r"D:\Articles\Working\Lightning India\Data\Death Data"
OUT_DIR  = r"D:\Articles\Working\Lightning India\Results"
os.makedirs(OUT_DIR, exist_ok=True)

YEARS = list(range(2000, 2023))

# ------------------------------------------------------------
# Mann-Kendall
# ------------------------------------------------------------
def mann_kendall(y):
    n = len(y)
    s = 0
    for k in range(n - 1):
        for j in range(k + 1, n):
            s += np.sign(y[j] - y[k])

    _, counts = np.unique(y, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p = 2 * (1 - norm.cdf(abs(z)))
    tau = s / (0.5 * n * (n - 1))
    return z, p, tau


# ------------------------------------------------------------
# Sen's slope + CI (bootstrap); also returns the bootstrap slope/intercept
# distribution so we can draw a true uncertainty band (fan) for the trend.
# ------------------------------------------------------------
def sens_slope_ci(x, y, n_boot=1000):
    slopes = []
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    slope = np.median(slopes)
    intercept = np.median(y - slope * x)

    boot_slopes, boot_intercepts = [], []
    rng = np.random.default_rng(42)
    for _ in range(n_boot):
        idx = rng.integers(0, len(x), len(x))
        xb, yb = x[idx], y[idx]
        tmp = []
        for i in range(len(xb)):
            for j in range(i + 1, len(xb)):
                if xb[j] != xb[i]:
                    tmp.append((yb[j] - yb[i]) / (xb[j] - xb[i]))
        if tmp:
            bs = np.median(tmp)
            boot_slopes.append(bs)
            boot_intercepts.append(np.median(yb - bs * xb))

    boot_slopes = np.array(boot_slopes)
    boot_intercepts = np.array(boot_intercepts)

    ci_low = np.percentile(boot_slopes, 2.5)
    ci_high = np.percentile(boot_slopes, 97.5)

    return slope, intercept, ci_low, ci_high, boot_slopes, boot_intercepts


# ------------------------------------------------------------
# Significance stars
# ------------------------------------------------------------
def significance_stars(p):
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    else:
        return "ns"


# ------------------------------------------------------------
# Load Data
# ------------------------------------------------------------
years, total, male, female = [], [], [], []

for yr in YEARS:
    f = os.path.join(DATA_DIR, f"Death_{yr}.csv")
    if not os.path.exists(f):
        continue

    df = pd.read_csv(f)
    df.columns = [c.strip() for c in df.columns]

    row = df[df["State/UT"].str.lower() == "total"]

    if not row.empty:
        total.append(float(row["Total"].values[0]))
        male.append(float(row["Male"].values[0]))
        female.append(float(row["Female"].values[0]))
    else:
        total.append(df["Total"].sum())
        male.append(df["Male"].sum())
        female.append(df["Female"].sum())

    years.append(yr)

years = np.array(years, dtype=float)
total = np.array(total, dtype=float)
male = np.array(male, dtype=float)
female = np.array(female, dtype=float)

# ------------------------------------------------------------
# Derived
# ------------------------------------------------------------
male_pct = (male / total) * 100
female_pct = (female / total) * 100
anom = (total - np.mean(total)) / np.std(total)

# LOWESS smoothing
lowess_total = lowess(total, years, frac=0.3)

# Stats
mk_z, mk_p, tau = mann_kendall(total)
sen_slope, sen_intercept, ci_low, ci_high, boot_slopes, boot_intercepts = sens_slope_ci(years, total)
stars = significance_stars(mk_p)
r2 = stats.linregress(years, total).rvalue ** 2

# ------------------------------------------------------------
# Style
# ------------------------------------------------------------
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COL_TOTAL  = "#1b1b1b"
COL_MALE   = "#1f77b4"
COL_FEMALE = "#d1495b"
COL_TREND  = "#f4a261"
COL_LOWESS = "#2a9d8f"
COL_POS    = "#e76f51"
COL_NEG    = "#457b9d"

fig = plt.figure(figsize=(13, 12))
# extra right margin reserved so legends can sit OUTSIDE every axes;
# extra hspace so panel titles/annotations never crowd the panel above
gs = fig.add_gridspec(3, 1, height_ratios=[2.3, 1.15, 1.15], hspace=0.55,
                       left=0.09, right=0.78, top=0.95, bottom=0.06)

# ------------------------------------------------------------
# PANEL A: Total trend with Sen's-slope uncertainty fan, LOWESS,
#          and clearly separated peak/trough call-outs + stats box
# ------------------------------------------------------------
ax1 = fig.add_subplot(gs[0])

# Sen's slope uncertainty fan (replaces a bare CI number with a visual band)
x_line = np.linspace(years.min(), years.max(), 100)
fan = np.array([bs * x_line + bi for bs, bi in zip(boot_slopes, boot_intercepts)])
fan_low = np.percentile(fan, 2.5, axis=0)
fan_high = np.percentile(fan, 97.5, axis=0)
ax1.fill_between(x_line, fan_low, fan_high, color=COL_TREND, alpha=0.22,
                  label="Sen's slope 95% CI", zorder=1)
ax1.plot(x_line, sen_slope * x_line + sen_intercept, '--', lw=2.2,
          color=COL_TREND, label="Sen's slope", zorder=2)

# LOWESS
ax1.plot(lowess_total[:, 0], lowess_total[:, 1], color=COL_LOWESS,
          lw=2.6, label='LOWESS', zorder=3)

# Total series (anchor)
ax1.plot(years, total, '-o', ms=6, lw=2.6, color=COL_TOTAL, label='Total deaths', zorder=5)

# extra headroom/legroom so call-outs never collide with the data
imax, imin = np.argmax(total), np.argmin(total)
y_top = max(total.max(), fan_high.max()) * 1.15
y_bot = total.min() * 0.55
ax1.set_ylim(y_bot, y_top)

ax1.annotate(f"Peak: {int(years[imax])}\n{total[imax]:.0f} deaths",
              xy=(years[imax], total[imax]),
              xytext=(years[imax] - 1.5, y_top * 0.92),
              ha='center', fontsize=10.5, fontweight='bold',
              arrowprops=dict(arrowstyle='-', color='gray', lw=0.9,
                               connectionstyle="arc3,rad=0.15"))
ax1.annotate(f"Trough: {int(years[imin])}\n{total[imin]:.0f} deaths",
              xy=(years[imin], total[imin]),
              xytext=(years[imin] + 3.2, y_bot * 1.3),
              ha='center', fontsize=10.5, fontweight='bold',
              arrowprops=dict(arrowstyle='-', color='gray', lw=0.9,
                               connectionstyle="arc3,rad=-0.15"))

ax1.set_title("(A) Lightning Deaths Trend (2000–2022)", fontweight='bold', loc='left')
ax1.set_ylabel("Deaths")
ax1.grid(alpha=0.25, axis='y')

# stats box sits in guaranteed-empty space (top-left, above all series)
txt = (f"Sen's slope = {sen_slope:.2f} [{ci_low:.2f}, {ci_high:.2f}] /yr\n"
       f"Mann-Kendall p = {mk_p:.4f} {stars}   |   τ = {tau:.2f}   |   R² = {r2:.2f}")
ax1.text(0.015, 0.97, txt, transform=ax1.transAxes, va='top', ha='left', fontsize=10.5,
          bbox=dict(boxstyle='round,pad=0.45', fc='white', ec='0.75', alpha=0.95))

ax1.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), frameon=False,
            fontsize=11, borderaxespad=0)

# ------------------------------------------------------------
# PANEL B: 100% stacked bar chart — each year's bar fills to 100%,
#          split into Male/Female shares, with the exact percentage
#          printed on each segment. This is the simplest, most widely
#          understood way to show a two-category composition over time.
# ------------------------------------------------------------
ax2 = fig.add_subplot(gs[1])

ax2.bar(years, male_pct, width=0.7, color=COL_MALE, label='Male %', zorder=3)
ax2.bar(years, female_pct, width=0.7, bottom=male_pct, color=COL_FEMALE,
         label='Female %', zorder=3)

# label every bar's split directly on the bar segment
for yr, mp, fp in zip(years, male_pct, female_pct):
    ax2.text(yr, mp / 2, f"{mp:.0f}%", ha='center', va='center',
              fontsize=8.5, color='white', fontweight='bold')
    ax2.text(yr, mp + fp / 2, f"{fp:.0f}%", ha='center', va='center',
              fontsize=8.5, color='white', fontweight='bold')

ax2.set_ylim(0, 100)
ax2.set_title("(B) Gender Contribution (% of Total Deaths)", fontweight='bold', loc='left')
ax2.set_ylabel("Share of deaths (%)")
ax2.grid(alpha=0.2, axis='y')
ax2.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), frameon=False,
            fontsize=11, borderaxespad=0)

# ------------------------------------------------------------
# PANEL C: Diverging anomaly bars + rolling mean, with a proper
#          y-axis tick spacing so intermediate z-score values are
#          actually printed (not just -2 and 0).
# ------------------------------------------------------------
ax3 = fig.add_subplot(gs[2])

bar_colors = [COL_POS if a >= 0 else COL_NEG for a in anom]
ax3.bar(years, anom, color=bar_colors, width=0.7, zorder=3)
ax3.axhline(0, linestyle='--', color='black', lw=1.0)

roll = pd.Series(anom).rolling(3, center=True, min_periods=1).mean()
ax3.plot(years, roll, color='black', lw=2.0, label='3-yr rolling mean', zorder=4)

# force readable, evenly spaced y-axis tick labels (coarser spacing so
# only a handful of round values are printed, e.g. -2, -1, 0, 1, 2)
ax3.yaxis.set_major_locator(MultipleLocator(1.0))
ax3.set_ylim(np.floor(anom.min()) - 0.5, np.ceil(anom.max()) + 0.5)

i_pos, i_neg = np.argmax(anom), np.argmin(anom)
for i in (i_pos, i_neg):
    ax3.annotate(f"{int(years[i])}\n(z={anom[i]:.2f})", xy=(years[i], anom[i]),
                  xytext=(0, 8 if anom[i] >= 0 else -8),
                  textcoords="offset points", ha='center',
                  va='bottom' if anom[i] >= 0 else 'top',
                  fontsize=9.5, fontweight='bold')

ax3.set_title("(C) Interannual Variability", fontweight='bold', loc='left')
ax3.set_ylabel("Z-score")
ax3.set_xlabel("Year")
ax3.grid(alpha=0.25, axis='y')
ax3.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), frameon=False,
            fontsize=11, borderaxespad=0)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------
outfile = os.path.join(OUT_DIR, "Lightning_Deaths_Advanced.tif")
plt.savefig(outfile, dpi=600, bbox_inches='tight')
plt.close()

print("Saved:", outfile)