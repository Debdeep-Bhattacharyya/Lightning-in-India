# ============================================================
# DIVISION-WISE DIURNAL / TIME-CYCLE LIGHTNING CONTRIBUTION
# TRMM LIS vs ISS LIS
#
# TRMM LIS : 2000–2014
# ISS LIS   : 2018–2022
#
# TIME:
#     IST (Indian Standard Time)
#
# METRIC:
#     Hourly lightning contribution (%)
#
# FIGURE:
#     TRMM LIS = BLUE
#     ISS LIS   = RED
#
#     NO COLOUR RAMP
#     NO COLOURBAR
#     NO MAIN TITLE
#
#     Common Y-axis across all divisions
#     based on the highest value across all panels.
#
# OUTPUT:
#     TIFF 600 DPI
#     PNG  600 DPI
#     Long CSV
#     Wide CSV
#
# ============================================================


# ============================================================
# IMPORT LIBRARIES
# ============================================================

import os

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt


# ============================================================
# INPUT DIRECTORY
# ============================================================

input_dir = (
    r"D:\Articles\Working\Lightning India"
    r"\Data\Lightning\3_Grid_Assigned"
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

output_dir = (
    r"D:\Articles\Working\Lightning India"
    r"\Data\Division Analysis"
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    output_dir,
    exist_ok=True
)


# ============================================================
# FIND YEARLY FILES
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


# ============================================================
# CHECK FILES
# ============================================================

if not files:

    raise FileNotFoundError(
        "\nNo yearly Grid CSV files were found in:\n"
        + input_dir
    )


# ============================================================
# PRINT FILES
# ============================================================

print()
print("=" * 90)
print("FILES FOUND")
print("=" * 90)

for year, filename in files:

    print(
        f"{year}: {filename}"
    )


# ============================================================
# READ DATA
# ============================================================

frames = []


for year, filename in files:

    print()
    print(
        f"Reading {os.path.basename(filename)} ..."
    )

    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    df = pd.read_csv(
        filename,
        low_memory=False
    )

    print(
        f"Rows: {len(df):,}"
    )

    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = [
        "Year",
        "IST",
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
            f"is missing required columns:\n"
            f"{missing_columns}"
        )

    # --------------------------------------------------------
    # KEEP REQUIRED COLUMNS
    # --------------------------------------------------------

    temp = df[
        [
            "Year",
            "IST",
            "Division"
        ]
    ].copy()

    # --------------------------------------------------------
    # CLEAN YEAR
    # --------------------------------------------------------

    temp["Year"] = pd.to_numeric(
        temp["Year"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # CLEAN IST
    # --------------------------------------------------------

    temp["IST"] = (
        temp["IST"]
        .astype("string")
        .str.strip()
    )

    # --------------------------------------------------------
    # CLEAN DIVISION
    # --------------------------------------------------------

    temp["Division"] = (
        temp["Division"]
        .astype("string")
        .str.strip()
    )

    # ========================================================
    # CREATE SENSOR COLUMN
    # ========================================================
    #
    # Explicit string dtype prevents the pandas error:
    #
    # Invalid value 'TRMM LIS' for dtype 'float64'
    #
    # ========================================================

    temp["Sensor"] = pd.Series(
        pd.NA,
        index=temp.index,
        dtype="string"
    )

    # --------------------------------------------------------
    # TRMM LIS: 2000–2014
    # --------------------------------------------------------

    temp.loc[
        temp["Year"].between(2000, 2014),
        "Sensor"
    ] = "TRMM LIS"

    # --------------------------------------------------------
    # ISS LIS: 2018–2022
    # --------------------------------------------------------

    temp.loc[
        temp["Year"].between(2018, 2022),
        "Sensor"
    ] = "ISS LIS"

    # --------------------------------------------------------
    # REMOVE 2015–2017
    # --------------------------------------------------------

    temp = temp.dropna(
        subset=[
            "Sensor",
            "IST",
            "Division"
        ]
    )

    frames.append(temp)


# ============================================================
# COMBINE ALL DATA
# ============================================================

data = pd.concat(
    frames,
    ignore_index=True
)


# ============================================================
# BASIC INFORMATION
# ============================================================

print()
print("=" * 90)
print("COMBINED DATA")
print("=" * 90)

print(
    f"Total observations: {len(data):,}"
)

print()
print("Sensor distribution:")

print(
    data["Sensor"].value_counts()
)


# ============================================================
# CONVERT IST TO DECIMAL HOURS
# ============================================================
#
# Example:
#
# 03:02:05 → 3.0347
# 08:32:05 → 8.5347
# 18:45:30 → 18.7583
#
# ============================================================

print()
print(
    "Converting IST to decimal hours..."
)


# ============================================================
# EXTRACT HOUR
# ============================================================

data["Hour"] = (
    data["IST"]
    .str.extract(
        r"^(\d{1,2})"
    )[0]
)


# ============================================================
# EXTRACT MINUTE
# ============================================================

data["Minute"] = (
    data["IST"]
    .str.extract(
        r"^\d{1,2}:(\d{1,2})"
    )[0]
)


# ============================================================
# EXTRACT SECOND
# ============================================================

data["Second"] = (
    data["IST"]
    .str.extract(
        r"^\d{1,2}:\d{1,2}:(\d{1,2})"
    )[0]
)


# ============================================================
# CONVERT TO NUMERIC
# ============================================================

data["Hour"] = pd.to_numeric(
    data["Hour"],
    errors="coerce"
)

data["Minute"] = pd.to_numeric(
    data["Minute"],
    errors="coerce"
)

data["Second"] = pd.to_numeric(
    data["Second"],
    errors="coerce"
)


# ============================================================
# MISSING SECONDS = ZERO
# ============================================================

data["Second"] = (
    data["Second"]
    .fillna(0)
)


# ============================================================
# CALCULATE DECIMAL IST HOUR
# ============================================================

data["IST_Decimal_Hour"] = (

    data["Hour"]

    +

    data["Minute"] / 60.0

    +

    data["Second"] / 3600.0

)


# ============================================================
# REMOVE INVALID TIME VALUES
# ============================================================

data = data[
    data["IST_Decimal_Hour"].between(
        0,
        24,
        inclusive="left"
    )
].copy()


print(
    f"Valid time observations: {len(data):,}"
)


# ============================================================
# CREATE 1-HOUR BIN
# ============================================================

data["Hour_Bin"] = (
    np.floor(
        data["IST_Decimal_Hour"]
    )
    .astype(int)
)


# ============================================================
# GET DIVISIONS
# ============================================================

divisions = sorted(
    data["Division"]
    .dropna()
    .unique()
)


print()
print("=" * 90)
print("DIVISIONS")
print("=" * 90)

for division in divisions:

    print(
        f"   {division}"
    )

print()

print(
    f"Number of divisions: {len(divisions)}"
)


# ============================================================
# SENSORS
# ============================================================

sensors = [
    "TRMM LIS",
    "ISS LIS"
]


# ============================================================
# HOURS
# ============================================================

hours = list(
    range(24)
)


# ============================================================
# CALCULATE HOURLY FLASH COUNTS
# ============================================================

print()
print(
    "Calculating hourly lightning counts..."
)


hourly = (

    data

    .groupby(
        [
            "Division",
            "Sensor",
            "Hour_Bin"
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
# Division × Sensor × 24 hours
#
# This ensures missing hours are represented as zero.
#
# ============================================================

full_index = pd.MultiIndex.from_product(

    [
        divisions,
        sensors,
        hours
    ],

    names=[
        "Division",
        "Sensor",
        "Hour_Bin"
    ]

)


hourly = (

    hourly

    .set_index(
        [
            "Division",
            "Sensor",
            "Hour_Bin"
        ]
    )

    .reindex(
        full_index,
        fill_value=0
    )

    .reset_index()

)


# ============================================================
# TOTAL FLASHES FOR EACH DIVISION × SENSOR
# ============================================================

hourly["Period_Total_Flashes"] = (

    hourly

    .groupby(
        [
            "Division",
            "Sensor"
        ],
        observed=False
    )[
        "Lightning_Flashes"
    ]

    .transform(
        "sum"
    )

)


# ============================================================
# HOURLY CONTRIBUTION (%)
# ============================================================
#
# Contribution =
#
# Hourly flashes
# ------------------------- × 100
# Total flashes
#
# ============================================================

hourly["Hourly_Contribution_Percent"] = np.where(

    hourly["Period_Total_Flashes"] > 0,

    (
        hourly["Lightning_Flashes"]
        /
        hourly["Period_Total_Flashes"]
        *
        100
    ),

    0

)


# ============================================================
# ROUND
# ============================================================

hourly["Hourly_Contribution_Percent"] = (

    hourly["Hourly_Contribution_Percent"]

    .round(6)

)


# ============================================================
# PERCENTAGE CHECK
# ============================================================

percentage_check = (

    hourly

    .groupby(
        [
            "Division",
            "Sensor"
        ],
        observed=False
    )[
        "Hourly_Contribution_Percent"
    ]

    .sum()

)


print()
print("=" * 90)
print("PERCENTAGE CHECK")
print("=" * 90)

for index, value in percentage_check.items():

    print(
        f"{index[0]} | "
        f"{index[1]}: "
        f"{value:.4f}%"
    )


# ============================================================
# SAVE LONG CSV
# ============================================================

long_csv = os.path.join(

    output_dir,

    "Division_Diurnal_Lightning_Contribution_TRMM_ISS.csv"

)


hourly.to_csv(

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
# CREATE WIDE CSV
# ============================================================

wide = (

    hourly

    .pivot_table(

        index=[
            "Division",
            "Hour_Bin"
        ],

        columns="Sensor",

        values="Hourly_Contribution_Percent",

        fill_value=0,

        observed=False

    )

    .reset_index()

)


# ============================================================
# REMOVE COLUMN INDEX NAME
# ============================================================

wide.columns.name = None


# ============================================================
# RENAME COLUMNS
# ============================================================

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

    "Division_Diurnal_Lightning_Contribution_TRMM_ISS_Wide.csv"

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
# GLOBAL MAXIMUM
# ============================================================
#
# Determine maximum hourly contribution from ALL:
#
#   Divisions
#   TRMM
#   ISS
#   Hours
#
# One common scale is then used for every panel.
#
# ============================================================

global_max = (

    hourly[
        "Hourly_Contribution_Percent"
    ]

    .max()

)


# ============================================================
# CHOOSE Y-AXIS INTERVAL
# ============================================================

if global_max <= 1:

    y_interval = 0.2

elif global_max <= 2:

    y_interval = 0.5

elif global_max <= 5:

    y_interval = 1

elif global_max <= 10:

    y_interval = 2

elif global_max <= 20:

    y_interval = 5

else:

    y_interval = 10


# ============================================================
# CALCULATE COMMON Y MAXIMUM
# ============================================================

y_max = (

    np.ceil(

        global_max
        /
        y_interval

    )

    *

    y_interval

)


# ============================================================
# ADD ONE INTERVAL HEADROOM
# ============================================================

if y_max <= global_max:

    y_max += y_interval


# ============================================================
# PRINT Y-AXIS INFORMATION
# ============================================================

print()
print("=" * 90)
print("COMMON Y-AXIS")
print("=" * 90)

print(
    f"Highest hourly contribution : "
    f"{global_max:.4f}%"
)

print(
    f"Common Y-axis maximum      : "
    f"{y_max:.4f}%"
)

print(
    f"Y-axis interval             : "
    f"{y_interval:.4f}%"
)


# ============================================================
# FIGURE LAYOUT
# ============================================================

n_divisions = len(
    divisions
)

ncols = 2

nrows = int(
    np.ceil(
        n_divisions / ncols
    )
)


# ============================================================
# LARGE FIGURE DIMENSIONS
# ============================================================

fig_width = 24

fig_height = max(
    8.0 * nrows,
    10
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
# LINE COLOURS
# ============================================================

TRMM_COLOR = "#2166AC"

ISS_COLOR = "#D73027"


# ============================================================
# PLOT EACH DIVISION
# ============================================================

for i, division in enumerate(divisions):

    # --------------------------------------------------------
    # AXIS
    # --------------------------------------------------------

    ax = axes[i]


    # --------------------------------------------------------
    # DIVISION DATA
    # --------------------------------------------------------

    division_data = hourly[
        hourly["Division"] == division
    ].copy()


    # ========================================================
    # TRMM
    # ========================================================

    trmm = (

        division_data[
            division_data["Sensor"] == "TRMM LIS"
        ]

        .set_index(
            "Hour_Bin"
        )

        .reindex(
            hours
        )[

            "Hourly_Contribution_Percent"

        ]

        .fillna(0)

        .values

    )


    # ========================================================
    # ISS
    # ========================================================

    iss = (

        division_data[
            division_data["Sensor"] == "ISS LIS"
        ]

        .set_index(
            "Hour_Bin"
        )

        .reindex(
            hours
        )[

            "Hourly_Contribution_Percent"

        ]

        .fillna(0)

        .values

    )


    # ========================================================
    # TRMM LINE
    # ========================================================

    ax.plot(

        hours,

        trmm,

        color=TRMM_COLOR,

        linewidth=3.5,

        marker="o",

        markersize=6.5,

        markeredgecolor="white",

        markeredgewidth=0.9,

        label="TRMM LIS"

    )


    # ========================================================
    # ISS LINE
    # ========================================================

    ax.plot(

        hours,

        iss,

        color=ISS_COLOR,

        linewidth=3.5,

        marker="o",

        markersize=6.5,

        markeredgecolor="white",

        markeredgewidth=0.9,

        label="ISS LIS"

    )


    # ========================================================
    # DIVISION NAME
    # ========================================================

    ax.set_title(

        division,

        fontsize=22,

        fontweight="bold",

        pad=12

    )


    # ========================================================
    # X AXIS
    # ========================================================

    ax.set_xlim(

        0,

        23

    )


    ax.set_xticks(

        np.arange(
            0,
            24,
            2
        )

    )


    ax.set_xticklabels(

        [
            "00",
            "02",
            "04",
            "06",
            "08",
            "10",
            "12",
            "14",
            "16",
            "18",
            "20",
            "22"
        ],

        fontsize=17

    )


    ax.set_xlabel(

        "IST (hour)",

        fontsize=19,

        labelpad=9

    )


    # ========================================================
    # Y AXIS
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

        "Hourly contribution (%)",

        fontsize=19,

        labelpad=10

    )


    ax.tick_params(

        axis="y",

        labelsize=16,

        width=1.3,

        length=7

    )


    ax.tick_params(

        axis="x",

        width=1.3,

        length=7

    )


    # ========================================================
    # GRID
    # ========================================================

    ax.grid(

        axis="y",

        linestyle="--",

        linewidth=0.8,

        alpha=0.35

    )


    ax.grid(

        axis="x",

        linestyle=":",

        linewidth=0.6,

        alpha=0.25

    )


    ax.set_axisbelow(True)


    # ========================================================
    # SPINES
    # ========================================================

    ax.spines[
        "top"
    ].set_visible(False)

    ax.spines[
        "right"
    ].set_visible(False)

    ax.spines[
        "left"
    ].set_linewidth(1.3)

    ax.spines[
        "bottom"
    ].set_linewidth(1.3)


# ============================================================
# REMOVE UNUSED AXES
# ============================================================

for j in range(

    n_divisions,

    len(axes)

):

    fig.delaxes(
        axes[j]
    )


# ============================================================
# SENSOR LEGEND
# ============================================================

legend_handles = [

    plt.Line2D(

        [0],

        [0],

        color=TRMM_COLOR,

        linewidth=4,

        marker="o",

        markersize=7,

        markeredgecolor="white",

        markeredgewidth=0.8,

        label="TRMM LIS (2000–2014)"

    ),

    plt.Line2D(

        [0],

        [0],

        color=ISS_COLOR,

        linewidth=4,

        marker="o",

        markersize=7,

        markeredgecolor="white",

        markeredgewidth=0.8,

        label="ISS LIS (2018–2022)"

    )

]


# ============================================================
# HORIZONTAL LEGEND AT TOP
# ============================================================

fig.legend(

    handles=legend_handles,

    loc="upper center",

    bbox_to_anchor=(

        0.5,

        0.995

    ),

    ncol=2,

    frameon=False,

    fontsize=18,

    handlelength=2.8,

    columnspacing=3.5,

    handletextpad=0.9

)


# ============================================================
# NO COLOURBAR
# ============================================================
#
# Deliberately no:
#
#     colour ramp
#     colourbar
#     ScalarMappable
#     gradient
#
# ============================================================


# ============================================================
# NO MAIN TITLE
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
# OUTPUT FILENAMES
# ============================================================

tiff_file = os.path.join(

    output_dir,

    "Division_Diurnal_Lightning_Contribution_TRMM_ISS.tiff"

)


png_file = os.path.join(

    output_dir,

    "Division_Diurnal_Lightning_Contribution_TRMM_ISS.png"

)


# ============================================================
# SAVE TIFF
# ============================================================

fig.savefig(

    tiff_file,

    dpi=600,

    format="tiff",

    bbox_inches="tight"

)


# ============================================================
# SAVE PNG
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

plt.close(fig)


# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 90)
print("DIURNAL ANALYSIS COMPLETED SUCCESSFULLY")
print("=" * 90)

print()

print(
    f"Files processed             : {len(files)}"
)

print(
    f"Divisions                   : {n_divisions}"
)

print(
    f"Total observations          : {len(data):,}"
)

print()

print(
    f"Highest hourly contribution : "
    f"{global_max:.4f}%"
)

print(
    f"Common Y-axis               : "
    f"0–{y_max:.4f}%"
)

print(
    f"Y-axis interval             : "
    f"{y_interval:.4f}%"
)

print()

print("OUTPUT FILES")
print("-" * 90)

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

print("=" * 90)
print("DONE")
print("=" * 90)