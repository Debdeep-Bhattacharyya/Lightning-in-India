# ============================================================
# Annual_Lightning_Flash_Density_Multipanel.py
# Publication-quality 5x4 multipanel annual lightning flash density
# Revised: boxed panels, centered year titles (non-overlapping),
#          turbo colormap, visible state boundaries, consistent extents
# ============================================================

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
CSV_DIR   = r"D:\Articles\Working\Lightning India\Data\Lightning\3_Grid_Assigned"
GRID_SHP  = r"D:\Articles\Working\Lightning India\Data\Shapefiles\India_025deg_Grid.shp"
STATE_SHP = r"D:\Articles\Working\Lightning India\Data\Shapefiles\India_States.shp"
OUT_DIR   = r"D:\Articles\Working\Lightning India\Results"

os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------------------------------------------
# Journal-style rcParams (Q1 journal look: Arial/Helvetica, clean ticks)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Load shapefiles
# ------------------------------------------------------------
grid   = gpd.read_file(GRID_SHP)
states = gpd.read_file(STATE_SHP)

if states.crs != grid.crs:
    states = states.to_crs(grid.crs)

minx, miny, maxx, maxy = grid.total_bounds
pad_x = (maxx - minx) * 0.01
pad_y = (maxy - miny) * 0.01
xlim = (minx - pad_x, maxx + pad_x)
ylim = (miny - pad_y, maxy + pad_y)

# ------------------------------------------------------------
# Build per-year flash density grids
# ------------------------------------------------------------
years = list(range(2000, 2015)) + list(range(2018, 2023))
maps = {}
allvals = []

for yr in years:
    f = os.path.join(CSV_DIR, f"{yr}_Grid.csv")
    if not os.path.exists(f):
        print(f"Missing {yr}")
        continue

    df = pd.read_csv(f)

    grp = (df.groupby("Grid_ID")
             .agg(Flash_Count=("Grid_ID", "size"),
                  Area_km2=("Area_km2", "first"))
             .reset_index())
    grp["Flash_Density"] = grp["Flash_Count"] / grp["Area_km2"]

    g = grid.merge(grp, on="Grid_ID", how="left")
    g["Flash_Density"] = g["Flash_Density"].fillna(0)

    maps[yr] = g
    allvals.extend(g["Flash_Density"].values.tolist())

vmin = 0
vmax = np.nanpercentile(allvals, 99)

CMAP = "turbo"

# ------------------------------------------------------------
# Figure
# ------------------------------------------------------------
fig, axs = plt.subplots(4, 5, figsize=(17, 13.3))
axs = axs.flatten()

for ax in axs:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.2)
        spine.set_color("black")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect("equal")

for i, yr in enumerate(years):
    if yr not in maps:
        axs[i].text(0.5, 0.5, "No Data", transform=axs[i].transAxes,
                     ha="center", va="center", fontsize=9, color="gray")
        axs[i].set_title(str(yr), fontsize=13, fontweight="bold", pad=3)
        continue

    g = maps[yr]
    g.plot(column="Flash_Density",
           cmap=CMAP,
           linewidth=0,
           edgecolor="none",
           vmin=vmin, vmax=vmax,
           ax=axs[i])

    states.boundary.plot(
        ax=axs[i],
        linewidth=0.8,
        edgecolor="black",
        zorder=20
    )

    # Re-apply extent (boundary.plot can autoscale the axes)
    axs[i].set_xlim(xlim)
    axs[i].set_ylim(ylim)

    # Year title, centered above each panel, with modest pad
    axs[i].set_title(str(yr), fontsize=13, fontweight="bold", pad=3)

for j in range(len(years), len(axs)):
    axs[j].set_visible(False)

# ------------------------------------------------------------
# Shared colorbar
# ------------------------------------------------------------
sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(vmin=vmin, vmax=vmax))
sm._A = []

cax = fig.add_axes([0.22, 0.045, 0.56, 0.020])
cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
cb.set_label(
    "Lightning Flash Density (flashes km$^{-2}$ yr$^{-1}$)",
    fontsize=14,
    fontweight="bold"
)
cb.ax.tick_params(labelsize=12)

# Just enough vertical room for the set_title() text (which sits
# ABOVE each axes box) to clear the panel row above it, without
# leaving a large empty gap between rows.
plt.subplots_adjust(left=0.02, right=0.98,
                    top=0.96, bottom=0.09,
                    wspace=0.06, hspace=0.16)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------
outfile_tif = os.path.join(
    OUT_DIR, "Annual_Lightning_Flash_Density_Multipanel.tif"
)

plt.savefig(outfile_tif, dpi=600, bbox_inches="tight",
            pil_kwargs={"compression": "tiff_lzw"})

plt.close()

print("Finished")
print(outfile_tif)