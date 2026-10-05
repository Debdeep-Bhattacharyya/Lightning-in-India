# ============================================================
# Step01_Create_India_025deg_Grid.py
#
# Creates a 0.25° Polygon Fishnet for India
#
# Output:
#   - India_025deg_Grid.shp
#
# Author : ChatGPT
# ============================================================

import os
import numpy as np
import geopandas as gpd
from shapely.geometry import box

# ============================================================
# USER INPUT
# ============================================================

ROOT = r"D:\Articles\Working\Lightning India"

SHAPEFILE = os.path.join(
    ROOT,
    "Data",
    "Shapefiles",
    "India_States.shp"
)

OUTPUT = os.path.join(
    ROOT,
    "Data",
    "Shapefiles"
)

os.makedirs(OUTPUT, exist_ok=True)

GRID_SIZE = 0.25  # degrees

# ============================================================
# LOAD INDIA
# ============================================================

print("\nLoading India boundary...")

india = gpd.read_file(SHAPEFILE)

if india.crs is None:
    raise ValueError("Input shapefile has no CRS defined.")

india = india.to_crs(epsg=4326)

# Dissolve all states into one India boundary
india_boundary = india.dissolve()

# ============================================================
# GET EXTENT
# ============================================================

minx, miny, maxx, maxy = india_boundary.total_bounds

print("\nIndia Extent")
print("---------------------------------------")
print(f"Longitude : {minx:.2f} to {maxx:.2f}")
print(f"Latitude  : {miny:.2f} to {maxy:.2f}")

# ============================================================
# CREATE FISHNET
# ============================================================

print("\nCreating 0.25° fishnet...")

x = np.arange(minx, maxx + GRID_SIZE, GRID_SIZE)
y = np.arange(miny, maxy + GRID_SIZE, GRID_SIZE)

polygons = []
grid_ids = []
rows = []
cols = []

gid = 1

for r in range(len(y) - 1):
    for c in range(len(x) - 1):

        polygons.append(
            box(
                x[c],
                y[r],
                x[c + 1],
                y[r + 1]
            )
        )

        grid_ids.append(gid)
        rows.append(r + 1)
        cols.append(c + 1)

        gid += 1

grid = gpd.GeoDataFrame(
    {
        "Grid_ID": grid_ids,
        "Row": rows,
        "Col": cols
    },
    geometry=polygons,
    crs="EPSG:4326"
)

print(f"Total grid cells created : {len(grid):,}")

# ============================================================
# CLIP TO INDIA
# ============================================================

print("\nClipping grid to India boundary...")

grid = gpd.overlay(
    grid,
    india_boundary,
    how="intersection"
)

grid = grid.reset_index(drop=True)

print(f"Grid cells after clipping : {len(grid):,}")

# ============================================================
# CALCULATE AREA (km²)
# ============================================================

print("\nCalculating grid area...")

grid_projected = grid.to_crs(epsg=6933)

grid["Area_km2"] = grid_projected.geometry.area / 1e6

# ============================================================
# CALCULATE CENTROIDS
# ============================================================

print("\nCalculating centroids...")

centroids = grid.geometry.centroid

grid["Centroid_Lon"] = centroids.x
grid["Centroid_Lat"] = centroids.y

# ============================================================
# SAVE SHAPEFILE ONLY
# ============================================================

print("\nSaving shapefile...")

shp_file = os.path.join(
    OUTPUT,
    "India_025deg_Grid.shp"
)

grid.to_file(
    shp_file,
    driver="ESRI Shapefile"
)

# ============================================================
# SUMMARY
# ============================================================

print("\n==========================================")
print(" GRID CREATION COMPLETED")
print("==========================================")

print(f"Grid Size      : {GRID_SIZE}° × {GRID_SIZE}°")
print(f"Grid Cells     : {len(grid):,}")
print(f"Mean Area      : {grid['Area_km2'].mean():.2f} km²")
print(f"Min Area       : {grid['Area_km2'].min():.2f} km²")
print(f"Max Area       : {grid['Area_km2'].max():.2f} km²")

print("\nOutput")
print("------------------------------------------")
print(shp_file)

print("\nDone.")