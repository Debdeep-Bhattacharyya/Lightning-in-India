# ============================================================
# DIURNAL LIGHTNING CONTRIBUTION OVER INDIA
# SMOOTH CURVE + GRADIENT COLOR
# TRMM-LIS vs ISS-LIS | SIDE-BY-SIDE
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import matplotlib.colors as mcolors
from scipy.signal import savgol_filter
from scipy.interpolate import make_interp_spline

# ---------------- PATHS ----------------
base_dir = r"D:\Articles\Almost Done\India Lightning"
input_file = base_dir + r"\Excel Files\India_LIS_AllYears_State_Season.xlsx"

fig_dir = base_dir + r"\Figures"
excel_out_dir = base_dir + r"\Derived_Statistics"

os.makedirs(fig_dir, exist_ok=True)
os.makedirs(excel_out_dir, exist_ok=True)

# ---------------- LOAD DATA ----------------
df = pd.read_excel(input_file)
df["Hour"] = pd.to_datetime(df["IST"], format="%H:%M:%S").dt.hour

# ---------------- PERIOD SPLIT ----------------
df_trmm = df[(df["Year"] >= 2000) & (df["Year"] <= 2014)]
df_iss  = df[(df["Year"] >= 2018) & (df["Year"] <= 2022)]

# ---------------- FUNCTION ----------------
def diurnal_stats(data):
    d = data.groupby("Hour").size().reset_index(name="Flash_Count")
    d["Contribution_%"] = 100 * d["Flash_Count"] / d["Flash_Count"].sum()
    return d

# ---------------- COMPUTE ----------------
trmm_d = diurnal_stats(df_trmm)
iss_d  = diurnal_stats(df_iss)

# ---------------- SAVE EXCEL (RAW) ----------------
trmm_d.to_excel(
    excel_out_dir + r"\Diurnal_Lightning_Contribution_TRMM.xlsx",
    index=False
)
iss_d.to_excel(
    excel_out_dir + r"\Diurnal_Lightning_Contribution_ISS.xlsx",
    index=False
)

# ---------------- SMOOTH + SPLINE ----------------
def smooth_spline(x, y):
    y_sg = savgol_filter(y, window_length=5, polyorder=2)
    x_new = np.linspace(x.min(), x.max(), 300)
    spline = make_interp_spline(x, y_sg, k=3)
    y_new = spline(x_new)
    return x_new, y_new

x_trmm, y_trmm = smooth_spline(
    trmm_d["Hour"].values, trmm_d["Contribution_%"].values
)
x_iss, y_iss = smooth_spline(
    iss_d["Hour"].values, iss_d["Contribution_%"].values
)

# ---------------- COMMON Y-LIMITS ----------------
ymin = min(y_trmm.min(), y_iss.min()) * 0.95
ymax = max(y_trmm.max(), y_iss.max()) * 1.05

# ---------------- GRADIENT LINE FUNCTION ----------------
def gradient_line(ax, x, y):
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    norm = mcolors.Normalize(vmin=y.min(), vmax=y.max())
    cmap = plt.cm.RdYlGn_r   # green (low) → red (high)

    lc = LineCollection(
        segments,
        cmap=cmap,
        norm=norm,
        linewidth=3
    )
    lc.set_array(y)
    ax.add_collection(lc)

# ---------------- PLOT ----------------
fig, axes = plt.subplots(
    nrows=1, ncols=2,
    figsize=(14, 5),
    sharey=True
)

# -------- TRMM --------
gradient_line(axes[0], x_trmm, y_trmm)
axes[0].set_title("TRMM-LIS (2000–2014)", fontsize=12)
axes[0].set_xlim(0, 23)
axes[0].set_ylim(ymin, ymax)
axes[0].grid(alpha=0.3)

# Panel label (a) – top right
axes[0].text(
    0.98, 0.98, "(a)",
    transform=axes[0].transAxes,
    fontsize=14,
    fontweight="bold",
    va="top",
    ha="right"
)

# -------- ISS --------
gradient_line(axes[1], x_iss, y_iss)
axes[1].set_title("ISS-LIS (2018–2022)", fontsize=12)
axes[1].set_xlim(0, 23)
axes[1].grid(alpha=0.3)

# Panel label (b) – top right
axes[1].text(
    0.98, 0.98, "(b)",
    transform=axes[1].transAxes,
    fontsize=14,
    fontweight="bold",
    va="top",
    ha="right"
)

# ---------------- X-AXIS (12-HOUR FORMAT) ----------------
labels = []
for h in range(24):
    if h == 0:
        labels.append("12\nAM")
    elif h < 12:
        labels.append(f"{h}\nAM")
    elif h == 12:
        labels.append("12\nPM")
    else:
        labels.append(f"{h-12}\nPM")

for ax in axes:
    ax.set_xticks(range(24))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Local Time (IST)")

axes[0].set_ylabel("Lightning Contribution (%)")

# ---------------- SAVE ----------------
plt.tight_layout()
plt.savefig(
    fig_dir + r"\Fig_Diurnal_Contribution_Smooth_Gradient_TRMM_ISS.tif",
    dpi=500
)
plt.close()

print("Smooth gradient diurnal plots with panel labels saved successfully.")
