# ============================================================
# INDIA LIGHTNING–FATALITY DECOUPLING
# FINAL PUBLICATION-READY TWO-PANEL FIGURE
# ============================================================
# This script is designed specifically to avoid the overlaps
# visible in earlier versions:
#
# 1. Statistics box is fixed in the TOP-RIGHT of panel (a).
# 2. Median labels are kept away from the title.
# 3. Scatter IDs are automatically repelled from one another.
# 4. The quadrant legend is BELOW panel (a), not over the key.
# 5. The State/UT number key is BELOW BOTH PANELS.
# 6. The key is separated from the legend and footnotes.
# 7. Panel (b) labels/value annotations are given adequate room.
#
# INPUT:
#   D:\Articles\Working\India Lightning\Excel Files\
#       FFEI_State_Level_Final.xlsx
#
# OUTPUT:
#   D:\Articles\Working\India Lightning\Excel Files\
#       FFEI_Figure_Final_NoOverlap\
#
# ============================================================

import os
import sys
import subprocess
import importlib.util

# ------------------------------------------------------------
# Optional dependency:
# adjustText gives the best publication-quality label repulsion.
# If unavailable, the script installs it automatically.
# ------------------------------------------------------------
if importlib.util.find_spec("adjustText") is None:
    print("adjustText is not installed. Installing it...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "adjustText"]
    )

from adjustText import adjust_text

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.stats import pearsonr, spearmanr, linregress


# ============================================================
# 1. PATHS
# ============================================================

BASE_PATH = r"D:\Articles\Working\India Lightning\Excel Files\FFEI"

INPUT_FILE = os.path.join(
    BASE_PATH,
    "FFEI_State_Level_Final.xlsx"
)

OUTPUT_FOLDER = os.path.join(
    BASE_PATH,
    "FFEI"
)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ============================================================
# 2. INPUT COLUMN DETECTION
# ============================================================

STATE_CANDIDATES = [
    "State/UT",
    "State_UT",
    "State",
]

FLASH_CANDIDATES = [
    "Flash Density (flashes km⁻² yr⁻¹)",
    "Flash Density (flashes km-2 yr-1)",
    "Flash Density",
    "Flash_Density",
]

MORTALITY_CANDIDATES = [
    "Deaths per Million Population",
    "Mortality Rate (deaths million⁻¹ yr⁻¹)",
    "Mortality Rate",
    "Mortality",
    "Deaths_per_Million",
]

FFEI_CANDIDATES = [
    "FFEI (relative disparity ratio)",
    "FFEI",
    "FFEI_Value",
]

QUADRANT_CANDIDATES = [
    "Quadrant (Median Threshold)",
    "Risk Quadrant",
    "Quadrant",
]

ELIGIBLE_CANDIDATES = [
    "Primary_Analysis_Eligible",
    "Eligible",
]


def find_column(dataframe, candidates, required=True):
    """Return the first matching column from a candidate list."""
    for col in candidates:
        if col in dataframe.columns:
            return col

    if required:
        raise KeyError(
            "\nCould not find a required column.\n"
            f"Tried: {candidates}\n\n"
            "Available columns:\n"
            + "\n".join(map(str, dataframe.columns))
        )

    return None


# ============================================================
# 3. LOAD DATA
# ============================================================

print("\n" + "=" * 75)
print("LOADING FFEI STATE-LEVEL DATA")
print("=" * 75)

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"\nInput file not found:\n{INPUT_FILE}"
    )

df = pd.read_excel(INPUT_FILE)

state_col = find_column(df, STATE_CANDIDATES)
flash_col = find_column(df, FLASH_CANDIDATES)
mortality_col = find_column(df, MORTALITY_CANDIDATES)
ffei_col = find_column(df, FFEI_CANDIDATES)

quadrant_col = find_column(
    df,
    QUADRANT_CANDIDATES,
    required=False
)

eligible_col = find_column(
    df,
    ELIGIBLE_CANDIDATES,
    required=False
)

print(f"State column:       {state_col}")
print(f"Flash-density col:  {flash_col}")
print(f"Mortality col:      {mortality_col}")
print(f"FFEI column:        {ffei_col}")


# ============================================================
# 4. PRIMARY ANALYSIS FILTER
# ============================================================

plot_df = df.copy()

if eligible_col is not None:
    # Handle bool, 1/0, Yes/No safely.
    eligible_values = (
        plot_df[eligible_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    eligible_mask = eligible_values.isin(
        ["true", "1", "yes", "y"]
    )

    # If the column is genuinely boolean, this also works.
    if plot_df[eligible_col].dtype == bool:
        eligible_mask = plot_df[eligible_col]

    if eligible_mask.sum() >= 3:
        plot_df = plot_df.loc[
            eligible_mask
        ].copy()

# Numeric conversion
for col in [flash_col, mortality_col, ffei_col]:
    plot_df[col] = pd.to_numeric(
        plot_df[col],
        errors="coerce"
    )

plot_df = plot_df.dropna(
    subset=[
        state_col,
        flash_col,
        mortality_col,
        ffei_col
    ]
).copy()

plot_df = plot_df.reset_index(drop=True)

if len(plot_df) < 3:
    raise ValueError(
        "Fewer than three valid state/UT records remain."
    )


# ============================================================
# 5. REPRODUCIBLE STATE NUMBER KEY
# ============================================================
#
# IDs are alphabetical and independent of FFEI ranking.
# This guarantees that the same state always has the same
# number in panel (a).
# ============================================================

plot_df[state_col] = (
    plot_df[state_col]
    .astype(str)
    .str.strip()
)

plot_df = plot_df.sort_values(
    state_col,
    key=lambda s: s.str.lower()
).reset_index(drop=True)

plot_df["State_ID"] = np.arange(
    1,
    len(plot_df) + 1
)


# ============================================================
# 6. STATISTICS
# ============================================================

x = plot_df[flash_col].to_numpy(dtype=float)
y = plot_df[mortality_col].to_numpy(dtype=float)

pearson_r, pearson_p = pearsonr(x, y)
spearman_rho, spearman_p = spearmanr(x, y)
reg = linregress(x, y)
r_squared = reg.rvalue ** 2

median_flash = np.median(x)
median_mortality = np.median(y)


# ============================================================
# 7. QUADRANT CLASSIFICATION
# ============================================================

def classify_quadrant(row):
    high_flash = row[flash_col] >= median_flash
    high_death = row[mortality_col] >= median_mortality

    if high_flash and high_death:
        return "High Flash–High Death"
    if high_flash and not high_death:
        return "High Flash–Low Death"
    if not high_flash and high_death:
        return "Low Flash–High Death"
    return "Low Flash–Low Death"


if quadrant_col is None:
    plot_df["_Plot_Quadrant"] = plot_df.apply(
        classify_quadrant,
        axis=1
    )
    quadrant_col = "_Plot_Quadrant"
else:
    # Recalculate from the exact median thresholds used in this
    # figure. This prevents an old quadrant field from disagreeing
    # with the current plot.
    plot_df["_Plot_Quadrant"] = plot_df.apply(
        classify_quadrant,
        axis=1
    )
    quadrant_col = "_Plot_Quadrant"


# ============================================================
# 8. SOFT JOURNAL COLOURS
# ============================================================

COLORS = {
    "High Flash–High Death": "#D99090",
    "High Flash–Low Death": "#8FB7D8",
    "Low Flash–High Death": "#E6B66F",
    "Low Flash–Low Death": "#92C28D",
}


# ============================================================
# 9. FIGURE GEOMETRY
# ============================================================
#
# Large lower reserve is intentional:
#
#   y = 0.26–0.91  : two panels
#   y = 0.20–0.245 : quadrant legend
#   y = 0.065–0.18 : state number key
#   y = 0.015–0.05 : methodological note
#
# This prevents the legend/key collision seen previously.
# ============================================================

FIG_W = 19.0
FIG_H = 12.5

fig = plt.figure(
    figsize=(FIG_W, FIG_H),
    facecolor="white"
)

gs = fig.add_gridspec(
    nrows=1,
    ncols=2,
    left=0.055,
    right=0.985,
    top=0.905,
    bottom=0.295,
    width_ratios=[1.16, 1.0],
    wspace=0.28
)

ax_a = fig.add_subplot(gs[0, 0])
ax_b = fig.add_subplot(gs[0, 1])


# ============================================================
# 10. PANEL (a): SCATTER
# ============================================================

for quadrant, color in COLORS.items():

    sub = plot_df[
        plot_df[quadrant_col] == quadrant
    ]

    if sub.empty:
        continue

    ax_a.scatter(
        sub[flash_col],
        sub[mortality_col],
        s=82,
        color=color,
        edgecolor="black",
        linewidth=0.65,
        alpha=0.95,
        zorder=4
    )


# ============================================================
# 11. PANEL (a): THRESHOLDS
# ============================================================

ax_a.axvline(
    median_flash,
    color="0.42",
    linestyle="--",
    linewidth=1.0,
    zorder=2
)

ax_a.axhline(
    median_mortality,
    color="0.42",
    linestyle="--",
    linewidth=1.0,
    zorder=2
)


# ============================================================
# 12. PANEL (a): REGRESSION
# ============================================================

x_line = np.linspace(
    x.min(),
    x.max(),
    400
)

y_line = (
    reg.intercept
    +
    reg.slope * x_line
)

ax_a.plot(
    x_line,
    y_line,
    color="black",
    linewidth=1.15,
    zorder=3
)


# ============================================================
# 13. PANEL (a): STATE IDS WITH AUTOMATIC REPULSION
# ============================================================
#
# This is the critical part.
#
# IDs are initially placed at the data points, then adjustText
# moves them apart while keeping them close to their points.
# Arrows are deliberately disabled unless movement is large.
# ============================================================

texts = []

for _, row in plot_df.iterrows():

    txt = ax_a.text(
        row[flash_col],
        row[mortality_col],
        f"{int(row['State_ID']):02d}",
        fontsize=9.5,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=10,
        bbox=dict(
            boxstyle="round,pad=0.10",
            facecolor="white",
            edgecolor="none",
            alpha=0.82
        )
    )

    texts.append(txt)


# First draw establishes the renderer.
fig.canvas.draw()

# Repel labels from each other and from data points.
adjust_text(
    texts,
    ax=ax_a,
    x=x,
    y=y,
    expand_text=(1.35, 1.45),
    expand_points=(1.25, 1.35),
    force_text=(0.55, 0.75),
    force_static=(0.40, 0.55),
    force_pull=(0.08, 0.12),
    force_explode=(0.30, 0.45),
    max_move=(14, 14),
    only_move={
        "text": "xy",
        "static": "xy",
        "explode": "xy",
        "pull": "xy",
    },
    ensure_inside_axes=True,
    prevent_crossings=True,
    arrowprops=dict(
        arrowstyle="-",
        color="0.35",
        lw=0.45,
        alpha=0.60
    )
)


# ============================================================
# 14. PANEL (a): AXES AND TITLE
# ============================================================

ax_a.set_xlabel(
    "Flash density "
    "(flashes km$^{-2}$ yr$^{-1}$)",
    fontsize=15.0,
    labelpad=7
)

ax_a.set_ylabel(
    "Lightning mortality "
    "(deaths million$^{-1}$ yr$^{-1}$)",
    fontsize=15.0,
    labelpad=8
)

ax_a.set_title(
    "(a) Lightning hazard–mortality relationship",
    loc="left",
    fontsize=17.0,
    fontweight="bold",
    pad=8
)

ax_a.grid(
    alpha=0.16,
    linewidth=0.65
)


# ============================================================
# 15. PANEL (a): STATISTICS — FIXED TOP RIGHT
# ============================================================

stats_text = (
    f"N = {len(plot_df)}\n"
    f"Pearson r = {pearson_r:.3f}, p = {pearson_p:.3f}\n"
    f"Spearman ρ = {spearman_rho:.3f}, p = {spearman_p:.3f}\n"
    f"R² = {r_squared:.3f}"
)

ax_a.text(
    0.965,
    0.965,
    stats_text,
    transform=ax_a.transAxes,
    ha="right",
    va="top",
    fontsize=12.0,
    linespacing=1.35,
    bbox=dict(
        boxstyle="round,pad=0.42",
        facecolor="white",
        edgecolor="0.62",
        linewidth=0.8,
        alpha=0.94
    ),
    zorder=30
)


# ============================================================
# 16. PANEL (a): THRESHOLD LABELS
# ============================================================
#
# IMPORTANT:
# Do NOT put the median flash label at y=top where it collides
# with the title. Instead place it just above the vertical line,
# inside the axes but below the title.
# ============================================================

y_top = ax_a.get_ylim()[1]
x_right = ax_a.get_xlim()[1]

ax_a.text(
    median_flash,
    y_top * 0.985,
    f"Median flash density = {median_flash:.3f}",
    ha="center",
    va="top",
    fontsize=10.5,
    color="0.30",
    bbox=dict(
        boxstyle="round,pad=0.16",
        facecolor="white",
        edgecolor="none",
        alpha=0.78
    ),
    zorder=15
)

ax_a.text(
    x_right * 0.995,
    median_mortality,
    f"Median mortality = {median_mortality:.3f}",
    ha="right",
    va="bottom",
    fontsize=10.5,
    color="0.30",
    bbox=dict(
        boxstyle="round,pad=0.16",
        facecolor="white",
        edgecolor="none",
        alpha=0.78
    ),
    zorder=15
)


# ============================================================
# 17. PANEL (b): FFEI BAR CHART
# ============================================================

ffei_plot = plot_df.sort_values(
    ffei_col,
    ascending=True
).copy()

y_positions = np.arange(
    len(ffei_plot)
)

bar_colors = [
    COLORS[q]
    for q in ffei_plot[quadrant_col]
]

bars = ax_b.barh(
    y_positions,
    ffei_plot[ffei_col],
    color=bar_colors,
    edgecolor="black",
    linewidth=0.35,
    alpha=0.95,
    zorder=3
)


# ============================================================
# 18. PANEL (b): STATE NAMES
# ============================================================

ax_b.set_yticks(y_positions)

ax_b.set_yticklabels(
    ffei_plot[state_col],
    fontsize=10.5
)


# ============================================================
# 19. PANEL (b): FFEI VALUES
# ============================================================

max_ffei = float(
    ffei_plot[ffei_col].max()
)

value_pad = max(
    max_ffei * 0.012,
    0.03
)

for ypos, (_, row) in zip(
    y_positions,
    ffei_plot.iterrows()
):

    ax_b.text(
        row[ffei_col] + value_pad,
        ypos,
        f"{row[ffei_col]:.2f}",
        ha="left",
        va="center",
        fontsize=9.5,
        zorder=10
    )


# ============================================================
# 20. PANEL (b): AXES AND TITLE
# ============================================================

ax_b.set_xlabel(
    "FFEI (mortality rate / flash density)",
    fontsize=15.0,
    labelpad=7
)

ax_b.set_title(
    "(b) Flash–Fatality Disparity Index (FFEI)",
    loc="left",
    fontsize=17.0,
    fontweight="bold",
    pad=8
)

ax_b.grid(
    axis="x",
    alpha=0.16,
    linewidth=0.65
)

ax_b.set_axisbelow(True)

ax_b.set_xlim(
    0,
    max_ffei * 1.16
)


# ============================================================
# 21. PANEL (a): QUADRANT LEGEND UNDER STATISTICS BOX
# ============================================================
# The quadrant legend is placed inside panel (a), directly below
# the statistics box in the upper-right corner.
# ============================================================

legend_handles = [
    Patch(
        facecolor=COLORS[q],
        edgecolor="black",
        linewidth=0.45,
        label=q
    )
    for q in COLORS
]

ax_a.legend(
    handles=legend_handles,
    loc="upper right",
    bbox_to_anchor=(0.965, 0.735),
    ncol=2,
    frameon=True,
    fancybox=True,
    framealpha=0.92,
    edgecolor="0.70",
    facecolor="white",
    fontsize=10.5,
    handlelength=1.25,
    handletextpad=0.40,
    columnspacing=0.85,
    borderpad=0.45,
    labelspacing=0.45
)


# ============================================================
# 22. PANEL (b): EXPLANATORY BOX — BOTTOM RIGHT
# ============================================================
# The FFEI definition is deliberately moved to the bottom-right
# corner of panel (b), leaving the upper-right area uncluttered.
# ============================================================

ax_b.text(
    0.985,
    0.035,
    (
        "FFEI = mortality rate / flash density\n"
        "Higher values = greater fatality relative to\n"
        "observed flash density"
    ),
    transform=ax_b.transAxes,
    ha="right",
    va="bottom",
    fontsize=10.5,
    linespacing=1.25,
    bbox=dict(
        boxstyle="round,pad=0.40",
        facecolor="white",
        edgecolor="0.62",
        linewidth=0.8,
        alpha=0.94
    ),
    zorder=30
)


# ============================================================
# 23. STATE / UT NUMBER KEY
# ============================================================
#
# FOUR columns x EIGHT rows.
# The key occupies a dedicated bottom band, separated from both panels.
# ============================================================

state_key = [
    f"{int(row['State_ID']):02d}  {row[state_col]}"
    for _, row in plot_df.iterrows()
]

n_states = len(state_key)
n_cols = 4
rows_per_col = int(
    np.ceil(n_states / n_cols)
)

key_columns = []

for i in range(n_cols):
    start = i * rows_per_col
    end = min(
        start + rows_per_col,
        n_states
    )
    key_columns.append(
        state_key[start:end]
    )


# Heading
fig.text(
    0.72,
    0.198,
    "State / UT number key",
    ha="center",
    va="bottom",
    fontsize=12.0,
    fontweight="bold"
)


# Four columns
key_x = [
    0.055,
    0.285,
    0.515,
    0.745
]

for xpos, entries in zip(
    key_x,
    key_columns
):

    fig.text(
        xpos,
        0.184,
        "\n".join(entries),
        ha="left",
        va="top",
        fontsize=10.0,
        family="DejaVu Sans Mono",
        linespacing=1.35
    )


# ============================================================
# 24. FOOTNOTE — SEPARATE FROM KEY
# ============================================================

fig.text(
    0.055,
    0.048,
    (
        "Common analysis period: 2000–2014 & 2018–2022 (20 years)   |   "
        "Mortality coverage threshold: ≥15 of 20 years   |   "
        f"Eligible states/UTs: {len(plot_df)}"
    ),
    ha="left",
    va="bottom",
    fontsize=9.5
)

fig.text(
    0.055,
    0.024,
    (
        "Flash density = flashes km$^{-2}$ yr$^{-1}$   |   "
        "Mortality rate = deaths million$^{-1}$ yr$^{-1}$   |   "
        "FFEI = mortality rate / flash density"
    ),
    ha="left",
    va="bottom",
    fontsize=9.5
)


# ============================================================
# 25. SAVE
# ============================================================

TIFF_FILE = os.path.join(
    OUTPUT_FOLDER,
    "Flash_Mortality_Decoupling_FFEI.tif"
)

fig.savefig(
    TIFF_FILE,
    dpi=600,
    bbox_inches="tight",
    pad_inches=0.08
)

# ============================================================
# 26. EXPORT KEY AND STATISTICS
# ============================================================

plot_df[
    ["State_ID", state_col]
].to_excel(
    os.path.join(
        OUTPUT_FOLDER,
        "State_Number_Key.xlsx"
    ),
    index=False
)

pd.DataFrame(
    [{
        "N": len(plot_df),
        "Pearson_r": pearson_r,
        "Pearson_p": pearson_p,
        "Spearman_rho": spearman_rho,
        "Spearman_p": spearman_p,
        "R_squared": r_squared,
        "Median_Flash_Density": median_flash,
        "Median_Mortality": median_mortality
    }]
).to_excel(
    os.path.join(
        OUTPUT_FOLDER,
        "Figure_Statistics.xlsx"
    ),
    index=False
)


# ============================================================
# 27. CONSOLE REPORT
# ============================================================

print("\n" + "=" * 75)
print("FINAL FIGURE CREATED — NO-OVERLAP LAYOUT")
print("=" * 75)

print(f"\nN = {len(plot_df)}")
print(
    f"Pearson r = {pearson_r:.4f}, "
    f"p = {pearson_p:.4f}"
)
print(
    f"Spearman rho = {spearman_rho:.4f}, "
    f"p = {spearman_p:.4f}"
)
print(f"R² = {r_squared:.4f}")

print(
    f"\nMedian flash density = {median_flash:.6f}"
)
print(
    f"Median mortality = {median_mortality:.6f}"
)

print(
    f"\nOutput folder:\n{OUTPUT_FOLDER}"
)

print("\nCreated:")
print("  1. 600-dpi TIFF")
print("  2. State-number key XLSX")
print("  3. Figure statistics XLSX")

print("\nFinished.")


plt.show()
plt.close(fig)
