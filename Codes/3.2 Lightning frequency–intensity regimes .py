"""
Lightning India — Frequency × Intensity Lightning Climatology
=====================================================================

Study period:
    2000-2022
    Excluding 2015, 2016, 2017

Input:
    Year-wise lightning CSV files:
        D:\\Articles\\Working\\Lightning India\\Data\\Lightning\\3_Grid_Assigned
    Grid:
        D:\\Articles\\Working\\Lightning India\\Data\\Shapefiles\\India_025deg_Grid.shp
    State boundary:
        D:\\Articles\\Working\\Lightning India\\Data\\Shapefiles\\India_States.shp

MAIN CONCEPT
------------
This analysis separates lightning climatology into TWO dimensions:
    1. FREQUENCY — mean number of lightning-active days
    2. INTENSITY — flash density per active lightning day

FOUR LIGHTNING REGIMES
----------------------
                LOW INTENSITY       HIGH INTENSITY
LOW FREQUENCY   Low Activity        Episodic Intense
HIGH FREQUENCY  Frequent but Weak    Persistent Intense

FIGURE LAYOUT (matches the reference hotspot-map figure exactly)
-------------------------------------------------------------------
- Two side-by-side blocks: (a) 3x4 monthly grid (left, wider) and
  (b) single annual map (right, narrower) -- same proportions and
  panel arrangement as the original mean-active-days hotspot figure.
- Each block has its OWN single-row "furniture" strip directly beneath
  it, combining: categorical legend (left) + scale bar (middle) + north
  arrow (right) -- all in one horizontal row, exactly like the
  reference figure's bottom rows.
- Monthly legend thresholds are labelled in "days month^-1" using ONE
  GLOBAL threshold pair pooled across all 12 months (not a separate
  threshold recomputed per month), so every monthly panel is on the
  same scale and directly comparable to every other month; annual
  legend thresholds are labelled in "days year^-1" (using the annual
  median, already on a single scale for the whole year). Intensity
  stays in flashes km^-2 active-day^-1 either way, since "active day"
  doesn't change meaning between the two blocks.
- No background tint behind the maps -- plain white, matching the
  reference figure.
- Month names sit as small bold labels at the top-left of each panel
  (matching the reference figure), and all 13 map panels (12 months +
  annual) share one common extent so everything lines up perfectly.

LEGEND UPDATE
--------------
- Swatch labels now show only the short class name (2-3 words), with
  explicit spacing between patches, so text can never bleed into a
  neighbouring swatch's label regardless of panel width.
- The numeric threshold definitions (frequency + intensity medians),
  which used to be repeated under every single swatch and were the
  actual source of the overlap, are now stated once as a compact
  italic caption line beneath the swatch row.
- Colour palette swapped to a higher-contrast, colourblind-safer set
  (yellow / orange / teal / purple / grey) that stays visually distinct
  from the black state-boundary lines and from itself under
  deuteranopia/protanopia simulation.

MONTHLY CLASSIFICATION SCALE UPDATE
-------------------------------------
- classify_monthly_frequency_intensity() previously recomputed a fresh
  median threshold pair separately for EACH calendar month, so e.g.
  "Persistent Intense Lightning" in January and in July represented
  different absolute magnitudes (only "top half of that month's own
  distribution"). This also produced a degenerate artifact in the
  driest months (Jan/Nov/Dec), where the local threshold collapsed
  toward the minimum nonzero value and the "Low Activity" class
  vanished entirely.
- Now ONE global threshold pair is computed by pooling every grid-cell
  x month row together (all 12 months at once), then applied
  identically across all months. The colour in any given month's panel
  now means the same absolute flash frequency/intensity as that same
  colour in any other month -- the 12 panels are directly comparable
  to one another, consistent with how the annual block already used a
  single threshold pair for the whole map.

OUTPUTS
-------
Results/
├── Figures/Lightning_Frequency_Intensity_Monthly_Annual.tif
├── Excel/Monthly_Frequency_Intensity_Classification.xlsx
├── Excel/Annual_Frequency_Intensity_Classification.xlsx
└── lightning_master_cache.parquet

Requires: pandas, geopandas, matplotlib, numpy, openpyxl, pyarrow
"""

# =====================================================================
# 1. IMPORT LIBRARIES
# =====================================================================

import glob
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec

from matplotlib.patches import Patch, Rectangle

# =====================================================================
# 2. CONFIGURATION
# =====================================================================

BASE_DIR = Path(r"D:\Articles\Working\Lightning India")
DATA_DIR = BASE_DIR / "Data" / "Lightning" / "3_Grid_Assigned"
SHP_GRID_PATH = BASE_DIR / "Data" / "Shapefiles" / "India_025deg_Grid.shp"
SHP_STATES_PATH = BASE_DIR / "Data" / "Shapefiles" / "India_States.shp"
RESULTS_DIR = BASE_DIR / "Results"

YEAR_START = 2000
YEAR_END = 2022
EXCLUDED_YEARS = {2015, 2016, 2017}

COL_YEAR = "Year"
COL_MONTH = "Month"
COL_DAY = "Day"
COL_GRID_ID = "Grid_ID"
COL_AREA = "Area_km2"

SHP_GRID_FIELD_CANDIDATES = ["Grid_ID", "GRID_ID", "grid_id", "GridID", "id", "ID"]

PANEL_ROWS = 3
PANEL_COLS = 4

# ----------------------------------------------------------------------
# Journal-style figure settings (Q1 look: clean sans-serif, large but not
# oversized text, crisp thin lines, no unnecessary chart junk)
# ----------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 13,
    "axes.linewidth": 0.6,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "figure.dpi": 150,
    "savefig.dpi": 600,
})

# =====================================================================
# MONTH CONVERSION
# =====================================================================

MONTH_NAME_TO_NUM = {name: num for num, name in enumerate(calendar.month_name) if name}
MONTH_NAME_TO_NUM_CI = {name.lower(): num for name, num in MONTH_NAME_TO_NUM.items()}
MONTH_ABBR_TO_NUM = {name.lower(): num for num, name in enumerate(calendar.month_abbr) if name}
MONTH_LOOKUP = {**MONTH_NAME_TO_NUM_CI, **MONTH_ABBR_TO_NUM}

# =====================================================================
# CLASSIFICATION COLOURS  (updated palette — higher contrast, more
# colourblind-safe, stays visually distinct from black state boundary
# lines and from itself under deuteranopia/protanopia simulation)
# =====================================================================

CLASS_ORDER = [
    "Low Activity",
    "Episodic Intense Lightning",
    "Frequent but Weak Lightning",
    "Persistent Intense Lightning",
    "No / Very Low Activity",
]

CLASS_CODES = {
    "Low Activity": 0,
    "Episodic Intense Lightning": 1,
    "Frequent but Weak Lightning": 2,
    "Persistent Intense Lightning": 3,
    "No / Very Low Activity": 4,
}

CLASS_COLOURS = [
    "#fdd835",   # Low activity          — warm yellow (light, calm)
    "#fb8c00",   # Episodic intense      — vivid orange
    "#00acc1",   # Frequent but weak     — teal / cyan
    "#8e24aa",   # Persistent intense    — deep purple
    "#e0e0e0",   # No / very low         — light neutral grey
]

CLASS_CMAP = mcolors.ListedColormap(CLASS_COLOURS)
CLASS_NORM = mcolors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], CLASS_CMAP.N)

# =====================================================================
# 3-4. READ / LOAD YEARLY CSVs
# =====================================================================

def read_year_csv(path):
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception as e:
        print(f"  ! Failed to read {path.name}: {e}")
        return None
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_all_years(data_dir, year_start, year_end, excluded_years):
    frames = []
    for year in range(year_start, year_end + 1):
        if year in excluded_years:
            print(f"  - Excluding year {year}")
            continue
        candidates = (
            glob.glob(str(data_dir / f"{year}_Grid.csv"))
            + glob.glob(str(data_dir / f"{year}_Grid.CSV"))
        )
        if not candidates:
            print(f"  ! No file found for {year}; skipping.")
            continue
        df = read_year_csv(Path(candidates[0]))
        if df is None or df.empty:
            print(f"  ! Empty file for {year}; skipping.")
            continue
        df["__source_year"] = year
        frames.append(df)
        print(f"  + Loaded {Path(candidates[0]).name} ({len(df):,} rows)")

    if not frames:
        raise RuntimeError("No lightning CSV files could be loaded. Check DATA_DIR and file names.")

    return pd.concat(frames, ignore_index=True)


# =====================================================================
# 5. BUILD MASTER TABLE
# =====================================================================

def build_master_table():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RESULTS_DIR / "lightning_master_cache.parquet"

    if cache_path.exists():
        print(f"\nLoading cached lightning master table:\n{cache_path}")
        return pd.read_parquet(cache_path)

    print("\nReading yearly lightning CSV files ...")
    master = load_all_years(DATA_DIR, YEAR_START, YEAR_END, EXCLUDED_YEARS)

    master[COL_GRID_ID] = master[COL_GRID_ID].astype(str).str.strip()
    master[COL_YEAR] = pd.to_numeric(master[COL_YEAR], errors="coerce")
    master["MonthNum"] = master[COL_MONTH].astype(str).str.strip().str.lower().map(MONTH_LOOKUP)
    master[COL_DAY] = pd.to_numeric(master[COL_DAY], errors="coerce")

    master["Date"] = pd.to_datetime(
        dict(year=master[COL_YEAR], month=master["MonthNum"], day=master[COL_DAY]),
        errors="coerce",
    )

    before = len(master)
    bad_month = master["MonthNum"].isna().sum()
    bad_year = master[COL_YEAR].isna().sum()
    bad_day = master[COL_DAY].isna().sum()

    master = master.dropna(subset=["Date", COL_GRID_ID])
    dropped = before - len(master)
    if dropped > 0:
        print(f"\n  Dropped {dropped:,} invalid rows.")
        print(f"  Invalid month: {bad_month:,}")
        print(f"  Invalid year: {bad_year:,}")
        print(f"  Invalid day: {bad_day:,}")

    master.to_parquet(cache_path, index=False)
    print(f"\nCached master table:\n{cache_path}")
    print(f"Total valid records: {len(master):,}")
    return master


# =====================================================================
# 6-7. LOAD SHAPEFILES
# =====================================================================

def load_grid_shapefile():
    gdf = gpd.read_file(SHP_GRID_PATH)
    gdf.columns = [str(c).strip() for c in gdf.columns]

    grid_field = next((c for c in SHP_GRID_FIELD_CANDIDATES if c in gdf.columns), None)
    if grid_field is None:
        raise KeyError(
            "Could not find Grid_ID field in grid shapefile.\n\n"
            f"Available columns:\n{list(gdf.columns)}\n\n"
            "Add the correct field name to SHP_GRID_FIELD_CANDIDATES."
        )
    gdf = gdf.rename(columns={grid_field: COL_GRID_ID})
    gdf[COL_GRID_ID] = gdf[COL_GRID_ID].astype(str).str.strip()

    if COL_AREA not in gdf.columns:
        raise KeyError(
            f"'{COL_AREA}' was not found in the grid shapefile.\n\n"
            f"Available fields:\n{list(gdf.columns)}\n\n"
            "The intensity calculation requires grid-cell area in km2."
        )

    print(f"\nLoaded grid shapefile: {len(gdf):,} cells")
    print(f"Grid ID field: {grid_field}")
    print(f"CRS: {gdf.crs}")
    print(f"Area field: {COL_AREA}")
    return gdf


def load_states_shapefile(target_crs):
    states = gpd.read_file(SHP_STATES_PATH)
    if states.crs is not None and target_crs is not None and states.crs != target_crs:
        states = states.to_crs(target_crs)
    print(f"\nLoaded state boundaries: {len(states):,} features")
    print(f"State CRS: {states.crs}")
    return states


# =====================================================================
# 8. COMPUTE MONTHLY FREQUENCY + INTENSITY
# =====================================================================

def compute_monthly_frequency_intensity(master, gdf_grid):
    """
    FREQUENCY: mean active days per calendar month (days month^-1)
    INTENSITY: total flashes / (grid area * total active days)
               (flashes km^-2 active-day^-1)
    """
    n_years = master["__source_year"].nunique()

    day_level = master.drop_duplicates(subset=[COL_GRID_ID, COL_YEAR, "MonthNum", "Date"])

    per_year_month = (
        day_level.groupby([COL_GRID_ID, COL_YEAR, "MonthNum"])["Date"]
        .nunique()
        .reset_index(name="active_days_in_month")
    )

    monthly_days = (
        per_year_month.groupby([COL_GRID_ID, "MonthNum"])["active_days_in_month"]
        .sum()
        .reset_index(name="total_active_days")
    )
    monthly_days["mean_monthly_active_days"] = monthly_days["total_active_days"] / n_years

    monthly_flashes = (
        master.groupby([COL_GRID_ID, "MonthNum"]).size().reset_index(name="total_flashes")
    )

    result = monthly_days.merge(monthly_flashes, on=[COL_GRID_ID, "MonthNum"], how="left")

    area_table = gdf_grid[[COL_GRID_ID, COL_AREA]].drop_duplicates(subset=[COL_GRID_ID])
    result = result.merge(area_table, on=COL_GRID_ID, how="left")

    result["monthly_intensity"] = result["total_flashes"] / (result[COL_AREA] * result["total_active_days"])
    result.loc[result["total_active_days"] <= 0, "monthly_intensity"] = np.nan

    return result


# =====================================================================
# 9. CLASSIFY MONTHLY FREQUENCY x INTENSITY
#    UPDATED: GLOBAL (pooled-across-all-12-months) thresholds instead
#    of a separate median recomputed for each calendar month.
#
#    Previously, each month was classified against its OWN median,
#    which meant "Persistent Intense" in January and "Persistent
#    Intense" in July did not represent the same absolute flash
#    density or active-day count -- only "top half of that month's
#    own distribution." That also produced a degenerate artifact in
#    the driest months (Jan/Nov/Dec), where the local threshold
#    collapsed to nearly the minimum nonzero value, making the "Low
#    Activity" class disappear entirely.
#
#    Now ONE frequency threshold and ONE intensity threshold are
#    computed from the full pooled monthly dataset (all grid-cell x
#    month rows together) and applied identically to every month. This
#    puts all 12 panels on the same scale, so the same colour always
#    means the same absolute magnitude regardless of which month it
#    appears in -- directly comparable to each other and consistent
#    with how the annual block already works (single threshold pair
#    for the whole map).
# =====================================================================

def classify_monthly_frequency_intensity(monthly_df):
    df = monthly_df.copy()
    df["monthly_class"] = "No / Very Low Activity"

    # Pool ALL months together to compute one global threshold pair
    valid = df[
        (df["mean_monthly_active_days"] > 0)
        & (df["monthly_intensity"] > 0)
    ].copy()

    if valid.empty:
        df["monthly_frequency_threshold"] = np.nan
        df["monthly_intensity_threshold"] = np.nan
        return df

    frequency_threshold = valid["mean_monthly_active_days"].median()
    intensity_threshold = valid["monthly_intensity"].median()

    print("\n" + "=" * 60)
    print("MONTHLY FREQUENCY x INTENSITY THRESHOLDS (GLOBAL, POOLED)")
    print("=" * 60)
    print(f"Frequency median (all months pooled): {frequency_threshold:.3f} active days month^-1")
    print(f"Intensity median (all months pooled): {intensity_threshold:.3f} flashes km^-2 active-day^-1")

    # Same threshold pair applied to every row regardless of month
    df["monthly_frequency_threshold"] = frequency_threshold
    df["monthly_intensity_threshold"] = intensity_threshold

    mask = (df["mean_monthly_active_days"] > 0) & (df["monthly_intensity"] > 0) & \
           (df["mean_monthly_active_days"] < frequency_threshold) & (df["monthly_intensity"] < intensity_threshold)
    df.loc[mask, "monthly_class"] = "Low Activity"

    mask = (df["mean_monthly_active_days"] > 0) & (df["monthly_intensity"] > 0) & \
           (df["mean_monthly_active_days"] < frequency_threshold) & (df["monthly_intensity"] >= intensity_threshold)
    df.loc[mask, "monthly_class"] = "Episodic Intense Lightning"

    mask = (df["mean_monthly_active_days"] > 0) & (df["monthly_intensity"] > 0) & \
           (df["mean_monthly_active_days"] >= frequency_threshold) & (df["monthly_intensity"] < intensity_threshold)
    df.loc[mask, "monthly_class"] = "Frequent but Weak Lightning"

    mask = (df["mean_monthly_active_days"] > 0) & (df["monthly_intensity"] > 0) & \
           (df["mean_monthly_active_days"] >= frequency_threshold) & (df["monthly_intensity"] >= intensity_threshold)
    df.loc[mask, "monthly_class"] = "Persistent Intense Lightning"

    print()
    print(df["monthly_class"].value_counts())

    return df


# =====================================================================
# 10. COMPUTE ANNUAL FREQUENCY + INTENSITY
# =====================================================================

def compute_annual_frequency_intensity(master, gdf_grid):
    n_years = master["__source_year"].nunique()

    day_level = master.drop_duplicates(subset=[COL_GRID_ID, COL_YEAR, "Date"])
    per_year = day_level.groupby([COL_GRID_ID, COL_YEAR])["Date"].nunique().reset_index(name="active_days_in_year")

    annual = per_year.groupby(COL_GRID_ID)["active_days_in_year"].sum().reset_index(name="total_active_days")
    annual["mean_annual_active_days"] = annual["total_active_days"] / n_years

    flash_counts = master.groupby(COL_GRID_ID).size().reset_index(name="total_flash_count")
    annual = annual.merge(flash_counts, on=COL_GRID_ID, how="left")

    area_table = gdf_grid[[COL_GRID_ID, COL_AREA]].drop_duplicates(subset=[COL_GRID_ID])
    annual = annual.merge(area_table, on=COL_GRID_ID, how="left")

    annual["mean_annual_flash_density"] = annual["total_flash_count"] / (annual[COL_AREA] * n_years)
    annual["flash_density_per_active_day"] = annual["total_flash_count"] / (annual[COL_AREA] * annual["total_active_days"])
    annual.loc[annual["total_active_days"] <= 0, "flash_density_per_active_day"] = np.nan

    return annual


# =====================================================================
# 11. CLASSIFY ANNUAL FREQUENCY x INTENSITY
# =====================================================================

def classify_annual_frequency_intensity(annual_df):
    df = annual_df.copy()
    valid = df[(df["mean_annual_active_days"] > 0) & (df["flash_density_per_active_day"] > 0)].copy()

    frequency_threshold = valid["mean_annual_active_days"].median()
    intensity_threshold = valid["flash_density_per_active_day"].median()

    print("\n" + "=" * 60)
    print("ANNUAL FREQUENCY x INTENSITY THRESHOLDS")
    print("=" * 60)
    print(f"Frequency median: {frequency_threshold:.3f} active days year^-1")
    print(f"Intensity median: {intensity_threshold:.3f} flashes km^-2 active-day^-1")

    df["annual_frequency_threshold"] = frequency_threshold
    df["annual_intensity_threshold"] = intensity_threshold
    df["annual_class"] = "No / Very Low Activity"

    mask = (df["mean_annual_active_days"] < frequency_threshold) & (df["flash_density_per_active_day"] < intensity_threshold)
    df.loc[mask, "annual_class"] = "Low Activity"

    mask = (df["mean_annual_active_days"] < frequency_threshold) & (df["flash_density_per_active_day"] >= intensity_threshold)
    df.loc[mask, "annual_class"] = "Episodic Intense Lightning"

    mask = (df["mean_annual_active_days"] >= frequency_threshold) & (df["flash_density_per_active_day"] < intensity_threshold)
    df.loc[mask, "annual_class"] = "Frequent but Weak Lightning"

    mask = (df["mean_annual_active_days"] >= frequency_threshold) & (df["flash_density_per_active_day"] >= intensity_threshold)
    df.loc[mask, "annual_class"] = "Persistent Intense Lightning"

    print()
    print(df["annual_class"].value_counts())
    return df


# =====================================================================
# 12. SCALE BAR LENGTH
# =====================================================================

def compute_scale_length(gdf):
    minx, miny, maxx, maxy = gdf.total_bounds
    is_geographic = gdf.crs is not None and gdf.crs.is_geographic

    if is_geographic:
        mean_lat = (miny + maxy) / 2.0
        km_per_deg = 111.32 * np.cos(np.radians(mean_lat))
        width_km = (maxx - minx) * km_per_deg
    else:
        km_per_deg = None
        width_km = (maxx - minx) / 1000.0

    nice_lengths_km = [10, 20, 25, 50, 100, 200, 250, 500, 1000]
    target_km = width_km * 0.25
    length_km = min(nice_lengths_km, key=lambda v: abs(v - target_km))
    length_units = length_km / km_per_deg if is_geographic else length_km * 1000.0
    return length_km, length_units


# =====================================================================
# 13. SHARED MAP EXTENT (ensures every subplot is perfectly aligned)
# =====================================================================

def compute_shared_extent(gdf, pad_frac=0.01):
    minx, miny, maxx, maxy = gdf.total_bounds
    pad_x = (maxx - minx) * pad_frac
    pad_y = (maxy - miny) * pad_frac
    return (minx - pad_x, maxx + pad_x), (miny - pad_y, maxy + pad_y)


def style_map_axes(ax, xlim, ylim):
    """Apply identical extent/aspect/frame to every map panel. No
    background tint -- plain white, matching the reference figure."""
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color("black")


# =====================================================================
# 14. LEGEND LABEL BUILDER
#     UPDATED: short per-swatch class names only (2-3 words) so text
#     can never overflow into a neighbouring patch's label. The full
#     numeric threshold definitions are returned separately as one
#     compact caption string instead of being repeated under every
#     swatch.
# =====================================================================

def build_legend_labels(freq_thresh, intens_thresh, freq_unit):
    """
    freq_unit: 'month' or 'year' -- controls the unit text shown next to
    the frequency threshold so the monthly-block caption reads "days
    month^-1" and the annual-block caption reads "days year^-1". The
    intensity unit (flashes km^-2 active-day^-1) doesn't change between
    blocks, since "active day" always means the same thing.

    Returns:
        short_labels : dict of class -> short swatch label (no numbers)
        caption       : single-line string with both numeric thresholds,
                         shown once beneath the swatch row
    """
    short_labels = {
    "Low Activity": "Low\nActivity",
    "Episodic Intense Lightning": "Episodic\nIntense",
    "Frequent but Weak Lightning": "Frequent\nbut Weak",
    "Persistent Intense Lightning": "Persistent\nIntense",
    "No / Very Low Activity": "No / Very Low",
    }

    freq_label = f"d {freq_unit}$^{{-1}}$"
    caption = (
        f"Frequency threshold (median): {freq_thresh:.2f} {freq_label}   |   "
        f"Intensity threshold (median): {intens_thresh:.3f} flashes km$^{{-2}}$ active-day$^{{-1}}$"
    )
    return short_labels, caption


# =====================================================================
# 15. SINGLE-ROW FURNITURE: legend + scale bar + north arrow together
#     (matches the reference figure's bottom-strip layout exactly)
#     UPDATED: explicit gap between swatches, short swatch labels, and
#     one caption line for the numeric thresholds -- eliminates the
#     text overlap that occurred when the full definition was repeated
#     under every patch.
# =====================================================================

def draw_bottom_furniture(ax, gdf_for_scale, freq_thresh, intens_thresh, freq_unit,
                           legend_title):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    short_labels, caption = build_legend_labels(freq_thresh, intens_thresh, freq_unit)

    # --- categorical legend swatches (left portion) ---
    n = len(CLASS_ORDER)
    legend_left, legend_right = 0.0, 0.62
    gap = 0.012                                    # explicit spacing between swatches
    patch_w = (legend_right - legend_left - gap * (n - 1)) / n

    ax.text(legend_left, 0.97, legend_title, ha="left", va="top",
            fontsize=13, fontweight="bold", transform=ax.transAxes)

    for i, cls in enumerate(CLASS_ORDER):
        x0 = legend_left + i * (patch_w + gap)
        ax.add_patch(Rectangle((x0, 0.48), patch_w, 0.28,
                                facecolor=CLASS_COLOURS[CLASS_CODES[cls]],
                                edgecolor="black", linewidth=0.5,
                                transform=ax.transAxes))
        ax.text(x0 + patch_w / 2, 0.42, short_labels[cls], ha="center", va="top",
                fontsize=11.5, fontweight="medium", transform=ax.transAxes)

    # --- single caption line with the numeric thresholds (stated once,
    #     not repeated per swatch, so it never overlaps the patches) ---
    ax.text(legend_left, 0.10, caption, ha="left", va="top",
            fontsize=10.5, style="italic", color="#333333",
            transform=ax.transAxes)

    # --- scale bar (middle) ---
    length_km, _ = compute_scale_length(gdf_for_scale)
    sb_x0, sb_x1 = 0.72, 0.86
    y = 0.55
    ax.plot([sb_x0, sb_x1], [y, y], color="black", linewidth=2.6, transform=ax.transAxes)
    ax.plot([sb_x0, sb_x0], [y - 0.08, y + 0.08], color="black", linewidth=2.6, transform=ax.transAxes)
    ax.plot([sb_x1, sb_x1], [y - 0.08, y + 0.08], color="black", linewidth=2.6, transform=ax.transAxes)
    ax.text((sb_x0 + sb_x1) / 2, y + 0.15, f"{length_km:g} km", ha="center", va="bottom",
            fontsize=11.5, fontweight="bold", transform=ax.transAxes)

    # --- north arrow (right) ---
    nx = 0.95
    ax.annotate("N", xy=(nx, 0.78), xytext=(nx, 0.32),
                xycoords="axes fraction", textcoords="axes fraction",
                ha="center", va="center", fontsize=13, fontweight="bold",
                arrowprops=dict(facecolor="black", edgecolor="black",
                                 width=4.0, headwidth=12, headlength=11))


# =====================================================================
# 16. FINAL COMBINED FIGURE  (layout matches the reference hotspot map)
#     UPDATED: taller furniture strips (height_ratios bumped) to make
#     room for the new caption line beneath the swatch labels.
# =====================================================================

def plot_final_figure(gdf_grid, monthly_df, annual_df, states_gdf, out_dir):
    """
    (a) 3x4 monthly classification grid (left block) with its own
        single-row legend+scale+north-arrow strip beneath it, using the
        MEDIAN-OF-MONTHLY-THRESHOLDS as the representative frequency
        number, labelled in days month^-1.
    (b) Annual classification map (right block) with its own
        single-row legend+scale+north-arrow strip, using the annual
        median threshold, labelled in days year^-1.
    No background tint; plain white throughout, matching the reference
    figure. Month labels sit top-left inside each panel.
    """

    monthly_map = gdf_grid.merge(monthly_df, on=COL_GRID_ID, how="left")
    monthly_map["class_code"] = monthly_map["monthly_class"].map(CLASS_CODES)

    annual_map = gdf_grid.merge(annual_df[[COL_GRID_ID, "annual_class"]], on=COL_GRID_ID, how="left")
    annual_map["class_code"] = annual_map["annual_class"].map(CLASS_CODES)

    xlim, ylim = compute_shared_extent(gdf_grid)

    month_numbers = list(range(1, 13))
    month_abbr = [calendar.month_abbr[m] for m in month_numbers]

    # Annual thresholds (for block b)
    valid_annual = annual_df[(annual_df["mean_annual_active_days"] > 0) & (annual_df["flash_density_per_active_day"] > 0)]
    annual_freq_thresh = valid_annual["mean_annual_active_days"].median()
    annual_intens_thresh = valid_annual["flash_density_per_active_day"].median()

    # MONTHLY thresholds (for block a) -- UPDATED: classify_monthly_
    # frequency_intensity() now computes ONE global threshold pair
    # pooled across all 12 months and stores the identical value in
    # every row, so we just read it once instead of averaging 12
    # separate per-month thresholds. This is what makes all 12 panels
    # directly comparable on the same scale, labelled in days month^-1.
    monthly_thresh_valid = monthly_df.dropna(subset=["monthly_frequency_threshold", "monthly_intensity_threshold"])
    monthly_freq_thresh = monthly_thresh_valid["monthly_frequency_threshold"].iloc[0]
    monthly_intens_thresh = monthly_thresh_valid["monthly_intensity_threshold"].iloc[0]

    # ------------------------------------------------------------
    # Overall layout: (a) monthly block | (b) annual block, side by
    # side -- same proportions as the reference figure.
    # ------------------------------------------------------------
    fig = plt.figure(figsize=(27, 13))
    outer = gridspec.GridSpec(1, 2, width_ratios=[2.15, 1.55], wspace=0.06, figure=fig)

    # ---------------- (a) monthly multipanel block ----------------
    monthly_outer = gridspec.GridSpecFromSubplotSpec(
        PANEL_ROWS + 1, PANEL_COLS, subplot_spec=outer[0],
        height_ratios=[1, 1, 1, 0.42], hspace=0.05, wspace=0.03,   # taller furniture row for caption line
    )

    month_axes = []
    for idx, month in enumerate(month_numbers):
        row, col = divmod(idx, PANEL_COLS)
        ax = fig.add_subplot(monthly_outer[row, col])

        subset = monthly_map[monthly_map["MonthNum"] == month]
        subset.plot(
            column="class_code", cmap=CLASS_CMAP, norm=CLASS_NORM,
            linewidth=0.10, edgecolor="black",
            ax=ax, legend=False,
            missing_kwds={"color": "#f5f5f5", "edgecolor": "#cccccc"},
        )
        states_gdf.boundary.plot(ax=ax, color="black", linewidth=0.5)

        style_map_axes(ax, xlim, ylim)
        # Month label top-left inside the panel (matches reference figure)
        ax.text(0.03, 0.97, month_abbr[idx], transform=ax.transAxes,
                ha="left", va="top", fontsize=13, fontweight="bold")

        month_axes.append(ax)

    month_axes[0].text(-0.06, 1.12, "(a)", transform=month_axes[0].transAxes,
                        ha="left", va="bottom", fontsize=20, fontweight="bold")

    furniture_ax_monthly = fig.add_subplot(monthly_outer[PANEL_ROWS, :])
    draw_bottom_furniture(
        furniture_ax_monthly, monthly_map,
        monthly_freq_thresh, monthly_intens_thresh, freq_unit="month",
        legend_title="Lightning climatology regime — monthly classification",
    )

    # ---------------- (b) annual block ----------------
    annual_outer = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=outer[1], height_ratios=[1, 0.18], hspace=0.04,   # taller furniture row for caption line
    )

    ax_annual = fig.add_subplot(annual_outer[0])
    annual_map.plot(
        column="class_code", cmap=CLASS_CMAP, norm=CLASS_NORM,
        linewidth=0.15, edgecolor="black",
        ax=ax_annual, legend=False,
        missing_kwds={"color": "#f5f5f5", "edgecolor": "#cccccc"},
    )
    states_gdf.boundary.plot(ax=ax_annual, color="black", linewidth=0.6)
    style_map_axes(ax_annual, xlim, ylim)
    ax_annual.text(-0.03, 1.02, "(b)", transform=ax_annual.transAxes,
                    ha="left", va="bottom", fontsize=20, fontweight="bold")

    furniture_ax_annual = fig.add_subplot(annual_outer[1])
    draw_bottom_furniture(
        furniture_ax_annual, annual_map,
        annual_freq_thresh, annual_intens_thresh, freq_unit="year",
        legend_title="Lightning climatology regime — annual classification",
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Lightning_Frequency_Intensity_Monthly_Annual.tif"
    fig.savefig(out_path, format="tiff", dpi=600, bbox_inches="tight",
                pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)

    print(f"\nFinal journal-ready figure saved:\n{out_path}")


# =====================================================================
# 17. EXCEL EXPORT
# =====================================================================

def export_excel(gdf_grid, monthly_df, annual_df, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    META_COLS = ["Row", "Col", "Area_km2", "index_state", "STNAME_SH", "Division"]
    meta_cols_present = [c for c in META_COLS if c in gdf_grid.columns]
    meta = gdf_grid[[COL_GRID_ID] + meta_cols_present].drop_duplicates(subset=[COL_GRID_ID])

    monthly_out = meta.merge(monthly_df, on=COL_GRID_ID, how="right")
    monthly_path = out_dir / "Monthly_Frequency_Intensity_Classification.xlsx"
    monthly_out.to_excel(monthly_path, index=False, sheet_name="Monthly_Classification")
    print(f"\nMonthly Excel saved:\n{monthly_path}")

    annual_out = meta.merge(annual_df, on=COL_GRID_ID, how="right")
    annual_path = out_dir / "Annual_Frequency_Intensity_Classification.xlsx"
    annual_out.to_excel(annual_path, index=False, sheet_name="Annual_Classification")
    print(f"\nAnnual Excel saved:\n{annual_path}")


# =====================================================================
# 18. PRINT SUMMARY
# =====================================================================

def print_analysis_summary(master, monthly_df, annual_df):
    print("\n" + "=" * 75)
    print("ANALYSIS SUMMARY")
    print("=" * 75)

    years_used = sorted(master["__source_year"].dropna().astype(int).unique())
    print(f"\nYears used:\n{years_used}")
    print(f"\nNumber of years used: {len(years_used)}")
    print(f"\nLightning records: {len(master):,}")

    print("\nAnnual frequency x intensity regimes:")
    print(annual_df["annual_class"].value_counts())

    print("\nMonthly frequency x intensity regimes:")
    monthly_counts = monthly_df.groupby(["MonthNum", "monthly_class"]).size().reset_index(name="GridCells")
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        subset = monthly_counts[monthly_counts["MonthNum"] == month]
        print(f"\n{month_name}")
        print(subset[["monthly_class", "GridCells"]].to_string(index=False))

    print("\n" + "=" * 75)


# =====================================================================
# 19. MAIN PIPELINE
# =====================================================================

def main():
    print("\n" + "=" * 75)
    print("LIGHTNING FREQUENCY x INTENSITY CLIMATOLOGY")
    print("=" * 75)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    figures_dir = RESULTS_DIR / "Figures"
    excel_dir = RESULTS_DIR / "Excel"
    figures_dir.mkdir(parents=True, exist_ok=True)
    excel_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 75)
    print("STEP 1: BUILDING COMBINED LIGHTNING TABLE")
    print("=" * 75)
    master = build_master_table()

    print("\n" + "=" * 75)
    print("STEP 2: LOADING SPATIAL DATA")
    print("=" * 75)
    gdf_grid = load_grid_shapefile()
    states_gdf = load_states_shapefile(target_crs=gdf_grid.crs)

    print("\n" + "=" * 75)
    print("STEP 3: COMPUTING MONTHLY FREQUENCY + INTENSITY")
    print("=" * 75)
    monthly_df = compute_monthly_frequency_intensity(master, gdf_grid)

    print("\n" + "=" * 75)
    print("STEP 4: CLASSIFYING MONTHLY LIGHTNING REGIMES")
    print("=" * 75)
    monthly_df = classify_monthly_frequency_intensity(monthly_df)

    print("\n" + "=" * 75)
    print("STEP 5: COMPUTING ANNUAL FREQUENCY + INTENSITY")
    print("=" * 75)
    annual_df = compute_annual_frequency_intensity(master, gdf_grid)

    print("\n" + "=" * 75)
    print("STEP 6: CLASSIFYING ANNUAL LIGHTNING REGIMES")
    print("=" * 75)
    annual_df = classify_annual_frequency_intensity(annual_df)

    print("\n" + "=" * 75)
    print("STEP 7: CREATING FINAL FIGURE")
    print("=" * 75)
    plot_final_figure(gdf_grid, monthly_df, annual_df, states_gdf, figures_dir)

    print("\n" + "=" * 75)
    print("STEP 8: EXPORTING EXCEL TABLES")
    print("=" * 75)
    export_excel(gdf_grid, monthly_df, annual_df, excel_dir)

    print("\n" + "=" * 75)
    print("STEP 9: SUMMARY")
    print("=" * 75)
    print_analysis_summary(master, monthly_df, annual_df)

    print("\n" + "=" * 75)
    print("ANALYSIS COMPLETED SUCCESSFULLY")
    print("=" * 75)
    print(f"\nResults directory:\n{RESULTS_DIR}")
    print(f"\nFinal figure:\n{figures_dir / 'Lightning_Frequency_Intensity_Monthly_Annual.tif'}")
    print(f"\nMonthly table:\n{excel_dir / 'Monthly_Frequency_Intensity_Classification.xlsx'}")
    print(f"\nAnnual table:\n{excel_dir / 'Annual_Frequency_Intensity_Classification.xlsx'}")
    print("\n" + "=" * 75)


if __name__ == "__main__":
    main()