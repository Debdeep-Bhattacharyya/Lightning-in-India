"""
LIS vs NRSC Lightning Data Validation Pipeline
================================================
Validates TRMM-LIS / ISS-LIS satellite lightning climatology against
NRSC ground-based lightning detection network data for India.

Produces:
  1. Gridded spatial climatology comparison (multiple resolutions) + validation stats
       - independent-scale pattern map (LIS vs NRSC hotspot agreement)
       - shared-colorbar log10 map (directly comparable magnitudes)
       - ratio/bias map (log10(NRSC/LIS) per cell)
  2. Seasonal/monthly cycle comparison + validation stats
  3. Event-level space-time matching (storm-scale co-occurrence)
  4. Optional: alignment to your India_025deg_Grid shapefile and state-level
     aggregation using India_States shapefile (same map/stat suite as #1)
  5. A single consolidated validation_statistics_master.csv summarizing every
     analysis (bias, RMSE, MAE, raw/log Pearson r, Spearman rho, etc.) for
     easy reporting to reviewers.

Run locally with: python lis_nrsc_validation.py

Requirements (install once):
  pip install pandas numpy scipy scikit-learn matplotlib geopandas shapely
"""

import os
import glob
import time
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.neighbors import BallTree
import matplotlib.pyplot as plt

# =========================================================================
# CONFIG -- EDIT THESE PATHS AND SETTINGS
# =========================================================================
LIS_FOLDER   = r"D:\Articles\Working\Lightning India\Data\Lightning\2 Yearly_CSV"
NRSC_FOLDER  = r"E:\PhD\Data\NRSC Data (India_Clean_20_25)"
OUTPUT_DIR   = r"D:\Articles\Working\Lightning India\Data\Validation_Output"

# Shapefiles (set to None to skip and use a plain regular degree grid instead)
GRID_SHAPEFILE   = r"D:\Articles\Working\Lightning India\Data\Shapefiles\India_025deg_Grid.shp"
STATES_SHAPEFILE = r"D:\Articles\Working\Lightning India\Data\Shapefiles\India_States.shp"
STATE_NAME_COLUMN = "STNAME_SH"   # column in India_States.shp holding state names

# Years present in BOTH datasets (edit if you add more NRSC years later)
YEARS = [2020, 2021, 2022]

# Grid resolutions (degrees) to test for the fallback regular-grid comparison
GRID_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0]

# Resolution (degrees) used specifically for the spatial map figures when no
# grid shapefile is available (finer = noisier map, coarser = smoother)
MAP_RESOLUTION_DEG = 0.5

# Known state-name column in India_States.shp
STATE_NAME_COL = "STNAME_SH"

# Event-level matching thresholds to test
SPATIAL_RADII_KM   = [25, 50, 100]
TIME_WINDOWS_MIN   = [30, 60, 120, 180, 360]

# Figure export settings
FIGURE_DPI = 300

R_EARTH_KM = 6371.0
MONTH_MAP = {m: i + 1 for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July',
     'August', 'September', 'October', 'November', 'December'])}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Accumulates one dict per analysis (grid resolution, official grid, state,
# seasonal, ...) -- exported at the very end as one master statistics table.
ALL_VALIDATION_STATS = []


# =========================================================================
# LOADERS
# =========================================================================
def load_lis(years):
    """Load and concatenate LIS yearly CSVs, parse IST datetime."""
    frames = []
    for y in years:
        path = os.path.join(LIS_FOLDER, f"{y}.csv")
        if not os.path.exists(path):
            print(f"  [WARN] LIS file not found, skipping: {path}")
            continue
        df = pd.read_csv(path)
        frames.append(df)
        print(f"  Loaded LIS {y}: {len(df):,} rows")
    lis = pd.concat(frames, ignore_index=True)

    lis['MonthNum'] = lis['Month'].map(MONTH_MAP)
    lis['datetime_IST'] = pd.to_datetime(
        lis['Year'].astype(str) + '-' + lis['MonthNum'].astype(str) + '-' +
        lis['Day'].astype(str) + ' ' + lis['IST'],
        format='%Y-%m-%d %H:%M:%S', errors='coerce')
    n_bad = lis['datetime_IST'].isna().sum()
    if n_bad:
        print(f"  [WARN] {n_bad} LIS rows failed datetime parse, dropping")
        lis = lis.dropna(subset=['datetime_IST'])
    lis['date'] = lis['datetime_IST'].dt.date
    return lis


def load_nrsc(years):
    """Load and concatenate NRSC yearly CSVs, parse IST datetime (12hr format)."""
    frames = []
    for y in years:
        path = os.path.join(NRSC_FOLDER, f"India_NRSC_{y}.csv")
        if not os.path.exists(path):
            print(f"  [WARN] NRSC file not found, skipping: {path}")
            continue
        df = pd.read_csv(path)
        frames.append(df)
        print(f"  Loaded NRSC {y}: {len(df):,} rows")
    nrsc = pd.concat(frames, ignore_index=True)

    nrsc = nrsc.dropna(subset=['Time'])
    nrsc['datetime_IST'] = pd.to_datetime(
        nrsc['Date'] + ' ' + nrsc['Time'],
        format='%Y-%m-%d %I:%M:%S %p', errors='coerce')
    n_bad = nrsc['datetime_IST'].isna().sum()
    if n_bad:
        print(f"  [WARN] {n_bad} NRSC rows failed datetime parse, dropping")
        nrsc = nrsc.dropna(subset=['datetime_IST'])
    nrsc['date'] = nrsc['datetime_IST'].dt.date
    return nrsc


# =========================================================================
# 0. VALIDATION STATISTICS (shared by every comparison below)
# =========================================================================
def compute_validation_stats(x, y, label=''):
    """Standard validation statistics for comparing x (LIS) against
    y (NRSC), following common remote-sensing validation practice.

    Both raw and log1p-transformed versions of bias/RMSE/MAE are reported,
    since the two datasets differ in magnitude by roughly 1-2 orders of
    magnitude (ground network vs. sparse satellite overpass sampling) --
    the raw-scale numbers will look large/biased almost by construction,
    the log-scale numbers are what's actually informative for pattern
    agreement.

    Returns a flat dict, ready to append to ALL_VALIDATION_STATS.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n == 0:
        return dict(label=label, n=0)

    r_raw, p_raw = pearsonr(x, y)
    r_log, p_log = pearsonr(np.log1p(x), np.log1p(y))
    rho, p_rho = spearmanr(x, y)

    diff = y - x
    bias = diff.mean()                                   # mean(NRSC - LIS)
    mae = np.abs(diff).mean()
    rmse = np.sqrt((diff ** 2).mean())
    nrmse = rmse / y.mean() if y.mean() != 0 else np.nan  # normalized by mean NRSC

    log_diff = np.log1p(y) - np.log1p(x)
    bias_log = log_diff.mean()
    mae_log = np.abs(log_diff).mean()
    rmse_log = np.sqrt((log_diff ** 2).mean())

    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(x > 0, y / x, np.nan)
    median_ratio = np.nanmedian(ratio)

    stats = dict(
        label=label, n=n,
        pearson_r_raw=r_raw, pearson_p_raw=p_raw,
        pearson_r_log=r_log, pearson_p_log=p_log,
        spearman_rho=rho, spearman_p=p_rho,
        bias_nrsc_minus_lis=bias, mae=mae, rmse=rmse, nrmse=nrmse,
        bias_log=bias_log, mae_log=mae_log, rmse_log=rmse_log,
        median_ratio_nrsc_over_lis=median_ratio,
    )
    print(f"  [STATS:{label}] n={n}  r_raw={r_raw:.3f}  r_log={r_log:.3f}  rho={rho:.3f}  "
          f"bias={bias:.2f}  rmse={rmse:.2f}  rmse_log={rmse_log:.3f}  median_ratio={median_ratio:.2f}")
    return stats


def export_master_validation_summary():
    """Write every stats dict collected in ALL_VALIDATION_STATS to one CSV,
    for easy reporting/reviewer response."""
    if not ALL_VALIDATION_STATS:
        print("\n[WARN] No validation statistics were collected -- nothing to export.")
        return None
    df = pd.DataFrame(ALL_VALIDATION_STATS)
    out_path = os.path.join(OUTPUT_DIR, "validation_statistics_master.csv")
    df.to_csv(out_path, index=False)
    print(f"\n=== Master validation statistics ({len(df)} analyses) ===")
    print(df.to_string(index=False))
    print(f"Saved: {out_path}")
    return df


# =========================================================================
# 1. GRIDDED SPATIAL CLIMATOLOGY COMPARISON
# =========================================================================
def grid_climatology_regular(lis, nrsc, resolutions):
    """Compare gridded counts at several plain regular-degree resolutions."""
    print("\n--- Gridded climatology (regular degree grid) ---")
    rows = []
    for res in resolutions:
        lis_gx = np.floor(lis['Long'] / res) * res
        lis_gy = np.floor(lis['Lat'] / res) * res
        nrsc_gx = np.floor(nrsc['x'] / res) * res
        nrsc_gy = np.floor(nrsc['y'] / res) * res

        lis_grid = pd.DataFrame({'gx': lis_gx, 'gy': lis_gy}).value_counts().rename('lis_count').reset_index()
        nrsc_grid = pd.DataFrame({'gx': nrsc_gx, 'gy': nrsc_gy}).value_counts().rename('nrsc_count').reset_index()
        merged = pd.merge(lis_grid, nrsc_grid, on=['gx', 'gy'], how='outer').fillna(0)

        stats = compute_validation_stats(merged.lis_count, merged.nrsc_count, label=f'grid_{res}deg')
        stats['resolution_deg'] = res
        stats['n_cells'] = len(merged)
        ALL_VALIDATION_STATS.append(stats)
        rows.append(stats)

        merged.to_csv(os.path.join(OUTPUT_DIR, f"grid_comparison_{res}deg.csv"), index=False)

    result = pd.DataFrame(rows)
    result.to_csv(os.path.join(OUTPUT_DIR, "grid_correlation_summary.csv"), index=False)
    return result


def make_regular_grid_map(lis, nrsc, resolution=None):
    """Build a regular-degree grid WITH polygon geometry (for when no official
    grid shapefile is available) and produce the full map suite."""
    import geopandas as gpd
    from shapely.geometry import box

    if resolution is None:
        resolution = MAP_RESOLUTION_DEG
    print(f"\n--- Spatial maps (fallback regular {resolution}deg grid, no shapefile) ---")

    lis_gx = np.floor(lis['Long'] / resolution) * resolution
    lis_gy = np.floor(lis['Lat'] / resolution) * resolution
    nrsc_gx = np.floor(nrsc['x'] / resolution) * resolution
    nrsc_gy = np.floor(nrsc['y'] / resolution) * resolution

    lis_grid = pd.DataFrame({'gx': lis_gx, 'gy': lis_gy}).value_counts().rename('lis_count').reset_index()
    nrsc_grid = pd.DataFrame({'gx': nrsc_gx, 'gy': nrsc_gy}).value_counts().rename('nrsc_count').reset_index()
    merged = pd.merge(lis_grid, nrsc_grid, on=['gx', 'gy'], how='outer').fillna(0)

    merged['geometry'] = merged.apply(
        lambda row: box(row['gx'], row['gy'], row['gx'] + resolution, row['gy'] + resolution), axis=1)
    gdf = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:4326')

    stats = compute_validation_stats(gdf['lis_count'], gdf['nrsc_count'], label=f'fallback_grid_{resolution}deg_map')
    ALL_VALIDATION_STATS.append(stats)

    plot_side_by_side_map(gdf, 'lis_count', 'nrsc_count',
                           title_left=f'LIS flash count (per {resolution}\u00b0 grid cell)',
                           title_right=f'NRSC stroke count (per {resolution}\u00b0 grid cell)',
                           out_name='grid_level_map_comparison.png')
    plot_log_shared_map(gdf, 'lis_count', 'nrsc_count',
                         out_name='grid_level_map_log_shared.png')
    plot_ratio_bias_map(gdf, 'lis_count', 'nrsc_count',
                         out_name='grid_level_map_ratio_bias.png')
    return gdf


def grid_climatology_shapefile(lis, nrsc, grid_shp_path):
    """Aggregate both datasets onto the actual India_025deg_Grid shapefile cells."""
    import geopandas as gpd
    from shapely.geometry import Point

    print("\n--- Gridded climatology (using India_025deg_Grid.shp) ---")
    grid = gpd.read_file(grid_shp_path)
    if grid.crs is None:
        grid = grid.set_crs('EPSG:4326')
    grid = grid.to_crs('EPSG:4326')
    grid['cell_id'] = range(len(grid))

    lis_pts = gpd.GeoDataFrame(
        lis, geometry=gpd.points_from_xy(lis['Long'], lis['Lat']), crs='EPSG:4326')
    nrsc_pts = gpd.GeoDataFrame(
        nrsc, geometry=gpd.points_from_xy(nrsc['x'], nrsc['y']), crs='EPSG:4326')

    lis_joined = gpd.sjoin(lis_pts, grid[['cell_id', 'geometry']], how='left', predicate='within')
    nrsc_joined = gpd.sjoin(nrsc_pts, grid[['cell_id', 'geometry']], how='left', predicate='within')

    lis_counts = lis_joined.groupby('cell_id').size().rename('lis_count')
    nrsc_counts = nrsc_joined.groupby('cell_id').size().rename('nrsc_count')

    merged = pd.concat([lis_counts, nrsc_counts], axis=1).fillna(0)
    merged = grid.merge(merged, left_on='cell_id', right_index=True, how='left').fillna(0)

    stats = compute_validation_stats(merged['lis_count'], merged['nrsc_count'], label='official_grid_0.25deg')
    ALL_VALIDATION_STATS.append(stats)

    out_path = os.path.join(OUTPUT_DIR, "grid_comparison_official.shp")
    merged.to_file(out_path)
    print(f"  Saved: {out_path}")

    plot_side_by_side_map(merged, 'lis_count', 'nrsc_count',
                           title_left='LIS flash count (per 0.25\u00b0 grid cell)',
                           title_right='NRSC stroke count (per 0.25\u00b0 grid cell)',
                           out_name='grid_level_map_comparison.png')
    plot_log_shared_map(merged, 'lis_count', 'nrsc_count',
                         out_name='grid_level_map_log_shared.png')
    plot_ratio_bias_map(merged, 'lis_count', 'nrsc_count',
                         out_name='grid_level_map_ratio_bias.png')
    return merged


# =========================================================================
# 2. SEASONAL / MONTHLY CYCLE COMPARISON
# =========================================================================
def seasonal_cycle_comparison(lis, nrsc):
    print("\n--- Seasonal cycle comparison ---")
    lis_month = lis.groupby('MonthNum').size().reindex(range(1, 13), fill_value=0)
    nrsc_month = nrsc.groupby('Month').size().reindex(range(1, 13), fill_value=0)

    lis_frac = lis_month / lis_month.sum()
    nrsc_frac = nrsc_month / nrsc_month.sum()

    stats_frac = compute_validation_stats(lis_frac.values, nrsc_frac.values, label='seasonal_monthly_fraction')
    ALL_VALIDATION_STATS.append(stats_frac)
    r, p = stats_frac['pearson_r_raw'], stats_frac['pearson_p_raw']
    rho = stats_frac['spearman_rho']

    out = pd.DataFrame({'LIS_frac': lis_frac, 'NRSC_frac': nrsc_frac})
    out.to_csv(os.path.join(OUTPUT_DIR, "seasonal_cycle_comparison.csv"))

    fig, ax = plt.subplots(figsize=(8, 5))
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    ax.plot(months, lis_frac.values, marker='o', label='LIS (satellite)')
    ax.plot(months, nrsc_frac.values, marker='s', label='NRSC (ground network)')
    ax.set_ylabel('Fraction of annual flashes')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "seasonal_cycle_comparison.png"), dpi=FIGURE_DPI)
    plt.close(fig)

    # Season-level totals (Winter=Dec-Feb, Pre-monsoon=Mar-May, Monsoon=Jun-Sep, Post-monsoon=Oct-Nov)
    season_map = {}
    for m in [12, 1, 2]: season_map[m] = 'Winter'
    for m in [3, 4, 5]: season_map[m] = 'Pre-monsoon'
    for m in [6, 7, 8, 9]: season_map[m] = 'Monsoon'
    for m in [10, 11]: season_map[m] = 'Post-monsoon'

    lis_season = lis['MonthNum'].map(season_map).value_counts()
    nrsc_season = nrsc['Month'].map(season_map).value_counts()
    season_table = pd.DataFrame({
        'LIS_count': lis_season, 'NRSC_count': nrsc_season,
        'LIS_%': (100 * lis_season / lis_season.sum()).round(1),
        'NRSC_%': (100 * nrsc_season / nrsc_season.sum()).round(1),
    })
    print(season_table)
    season_table.to_csv(os.path.join(OUTPUT_DIR, "seasonal_totals.csv"))
    return out, season_table


# =========================================================================
# 3. EVENT-LEVEL SPACE-TIME MATCHING
# =========================================================================
def event_level_matching(lis, nrsc, radii_km, time_windows_min):
    print("\n--- Event-level space-time matching ---")
    nrsc_by_date = {d: g for d, g in nrsc.groupby('date')}
    rows = []
    t0 = time.time()
    for R in radii_km:
        for T in time_windows_min:
            matched, total = 0, 0
            for d, lis_day in lis.groupby('date'):
                total += len(lis_day)
                if d not in nrsc_by_date:
                    continue
                nrsc_day = nrsc_by_date[d]
                tree = BallTree(np.radians(nrsc_day[['y', 'x']].values), metric='haversine')
                ind = tree.query_radius(np.radians(lis_day[['Lat', 'Long']].values), r=R / R_EARTH_KM)
                nrsc_times = nrsc_day['datetime_IST'].values
                lis_times = lis_day['datetime_IST'].values
                for i, cand_idx in enumerate(ind):
                    if len(cand_idx) == 0:
                        continue
                    dt = np.abs((nrsc_times[cand_idx] - lis_times[i]).astype('timedelta64[s]').astype(float)) / 60.0
                    if (dt <= T).any():
                        matched += 1
            pct = matched / total * 100 if total else float('nan')
            rows.append(dict(radius_km=R, time_window_min=T, matched=matched, total=total, match_pct=pct))
            print(f"  R={R}km T={T}min  matched={matched}/{total} ({pct:.1f}%)  [{time.time()-t0:.0f}s elapsed]")
    result = pd.DataFrame(rows)
    result.to_csv(os.path.join(OUTPUT_DIR, "event_matching_summary.csv"), index=False)
    return result


# =========================================================================
# 4. OPTIONAL: STATE-LEVEL AGGREGATION
# =========================================================================
def state_level_comparison(lis, nrsc, states_shp_path, name_col=None):
    import geopandas as gpd

    print("\n--- State-level aggregation ---")
    states = gpd.read_file(states_shp_path)
    if states.crs is None:
        states = states.set_crs('EPSG:4326')
    states = states.to_crs('EPSG:4326')

    if name_col is None:
        name_col = STATE_NAME_COLUMN if 'STATE_NAME_COLUMN' in globals() else None
    if name_col not in states.columns:
        # fall back to auto-detect
        for c in states.columns:
            if c.lower() in ('stname_sh', 'st_nm', 'state_name', 'name', 'st_name', 'name_1'):
                name_col = c
                break
        else:
            name_col = states.columns[0]
        print(f"  [WARN] Configured name column not found, using '{name_col}' instead")

    lis_pts = gpd.GeoDataFrame(lis, geometry=gpd.points_from_xy(lis['Long'], lis['Lat']), crs='EPSG:4326')
    nrsc_pts = gpd.GeoDataFrame(nrsc, geometry=gpd.points_from_xy(nrsc['x'], nrsc['y']), crs='EPSG:4326')

    lis_joined = gpd.sjoin(lis_pts, states[[name_col, 'geometry']], how='left', predicate='within')
    nrsc_joined = gpd.sjoin(nrsc_pts, states[[name_col, 'geometry']], how='left', predicate='within')

    lis_state = lis_joined.groupby(name_col).size().rename('lis_count')
    nrsc_state = nrsc_joined.groupby(name_col).size().rename('nrsc_count')
    table = pd.concat([lis_state, nrsc_state], axis=1).fillna(0)
    table['lis_rank'] = table['lis_count'].rank(ascending=False)
    table['nrsc_rank'] = table['nrsc_count'].rank(ascending=False)

    stats = compute_validation_stats(table['lis_count'], table['nrsc_count'], label='state_level')
    ALL_VALIDATION_STATS.append(stats)

    table = table.sort_values('lis_count', ascending=False)
    print(table)
    table.to_csv(os.path.join(OUTPUT_DIR, "state_level_comparison.csv"))

    # attach geometry back for mapping
    states_table = states[[name_col, 'geometry']].merge(table, left_on=name_col, right_index=True, how='left').fillna(0)
    plot_side_by_side_map(states_table, 'lis_count', 'nrsc_count',
                           title_left='LIS flash count (per state)',
                           title_right='NRSC stroke count (per state)',
                           out_name='state_level_map_comparison.png',
                           label_col=name_col)
    plot_log_shared_map(states_table, 'lis_count', 'nrsc_count',
                         out_name='state_level_map_log_shared.png')
    plot_ratio_bias_map(states_table, 'lis_count', 'nrsc_count',
                         out_name='state_level_map_ratio_bias.png')
    return table


# =========================================================================
# MAP FIGURES
# =========================================================================
def plot_side_by_side_map(gdf, left_col, right_col, title_left, title_right, out_name, label_col=None):
    """Independent-scale pattern map: LIS vs NRSC.

    Each panel uses its OWN independent log color scale, not a shared one.
    NRSC's raw counts run ~50-100x higher than LIS's (ground network vs.
    sparse satellite overpass sampling), so a shared scale would wash out
    LIS's own spatial variation. This map answers "do the hotspots line up
    geographically" (pattern), NOT "are the magnitudes similar" -- for that,
    see plot_log_shared_map and plot_ratio_bias_map below, and the
    correlation/bias statistics in validation_statistics_master.csv.

    No figure title is drawn. Colorbar ticks are plain numbers (1, 10,
    1,234, ...) rather than matplotlib's default 10^x notation.
    """
    import matplotlib.colors as mcolors
    import matplotlib.ticker as mticker

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    def _plain_number(x, _pos):
        if x >= 1000:
            return f'{x:,.0f}'
        elif x >= 1:
            return f'{x:.0f}'
        else:
            return f'{x:.2g}'

    for ax, col, title in zip(axes, [left_col, right_col], [title_left, title_right]):
        plot_vals = gdf[col].replace(0, np.nan)  # avoid log(0) issues in display
        vmax = plot_vals.max()
        norm = mcolors.LogNorm(vmin=1, vmax=vmax) if pd.notna(vmax) and vmax > 0 else None
        gdf.assign(_val=plot_vals).plot(
            column='_val', ax=ax, cmap='inferno_r', legend=True,
            norm=norm, edgecolor='black', linewidth=0.4,
            missing_kwds={'color': 'lightgrey', 'label': 'No data'},
            legend_kwds={'format': mticker.FuncFormatter(_plain_number)}
        )
        ax.set_axis_off()

    fig.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, out_name)
    fig.savefig(out_path, dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved pattern map (independent scales): {out_path}")


def plot_log_shared_map(gdf, left_col, right_col, out_name, left_label='LIS', right_label='NRSC'):
    """Journal-ready side-by-side map: BOTH panels transformed to
    log10(count + 1) and plotted on ONE SHARED colorbar, so the two panels
    are directly, visually comparable in magnitude (not just pattern).

    Colorbar ticks are shown as the back-transformed actual counts (1, 10,
    100, ...) so the log axis stays interpretable. No figure title.
    """
    gdf = gdf.copy()
    gdf['_left_log'] = np.log10(gdf[left_col].astype(float) + 1)
    gdf['_right_log'] = np.log10(gdf[right_col].astype(float) + 1)
    vmax = max(gdf['_left_log'].max(), gdf['_right_log'].max())
    vmax = vmax if vmax > 0 else 1.0
    vmin = 0.0

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    mappable = None
    for ax, col, label in zip(axes, ['_left_log', '_right_log'], [left_label, right_label]):
        plot = gdf.plot(column=col, ax=ax, cmap='inferno_r', vmin=vmin, vmax=vmax,
                         edgecolor='black', linewidth=0.4)
        ax.set_axis_off()
        ax.text(0.02, 0.98, label, transform=ax.transAxes, fontsize=12,
                 fontweight='bold', va='top', ha='left')
        mappable = plot.collections[-1]

    cbar = fig.colorbar(mappable, ax=axes, orientation='horizontal', fraction=0.05, pad=0.06)
    tick_locs = np.arange(0, np.ceil(vmax) + 1)
    cbar.set_ticks(tick_locs)
    cbar.set_ticklabels([f'{10 ** t:,.0f}' for t in tick_locs])
    cbar.set_label('Flash / stroke count (shared log scale)')

    out_path = os.path.join(OUTPUT_DIR, out_name)
    fig.savefig(out_path, dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved shared-colorbar log map: {out_path}")


def plot_ratio_bias_map(gdf, left_col, right_col, out_name, left_label='LIS', right_label='NRSC'):
    """Single-panel ratio/bias map: log10((NRSC+1)/(LIS+1)) per spatial unit.

    Positive (red) = NRSC exceeds LIS at that location (LIS underestimates
    there); negative (blue) = LIS exceeds NRSC. Diverging colormap centered
    at zero. This is the map reviewers usually want to see the spatial
    structure of the bias, complementing the aggregate bias/RMSE numbers in
    validation_statistics_master.csv. No figure title.
    """
    import matplotlib.colors as mcolors

    gdf = gdf.copy()
    gdf['_log_ratio'] = np.log10((gdf[right_col].astype(float) + 1) / (gdf[left_col].astype(float) + 1))
    vabs = np.nanmax(np.abs(gdf['_log_ratio'].values))
    vabs = vabs if vabs and np.isfinite(vabs) and vabs > 0 else 1.0
    norm = mcolors.TwoSlopeNorm(vmin=-vabs, vcenter=0, vmax=vabs)

    fig, ax = plt.subplots(figsize=(9, 8))
    gdf.plot(column='_log_ratio', ax=ax, cmap='RdBu_r', norm=norm,
              edgecolor='black', linewidth=0.4, legend=True,
              legend_kwds={'label': f'log10(({right_label}+1) / ({left_label}+1))', 'shrink': 0.7})
    ax.set_axis_off()

    out_path = os.path.join(OUTPUT_DIR, out_name)
    fig.savefig(out_path, dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved ratio/bias map: {out_path}")


# =========================================================================
# MAIN
# =========================================================================
if __name__ == '__main__':
    print("Loading LIS data...")
    lis = load_lis(YEARS)
    print(f"Total LIS records: {len(lis):,}")

    print("\nLoading NRSC data...")
    nrsc = load_nrsc(YEARS)
    print(f"Total NRSC records: {len(nrsc):,}")

    # 1. Gridded climatology
    if GRID_SHAPEFILE and os.path.exists(GRID_SHAPEFILE):
        grid_climatology_shapefile(lis, nrsc, GRID_SHAPEFILE)
    else:
        print("\n[INFO] Grid shapefile not found/set -- using regular degree grid instead.")
        make_regular_grid_map(lis, nrsc)
    grid_climatology_regular(lis, nrsc, GRID_RESOLUTIONS)

    # 2. Seasonal cycle
    seasonal_cycle_comparison(lis, nrsc)

    # 3. Event-level matching
    event_level_matching(lis, nrsc, SPATIAL_RADII_KM, TIME_WINDOWS_MIN)

    # 4. State-level (optional)
    if STATES_SHAPEFILE and os.path.exists(STATES_SHAPEFILE):
        state_level_comparison(lis, nrsc, STATES_SHAPEFILE, name_col=STATE_NAME_COLUMN)
    else:
        print("\n[INFO] States shapefile not found/set -- skipping state-level breakdown.")

    # 5. Consolidated validation statistics table (all analyses, one file)
    export_master_validation_summary()

    print(f"\nAll outputs saved to: {OUTPUT_DIR}")