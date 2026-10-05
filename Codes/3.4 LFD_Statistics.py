# ============================================================
# Step06_LFD_Statistics.py
#
# Computes Annual, Monthly and Seasonal Lightning Flash Density
# statistics separately for:
#
#   1. TRMM-LIS : 2000–2014 (15 years)
#   2. ISS-LIS  : 2018–2022 (5 years)
#
# PURPOSE:
#   Address the TRMM–ISS sensor comparability issue identified
#   during manuscript revision.
#
# IMPORTANT:
#   TRMM-LIS and ISS-LIS absolute flash counts/LFD values are
#   NOT pooled into a single climatology.
#
#   Cross-platform comparisons should focus on relative spatial
#   and temporal characteristics rather than absolute magnitude.
#
# LFD:
#   Annual:
#       Flash_Count / Area_km2
#
#   Monthly:
#       Total flashes for that month across observation years
#       / (Area_km2 × number of observation years)
#
#   Seasonal:
#       Total flashes for that season across observation years
#       / (Area_km2 × number of observation years)
#
# IMPORTANT ZERO-FLASH YEAR HANDLING:
#   A year with zero flashes is still counted in the denominator.
#   Therefore, n_years is determined from the defined observation
#   period, NOT from the number of years containing lightning
#   records.
#
# OUTPUTS:
#   Annual_LFD_Statistics_By_Sensor.csv
#   Monthly_LFD_Statistics_By_Sensor.csv
#   Seasonal_LFD_Statistics_By_Sensor.csv
#
# ============================================================

import os
import numpy as np
import pandas as pd


# ============================================================
# 1. PATHS
# ============================================================

CSV_DIR = r"D:\Articles\Working\Lightning India\Data\Lightning\3_Grid_Assigned"

OUT_DIR = r"D:\Articles\Working\Lightning India\Results"

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# 2. OBSERVATION PERIODS
# ============================================================

# TRMM-LIS observation period
TRMM_YEARS = list(range(2000, 2015))       # 15 years

# ISS-LIS observation period
ISS_YEARS = list(range(2018, 2023))        # 5 years


SENSOR_PERIODS = {
    "TRMM-LIS": TRMM_YEARS,
    "ISS-LIS": ISS_YEARS
}


# ============================================================
# 3. MONTHS
# ============================================================

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
]


# ============================================================
# 4. SEASONS
# ============================================================

SEASONS = {

    "Winter": [
        "January",
        "February"
    ],

    "Pre-Monsoon": [
        "March",
        "April",
        "May"
    ],

    "Monsoon": [
        "June",
        "July",
        "August",
        "September"
    ],

    "Post-Monsoon": [
        "October",
        "November",
        "December"
    ]
}


# ============================================================
# 5. SUMMARY FUNCTION
# ============================================================

def summarize(df, label, n_years=1, sensor_period=None):
    """
    Calculate LFD summary statistics.

    Parameters
    ----------
    df : pandas.DataFrame
        Lightning records.

    label : str
        Year / month / season label.

    n_years : int
        Number of years represented by the dataset.

    sensor_period : str
        TRMM-LIS or ISS-LIS.

    Notes
    -----
    LFD is calculated as:

        LFD = Flash_Count / (Area_km2 × n_years)

    For annual statistics n_years = 1.

    For monthly and seasonal climatologies:
        n_years = total number of years in the observation period,
        including years with zero flashes.
    """

    # --------------------------------------------------------
    # Empty dataset
    # --------------------------------------------------------

    if df.empty:
        return None


    # --------------------------------------------------------
    # Grid-level flash count
    # --------------------------------------------------------

    grp = (
        df.groupby("Grid_ID")
          .agg(
              Flash_Count=("Grid_ID", "size"),
              Area_km2=("Area_km2", "first")
          )
          .reset_index()
    )


    # --------------------------------------------------------
    # Remove invalid areas
    # --------------------------------------------------------

    grp = grp[
        grp["Area_km2"].notna() &
        (grp["Area_km2"] > 0)
    ].copy()


    if grp.empty:
        return None


    # --------------------------------------------------------
    # Lightning Flash Density
    # --------------------------------------------------------

    grp["LFD"] = (
        grp["Flash_Count"] /
        (grp["Area_km2"] * n_years)
    )


    # --------------------------------------------------------
    # Summary statistics
    # --------------------------------------------------------

    mean_lfd = grp["LFD"].mean()
    std_lfd = grp["LFD"].std()


    result = {

        "Sensor_Period": sensor_period,

        "Name": label,

        "N_Years_Used": n_years,

        "Total_Flashes": int(
            grp["Flash_Count"].sum()
        ),

        "Active_Grids": int(
            (grp["Flash_Count"] > 0).sum()
        ),

        "Mean_LFD": mean_lfd,

        "Median_LFD": grp["LFD"].median(),

        "Min_LFD": grp["LFD"].min(),

        "Max_LFD": grp["LFD"].max(),

        "Std_LFD": std_lfd,

        "CV_percent": (
            std_lfd / mean_lfd * 100
            if mean_lfd > 0
            else np.nan
        ),

        "P95": grp["LFD"].quantile(0.95),

        "P99": grp["LFD"].quantile(0.99)
    }


    return result


# ============================================================
# 6. STORAGE
# ============================================================

annual_results = []

monthly_results = []

seasonal_results = []


# ============================================================
# 7. FUNCTION TO LOAD YEAR FILE
# ============================================================

def load_year_file(year):

    file_path = os.path.join(
        CSV_DIR,
        f"{year}_Grid.csv"
    )

    if not os.path.exists(file_path):
        print(
            f"WARNING: File not found for {year}: "
            f"{file_path}"
        )

        return None

    try:

        df = pd.read_csv(file_path)

    except Exception as e:

        print(
            f"ERROR reading {year}: {e}"
        )

        return None


    return df


# ============================================================
# 8. PROCESS EACH SENSOR PERIOD
# ============================================================

for sensor_period, years in SENSOR_PERIODS.items():

    print("\n")
    print("=" * 70)
    print(f"PROCESSING: {sensor_period}")
    print(
        f"Years: {years[0]}–{years[-1]} "
        f"({len(years)} years)"
    )
    print("=" * 70)


    # ========================================================
    # 8.1 LOAD ALL AVAILABLE YEARS
    # ========================================================

    yearly_data = {}

    missing_years = []

    for yr in years:

        df = load_year_file(yr)

        if df is None:

            missing_years.append(yr)

        else:

            yearly_data[yr] = df


    # --------------------------------------------------------
    # Report missing years
    # --------------------------------------------------------

    if missing_years:

        print(
            f"\nWARNING: Missing files for "
            f"{sensor_period}: {missing_years}"
        )

        print(
            "Statistics will use the defined observation "
            "period denominator only if all expected years "
            "are available."
        )


    # ========================================================
    # 8.2 EFFECTIVE NUMBER OF YEARS
    # ========================================================

    #
    # IMPORTANT:
    #
    # We do NOT use len(dfs).
    #
    # A year with zero lightning must still count.
    #
    # If all expected files exist:
    #
    #   TRMM = 15
    #   ISS  = 5
    #
    # If files are genuinely missing, the denominator should
    # reflect the years actually available rather than silently
    # assuming missing files contained zero lightning.
    #

    available_years = [
        yr for yr in years
        if yr in yearly_data
    ]

    n_years = len(available_years)


    if n_years == 0:

        print(
            f"No valid data available for {sensor_period}."
        )

        continue


    print(
        f"Available years: {n_years} / {len(years)}"
    )


    # ========================================================
    # 8.3 ANNUAL STATISTICS
    # ========================================================

    print("\nCalculating annual statistics...")


    for yr in available_years:

        df = yearly_data[yr]

        result = summarize(
            df=df,
            label=str(yr),
            n_years=1,
            sensor_period=sensor_period
        )

        if result is not None:

            annual_results.append(result)


    # ========================================================
    # 8.4 MONTHLY STATISTICS
    # ========================================================

    print("Calculating monthly statistics...")


    for month in MONTHS:

        month_data = []


        # ----------------------------------------------------
        # Collect the specified month from EVERY available
        # year.
        # ----------------------------------------------------

        for yr in available_years:

            df = yearly_data[yr]

            if "Month" not in df.columns:
                continue


            month_mask = (
                df["Month"]
                .astype(str)
                .str.strip()
                .str.lower()
                == month.lower()
            )


            d = df.loc[month_mask].copy()


            # IMPORTANT:
            #
            # If d is empty, that year contributes ZERO
            # lightning flashes for this month.
            #
            # We do NOT remove that year from n_years.
            #

            if not d.empty:

                month_data.append(d)


        # ----------------------------------------------------
        # Combine all non-empty monthly datasets
        # ----------------------------------------------------

        if month_data:

            combined = pd.concat(
                month_data,
                ignore_index=True
            )

        else:

            combined = pd.DataFrame()


        # ----------------------------------------------------
        # Calculate climatological monthly LFD
        # ----------------------------------------------------

        if not combined.empty:

            result = summarize(
                df=combined,
                label=month,
                n_years=n_years,
                sensor_period=sensor_period
            )

            if result is not None:

                monthly_results.append(result)

        else:

            print(
                f"WARNING: No {month} data "
                f"for {sensor_period}."
            )


    # ========================================================
    # 8.5 SEASONAL STATISTICS
    # ========================================================

    print("Calculating seasonal statistics...")


    for season, season_months in SEASONS.items():

        season_months_lower = [
            m.lower()
            for m in season_months
        ]


        season_data = []


        # ----------------------------------------------------
        # Collect season from every available year
        # ----------------------------------------------------

        for yr in available_years:

            df = yearly_data[yr]

            if "Month" not in df.columns:
                continue


            month_values = (
                df["Month"]
                .astype(str)
                .str.strip()
                .str.lower()
            )


            season_mask = (
                month_values.isin(
                    season_months_lower
                )
            )


            d = df.loc[season_mask].copy()


            # A year with no lightning in the season still
            # counts in n_years.
            #

            if not d.empty:

                season_data.append(d)


        # ----------------------------------------------------
        # Combine season data
        # ----------------------------------------------------

        if season_data:

            combined = pd.concat(
                season_data,
                ignore_index=True
            )

        else:

            combined = pd.DataFrame()


        # ----------------------------------------------------
        # Calculate seasonal climatological LFD
        # ----------------------------------------------------

        if not combined.empty:

            result = summarize(
                df=combined,
                label=season,
                n_years=n_years,
                sensor_period=sensor_period
            )

            if result is not None:

                seasonal_results.append(result)

        else:

            print(
                f"WARNING: No {season} data "
                f"for {sensor_period}."
            )


# ============================================================
# 9. CREATE DATAFRAMES
# ============================================================

annual_df = pd.DataFrame(
    annual_results
)

monthly_df = pd.DataFrame(
    monthly_results
)

seasonal_df = pd.DataFrame(
    seasonal_results
)


# ============================================================
# 10. SORT RESULTS
# ============================================================

# ------------------------------------------------------------
# Annual
# ------------------------------------------------------------

if not annual_df.empty:

    annual_df["Year"] = pd.to_numeric(
        annual_df["Name"],
        errors="coerce"
    )

    annual_df = (
        annual_df
        .sort_values(
            ["Sensor_Period", "Year"]
        )
        .drop(columns=["Year"])
    )


# ------------------------------------------------------------
# Monthly
# ------------------------------------------------------------

if not monthly_df.empty:

    month_order = {
        month: i
        for i, month in enumerate(
            MONTHS,
            start=1
        )
    }

    monthly_df["Month_Order"] = (
        monthly_df["Name"]
        .map(month_order)
    )

    monthly_df = (
        monthly_df
        .sort_values(
            ["Sensor_Period", "Month_Order"]
        )
        .drop(columns=["Month_Order"])
    )


# ------------------------------------------------------------
# Seasonal
# ------------------------------------------------------------

if not seasonal_df.empty:

    season_order = {
        "Winter": 1,
        "Pre-Monsoon": 2,
        "Monsoon": 3,
        "Post-Monsoon": 4
    }

    seasonal_df["Season_Order"] = (
        seasonal_df["Name"]
        .map(season_order)
    )

    seasonal_df = (
        seasonal_df
        .sort_values(
            ["Sensor_Period", "Season_Order"]
        )
        .drop(columns=["Season_Order"])
    )


# ============================================================
# 11. SAVE OUTPUTS
# ============================================================

annual_output = os.path.join(
    OUT_DIR,
    "Annual_LFD_Statistics_By_Sensor.csv"
)

monthly_output = os.path.join(
    OUT_DIR,
    "Monthly_LFD_Statistics_By_Sensor.csv"
)

seasonal_output = os.path.join(
    OUT_DIR,
    "Seasonal_LFD_Statistics_By_Sensor.csv"
)


annual_df.to_csv(
    annual_output,
    index=False
)

monthly_df.to_csv(
    monthly_output,
    index=False
)

seasonal_df.to_csv(
    seasonal_output,
    index=False
)


# ============================================================
# 12. PRINT SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("STEP 06 COMPLETED")
print("=" * 70)


print("\nOutput files:")
print(
    f"  Annual   : {annual_output}"
)

print(
    f"  Monthly  : {monthly_output}"
)

print(
    f"  Seasonal : {seasonal_output}"
)


# ============================================================
# 13. BASIC VALIDATION
# ============================================================

print("\n")
print("=" * 70)
print("VALIDATION")
print("=" * 70)


# ------------------------------------------------------------
# Annual validation
# ------------------------------------------------------------

if not annual_df.empty:

    print("\nAnnual records by sensor:")

    print(
        annual_df
        .groupby("Sensor_Period")
        .size()
    )


# ------------------------------------------------------------
# Monthly validation
# ------------------------------------------------------------

if not monthly_df.empty:

    print("\nMonthly records by sensor:")

    print(
        monthly_df
        .groupby("Sensor_Period")
        .size()
    )


# ------------------------------------------------------------
# Seasonal validation
# ------------------------------------------------------------

if not seasonal_df.empty:

    print("\nSeasonal records by sensor:")

    print(
        seasonal_df
        .groupby("Sensor_Period")
        .size()
    )


# ============================================================
# 14. PERIOD SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("PERIOD SUMMARY")
print("=" * 70)


for sensor_period in SENSOR_PERIODS.keys():

    print(f"\n{sensor_period}")

    # --------------------------------------------------------
    # Annual
    # --------------------------------------------------------

    a = annual_df[
        annual_df["Sensor_Period"]
        == sensor_period
    ].copy()


    if not a.empty:

        print(
            f"  Annual years: {len(a)}"
        )

        print(
            f"  Mean annual flashes: "
            f"{a['Total_Flashes'].mean():,.1f}"
        )

        print(
            f"  Mean annual LFD: "
            f"{a['Mean_LFD'].mean():.4f}"
        )

        max_row = a.loc[
            a["Mean_LFD"].idxmax()
        ]

        min_row = a.loc[
            a["Mean_LFD"].idxmin()
        ]

        print(
            f"  Maximum annual LFD: "
            f"{max_row['Mean_LFD']:.4f} "
            f"({max_row['Name']})"
        )

        print(
            f"  Minimum annual LFD: "
            f"{min_row['Mean_LFD']:.4f} "
            f"({min_row['Name']})"
        )


    # --------------------------------------------------------
    # Monthly
    # --------------------------------------------------------

    m = monthly_df[
        monthly_df["Sensor_Period"]
        == sensor_period
    ]

    print(
        f"  Monthly climatologies: {len(m)}"
    )


    # --------------------------------------------------------
    # Seasonal
    # --------------------------------------------------------

    s = seasonal_df[
        seasonal_df["Sensor_Period"]
        == sensor_period
    ]

    print(
        f"  Seasonal climatologies: {len(s)}"
    )


# ============================================================
# 15. FINAL NOTES
# ============================================================

print("\n")
print("=" * 70)
print("IMPORTANT INTERPRETATION NOTE")
print("=" * 70)

print(
    """
TRMM-LIS and ISS-LIS statistics are calculated separately.

TRMM-LIS:
    2000–2014 = 15 observation years

ISS-LIS:
    2018–2022 = 5 observation years

No pooled 2000–2022 absolute LFD climatology is produced.

The 2015–2017 observational gap is not interpolated.

For monthly and seasonal climatologies, years with zero
lightning are retained in the denominator.

Therefore:
    Monthly LFD =
        total monthly flashes /
        (grid-cell area × number of observation years)

    Seasonal LFD =
        total seasonal flashes /
        (grid-cell area × number of observation years)

Cross-sensor comparisons should focus primarily on relative
spatial and temporal characteristics rather than absolute
flash magnitude.
"""
)

print("\nDone.")