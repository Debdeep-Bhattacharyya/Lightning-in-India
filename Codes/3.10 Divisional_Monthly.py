# ============================================================
# DIVISION-WISE MONTHLY LIGHTNING CONTRIBUTION (%)
# TRMM LIS vs ISS LIS
#
# TRMM LIS : 2000–2014
# ISS LIS   : 2018–2022
#
# 2015–2017 : Excluded
#
# Monthly contribution (%) is calculated as:
#
#   Monthly flashes
#   ------------------------------ × 100
#   Total flashes for that Division
#   and Sensor during the full
#   available observation period
#
# The Y-axis is identical for ALL subplots.
# The upper limit is determined from the highest percentage
# found across all divisions and both sensors.
#
# ============================================================


# ============================================================
# IMPORT LIBRARIES
# ============================================================

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# INPUT / OUTPUT DIRECTORIES
# ============================================================

input_dir = (
    r"D:\Articles\Working\Lightning India"
    r"\Data\Lightning\3_Grid_Assigned"
)

output_dir = (
    r"D:\Articles\Working\Lightning India"
    r"\Data\Division Analysis"
)


# Create output directory if it does not exist
os.makedirs(
    output_dir,
    exist_ok=True
)


# ============================================================
# FIND YEARLY CSV FILES
# ============================================================

files = []


for year in range(2000, 2023):

    filename = os.path.join(
        input_dir,
        f"{year}_Grid.csv"
    )

    if os.path.isfile(filename):

        files.append(
            (year, filename)
        )


# ------------------------------------------------------------
# Check files
# ------------------------------------------------------------

if not files:

    raise FileNotFoundError(

        "\nNo yearly Grid CSV files were found in:\n"
        + input_dir

    )


print()
print("=" * 80)
print("FILES FOUND")
print("=" * 80)


for year, filename in files:

    print(
        f"{year}: {filename}"
    )


# ============================================================
# READ ALL YEARLY FILES
# ============================================================

frames = []


for year, filename in files:

    print()
    print(
        f"Reading {os.path.basename(filename)} ..."
    )


    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    df = pd.read_csv(

        filename,

        low_memory=False

    )


    print(
        f"Rows: {len(df):,}"
    )


    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [

        "Year",
        "Month",
        "Division"

    ]


    missing_columns = [

        col

        for col in required_columns

        if col not in df.columns

    ]


    if missing_columns:

        raise ValueError(

            f"\n{os.path.basename(filename)} "
            f"is missing columns:\n"
            f"{missing_columns}"

        )


    # --------------------------------------------------------
    # Keep only required columns
    # --------------------------------------------------------

    temp = df[

        [
            "Year",
            "Month",
            "Division"
        ]

    ].copy()


    # --------------------------------------------------------
    # Clean Year
    # --------------------------------------------------------

    temp["Year"] = pd.to_numeric(

        temp["Year"],

        errors="coerce"

    )


    # --------------------------------------------------------
    # Clean Month
    # --------------------------------------------------------

    temp["Month"] = (

        temp["Month"]

        .astype("string")

        .str.strip()

    )


    # --------------------------------------------------------
    # Clean Division
    # --------------------------------------------------------

    temp["Division"] = (

        temp["Division"]

        .astype("string")

        .str.strip()

    )


    # ========================================================
    # SENSOR CLASSIFICATION
    # ========================================================
    #
    # IMPORTANT:
    #
    # Do NOT initialize Sensor with np.nan because that
    # creates a float64 column.
    #
    # Using pandas string dtype prevents:
    #
    # TypeError:
    # Invalid value 'TRMM LIS' for dtype 'float64'
    #
    # ========================================================

    temp["Sensor"] = pd.Series(

        pd.NA,

        index=temp.index,

        dtype="string"

    )


    # --------------------------------------------------------
    # TRMM LIS
    # --------------------------------------------------------

    temp.loc[

        temp["Year"].between(
            2000,
            2014
        ),

        "Sensor"

    ] = "TRMM LIS"


    # --------------------------------------------------------
    # ISS LIS
    # --------------------------------------------------------

    temp.loc[

        temp["Year"].between(
            2018,
            2022
        ),

        "Sensor"

    ] = "ISS LIS"


    # --------------------------------------------------------
    # Remove years outside the sensor periods
    #
    # 2015–2017 are therefore excluded.
    # --------------------------------------------------------

    temp = temp.dropna(

        subset=[

            "Sensor",
            "Division",
            "Month"

        ]

    )


    # --------------------------------------------------------
    # Append to list
    # --------------------------------------------------------

    frames.append(
        temp
    )


# ============================================================
# COMBINE ALL YEARS
# ============================================================

data = pd.concat(

    frames,

    ignore_index=True

)


print()
print("=" * 80)
print("COMBINED DATA")
print("=" * 80)


print(
    f"Total observations: {len(data):,}"
)


# ============================================================
# SENSOR SUMMARY
# ============================================================

print()
print("Sensor distribution:")

print(

    data["Sensor"]
    .value_counts()

)


# ============================================================
# STANDARDIZE MONTH NAMES
# ============================================================

month_map = {

    "Jan": "January",
    "Feb": "February",
    "Mar": "March",
    "Apr": "April",

    "May": "May",

    "Jun": "June",
    "Jul": "July",
    "Aug": "August",

    "Sep": "September",
    "Sept": "September",

    "Oct": "October",
    "Nov": "November",
    "Dec": "December"

}


data["Month"] = (

    data["Month"]

    .replace(month_map)

)


# ============================================================
# MONTH ORDER
# ============================================================

month_order = [

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


# ------------------------------------------------------------
# Keep only valid months
# ------------------------------------------------------------

data = data[

    data["Month"].isin(
        month_order
    )

].copy()


# ------------------------------------------------------------
# Ordered categorical month
# ------------------------------------------------------------

data["Month"] = pd.Categorical(

    data["Month"],

    categories=month_order,

    ordered=True

)


# ============================================================
# FIND DIVISIONS
# ============================================================

divisions = sorted(

    data["Division"]

    .dropna()

    .unique()

)


print()
print("=" * 80)
print("DIVISIONS")
print("=" * 80)


for division in divisions:

    print(
        f"   {division}"
    )


print()
print(
    f"Number of divisions: {len(divisions)}"
)


# ============================================================
# COUNT MONTHLY LIGHTNING OBSERVATIONS
# ============================================================
#
# Each row is treated as one lightning observation.
#
# If each row in your processed CSV represents one flash,
# this gives the monthly flash count.
#
# ============================================================

print()
print("Calculating monthly lightning counts...")


monthly = (

    data

    .groupby(

        [
            "Division",
            "Sensor",
            "Month"
        ],

        observed=False

    )

    .size()

    .reset_index(

        name="Lightning_Flashes"

    )

)


# ============================================================
# CREATE COMPLETE MATRIX
# ============================================================
#
# Ensures every Division × Sensor × Month combination exists.
#
# Missing combinations are assigned zero.
#
# ============================================================

sensors = [

    "TRMM LIS",
    "ISS LIS"

]


full_index = pd.MultiIndex.from_product(

    [

        divisions,
        sensors,
        month_order

    ],

    names=[

        "Division",
        "Sensor",
        "Month"

    ]

)


monthly = (

    monthly

    .set_index(

        [
            "Division",
            "Sensor",
            "Month"
        ]

    )

    .reindex(

        full_index,

        fill_value=0

    )

    .reset_index()

)


# Restore month ordering
monthly["Month"] = pd.Categorical(

    monthly["Month"],

    categories=month_order,

    ordered=True

)


# ============================================================
# TOTAL FLASHES FOR EACH DIVISION × SENSOR
# ============================================================
#
# Example:
#
# North West India + TRMM LIS
#       ↓
# Sum of all 12 months from 2000–2014
#
# North West India + ISS LIS
#       ↓
# Sum of all 12 months from 2018–2022
#
# ============================================================

monthly["Period_Total_Flashes"] = (

    monthly

    .groupby(

        [
            "Division",
            "Sensor"
        ],

        observed=False

    )["Lightning_Flashes"]

    .transform("sum")

)


# ============================================================
# MONTHLY CONTRIBUTION (%)
# ============================================================
#
# Contribution =
#
#       Monthly flashes
#       ----------------------------- × 100
#       Total flashes for sensor period
#
# ============================================================

monthly["Monthly_Contribution_Percent"] = np.where(

    monthly["Period_Total_Flashes"] > 0,

    (

        monthly["Lightning_Flashes"]

        /

        monthly["Period_Total_Flashes"]

        *

        100

    ),

    0

)


# ============================================================
# ROUND PERCENTAGE
# ============================================================

monthly["Monthly_Contribution_Percent"] = (

    monthly["Monthly_Contribution_Percent"]

    .round(4)

)


# ============================================================
# VERIFY EACH DIVISION × SENSOR SUMS TO 100%
# ============================================================

percentage_check = (

    monthly

    .groupby(

        [
            "Division",
            "Sensor"
        ],

        observed=False

    )["Monthly_Contribution_Percent"]

    .sum()

)


print()
print("=" * 80)
print("PERCENTAGE CHECK")
print("=" * 80)


for index, value in percentage_check.items():

    division = index[0]

    sensor = index[1]

    print(

        f"{division} | "
        f"{sensor}: "
        f"{value:.4f}%"

    )


# ============================================================
# SAVE LONG-FORM CSV
# ============================================================

long_csv = os.path.join(

    output_dir,

    "Division_Monthly_Lightning_Contribution_TRMM_ISS.csv"

)


monthly.to_csv(

    long_csv,

    index=False

)


print()
print(
    "Long-format CSV saved:"
)

print(
    long_csv
)


# ============================================================
# CREATE WIDE-FORM CSV
# ============================================================

wide = (

    monthly

    .pivot_table(

        index=[

            "Division",
            "Month"

        ],

        columns="Sensor",

        values="Monthly_Contribution_Percent",

        fill_value=0,

        observed=False

    )

    .reset_index()

)


# Remove column index name
wide.columns.name = None


# ------------------------------------------------------------
# Rename sensor columns
# ------------------------------------------------------------

wide = wide.rename(

    columns={

        "TRMM LIS":
            "TRMM_LIS_Contribution_Percent",

        "ISS LIS":
            "ISS_LIS_Contribution_Percent"

    }

)


# ============================================================
# SAVE WIDE CSV
# ============================================================

wide_csv = os.path.join(

    output_dir,

    "Division_Monthly_Lightning_Contribution_TRMM_ISS_Wide.csv"

)


wide.to_csv(

    wide_csv,

    index=False

)


print()
print(
    "Wide-format CSV saved:"
)

print(
    wide_csv
)


# ============================================================
# DETERMINE COMMON Y-AXIS
# ============================================================
#
# Find the highest monthly contribution across ALL:
#
#   Division
#   Sensor
#   Month
#
# ============================================================

global_max = (

    monthly[
        "Monthly_Contribution_Percent"
    ]

    .max()

)


# ------------------------------------------------------------
# Select sensible tick interval
# ------------------------------------------------------------

if global_max <= 20:

    y_interval = 5

elif global_max <= 50:

    y_interval = 10

else:

    y_interval = 20


# ------------------------------------------------------------
# Round maximum upward
# ------------------------------------------------------------

y_max = (

    np.ceil(

        global_max
        /
        y_interval

    )

    *
    y_interval

)


# ------------------------------------------------------------
# Add one interval of headroom if needed
# ------------------------------------------------------------

if y_max <= global_max:

    y_max += y_interval


print()
print("=" * 80)
print("COMMON Y-AXIS")
print("=" * 80)


print(

    f"Highest monthly contribution: "
    f"{global_max:.2f}%"

)


print(

    f"Common Y-axis maximum: "
    f"{y_max:.0f}%"

)


print(

    f"Y-axis interval: "
    f"{y_interval}%"

)


# ============================================================
# FIGURE DIMENSIONS
# ============================================================

n_divisions = len(
    divisions
)


# Two columns
ncols = 2


# Number of rows
nrows = int(

    np.ceil(

        n_divisions
        /
        ncols

    )

)


# Large dimensions for clear labels
fig_width = 22

fig_height = max(

    7.5 * nrows,

    9

)


# ============================================================
# CREATE FIGURE
# ============================================================

fig, axes = plt.subplots(

    nrows=nrows,

    ncols=ncols,

    figsize=(

        fig_width,

        fig_height

    ),

    squeeze=False

)


axes = axes.flatten()


# ============================================================
# BAR PARAMETERS
# ============================================================

x = np.arange(

    len(month_order)

)


bar_width = 0.36


# ============================================================
# COLOURS
# ============================================================

# TRMM LIS
TRMM_COLOR = "#377EB8"

# ISS LIS
ISS_COLOR = "#E66101"


# ============================================================
# MONTH LABELS
# ============================================================

month_labels = [

    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec"

]


# ============================================================
# CREATE EACH DIVISION PANEL
# ============================================================

for i, division in enumerate(
    divisions
):


    ax = axes[i]


    # --------------------------------------------------------
    # Select division
    # --------------------------------------------------------

    division_data = monthly[

        monthly["Division"]
        ==
        division

    ].copy()


    # ========================================================
    # TRMM DATA
    # ========================================================

    trmm = (

        division_data[

            division_data["Sensor"]
            ==
            "TRMM LIS"

        ]

        .set_index(
            "Month"
        )

        .reindex(
            month_order
        )

        [
            "Monthly_Contribution_Percent"
        ]

        .fillna(0)

        .values

    )


    # ========================================================
    # ISS DATA
    # ========================================================

    iss = (

        division_data[

            division_data["Sensor"]
            ==
            "ISS LIS"

        ]

        .set_index(
            "Month"
        )

        .reindex(
            month_order
        )

        [
            "Monthly_Contribution_Percent"
        ]

        .fillna(0)

        .values

    )


    # ========================================================
    # TRMM BAR
    # ========================================================

    ax.bar(

        x - bar_width / 2,

        trmm,

        width=bar_width,

        color=TRMM_COLOR,

        edgecolor="black",

        linewidth=0.5,

        label="TRMM LIS"

    )


    # ========================================================
    # ISS BAR
    # ========================================================

    ax.bar(

        x + bar_width / 2,

        iss,

        width=bar_width,

        color=ISS_COLOR,

        edgecolor="black",

        linewidth=0.5,

        label="ISS LIS"

    )


    # ========================================================
    # DIVISION NAME
    # ========================================================

    ax.set_title(

        division,

        fontsize=18,

        fontweight="bold",

        pad=10

    )


    # ========================================================
    # X AXIS
    # ========================================================

    ax.set_xticks(
        x
    )


    ax.set_xticklabels(

        month_labels,

        fontsize=13

    )


    # ========================================================
    # COMMON Y AXIS
    # ========================================================

    ax.set_ylim(

        0,

        y_max

    )


    ax.set_yticks(

        np.arange(

            0,

            y_max + y_interval,

            y_interval

        )

    )


    ax.set_ylabel(

        "Monthly contribution (%)",

        fontsize=14

    )


    ax.tick_params(

        axis="y",

        labelsize=12

    )


    # ========================================================
    # GRID
    # ========================================================

    ax.grid(

        axis="y",

        linestyle="--",

        linewidth=0.6,

        alpha=0.4

    )


    ax.set_axisbelow(
        True
    )


    # ========================================================
    # REMOVE TOP / RIGHT SPINES
    # ========================================================

    ax.spines[
        "top"
    ].set_visible(
        False
    )


    ax.spines[
        "right"
    ].set_visible(
        False
    )


# ============================================================
# REMOVE EMPTY SUBPLOTS
# ============================================================

for j in range(

    n_divisions,

    len(axes)

):

    fig.delaxes(
        axes[j]
    )


# ============================================================
# HORIZONTAL LEGEND AT TOP
# ============================================================

legend_handles = [

    plt.Rectangle(

        (0, 0),

        1,

        1,

        facecolor=TRMM_COLOR,

        edgecolor="black",

        linewidth=0.5

    ),

    plt.Rectangle(

        (0, 0),

        1,

        1,

        facecolor=ISS_COLOR,

        edgecolor="black",

        linewidth=0.5

    )

]


legend_labels = [

    "TRMM LIS (2000–2014)",

    "ISS LIS (2018–2022)"

]


fig.legend(

    legend_handles,

    legend_labels,

    loc="upper center",

    bbox_to_anchor=(

        0.5,

        0.995

    ),

    ncol=2,

    frameon=False,

    fontsize=14,

    handlelength=1.5,

    columnspacing=2.5

)


# ============================================================
# NO OVERALL TITLE
# ============================================================
#
# Deliberately no fig.suptitle()
#
# ============================================================


# ============================================================
# LAYOUT
# ============================================================

plt.tight_layout(

    rect=[

        0.025,

        0.025,

        0.985,

        0.955

    ]

)


# ============================================================
# OUTPUT FILE NAMES
# ============================================================

tiff_file = os.path.join(

    output_dir,

    "Division_Monthly_Lightning_Contribution_TRMM_ISS.tiff"

)


png_file = os.path.join(

    output_dir,

    "Division_Monthly_Lightning_Contribution_TRMM_ISS.png"

)


# ============================================================
# SAVE TIFF — 600 DPI
# ============================================================

fig.savefig(

    tiff_file,

    dpi=600,

    format="tiff",

    bbox_inches="tight"

)


# ============================================================
# SAVE PNG — 600 DPI
# ============================================================

fig.savefig(

    png_file,

    dpi=600,

    format="png",

    bbox_inches="tight"

)


# ============================================================
# CLOSE FIGURE
# ============================================================

plt.close(
    fig
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 80)
print("ANALYSIS COMPLETED SUCCESSFULLY")
print("=" * 80)

print()
print(
    f"Files processed       : {len(files)}"
)

print(
    f"Divisions             : {n_divisions}"
)

print(
    f"Total observations    : {len(data):,}"
)

print()
print(
    f"Highest contribution  : {global_max:.2f}%"
)

print(
    f"Common Y-axis         : 0–{y_max:.0f}%"
)

print(
    f"Y-axis interval       : {y_interval}%"
)

print()
print("OUTPUT FILES")
print("-" * 80)

print()
print(
    f"TIFF:\n{tiff_file}"
)

print()
print(
    f"PNG:\n{png_file}"
)

print()
print(
    f"Long CSV:\n{long_csv}"
)

print()
print(
    f"Wide CSV:\n{wide_csv}"
)

print()
print("=" * 80)
print("DONE")
print("=" * 80)