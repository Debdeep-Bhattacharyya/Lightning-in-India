# ============================================================
# Seasonal_Lightning_Flash_Density_Multipanel.py
# Publication-quality 2x2 Seasonal Climatological Lightning Flash Density
# Uses yearly *_Grid.csv files with Month names.
# Seasons (standard Indian climatological seasons):
#   Winter       -> Dec, Jan, Feb
#   Pre-Monsoon  -> Mar, Apr, May
#   Monsoon      -> Jun, Jul, Aug, Sep
#   Post-Monsoon -> Oct, Nov
# ============================================================

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl

CSV_DIR   = r"D:\Articles\Working\Lightning India\Data\Lightning\3_Grid_Assigned"
GRID_SHP  = r"D:\Articles\Working\Lightning India\Data\Shapefiles\India_025deg_Grid.shp"
STATE_SHP = r"D:\Articles\Working\Lightning India\Data\Shapefiles\India_States.shp"
OUT_DIR   = r"D:\Articles\Working\Lightning India\Results"

os.makedirs(OUT_DIR, exist_ok=True)

mpl.rcParams.update({
    "font.family": "Arial",
    "font.size": 13,
    "axes.linewidth": 1.0,
    "axes.titlesize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

grid = gpd.read_file(GRID_SHP)
states = gpd.read_file(STATE_SHP)

if states.crs != grid.crs:
    states = states.to_crs(grid.crs)

minx, miny, maxx, maxy = grid.total_bounds
padx = (maxx - minx) * 0.01
pady = (maxy - miny) * 0.01
xlim = (minx - padx, maxx + padx)
ylim = (miny - pady, maxy + pady)

# --- Season definitions. Edit here if you use a different scheme
# (e.g. IMD sometimes groups Monsoon as Jun-Sep and Post-Monsoon as
# Oct-Dec, folding December out of Winter — adjust the lists below
# to match your paper's convention).
SEASONS = {
    "Winter":       ["January", "February"],
    "Pre-Monsoon":  ["March", "April", "May"],
    "Monsoon":      ["June", "July", "August", "September"],
    "Post-Monsoon": ["October", "November", "December"]
}

years = list(range(2000, 2015)) + list(range(2018, 2023))

maps = {}
allvals = []

for season, season_months in SEASONS.items():
    season_months_lower = [m.lower() for m in season_months]
    merged = None
    nyears = 0

    for yr in years:
        f = os.path.join(CSV_DIR, f"{yr}_Grid.csv")
        if not os.path.exists(f):
            continue

        df = pd.read_csv(f)
        df = df[df["Month"].astype(str).str.strip().str.lower().isin(season_months_lower)]

        if df.empty:
            continue

        grp = (df.groupby("Grid_ID")
                 .agg(Flash_Count=("Grid_ID", "size"),
                      Area_km2=("Area_km2", "first"))
                 .reset_index())

        if merged is None:
            merged = grp.copy()
            merged.rename(columns={"Flash_Count": "FlashSum"}, inplace=True)
        else:
            merged = merged.merge(
                grp[["Grid_ID", "Flash_Count"]],
                on="Grid_ID",
                how="outer"
            )
            merged["FlashSum"] = merged["FlashSum"].fillna(0) + merged["Flash_Count"].fillna(0)
            merged.drop(columns="Flash_Count", inplace=True)

        nyears += 1

    if merged is None or nyears == 0:
        continue

    # Fill any gaps in Area_km2 introduced by the outer merges
    merged["Area_km2"] = merged["Area_km2"].ffill().bfill()

    # Average annual seasonal flash density for this grid cell
    merged["Flash_Density"] = merged["FlashSum"] / (merged["Area_km2"] * nyears)

    g = grid.merge(merged[["Grid_ID", "Flash_Density"]], on="Grid_ID", how="left")
    g["Flash_Density"] = g["Flash_Density"].fillna(0)

    maps[season] = g
    allvals.extend(g["Flash_Density"].tolist())

vmin = 0
vmax = np.nanpercentile(allvals, 99)
CMAP = "turbo"

# ------------------------------------------------------------
# Figure: 2 rows x 2 columns
# ------------------------------------------------------------
season_order = list(SEASONS.keys())

fig, axs = plt.subplots(2, 2, figsize=(11, 11))
axs = axs.flatten()

for ax in axs:
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(1.2)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect("equal")

for i, season in enumerate(season_order):
    ax = axs[i]
    if season not in maps:
        ax.text(0.5, 0.5, "No Data", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_title(season, fontweight="bold", pad=3)
        continue

    maps[season].plot(
        column="Flash_Density",
        cmap=CMAP,
        linewidth=0,
        edgecolor="none",
        vmin=vmin,
        vmax=vmax,
        ax=ax
    )

    states.boundary.plot(
        ax=ax,
        linewidth=0.8,
        edgecolor="black",
        zorder=20
    )

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_title(season, fontweight="bold", pad=3)

sm = plt.cm.ScalarMappable(
    cmap=CMAP,
    norm=plt.Normalize(vmin=vmin, vmax=vmax)
)
sm._A = []

cax = fig.add_axes([0.25, 0.045, 0.5, 0.018])
cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
cb.set_label(
    "Lightning Flash Density (flashes km$^{-2}$ season$^{-1}$)",
    fontsize=14,
    fontweight="bold"
)

plt.subplots_adjust(
    left=0.03,
    right=0.97,
    top=0.95,
    bottom=0.10,
    wspace=0.08,
    hspace=0.18
)

outfile = os.path.join(
    OUT_DIR,
    "Seasonal_Lightning_Flash_Density_Multipanel.tif"
)

plt.savefig(
    outfile,
    dpi=600,
    bbox_inches="tight",
    pil_kwargs={"compression": "tiff_lzw"}
)

plt.close()

print("Finished")
print(outfile)