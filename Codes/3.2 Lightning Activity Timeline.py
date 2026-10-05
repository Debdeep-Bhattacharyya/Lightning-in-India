"""
=====================================================================
Climatological lightning-season detection for Indian States/UTs using
the Percentage of Active Grid Cells (PAGC) method.

METHOD SUMMARY
--------------
For every state, a fixed inventory of Grid_ID cells is established from
the full 2000-2022 record (excluding 2015-2017, which are absent from
the input folder). For every day, PAGC = 100 x (unique active grids that
day) / (total grids belonging to that state). This daily PAGC series is
smoothed with a 7-day centered moving average, and the lightning season
is detected as the period during which the smoothed PAGC stays above a
year-specific threshold (a user-editable fraction of that year's peak
smoothed PAGC), sustained for >=3 consecutive days at onset/offset.
Within-season dry spells of >=5 consecutive sub-threshold days are
flagged as "break periods".

OUTPUTS (all under D:\\Articles\\Working\\Lightning India\\Results\\Seasonality)
    Annual_State_Statistics.xlsx   one row per State x Year
    State_Climatology.xlsx         one row per State (2000-2022 climatology; mean AND median)
    Daily_PAGC.xlsx                full daily PAGC / smoothed PAGC series
    Break_Periods.xlsx             every detected break period, individually
    Grid_Inventory.xlsx            fixed grid counts + grid IDs per state
    Figure1_Timeline.tif/.png/.pdf  two-panel publication figure (600 dpi TIFF/PNG + vector PDF):
                                    panel (a) season timeline + median peak date,
                                    panel (b) median longest-break duration bar chart
    Processing_Log.txt             run diagnostics

    (Figure 2 heatmap and Figure 3 division curves are still computed as
    functions below but are NOT called from main() - see the "FIGURES"
    section of main() if you want to re-enable them later.)

HOW TO RUN
----------
    pip install pandas numpy matplotlib scipy openpyxl tqdm
    python Step07_Lightning_Seasonality_PAGC.py

Adjust the CONFIG block below if your paths, file pattern, or season
threshold differ from the defaults.

KEY ASSUMPTIONS (documented because the spec leaves them to the analyst)
--------------------------------------------------------------------
  * "Duplicate lightning events in the same Grid_ID on the same date"
    are collapsed to a single (State, Grid_ID, Date) record before any
    counting - this is what makes a grid cell "active" that day.
  * A state's total grid inventory is the set of distinct Grid_ID values
    ever seen for that state across the ENTIRE 2000-2022 record (fixed,
    does not vary by year).
  * The 7-day moving average is centered (window symmetric around each
    day) with min_periods=1 so the first/last 3 days of the year are not
    dropped, only computed from fewer neighbours.
  * Season threshold = THRESHOLD_FRACTION (default 0.15) x that year's
    MAXIMUM SMOOTHED PAGC value (not the raw maximum).
  * If no run of >=3 consecutive above-threshold days exists in a given
    state-year, that state-year is logged and excluded from season
    statistics (it still appears in Daily_PAGC.xlsx).
  * RESOLVING A CONTRADICTION IN THE SPEC: taken literally, "season
    starts/ends on a >=3-day threshold crossing" and "a break is a
    >=5-day sub-threshold run INSIDE the season" cannot both hold, since
    any 5-day break is also a qualifying 3-day end-of-season run - the
    season would always end at the first break, before a break long
    enough to count (5 days) could ever be observed as "inside" it. This
    script resolves that by using the >=3-day rule to identify individual
    ACTIVE RUNS (sustained above-threshold spans, which filters out
    single-day/two-day noise blips from counting as real activity), then
    defines Season_Start = start of the FIRST active run and Season_End
    = end of the LAST active run in that year. Sub-threshold gaps of
    >=5 days that fall between Season_Start and Season_End are then
    reported as break periods (STEP 8); shorter sub-threshold gaps
    (3-4 days) are treated as normal within-season noise and neither
    split the season nor count as a break.
  * Peak Date / Peak PAGC are the day of maximum smoothed PAGC WITHIN
    the detected season window (not the calendar year).
  * Total Lightning Days = number of days within the season window with
    raw (unsmoothed) PAGC > 0.
  * BREAK POSITION (fixed in this revision): for every state-year, the
    START and END day-of-year of the SINGLE LONGEST break that year are
    now recorded alongside its length (Longest_Break_Start_DOY /
    Longest_Break_End_DOY), not just the length. The climatology then
    reports the climatological average START/END position of the
    longest break (Avg_Longest_Break_Start_DOY / _End_DOY), computed
    across the years that actually had a break. Figure 1 draws the
    hatched "break" box at that real average position. Previously the
    figure only had a mean break LENGTH and centered a box of that
    length in the middle of the season bar, which had no relationship
    to when the break actually tended to occur and made it visually
    collide with the (independently computed) average peak date.
  * CIRCULAR DAY-OF-YEAR AVERAGING: Season_Start_DOY, Season_End_DOY,
    Peak_DOY, and the longest-break start/end DOYs are all calendar
    positions on a 1-366 cycle, so a plain arithmetic mean is not the
    correct way to average them (it breaks down for any state-year
    distribution that straddles the Dec/Jan boundary, and even away
    from the boundary a circular mean is the statistically appropriate
    tool for angular/cyclical data). All "Mean_*_DOY" climatology
    columns are computed with a circular (sine/cosine) mean instead of
    np.mean. P25/P75 are also still reported for reference.
  * Climatological date-like quantities (Start/End/Peak) are averaged
    as day-of-year (both circular mean AND median are reported), then
    mapped onto a fixed non-leap reference calendar (2001) purely for
    display purposes.
  * PUBLICATION FIGURE REVISION: the timeline figure previously drew
    a hatched box for the average longest break, centered inside the
    season bar. That placement had no relationship to when the break
    actually occurred and has been REMOVED. The figure is now a
    two-panel layout: panel (a) is the season timeline (bar = median
    season, dot = median peak date, no break indicator at all); panel
    (b) is a separate horizontal bar chart of each state's MEDIAN
    longest-break duration, in the same state order as panel (a), with
    the duration labeled at the end of each bar. This avoids implying
    a break location that was never actually measured.
  * MEDIAN VS MEAN FOR TIMING: per the latest revision, the figure and
    the state ordering use MEDIAN Season_Start_DOY / Season_End_DOY /
    Peak_DOY / Longest_Break_Days (robust to outlier years), while
    State_Climatology.xlsx continues to export both Mean_* (circular
    mean for DOY columns) and Median_* versions of every timing
    variable, plus Std/P25/P75, so the underlying spread is not lost.
"""

import gc
import logging
import time
import tracemalloc
import warnings
from itertools import groupby
from operator import itemgetter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy import stats
from tqdm import tqdm

# =====================================================================
# CONFIG - edit these to match your environment
# =====================================================================
DATA_DIR = Path(r"D:\Articles\Working\Lightning India\Data\Lightning\3_Grid_Assigned")
RESULTS_DIR = Path(r"D:\Articles\Working\Lightning India\Results\Seasonality")
FILE_PATTERN = "*_Grid.csv"
EXCLUDED_YEARS = {2015, 2016, 2017}

REQUIRED_COLUMNS = ["Year", "Month", "Day", "Grid_ID", "STNAME_SH", "Division"]
READ_CHUNKSIZE = 500_000          # rows per chunk while reading each yearly CSV
THRESHOLD_FRACTION = 0.15         # season on/off threshold, as fraction of annual smoothed peak PAGC
ONSET_OFFSET_RUN_DAYS = 3         # consecutive days needed to start/end a season
BREAK_RUN_DAYS = 5                # consecutive sub-threshold days needed to count as a "break"
SMOOTH_WINDOW = 7                 # days, centered moving average
DOY_CIRCULAR_PERIOD = 365.25      # period used for circular-mean DOY averaging

FIGSIZE_TIMELINE = (16, 8)        # two-panel publication figure, ~16 x 8 in
FIGSIZE_HEATMAP = (16, 12)
FIGSIZE_DIVISIONS = (16, 12)
FIG_DPI_RASTER = 600

LOG_FILE_NAME = "Processing_Log.txt"
# =====================================================================


# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
def setup_logging(results_dir: Path) -> logging.Logger:
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / LOG_FILE_NAME

    logger = logging.getLogger("pagc")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------
# STEP 1: Read + validate + deduplicate every yearly CSV
# ---------------------------------------------------------------------
def find_year_files(data_dir: Path, pattern: str, excluded_years: set) -> list:
    files = sorted(data_dir.glob(pattern))
    kept = []
    for f in files:
        digits = "".join(ch for ch in f.stem if ch.isdigit())
        if len(digits) < 4:
            continue
        year = int(digits[:4])
        if year in excluded_years:
            continue
        kept.append((year, f))
    return kept


def load_and_deduplicate(data_dir: Path, pattern: str, excluded_years: set,
                          chunksize: int, logger: logging.Logger) -> tuple:
    """
    Reads every yearly CSV in chunks, keeps only the columns needed,
    builds a Date column, and drops duplicate (State, Grid_ID, Date)
    combinations (i.e. repeat flashes in the same grid cell on the same
    day count once). Returns:
        grid_days: DataFrame[State, Division, Grid_ID, Date, Year, DOY]
        stats: dict of run diagnostics
    """
    year_files = find_year_files(data_dir, pattern, excluded_years)
    if not year_files:
        raise FileNotFoundError(
            f"No files matching '{pattern}' found in {data_dir}. "
            "Check DATA_DIR / FILE_PATTERN in the CONFIG block."
        )

    dtype_map = {
        "Year": "int32", "Day": "int16", "Grid_ID": "int64",
        "STNAME_SH": "category", "Division": "category", "Month": "category",
    }

    all_frames = []
    total_rows_read = 0
    missing_value_rows = 0
    files_with_errors = []

    for year, fpath in tqdm(year_files, desc="Reading yearly CSVs"):
        try:
            sample = pd.read_csv(fpath, sep=None, engine="python", nrows=5)
        except Exception as e:
            logger.error(f"Could not sniff delimiter for {fpath.name}: {e}")
            files_with_errors.append(str(fpath))
            continue

        missing_cols = set(REQUIRED_COLUMNS) - set(sample.columns)
        if missing_cols:
            logger.error(f"{fpath.name} is missing required columns {missing_cols}; skipping file.")
            files_with_errors.append(str(fpath))
            continue

        detected_sep = "\t" if "\t" in open(fpath, encoding="utf-8", errors="ignore").readline() else ","

        file_chunks = []
        try:
            reader = pd.read_csv(
                fpath, sep=detected_sep, usecols=REQUIRED_COLUMNS,
                dtype=dtype_map, chunksize=chunksize
            )
            for chunk in reader:
                total_rows_read += len(chunk)
                before = len(chunk)
                chunk = chunk.dropna(subset=REQUIRED_COLUMNS)
                missing_value_rows += before - len(chunk)

                chunk["Date"] = pd.to_datetime(
                    chunk["Year"].astype(str) + "-" + chunk["Month"].astype(str) + "-" + chunk["Day"].astype(str),
                    format="%Y-%B-%d", errors="coerce"
                )
                bad_dates = chunk["Date"].isna().sum()
                missing_value_rows += int(bad_dates)
                chunk = chunk.dropna(subset=["Date"])

                chunk = chunk[["STNAME_SH", "Division", "Grid_ID", "Date"]].drop_duplicates()
                file_chunks.append(chunk)
        except Exception as e:
            logger.error(f"Error reading {fpath.name}: {e}")
            files_with_errors.append(str(fpath))
            continue

        if file_chunks:
            year_df = pd.concat(file_chunks, ignore_index=True).drop_duplicates(
                subset=["STNAME_SH", "Grid_ID", "Date"]
            )
            all_frames.append(year_df)
        del file_chunks
        gc.collect()

    if not all_frames:
        raise ValueError("No usable data was loaded from any file.")

    grid_days = pd.concat(all_frames, ignore_index=True)
    del all_frames
    gc.collect()

    grid_days["Year"] = grid_days["Date"].dt.year.astype("int32")
    grid_days["DOY"] = grid_days["Date"].dt.dayofyear.astype("int16")

    run_stats = {
        "total_rows_read": total_rows_read,
        "missing_value_rows_dropped": missing_value_rows,
        "files_with_errors": files_with_errors,
        "grid_day_records_after_dedup": len(grid_days),
        "years_processed": sorted(grid_days["Year"].unique().tolist()),
        "n_states": grid_days["STNAME_SH"].nunique(),
    }
    return grid_days, run_stats


# ---------------------------------------------------------------------
# STEP 2 & 3: Active grids per state-day, and fixed total grid inventory
# ---------------------------------------------------------------------
def compute_grid_inventory(grid_days: pd.DataFrame) -> pd.DataFrame:
    """Fixed (all-years) unique grid count per state, plus the Division."""
    inv = (
        grid_days.groupby(["STNAME_SH", "Division"], observed=True)["Grid_ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Grid_ID": "Total_Grids"})
    )
    return inv


def compute_daily_active_grids(grid_days: pd.DataFrame) -> pd.DataFrame:
    daily = (
        grid_days.groupby(["STNAME_SH", "Division", "Date"], observed=True)["Grid_ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Grid_ID": "Active_Grids"})
    )
    return daily


# ---------------------------------------------------------------------
# STEP 4 & 5: PAGC + continuous daily calendar (fill missing days with 0)
# ---------------------------------------------------------------------
def build_continuous_pagc_series(daily_active: pd.DataFrame, grid_inventory: pd.DataFrame,
                                  years: list, logger: logging.Logger) -> pd.DataFrame:
    state_info = grid_inventory.set_index("STNAME_SH")
    states = state_info.index.tolist()

    full_index_frames = []
    for state in states:
        div = state_info.loc[state, "Division"]
        for year in years:
            date_range = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
            full_index_frames.append(pd.DataFrame({
                "STNAME_SH": state, "Division": div, "Date": date_range, "Year": year
            }))
    calendar = pd.concat(full_index_frames, ignore_index=True)
    del full_index_frames

    merged = calendar.merge(
        daily_active[["STNAME_SH", "Date", "Active_Grids"]],
        on=["STNAME_SH", "Date"], how="left"
    )
    merged["Active_Grids"] = merged["Active_Grids"].fillna(0).astype("int32")
    merged["Total_Grids"] = merged["STNAME_SH"].map(state_info["Total_Grids"])
    merged["PAGC"] = 100.0 * merged["Active_Grids"] / merged["Total_Grids"]
    merged["DOY"] = merged["Date"].dt.dayofyear.astype("int16")

    logger.info(f"Built continuous daily PAGC calendar: {len(merged):,} state-days "
                f"across {len(states)} states and {len(years)} years.")
    return merged.sort_values(["STNAME_SH", "Date"]).reset_index(drop=True)


# ---------------------------------------------------------------------
# STEP 6: 7-day centered moving average, per state-year
# ---------------------------------------------------------------------
def add_smoothed_pagc(daily_pagc: pd.DataFrame, window: int) -> pd.DataFrame:
    daily_pagc = daily_pagc.sort_values(["STNAME_SH", "Year", "Date"])
    daily_pagc["Smoothed_PAGC"] = (
        daily_pagc.groupby(["STNAME_SH", "Year"], observed=True)["PAGC"]
        .transform(lambda s: s.rolling(window=window, center=True, min_periods=1).mean())
    )
    return daily_pagc


# ---------------------------------------------------------------------
# STEPS 7-9: Season / break detection per state-year
# ---------------------------------------------------------------------
def _runs_of_true(mask: np.ndarray) -> list:
    """Return list of (start_idx, end_idx_inclusive, length) for runs of True in mask."""
    runs = []
    idx = np.arange(len(mask))
    for key, group in groupby(zip(idx, mask), key=itemgetter(1)):
        group = list(group)
        if key:
            start = group[0][0]
            end = group[-1][0]
            runs.append((start, end, end - start + 1))
    return runs


def detect_season_for_state_year(sub: pd.DataFrame, threshold_fraction: float,
                                  onset_offset_run_days: int, break_run_days: int) -> dict:
    """
    sub: single state-year slice of daily_pagc, sorted by Date, full calendar
         (365 or 366 rows), columns Date, DOY, PAGC, Smoothed_PAGC.
    Returns a dict of season statistics, or None fields if no season detected.
    """
    sub = sub.reset_index(drop=True)
    smoothed = sub["Smoothed_PAGC"].to_numpy()
    raw = sub["PAGC"].to_numpy()
    dates = sub["Date"].to_numpy()

    annual_max_smoothed = float(np.nanmax(smoothed)) if len(smoothed) else 0.0
    threshold = threshold_fraction * annual_max_smoothed

    above = smoothed > threshold

    active_runs = [r for r in _runs_of_true(above) if r[2] >= onset_offset_run_days]
    if not active_runs or annual_max_smoothed <= 0:
        return {
            "Season_Detected": False, "Threshold_PAGC": threshold,
            "Annual_Max_Smoothed_PAGC": annual_max_smoothed,
            "Season_Start_Date": pd.NaT, "Season_End_Date": pd.NaT,
            "Season_Start_DOY": np.nan, "Season_End_DOY": np.nan,
            "Season_Length_Days": np.nan, "Peak_Date": pd.NaT, "Peak_DOY": np.nan,
            "Peak_PAGC": np.nan, "Total_Lightning_Days": 0,
            "Num_Breaks": 0, "Longest_Break_Days": 0, "Avg_Break_Days": np.nan,
            "Longest_Break_Start_DOY": np.nan, "Longest_Break_End_DOY": np.nan,
            "breaks": [],
        }

    # Season spans from the start of the first sustained active run to the
    # end of the last sustained active run that year (see docstring for why
    # this resolves the onset/offset-vs-break contradiction in the spec).
    start_idx = active_runs[0][0]
    end_idx = active_runs[-1][1]

    below = ~above
    season_slice = sub.iloc[start_idx:end_idx + 1]
    season_below_mask = below[start_idx:end_idx + 1]
    break_runs = [r for r in _runs_of_true(season_below_mask) if r[2] >= break_run_days]

    breaks = []
    for r_start, r_end, r_len in break_runs:
        b_start_date = season_slice["Date"].iloc[r_start]
        b_end_date = season_slice["Date"].iloc[r_end]
        breaks.append({
            "Break_Start": b_start_date, "Break_End": b_end_date,
            "Break_Length_Days": r_len,
            "Break_Start_DOY": int(season_slice["DOY"].iloc[r_start]),
            "Break_End_DOY": int(season_slice["DOY"].iloc[r_end]),
        })

    # Identify the SINGLE LONGEST break of the year and keep its actual
    # start/end DOY (not just its length) so climatology can later report
    # where breaks tend to occur, not only how long they tend to last.
    longest_break_start_doy = np.nan
    longest_break_end_doy = np.nan
    if breaks:
        longest = max(breaks, key=lambda b: b["Break_Length_Days"])
        longest_break_start_doy = longest["Break_Start_DOY"]
        longest_break_end_doy = longest["Break_End_DOY"]

    season_raw = season_slice["PAGC"].to_numpy()
    season_smoothed = season_slice["Smoothed_PAGC"].to_numpy()
    peak_local_idx = int(np.nanargmax(season_smoothed)) if len(season_smoothed) else 0

    result = {
        "Season_Detected": True,
        "Threshold_PAGC": threshold,
        "Annual_Max_Smoothed_PAGC": annual_max_smoothed,
        "Season_Start_Date": pd.Timestamp(dates[start_idx]),
        "Season_End_Date": pd.Timestamp(dates[end_idx]),
        "Season_Start_DOY": int(sub["DOY"].iloc[start_idx]),
        "Season_End_DOY": int(sub["DOY"].iloc[end_idx]),
        "Season_Length_Days": end_idx - start_idx + 1,
        "Peak_Date": pd.Timestamp(season_slice["Date"].iloc[peak_local_idx]),
        "Peak_DOY": int(season_slice["DOY"].iloc[peak_local_idx]),
        "Peak_PAGC": float(season_smoothed[peak_local_idx]),
        "Total_Lightning_Days": int((season_raw > 0).sum()),
        "Num_Breaks": len(breaks),
        "Longest_Break_Days": max([b["Break_Length_Days"] for b in breaks], default=0),
        "Avg_Break_Days": float(np.mean([b["Break_Length_Days"] for b in breaks])) if breaks else np.nan,
        "Longest_Break_Start_DOY": longest_break_start_doy,
        "Longest_Break_End_DOY": longest_break_end_doy,
        "breaks": breaks,
    }
    return result


def run_season_detection(daily_pagc: pd.DataFrame, logger: logging.Logger) -> tuple:
    annual_rows = []
    break_rows = []
    n_no_season = 0

    groups = list(daily_pagc.groupby(["STNAME_SH", "Division", "Year"], observed=True))
    for (state, division, year), sub in tqdm(groups, desc="Detecting seasons per state-year"):
        res = detect_season_for_state_year(
            sub.sort_values("Date"), THRESHOLD_FRACTION, ONSET_OFFSET_RUN_DAYS, BREAK_RUN_DAYS
        )
        breaks = res.pop("breaks")
        if not res["Season_Detected"]:
            n_no_season += 1
        row = {"STNAME_SH": state, "Division": division, "Year": year}
        row.update(res)
        annual_rows.append(row)

        for b in breaks:
            break_rows.append({
                "STNAME_SH": state, "Division": division, "Year": year,
                "Break_Start": b["Break_Start"], "Break_End": b["Break_End"],
                "Break_Length_Days": b["Break_Length_Days"],
                "Break_Start_DOY": b["Break_Start_DOY"], "Break_End_DOY": b["Break_End_DOY"],
            })

    annual_df = pd.DataFrame(annual_rows)
    break_df = pd.DataFrame(break_rows) if break_rows else pd.DataFrame(
        columns=["STNAME_SH", "Division", "Year", "Break_Start", "Break_End",
                 "Break_Length_Days", "Break_Start_DOY", "Break_End_DOY"])

    logger.info(f"Season detection complete: {n_no_season} state-year combinations had no "
                f"detectable season (below threshold all year) out of {len(annual_rows)}.")
    return annual_df, break_df


# ---------------------------------------------------------------------
# STEP 10: Climatology (2000-2022, excluding 2015-2017 which are absent)
# ---------------------------------------------------------------------
def _doy_to_display_date(doy, ref_year=2001):
    if pd.isna(doy):
        return None
    base = pd.Timestamp(f"{ref_year}-01-01")
    return (base + pd.Timedelta(days=float(doy) - 1)).strftime("%d-%b")


def _circular_mean_doy(values, period: float = DOY_CIRCULAR_PERIOD) -> float:
    """
    Circular (sine/cosine) mean of a set of day-of-year values, treating
    the calendar as a closed cycle of length `period`. This is the
    statistically correct way to average angular/cyclical quantities
    like day-of-year (a plain arithmetic mean is only safe when a
    distribution is known never to straddle the Dec/Jan wrap point, and
    even then the circular mean reduces to essentially the same answer,
    so there is no downside to using it uniformly here).
    """
    s = pd.Series(values).dropna().astype(float)
    if len(s) == 0:
        return np.nan
    angles = 2 * np.pi * s / period
    sin_sum = np.sin(angles).sum()
    cos_sum = np.cos(angles).sum()
    if sin_sum == 0 and cos_sum == 0:
        return np.nan
    mean_angle = np.arctan2(sin_sum, cos_sum)
    mean_doy = (mean_angle / (2 * np.pi)) * period
    if mean_doy <= 0:
        mean_doy += period
    return mean_doy


def compute_climatology(annual_df: pd.DataFrame) -> pd.DataFrame:
    detected = annual_df[annual_df["Season_Detected"]].copy()

    def agg_block(s: pd.Series, is_doy: bool = False) -> dict:
        s = s.dropna()
        if len(s) == 0:
            return {"mean": np.nan, "circmean": np.nan, "std": np.nan,
                     "median": np.nan, "p25": np.nan, "p75": np.nan}
        block = {
            "mean": float(np.mean(s)),
            "std": float(np.std(s, ddof=1)) if len(s) > 1 else 0.0,
            "median": float(np.median(s)),
            "p25": float(stats.scoreatpercentile(s, 25)),
            "p75": float(stats.scoreatpercentile(s, 75)),
        }
        # For calendar/day-of-year quantities, report the circular mean as
        # the primary "average" instead of the (potentially misleading)
        # arithmetic mean. Non-DOY quantities keep the arithmetic mean.
        block["circmean"] = _circular_mean_doy(s) if is_doy else block["mean"]
        return block

    rows = []
    for (state, division), sub in detected.groupby(["STNAME_SH", "Division"], observed=True):
        n_years = len(sub)
        start_doy = agg_block(sub["Season_Start_DOY"], is_doy=True)
        end_doy = agg_block(sub["Season_End_DOY"], is_doy=True)
        peak_doy = agg_block(sub["Peak_DOY"], is_doy=True)
        length = agg_block(sub["Season_Length_Days"])
        peak_pagc = agg_block(sub["Peak_PAGC"])
        n_breaks = agg_block(sub["Num_Breaks"])
        longest_break = agg_block(sub["Longest_Break_Days"])
        avg_break = agg_block(sub["Avg_Break_Days"])
        total_days = agg_block(sub["Total_Lightning_Days"])
        # Longest-break START/END DOY, aggregated only across the years
        # that actually had a break (rows are NaN in years with none).
        lb_start_doy = agg_block(sub["Longest_Break_Start_DOY"], is_doy=True)
        lb_end_doy = agg_block(sub["Longest_Break_End_DOY"], is_doy=True)

        rows.append({
            "STNAME_SH": state, "Division": division, "N_Years_With_Season": n_years,

            # --- Season Start: median (used for figure + sort order) and mean (circular) ---
            "Median_Start_DOY": round(start_doy["median"], 1) if pd.notna(start_doy["median"]) else np.nan,
            "Median_Start_Date": _doy_to_display_date(start_doy["median"]),
            "Mean_Start_DOY": round(start_doy["circmean"], 1) if pd.notna(start_doy["circmean"]) else np.nan,
            "Mean_Start_Date": _doy_to_display_date(start_doy["circmean"]),
            "Std_Start_DOY": round(start_doy["std"], 1),
            "P25_Start_DOY": round(start_doy["p25"], 1), "P75_Start_DOY": round(start_doy["p75"], 1),

            # --- Season End: median and mean (circular) ---
            "Median_End_DOY": round(end_doy["median"], 1) if pd.notna(end_doy["median"]) else np.nan,
            "Median_End_Date": _doy_to_display_date(end_doy["median"]),
            "Mean_End_DOY": round(end_doy["circmean"], 1) if pd.notna(end_doy["circmean"]) else np.nan,
            "Mean_End_Date": _doy_to_display_date(end_doy["circmean"]),
            "Std_End_DOY": round(end_doy["std"], 1),
            "P25_End_DOY": round(end_doy["p25"], 1), "P75_End_DOY": round(end_doy["p75"], 1),

            # --- Season Length ---
            "Median_Season_Length_Days": round(length["median"], 1) if pd.notna(length["median"]) else np.nan,
            "Mean_Season_Length_Days": round(length["mean"], 1) if pd.notna(length["mean"]) else np.nan,
            "Std_Season_Length_Days": round(length["std"], 1),
            "P25_Season_Length_Days": round(length["p25"], 1), "P75_Season_Length_Days": round(length["p75"], 1),

            # --- Peak Date: median (used for figure) and mean (circular) ---
            "Median_Peak_DOY": round(peak_doy["median"], 1) if pd.notna(peak_doy["median"]) else np.nan,
            "Median_Peak_Date": _doy_to_display_date(peak_doy["median"]),
            "Mean_Peak_DOY": round(peak_doy["circmean"], 1) if pd.notna(peak_doy["circmean"]) else np.nan,
            "Mean_Peak_Date": _doy_to_display_date(peak_doy["circmean"]),
            "Std_Peak_DOY": round(peak_doy["std"], 1),

            "Mean_Peak_PAGC": round(peak_pagc["mean"], 2) if pd.notna(peak_pagc["mean"]) else np.nan,
            "Median_Peak_PAGC": round(peak_pagc["median"], 2) if pd.notna(peak_pagc["median"]) else np.nan,
            "Std_Peak_PAGC": round(peak_pagc["std"], 2),

            "Mean_Total_Lightning_Days": round(total_days["mean"], 1) if pd.notna(total_days["mean"]) else np.nan,
            "Std_Total_Lightning_Days": round(total_days["std"], 1),

            "Mean_Num_Breaks": round(n_breaks["mean"], 2) if pd.notna(n_breaks["mean"]) else np.nan,
            "Std_Num_Breaks": round(n_breaks["std"], 2),

            # --- Longest Break Duration: median (used for figure panel b) and mean ---
            "Median_Longest_Break_Days": round(longest_break["median"], 1) if pd.notna(longest_break["median"]) else np.nan,
            "Mean_Longest_Break_Days": round(longest_break["mean"], 1) if pd.notna(longest_break["mean"]) else np.nan,
            "Std_Longest_Break_Days": round(longest_break["std"], 1) if pd.notna(longest_break["std"]) else np.nan,

            "Median_Break_Days": round(avg_break["median"], 1) if pd.notna(avg_break["median"]) else np.nan,
            "Mean_Break_Days": round(avg_break["mean"], 1) if pd.notna(avg_break["mean"]) else np.nan,
            "Std_Break_Days": round(avg_break["std"], 1) if pd.notna(avg_break["std"]) else np.nan,

            # Climatological position (median/mean start+end DOY) of the
            # longest break, kept for reference/diagnostics even though
            # the publication figure no longer plots a break location.
            # NaN if no state-year in the record had a break at all.
            "Median_Longest_Break_Start_DOY": round(lb_start_doy["median"], 1) if pd.notna(lb_start_doy["median"]) else np.nan,
            "Median_Longest_Break_End_DOY": round(lb_end_doy["median"], 1) if pd.notna(lb_end_doy["median"]) else np.nan,
            "Mean_Longest_Break_Start_DOY": round(lb_start_doy["circmean"], 1) if pd.notna(lb_start_doy["circmean"]) else np.nan,
            "Mean_Longest_Break_End_DOY": round(lb_end_doy["circmean"], 1) if pd.notna(lb_end_doy["circmean"]) else np.nan,
        })

    return pd.DataFrame(rows).sort_values(["Division", "STNAME_SH"]).reset_index(drop=True)


# ---------------------------------------------------------------------
# STEP 11: Excel exports
# ---------------------------------------------------------------------
def _autofit(writer, sheet_name, frame):
    ws = writer.sheets[sheet_name]
    for i, col in enumerate(frame.columns, start=1):
        try:
            width = max(12, min(32, int(frame[col].astype(str).str.len().max() or 10) + 2))
        except Exception:
            width = 14
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width


def export_excel_outputs(results_dir: Path, annual_df: pd.DataFrame, climatology_df: pd.DataFrame,
                          daily_pagc: pd.DataFrame, break_df: pd.DataFrame,
                          grid_inventory: pd.DataFrame, grid_days: pd.DataFrame,
                          logger: logging.Logger):
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Annual_State_Statistics.xlsx
    path = results_dir / "Annual_State_Statistics.xlsx"
    out = annual_df.copy()
    for c in ["Season_Start_Date", "Season_End_Date", "Peak_Date"]:
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d")
    # Lead with the columns explicitly requested for this sheet (Season
    # Start/End/Length, Peak Date/PAGC, Number/Longest/Average Break);
    # any remaining diagnostic columns (thresholds, DOY, break position,
    # etc.) are kept at the end rather than dropped.
    lead_cols = [
        "STNAME_SH", "Division", "Year",
        "Season_Start_Date", "Season_End_Date", "Season_Length_Days",
        "Peak_Date", "Peak_PAGC",
        "Num_Breaks", "Longest_Break_Days", "Avg_Break_Days",
    ]
    remaining_cols = [c for c in out.columns if c not in lead_cols]
    out = out[[c for c in lead_cols if c in out.columns] + remaining_cols]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="Annual_Stats", index=False)
        _autofit(writer, "Annual_Stats", out)
    logger.info(f"Saved {path}")

    # 2. State_Climatology.xlsx
    path = results_dir / "State_Climatology.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        climatology_df.to_excel(writer, sheet_name="Climatology", index=False)
        _autofit(writer, "Climatology", climatology_df)
    logger.info(f"Saved {path}")

    # 3. Daily_PAGC.xlsx
    path = results_dir / "Daily_PAGC.xlsx"
    out = daily_pagc.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out = out[["STNAME_SH", "Division", "Date", "Year", "DOY", "Active_Grids",
               "Total_Grids", "PAGC", "Smoothed_PAGC"]]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="Daily_PAGC", index=False)
        _autofit(writer, "Daily_PAGC", out)
    logger.info(f"Saved {path} ({len(out):,} rows)")

    # 4. Break_Periods.xlsx
    path = results_dir / "Break_Periods.xlsx"
    out = break_df.copy()
    if len(out):
        out["Break_Start"] = pd.to_datetime(out["Break_Start"]).dt.strftime("%Y-%m-%d")
        out["Break_End"] = pd.to_datetime(out["Break_End"]).dt.strftime("%Y-%m-%d")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="Break_Periods", index=False)
        _autofit(writer, "Break_Periods", out)
    logger.info(f"Saved {path} ({len(out):,} rows)")

    # 5. Grid_Inventory.xlsx
    path = results_dir / "Grid_Inventory.xlsx"
    grid_list = (
        grid_days[["STNAME_SH", "Division", "Grid_ID"]]
        .drop_duplicates()
        .sort_values(["STNAME_SH", "Grid_ID"])
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        grid_inventory.sort_values(["Division", "STNAME_SH"]).to_excel(
            writer, sheet_name="Total_Grids_Per_State", index=False)
        _autofit(writer, "Total_Grids_Per_State", grid_inventory)
        grid_list.to_excel(writer, sheet_name="Grid_ID_List", index=False)
        _autofit(writer, "Grid_ID_List", grid_list)
    logger.info(f"Saved {path}")


# ---------------------------------------------------------------------
# STEP 12: Figures
# ---------------------------------------------------------------------
def _save_all_formats(fig, results_dir: Path, basename: str, logger: logging.Logger,
                       formats=("tif", "png", "pdf")):
    format_kwargs = {
        "tif": dict(format="tiff", dpi=FIG_DPI_RASTER, pil_kwargs={"compression": "tiff_lzw"}, bbox_inches="tight"),
        "png": dict(format="png", dpi=FIG_DPI_RASTER, bbox_inches="tight"),
        "pdf": dict(format="pdf", bbox_inches="tight"),
    }
    for ext in formats:
        out_path = results_dir / f"{basename}.{ext}"
        fig.savefig(out_path, **format_kwargs[ext])
        logger.info(f"Saved {out_path}")


# Colour-blind-friendly qualitative palette (Okabe & Ito, 2008) used for
# IMD Division colours in panel (a).
_OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
              "#0072B2", "#D55E00", "#CC79A7", "#000000"]
# Neutral single hue for the panel (b) break-duration bars.
_BREAK_BAR_COLOR = "#D55E00"  # colour-blind-friendly vermillion/orange


def figure1_timeline(climatology_df: pd.DataFrame, results_dir: Path, logger: logging.Logger):
    """
    Two-panel publication figure.
      Panel (a): season timeline (bar = MEDIAN season Start-End, dot =
                 MEDIAN peak date). No break indicator is drawn here.
      Panel (b): horizontal bar chart of each state's MEDIAN longest-break
                 duration (days), in the same state order as panel (a),
                 with the value labeled at the end of every bar.
    States are sorted by Division, then by median season start DOY.
    """
    df = climatology_df.dropna(subset=["Median_Start_DOY", "Median_End_DOY"]).copy()
    df = df.sort_values(["Division", "Median_Start_DOY"]).reset_index(drop=True)
    n = len(df)
    y_pos = np.arange(n)

    divisions = df["Division"].unique().tolist()
    div_color = {d: _OKABE_ITO[i % len(_OKABE_ITO)] for i, d in enumerate(divisions)}

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
    })

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=FIGSIZE_TIMELINE, sharey=True,
        gridspec_kw={"width_ratios": [2.3, 1.0], "wspace": 0.06},
    )

    # ---------------- Panel (a): season timeline ----------------
    for i, row in df.iterrows():
        start, end = row["Median_Start_DOY"], row["Median_End_DOY"]
        color = div_color[row["Division"]]
        ax1.barh(i, end - start, left=start, height=0.6, color=color,
                  edgecolor="black", linewidth=0.6, zorder=2)

        peak = row.get("Median_Peak_DOY", np.nan)
        if pd.notna(peak):
            ax1.scatter([peak], [i], color="black", s=32, zorder=4,
                        edgecolor="white", linewidth=0.6)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(df["STNAME_SH"], fontsize=12)
    ax1.tick_params(axis="x", labelsize=12)
    ax2.tick_params(axis="x", labelsize=12)
    ax2.tick_params(axis="y", labelsize=12)
    ax1.set_xlabel("Month")
    ax1.set_ylabel("State / UT")
    ax1.set_title("(a) Climatological Lightning Season", loc="left", fontsize= 12, fontweight="bold")

    month_starts = [pd.Timestamp(2001, m, 1).dayofyear for m in range(1, 13)]
    month_labels = [pd.Timestamp(2001, m, 1).strftime("%b") for m in range(1, 13)]
    ax1.set_xticks(month_starts)
    ax1.set_xticklabels(month_labels)
    ax1.set_xlim(1, 366)
    ax1.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    div_handles = [Patch(facecolor=div_color[d], edgecolor="black", label=d) for d in divisions]
    peak_handle = plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="black",
                              markeredgecolor="white", markersize=7, label="Median peak date")

    # ---------------- Panel (b): median longest-break duration ----------------
    lb_vals = df["Median_Longest_Break_Days"].fillna(0.0).to_numpy()
    ax2.barh(y_pos, lb_vals, height=0.6, color=_BREAK_BAR_COLOR,
             edgecolor="black", linewidth=0.6, zorder=2)

    x_max = max(float(np.nanmax(lb_vals)) * 1.18, 5.0) if len(lb_vals) else 5.0
    for i, v in enumerate(lb_vals):
        ax2.text(v + x_max * 0.015, i, f"{v:.0f}", va="center", ha="left", fontsize=8.5)

    ax2.set_xlabel("Longest Break (Days)")
    ax2.set_title("(b) Median Longest Break Duration", loc="left", fontsize= 12, fontweight="bold")
    ax2.set_xlim(0, x_max)
    ax2.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.tick_params(axis="y", left=False)

    ax1.invert_yaxis()  # shared y-axis: inverts both panels together

    # fig.suptitle("Climatological Lightning Season Characteristics by State/UT (PAGC method, 2000-2022)",
    #              fontsize=13, y=1.02)
    fig.legend(handles=div_handles + [peak_handle], loc="lower center",
               bbox_to_anchor=(0.5, -0.06), ncol=min(len(div_handles) + 1, 6),
               frameon=False, fontsize=16, markerscale=1.8, handlelength=2.2, handleheight=1.5, labelspacing=0.8, columnspacing=1.4)

    _save_all_formats(fig, results_dir, "Figure1_Timeline", logger, formats=("tif", "png", "pdf"))
    plt.close(fig)


def figure2_heatmap(daily_pagc: pd.DataFrame, results_dir: Path, logger: logging.Logger):
    pivot = (
        daily_pagc.groupby(["STNAME_SH", "DOY"], observed=True)["Smoothed_PAGC"]
        .mean()
        .reset_index()
        .pivot(index="STNAME_SH", columns="DOY", values="Smoothed_PAGC")
    )
    pivot = pivot.reindex(columns=range(1, 367))
    # order states by division then name for readability
    div_lookup = daily_pagc.drop_duplicates("STNAME_SH").set_index("STNAME_SH")["Division"]
    state_order = div_lookup.reindex(pivot.index).sort_values(kind="stable").index
    pivot = pivot.loc[state_order]

    fig, ax = plt.subplots(figsize=FIGSIZE_HEATMAP)
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis",
                    extent=[1, 366, len(pivot), 0])
    ax.set_yticks(np.arange(len(pivot)) + 0.5)
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Day of Year")
    ax.set_ylabel("State / UT")
    ax.set_title("Mean Smoothed PAGC by State and Day of Year (2000-2022 climatology)")

    month_starts = [pd.Timestamp(2001, m, 1).dayofyear for m in range(1, 13)]
    month_labels = [pd.Timestamp(2001, m, 1).strftime("%b") for m in range(1, 13)]
    ax.set_xticks(month_starts)
    ax.set_xticklabels(month_labels)

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Mean Smoothed PAGC (%)")

    plt.tight_layout()
    _save_all_formats(fig, results_dir, "Figure2_Heatmap", logger)
    plt.close(fig)


def figure3_division_curves(daily_pagc: pd.DataFrame, results_dir: Path, logger: logging.Logger):
    div_year_mean = (
        daily_pagc.groupby(["Division", "Year", "DOY"], observed=True)["Smoothed_PAGC"]
        .mean()
        .reset_index()
    )
    divisions = sorted(div_year_mean["Division"].unique().tolist())
    n_div = len(divisions)
    ncols = 2 if n_div > 1 else 1
    nrows = int(np.ceil(n_div / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=FIGSIZE_DIVISIONS, squeeze=False, sharex=True, sharey=True)
    years = sorted(div_year_mean["Year"].unique().tolist())
    cmap = plt.get_cmap("viridis", len(years))

    for i, div in enumerate(divisions):
        ax = axes[i // ncols][i % ncols]
        sub = div_year_mean[div_year_mean["Division"] == div]
        for j, year in enumerate(years):
            ysub = sub[sub["Year"] == year].sort_values("DOY")
            if len(ysub):
                ax.plot(ysub["DOY"], ysub["Smoothed_PAGC"], color=cmap(j), linewidth=0.8, alpha=0.85)
        ax.set_title(div)
        ax.grid(alpha=0.3)

    # turn off any unused axes
    for k in range(n_div, nrows * ncols):
        axes[k // ncols][k % ncols].axis("off")

    for ax in axes[-1]:
        ax.set_xlabel("Day of Year")
    for row in axes:
        row[0].set_ylabel("Mean Smoothed PAGC (%)")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=min(years), vmax=max(years)))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, fraction=0.02, pad=0.02)
    cbar.set_label("Year")

    fig.suptitle("Annual PAGC Curves (7-day moving average) by IMD Division", y=0.995)
    _save_all_formats(fig, results_dir, "Figure3_DivisionCurves", logger)
    plt.close(fig)


# ---------------------------------------------------------------------
# STEP 16: Processing log summary
# ---------------------------------------------------------------------
def write_summary_log(logger: logging.Logger, run_stats: dict, grid_inventory: pd.DataFrame,
                       annual_df: pd.DataFrame, elapsed_seconds: float, mem_current, mem_peak):
    logger.info("=" * 70)
    logger.info("RUN SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total processing time: {elapsed_seconds:.1f} seconds")
    logger.info(f"Peak memory usage: {mem_peak / (1024 ** 2):.1f} MB "
                f"(current at end: {mem_current / (1024 ** 2):.1f} MB)")
    logger.info(f"Total raw rows read: {run_stats['total_rows_read']:,}")
    logger.info(f"Rows dropped (missing/invalid values): {run_stats['missing_value_rows_dropped']:,}")
    logger.info(f"Grid-day records after deduplication: {run_stats['grid_day_records_after_dedup']:,}")
    logger.info(f"Years processed: {run_stats['years_processed']}")
    logger.info(f"Number of states/UTs: {run_stats['n_states']}")
    logger.info(f"Total grid cells (sum across states): {grid_inventory['Total_Grids'].sum():,}")
    if run_stats["files_with_errors"]:
        logger.warning(f"Files with errors (skipped): {run_stats['files_with_errors']}")
    else:
        logger.info("No file read errors.")
    n_no_season = (~annual_df["Season_Detected"]).sum()
    logger.info(f"State-year combinations with no detectable season: {n_no_season} / {len(annual_df)}")
    logger.info("=" * 70)


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    tracemalloc.start()
    t0 = time.time()

    logger = setup_logging(RESULTS_DIR)
    logger.info("Starting Step07_Lightning_Seasonality_PAGC.py")
    logger.info(f"DATA_DIR = {DATA_DIR}")
    logger.info(f"RESULTS_DIR = {RESULTS_DIR}")
    logger.info(f"THRESHOLD_FRACTION = {THRESHOLD_FRACTION}, "
                f"ONSET_OFFSET_RUN_DAYS = {ONSET_OFFSET_RUN_DAYS}, BREAK_RUN_DAYS = {BREAK_RUN_DAYS}")

    warnings.filterwarnings("ignore", category=FutureWarning)

    # STEP 1: load + dedup
    grid_days, run_stats = load_and_deduplicate(
        DATA_DIR, FILE_PATTERN, EXCLUDED_YEARS, READ_CHUNKSIZE, logger
    )
    years = run_stats["years_processed"]

    # STEP 2/3: inventory + daily active grids
    grid_inventory = compute_grid_inventory(grid_days)
    daily_active = compute_daily_active_grids(grid_days)
    logger.info(f"Grid inventory computed for {len(grid_inventory)} states.")

    # STEP 4/5: continuous PAGC calendar
    daily_pagc = build_continuous_pagc_series(daily_active, grid_inventory, years, logger)
    del daily_active
    gc.collect()

    # STEP 6: smoothing
    daily_pagc = add_smoothed_pagc(daily_pagc, SMOOTH_WINDOW)
    logger.info("7-day centered moving average computed.")

    # STEPS 7-9: season + break detection
    annual_df, break_df = run_season_detection(daily_pagc, logger)

    # STEP 10: climatology
    climatology_df = compute_climatology(annual_df)
    logger.info(f"Climatology computed for {len(climatology_df)} states.")

    # STEP 11: Excel exports
    export_excel_outputs(RESULTS_DIR, annual_df, climatology_df, daily_pagc,
                          break_df, grid_inventory, grid_days, logger)

    # free the large deduplicated grid-day table before plotting (Grid_Inventory export already used it)
    del grid_days
    gc.collect()

    # STEP 12: Figures
    # Only Figure 1 (timeline) is generated per current requirements.
    # figure2_heatmap() and figure3_division_curves() are still defined
    # above and fully usable - uncomment the two lines below to re-enable them.
    figure1_timeline(climatology_df, RESULTS_DIR, logger)
    # figure2_heatmap(daily_pagc, RESULTS_DIR, logger)
    # figure3_division_curves(daily_pagc, RESULTS_DIR, logger)

    # STEP 16: summary log
    mem_current, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.time() - t0
    write_summary_log(logger, run_stats, grid_inventory, annual_df, elapsed, mem_current, mem_peak)

    logger.info("Done.")


if __name__ == "__main__":
    main()