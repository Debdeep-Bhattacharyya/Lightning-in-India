# ============================================================
# MODULE-3 FINAL MASTER PLOTS (PUBLICATION READY)
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from matplotlib.ticker import ScalarFormatter

# ============================================================
# PATH
# ============================================================

storm_path = r"D:\Articles\Almost Done\India Lightning\Output\Module 3\India_StormDatabase_TRMM_ISS.xlsx"
out_dir    = r"D:\Articles\Almost Done\India Lightning\Output\Module 3"
os.makedirs(out_dir, exist_ok=True)

print("Loading storm database...")
df = pd.read_excel(storm_path)

# numeric safety
for col in ["Total_Radiance","Energy_per_Flash","Duration_min","Total_Flashes"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["Division","Season","Period"])

season_order = ["Winter","Pre Monsoon","Monsoon","Post Monsoon"]
divisions = sorted(df["Division"].unique())

# consistent y scales
energy_ymax = df["Total_Radiance"].quantile(0.995)*1.05
eff_ymax    = df["Energy_per_Flash"].quantile(0.995)*1.05
dur_ymax    = df["Duration_min"].quantile(0.995)*1.05

# ============================================================
# COMMON FORMAT FUNCTION
# ============================================================

def format_axis(ax, ylabel):
    ax.set_xlabel("Period", fontweight="bold")
    ax.set_ylabel(ylabel, fontweight="bold")
    ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    ax.ticklabel_format(style='plain', axis='y')
    ax.tick_params(labelsize=9)

# ============================================================
# FIGURE 1: STORM ENERGY
# ============================================================

fig, axes = plt.subplots(len(divisions),4, figsize=(16,14), sharey=True)

for r, divn in enumerate(divisions):
    for c, season in enumerate(season_order):

        ax = axes[r,c]
        sub = df[(df["Division"]==divn)&(df["Season"]==season)]

        sns.violinplot(data=sub,
                       x="Period", y="Total_Radiance",
                       order=["TRMM","ISS"],
                       palette={"TRMM":"royalblue","ISS":"red"},
                       inner="box", cut=0, ax=ax)

        ax.set_ylim(0,energy_ymax)
        format_axis(ax,"Storm Electrical Energy")

        # season titles
        if r==0:
            ax.set_title(season,fontsize=13,fontweight="bold")

        # division labels LEFT side
        if c==0:
            ax.set_ylabel(f"{divn}\n\nStorm Electrical Energy",
                          fontweight="bold",rotation=90)

plt.tight_layout()
plt.savefig(f"{out_dir}\\M3_StormEnergy_Violin.tif",dpi=400,bbox_inches="tight")
plt.close()

# ============================================================
# FIGURE 2: ENERGY PER FLASH
# ============================================================

fig, axes = plt.subplots(len(divisions),4, figsize=(16,14), sharey=True)

for r, divn in enumerate(divisions):
    for c, season in enumerate(season_order):

        ax = axes[r,c]
        sub = df[(df["Division"]==divn)&(df["Season"]==season)]

        sns.violinplot(data=sub,
                       x="Period", y="Energy_per_Flash",
                       order=["TRMM","ISS"],
                       palette={"TRMM":"royalblue","ISS":"red"},
                       inner="box", cut=0, ax=ax)

        ax.set_ylim(0,eff_ymax)
        format_axis(ax,"Energy per Flash")

        if r==0:
            ax.set_title(season,fontsize=13,fontweight="bold")

        if c==0:
            ax.set_ylabel(f"{divn}\n\nEnergy per Flash",
                          fontweight="bold",rotation=90)

plt.tight_layout()
plt.savefig(f"{out_dir}\\M3_EnergyPerFlash_Violin.tif",dpi=400,bbox_inches="tight")
plt.close()

# ============================================================
# FIGURE 3: STORM DURATION
# ============================================================

fig, axes = plt.subplots(len(divisions),4, figsize=(16,14), sharey=True)

for r, divn in enumerate(divisions):
    for c, season in enumerate(season_order):

        ax = axes[r,c]
        sub = df[(df["Division"]==divn)&(df["Season"]==season)]

        sns.violinplot(data=sub,
                       x="Period", y="Duration_min",
                       order=["TRMM","ISS"],
                       palette={"TRMM":"royalblue","ISS":"red"},
                       inner="box", cut=0, ax=ax)

        ax.set_ylim(0,dur_ymax)
        format_axis(ax,"Storm Duration (min)")

        if r==0:
            ax.set_title(season,fontsize=13,fontweight="bold")

        if c==0:
            ax.set_ylabel(f"{divn}\n\nStorm Duration (min)",
                          fontweight="bold",rotation=90)

plt.tight_layout()
plt.savefig(f"{out_dir}\\M3_StormDuration_Violin.tif",dpi=400,bbox_inches="tight")
plt.close()

# ============================================================
# FIGURE 4: EXTREME STORM HEATMAP
# ============================================================

thr = df["Total_Radiance"].quantile(0.95)
extreme = df[df["Total_Radiance"]>=thr]

fig, axes = plt.subplots(1,2, figsize=(14,6), sharey=True)

for i,period in enumerate(["TRMM","ISS"]):

    ax = axes[i]
    sub = extreme[extreme["Period"]==period]

    pivot = pd.pivot_table(sub,
                           values="Storm_ID",
                           index="Division",
                           columns="Season",
                           aggfunc="count",
                           fill_value=0)

    hm = sns.heatmap(pivot,
                     cmap="rocket",
                     linewidths=0.8,
                     linecolor="black",
                     annot=True,fmt="d",
                     cbar=True,
                     cbar_kws={"orientation":"horizontal",
                               "pad":0.12,
                               "label":"Number of Extreme Storms"},
                     ax=ax)

    ax.set_title(period,fontweight="bold")
    ax.set_xlabel("Season",fontweight="bold")
    ax.set_ylabel("Division",fontweight="bold")

plt.tight_layout()
plt.savefig(f"{out_dir}\\M3_ExtremeStorms_Heatmap.tif",dpi=400,bbox_inches="tight")
plt.close()

print("\nALL FINAL MODULE-3 FIGURES READY")
print("Location:",out_dir)
print("These are journal-quality figures")
