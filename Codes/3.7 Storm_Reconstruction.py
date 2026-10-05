# ============================================================
# FINAL STORM RECONSTRUCTION ENGINE (CORRECT SEASONS)
# 30 km + 30 min | FAST | PROGRESS SHOWN
# ============================================================

import pandas as pd
import numpy as np
import geopandas as gpd
import os
from math import radians, sin, cos, sqrt, atan2
from datetime import timedelta
from shapely.geometry import Point

# ============================================================
# PATHS
# ============================================================

excel_path   = r"D:\Articles\Almost Done\India Lightning\Excel Files\India_LIS_AllYears_State_Season.xlsx"
division_shp = r"D:\Articles\Almost Done\India Lightning\India Shapefiles\Divisions\India_Divisions.shp"

out_dir = r"D:\Articles\Almost Done\India Lightning\Output\Module 3"
os.makedirs(out_dir, exist_ok=True)

out_excel = f"{out_dir}\\India_StormDatabase_TRMM_ISS.xlsx"

# ============================================================
# LOAD DATA
# ============================================================

print("Loading data...")
df = pd.read_excel(excel_path)

df["Radiance"] = pd.to_numeric(df["Radiance"], errors="coerce")
df["Events"]   = pd.to_numeric(df["Events"], errors="coerce")
df["Year"]     = pd.to_numeric(df["Year"], errors="coerce")

df = df.dropna(subset=["Radiance","Lat","Long","IST","Year"])

# ============================================================
# STANDARDIZE SEASONS FIRST
# ============================================================

print("Standardizing seasons...")

df["Season"] = df["Season"].astype(str)

df["Season"] = df["Season"].replace({
    "Winter":"Winter",
    "winter":"Winter",

    "Pre-Monsoon":"Pre Monsoon",
    "Pre Monsoon":"Pre Monsoon",
    "Premonsoon":"Pre Monsoon",

    "Southwest Monsoon":"Monsoon",
    "SW Monsoon":"Monsoon",
    "Monsoon":"Monsoon",

    "Post-Monsoon":"Post Monsoon",
    "Post Monsoon":"Post Monsoon",
    "Postmonsoon":"Post Monsoon"
})

season_order = ["Winter","Pre Monsoon","Monsoon","Post Monsoon"]

# ============================================================
# ADD DIVISION
# ============================================================

print("Joining division shapefile...")

geometry = [Point(xy) for xy in zip(df["Long"], df["Lat"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

div = gpd.read_file(division_shp).to_crs("EPSG:4326")
gdf = gpd.sjoin(gdf, div[["Division","geometry"]], how="left", predicate="within")
gdf = pd.DataFrame(gdf.drop(columns="geometry"))

# ============================================================
# PERIOD SPLIT
# ============================================================

gdf["Period"] = None
gdf.loc[(gdf["Year"]>=2000)&(gdf["Year"]<=2014),"Period"]="TRMM"
gdf.loc[(gdf["Year"]>=2018)&(gdf["Year"]<=2022),"Period"]="ISS"
gdf = gdf.dropna(subset=["Period"])

# ============================================================
# TIME
# ============================================================

gdf["DateTime"] = pd.to_datetime(
    gdf["Year"].astype(int).astype(str) + "-" +
    gdf["Month"].astype(str) + "-" +
    gdf["Day"].astype(str) + " " +
    gdf["IST"].astype(str),
    errors="coerce"
)

gdf = gdf.dropna(subset=["DateTime"])
gdf = gdf.sort_values("DateTime").reset_index(drop=True)

# ============================================================
# DISTANCE FUNCTION
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*atan2(sqrt(a), sqrt(1-a))

# ============================================================
# STORM CLUSTER FUNCTION
# ============================================================

def build_storms(data, period_name):

    print(f"\nProcessing {period_name} storms...")
    data = data.sort_values("DateTime").reset_index(drop=True)

    storm_id = 0
    storm_ids = np.full(len(data), -1)

    for i in range(len(data)):

        if storm_ids[i] != -1:
            continue

        storm_id += 1
        storm_ids[i] = storm_id

        lat1 = data.loc[i,"Lat"]
        lon1 = data.loc[i,"Long"]
        t1   = data.loc[i,"DateTime"]

        j = i + 1

        while j < len(data):
            t2 = data.loc[j,"DateTime"]

            if (t2 - t1) > timedelta(minutes=30):
                break

            lat2 = data.loc[j,"Lat"]
            lon2 = data.loc[j,"Long"]

            if haversine(lat1,lon1,lat2,lon2) <= 30:
                storm_ids[j] = storm_id

            j += 1

        if i % 50000 == 0:
            print(f"{period_name}: processed {i}/{len(data)} flashes")

    data["Storm_ID"] = storm_ids
    return data

# ============================================================
# PROCESS
# ============================================================

trmm = gdf[gdf["Period"]=="TRMM"].copy()
iss  = gdf[gdf["Period"]=="ISS"].copy()

trmm = build_storms(trmm,"TRMM")
iss  = build_storms(iss,"ISS")

all_data = pd.concat([trmm,iss])

# ============================================================
# STORM DATABASE
# ============================================================

print("\nCreating storm database...")

def mode_func(x):
    return x.mode().iloc[0] if not x.mode().empty else x.iloc[0]

storm = all_data.groupby(["Period","Storm_ID"]).agg(
    Start_Time=("DateTime","min"),
    End_Time=("DateTime","max"),
    Duration_min=("DateTime", lambda x:(x.max()-x.min()).total_seconds()/60),
    Total_Flashes=("Radiance","count"),
    Total_Radiance=("Radiance","sum"),
    Mean_Radiance=("Radiance","mean"),
    Total_Events=("Events","sum"),
    Division=("Division",mode_func),
    Season=("Season",mode_func),
    Year=("Year","first")
).reset_index()

storm["Energy_per_Flash"] = storm["Total_Radiance"]/storm["Total_Flashes"]

storm.to_excel(out_excel,index=False)

print("\nFINAL STORM DATABASE READY")
print("Saved:", out_excel)
print("Now rerun Module-3 plotting code")
