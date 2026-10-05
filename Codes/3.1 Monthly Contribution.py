# ============================================================
# MONTHLY LIGHTNING CONTRIBUTION & SD DEVIATION
# GROUPED BY MONTH
# TRMM-LIS (2000–2014) vs ISS-LIS (2018–2022)
# FIGURE + EXCEL OUTPUTS
# ============================================================

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------- PATHS ----------------
base_dir = r"D:\Articles\Almost Done\India Lightning"
input_file = base_dir + r"\Excel Files\India_LIS_AllYears_State_Season.xlsx"

fig_dir = base_dir + r"\Figures"
excel_out_dir = base_dir + r"\Derived_Statistics"

os.makedirs(fig_dir, exist_ok=True)
os.makedirs(excel_out_dir, exist_ok=True)

# ---------------- LOAD DATA ----------------
df = pd.read_excel(input_file)

month_order = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# ---------------- PERIOD SPLIT ----------------
df_trmm = df[(df["Year"] >= 2000) & (df["Year"] <= 2014)]
df_iss  = df[(df["Year"] >= 2018) & (df["Year"] <= 2022)]

# ---------------- FUNCTION ----------------
def monthly_stats(data):
    m = (
        data.groupby("Month")
            .size()
            .reindex(month_order)
            .reset_index(name="Flash_Count")
    )

    m["Contribution_%"] = 100 * m["Flash_Count"] / m["Flash_Count"].sum()
    mean_c = m["Contribution_%"].mean()
    std_c  = m["Contribution_%"].std()

    m["Z_SD"] = (m["Contribution_%"] - mean_c) / std_c
    return m

# ---------------- COMPUTE ----------------
trmm_m = monthly_stats(df_trmm)
iss_m  = monthly_stats(df_iss)

# ---------------- SAVE EXCEL FILES ----------------
trmm_m.to_excel(
    excel_out_dir + r"\Monthly_Contribution_SD_TRMM.xlsx",
    index=False
)
iss_m.to_excel(
    excel_out_dir + r"\Monthly_Contribution_SD_ISS.xlsx",
    index=False
)

# ---------------- COMMON Y-LIMITS ----------------
contrib_max = max(
    trmm_m["Contribution_%"].max(),
    iss_m["Contribution_%"].max()
)

zlim = max(
    abs(trmm_m["Z_SD"]).max(),
    abs(iss_m["Z_SD"]).max()
)

# ---------------- PLOT ----------------
x = np.arange(len(month_order))
width = 0.38

fig, axes = plt.subplots(
    nrows=2, ncols=1,
    figsize=(14, 8),
    sharex=True
)

# ============================================================
# (a) MONTHLY CONTRIBUTION (%)
# ============================================================

axes[0].bar(
    x - width/2, trmm_m["Contribution_%"],
    width=width, color="tab:blue",
    edgecolor="black", linewidth=0.6,
    label="TRMM-LIS (2000–2014)"
)

axes[0].bar(
    x + width/2, iss_m["Contribution_%"],
    width=width, color="tab:red",
    edgecolor="black", linewidth=0.6,
    label="ISS-LIS (2018–2022)"
)

axes[0].set_ylabel("Contribution (%)", fontsize=12)
axes[0].set_ylim(0, contrib_max * 1.15)
axes[0].grid(axis="y", alpha=0.3)
axes[0].legend(ncol=2, loc="upper right")

# Panel label (a)
axes[0].text(
    0.01, 0.98, "(a)",
    transform=axes[0].transAxes,
    fontsize=14,
    fontweight="bold",
    va="top",
    ha="left"
)

# ============================================================
# (b) SD DEVIATION (Z-SCORE)
# ============================================================

axes[1].bar(
    x - width/2, trmm_m["Z_SD"],
    width=width, color="tab:blue",
    edgecolor="black", linewidth=0.6
)

axes[1].bar(
    x + width/2, iss_m["Z_SD"],
    width=width, color="tab:red",
    edgecolor="black", linewidth=0.6
)

axes[1].axhline(0, color="black", linewidth=1)
axes[1].set_ylabel("Deviation (σ)", fontsize=12)
axes[1].set_ylim(-zlim * 1.15, zlim * 1.15)
axes[1].grid(axis="y", alpha=0.3)

# Panel label (b)
axes[1].text(
    0.01, 0.98, "(b)",
    transform=axes[1].transAxes,
    fontsize=14,
    fontweight="bold",
    va="top",
    ha="left"
)

# ---------------- X-AXIS ----------------
axes[1].set_xticks(x)
axes[1].set_xticklabels(month_order, rotation=45, ha="right")
axes[1].set_xlabel("Month", fontsize=12)

# ---------------- SAVE ----------------
plt.tight_layout()
plt.savefig(
    fig_dir + r"\Fig_Monthly_Contribution_SD_Deviation_Grouped_TRMM_ISS.tif",
    dpi=500
)
plt.close()

print("Grouped monthly contribution & SD-deviation figure with panel labels saved successfully.")
