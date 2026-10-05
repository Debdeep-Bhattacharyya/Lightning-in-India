# ============================================================
# FINAL DIURNAL MULTIPANEL + EXCEL OUTPUT
# DIVISION × SEASON | TRMM vs ISS
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import os
from shapely.geometry import Point

# ============================================================
# PATHS
# ============================================================

excel_path = r"D:\Articles\Almost Done\India Lightning\Excel Files\India_LIS_AllYears_State_Season.xlsx"
division_shp = r"D:\Articles\Almost Done\India Lightning\India Shapefiles\Divisions\India_Divisions.shp"

out_dir = r"D:\Articles\Almost Done\India Lightning\Output\Module 1"
os.makedirs(out_dir, exist_ok=True)

excel_out = f"{out_dir}\\Diurnal_Division_Season_TRMM_ISS.xlsx"

plt.rcParams["font.size"] = 11

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_excel(excel_path)

df["Radiance"] = pd.to_numeric(df["Radiance"], errors="coerce")
df["Year"]     = pd.to_numeric(df["Year"], errors="coerce")

df = df.dropna(subset=["Radiance","Lat","Long","Year"])

# ============================================================
# PERIOD SPLIT
# ============================================================

df["Period"] = None
df.loc[(df["Year"]>=2000)&(df["Year"]<=2014),"Period"]="TRMM"
df.loc[(df["Year"]>=2018)&(df["Year"]<=2022),"Period"]="ISS"
df = df.dropna(subset=["Period"])

# ============================================================
# SEASON ORDER
# ============================================================

df["Season"] = df["Season"].replace({
    "Southwest Monsoon":"Monsoon",
    "SW Monsoon":"Monsoon",
    "Post-Monsoon":"Post Monsoon",
    "Pre-Monsoon":"Pre Monsoon"
})

season_order = ["Winter","Pre Monsoon","Monsoon","Post Monsoon"]

# ============================================================
# GEO JOIN
# ============================================================

geometry = [Point(xy) for xy in zip(df["Long"], df["Lat"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

div = gpd.read_file(division_shp).to_crs("EPSG:4326")
join = gpd.sjoin(gdf, div[["Division","geometry"]], how="left", predicate="within")

divisions = sorted(join["Division"].dropna().unique())[:4]

# ============================================================
# DIURNAL CALCULATION
# ============================================================

join["Hour"] = pd.to_datetime(join["IST"],format="%H:%M:%S",errors="coerce").dt.hour

diurnal = join.groupby(["Division","Season","Period","Hour"])["Radiance"].sum().reset_index()

# ============================================================
# SAVE EXCEL
# ============================================================

with pd.ExcelWriter(excel_out) as writer:
    join.to_excel(writer, sheet_name="All_Data", index=False)
    diurnal.to_excel(writer, sheet_name="Diurnal_Data", index=False)

print("Excel file saved")

# ============================================================
# SAME Y-SCALE
# ============================================================

ymax = diurnal["Radiance"].max()*1.05

# ============================================================
# MULTIPANEL FIGURE
# ============================================================

fig,axes = plt.subplots(4,4,figsize=(16,14),sharey=True)

for r,divn in enumerate(divisions):
    for c,season in enumerate(season_order):

        ax = axes[r,c]
        sub = diurnal[(diurnal["Division"]==divn)&(diurnal["Season"]==season)]

        for p,color in zip(["TRMM","ISS"],["blue","red"]):
            ss = sub[sub["Period"]==p]
            ss = ss.set_index("Hour").reindex(range(24),fill_value=0)

            ax.plot(range(24), ss["Radiance"],
                    marker="o", linewidth=1.6,
                    label=p, color=color)

        ax.set_ylim(0, ymax)
        ax.set_xticks(range(0,24,3))
        ax.set_xlabel("Hour (IST)")
        ax.set_ylabel("Total Radiance")

        # season titles top row
        if r == 0:
            ax.set_title(season, fontsize=13, fontweight="bold", pad=12)

        # division labels left vertical
        if c == 0:
            ax.text(-0.35,0.5,divn,
                    transform=ax.transAxes,
                    rotation=90,
                    va="center",
                    ha="center",
                    fontsize=13,
                    fontweight="bold")

# legend bottom
handles,labels = axes[0,0].get_legend_handles_labels()
fig.legend(handles,labels,
           loc="lower center",
           ncol=2,
           bbox_to_anchor=(0.5,0.01),
           fontsize=12)

plt.subplots_adjust(hspace=0.35,wspace=0.25,bottom=0.08)
plt.savefig(f"{out_dir}\\Final_Diurnal_Division_Season_TRMM_ISS.tif",dpi=400)
plt.close()

print("FINAL FIGURE + EXCEL READY")
print("Saved in:", out_dir)
