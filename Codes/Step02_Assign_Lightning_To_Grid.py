# ============================================================
# Step02_Assign_Lightning_To_Grid.py
#
# Assigns every lightning flash to:
#   - India 0.25° Grid
#   - State
#   - Division
#
# Input
#   Data/Lightning/2 Yearly_CSV/*.csv
#   Data/Shapefiles/India_025deg_Grid.shp
#   Data/Shapefiles/India_States.shp
#
# Output
#   Data/Lightning/3_Grid_Assigned/*.csv
# ============================================================

import os
import time
import glob
import pandas as pd
import geopandas as gpd

ROOT = r"D:\Articles\Working\Lightning India"

LIGHTNING_FOLDER = os.path.join(ROOT,"Data","Lightning","2 Yearly_CSV")
GRID_FILE = os.path.join(ROOT,"Data","Shapefiles","India_025deg_Grid.shp")
STATE_FILE = os.path.join(ROOT,"Data","Shapefiles","India_States.shp")

OUTPUT = os.path.join(ROOT,"Data","Lightning","3_Grid_Assigned")
os.makedirs(OUTPUT, exist_ok=True)

LOG = []

print("Loading shapefiles...")

grid = gpd.read_file(GRID_FILE).to_crs(4326)

states = gpd.read_file(STATE_FILE).to_crs(4326)
states = states[["STNAME_SH","Division","geometry"]]

csvs = sorted(glob.glob(os.path.join(LIGHTNING_FOLDER,"*.csv")))

print(f"Found {len(csvs)} yearly CSV files")

for csv in csvs:

    start = time.time()

    year_name = os.path.basename(csv)

    print("-"*60)
    print(year_name)

    df = pd.read_csv(csv)

    before = len(df)

    df = df.dropna(subset=["Lat","Long"])

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Long"],df["Lat"]),
        crs="EPSG:4326"
    )

    # Assign grid
    gdf = gpd.sjoin(
        gdf,
        grid[["Grid_ID","Row","Col","Area_km2","geometry"]],
        how="inner",
        predicate="within"
    )

    # Assign state/division
    gdf = gpd.sjoin(
        gdf,
        states,
        how="left",
        predicate="within",
        lsuffix="grid",
        rsuffix="state"
    )

    # Remove join index columns if present
    for c in ["index_right_grid","index_right_state","index_right"]:
        if c in gdf.columns:
            gdf = gdf.drop(columns=c)

    after = len(gdf)

    out = os.path.join(
        OUTPUT,
        os.path.splitext(year_name)[0] + "_Grid.csv"
    )

    pd.DataFrame(gdf.drop(columns="geometry")).to_csv(
        out,
        index=False
    )

    LOG.append({
        "File":year_name,
        "Input_Flashes":before,
        "Assigned_Flashes":after,
        "Unique_Grid_Cells":gdf["Grid_ID"].nunique(),
        "Processing_Time_sec":round(time.time()-start,2)
    })

    print(f"Saved : {out}")

log_df = pd.DataFrame(LOG)

log_file = os.path.join(
    OUTPUT,
    "Processing_Log.csv"
)

log_df.to_csv(
    log_file,
    index=False
)

print("="*60)
print("PROCESS COMPLETED")
print("="*60)
print(log_df)
print(f"\nProcessing log saved to:\n{log_file}")