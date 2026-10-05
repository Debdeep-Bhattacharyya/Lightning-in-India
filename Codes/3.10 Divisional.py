# ============================================================
# INDIA LIGHTNING–DEATH ANALYSIS
# TRMM LIS + ISS LIS
# 2000–2022
#
# STYLE MATCHED TO REFERENCE FIGURE:
#   - Per-panel legend box (top-left of each subplot)
#   - Centered bold navy panel titles
#   - Blue / red axis labels + ticks
#   - Bottom row = two separate horizontal bar charts
#     (Flash % | Death %) + a color-key legend box
#
# OUTPUT:
#   1. PNG  – 600 dpi
#   2. TIFF – 600 dpi
#   3. XLSX – analytical tables
#
# NO PDF
# NO plt.show()
# WHITE BACKGROUND
#
# ------------------------------------------------------------
# FIX LOG (state-matching):
#   1. "Total" (and similar footer/summary rows) is now dropped
#      from the death data before any matching happens.
#   2. Added explicit corrections for Chhattisgarh, Lakshadweep,
#      and the pre-2020 split UTs "Dadra and Nagar Haveli" /
#      "Daman and Diu" (both now map to the merged UT name used
#      in the lightning data).
#   3. Added a normalization + difflib fallback pass: anything
#      still unmatched after the manual dictionary is compared
#      (ignoring case/punctuation/"and"/"&"/"islands"/"state")
#      against the lightning STNAME_SH values, and the closest
#      candidate is printed so you can add it to the dictionary
#      with confidence instead of guessing.
# ------------------------------------------------------------
# ============================================================


# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

import re
import difflib

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from matplotlib.patches import Patch
from matplotlib.lines import Line2D


# ============================================================
# 2. INPUT / OUTPUT PATHS
# ============================================================

LIGHTNING_DIR = Path(
    r"D:\Articles\Working\Lightning India\Data\Lightning\3_Grid_Assigned"
)

DEATH_DIR = Path(
    r"D:\Articles\Working\Lightning India\Data\Death Data"
)

OUTPUT_DIR = Path(
    r"D:\Articles\Working\Lightning India\Data\Division Analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. YEARS
# ============================================================

YEARS = list(range(2000, 2023))


# ============================================================
# 4. GLOBAL PLOT SETTINGS
# ============================================================

plt.rcParams.update({

    "font.family": "DejaVu Sans",
    "font.size": 18,

    "axes.labelsize": 22,
    "axes.titlesize": 26,
    "axes.linewidth": 1.6,

    "xtick.labelsize": 16,
    "ytick.labelsize": 17,

    "legend.fontsize": 15,

    "savefig.dpi": 600
})


# ============================================================
# 5. READ LIGHTNING DATA
# ============================================================

print("\n")
print("=" * 70)
print("READING LIGHTNING DATA")
print("=" * 70)


lightning_list = []


for year in YEARS:

    file = LIGHTNING_DIR / f"{year}_Grid.csv"

    if not file.exists():
        print(f"WARNING: Lightning file not found: {file}")
        continue

    print(f"Reading lightning data: {year}")

    df = pd.read_csv(file, low_memory=False)

    required_columns = ["Year", "STNAME_SH", "Division"]

    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        print(f"WARNING: {year} missing columns: {missing}")
        continue

    df["STNAME_SH"] = (
        df["STNAME_SH"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    df["Division"] = (
        df["Division"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    lightning_list.append(df[["Year", "STNAME_SH", "Division"]])


# ============================================================
# 6. COMBINE LIGHTNING DATA
# ============================================================

if len(lightning_list) == 0:
    raise FileNotFoundError("No lightning files were found.")

lightning_all = pd.concat(lightning_list, ignore_index=True)

print("\nTotal lightning records:", f"{len(lightning_all):,}")


# ============================================================
# 7. STATE → DIVISION RELATIONSHIP
# ============================================================

state_division = (
    lightning_all[["STNAME_SH", "Division"]]
    .drop_duplicates()
    .sort_values(["STNAME_SH", "Division"])
)


# ============================================================
# 8. CHECK MULTIPLE DIVISION ASSIGNMENTS
# ============================================================

state_division_check = (
    state_division.groupby("STNAME_SH")["Division"].nunique()
)

multiple_divisions = state_division_check[state_division_check > 1]

if len(multiple_divisions) > 0:
    print("\nWARNING:")
    print("Some states are associated with multiple divisions.")
    print(
        state_division[
            state_division["STNAME_SH"].isin(multiple_divisions.index)
        ].to_string(index=False)
    )


# ============================================================
# 9. DIVISION-WISE FLASH COUNT
# ============================================================

flash_division = (
    lightning_all.groupby(["Year", "Division"]).size().reset_index(name="Flashes")
)


# ============================================================
# 10. READ DEATH DATA
# ============================================================

print("\n")
print("=" * 70)
print("READING DEATH DATA")
print("=" * 70)

# ------------------------------------------------------------
# FIX 1: rows that are footer/summary rows, not real states/UTs.
# These get dropped immediately on read so they never reach the
# matching step (this is what produced the "Total" entry in
# your unmatched list).
# ------------------------------------------------------------
AGGREGATE_ROWS = {
    "total", "all india", "india", "grand total",
    "total (state)", "total (ut)", "total state", "total ut",
}

death_list = []


for year in YEARS:

    file = DEATH_DIR / f"Death_{year}.csv"

    if not file.exists():
        print(f"WARNING: Death file not found: {file}")
        continue

    print(f"Reading death data: {year}")

    df = pd.read_csv(file, low_memory=False)

    required_columns = ["State/UT", "Total"]

    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        print(f"WARNING: {year} missing columns: {missing}")
        continue

    df["State/UT"] = (
        df["State/UT"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # Drop footer/summary rows (case-insensitive match)
    before_rows = len(df)
    df = df[~df["State/UT"].str.lower().isin(AGGREGATE_ROWS)]
    dropped = before_rows - len(df)
    if dropped > 0:
        print(f"   Dropped {dropped} aggregate/footer row(s) (e.g. 'Total') for {year}")

    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)

    df["Year"] = year

    death_list.append(df[["Year", "State/UT", "Total"]])


# ============================================================
# 11. COMBINE DEATH DATA
# ============================================================

if len(death_list) == 0:
    raise FileNotFoundError("No death files were found.")

deaths_all = pd.concat(death_list, ignore_index=True)


# ============================================================
# 12. STATE NAME STANDARDIZATION
# ============================================================

# ------------------------------------------------------------
# FIX 2: expanded dictionary.
#   - Chhattisgarh / Lakshadweep added explicitly (common source
#     of a silent no-op if the death-data spelling differs even
#     slightly from the lightning STNAME_SH spelling).
#   - Pre-2020 split UTs "Dadra and Nagar Haveli" and
#     "Daman and Diu" both now map onto the same merged UT name
#     used after the 2020 merger, matching what the lightning
#     data (post-merger STNAME_SH) will contain.
# ------------------------------------------------------------
state_name_corrections = {
    "Andaman and Nicobar Islands": "Andaman & Nicobar",
    "Andaman & Nicobar Islands": "Andaman & Nicobar",
    "Dadra and Nagar Haveli and Daman and Diu": "Dadra & Nagar Haveli and Daman & Diu",
    "Dadra and Nagar Haveli": "Dadra & Nagar Haveli and Daman & Diu",
    "Daman and Diu": "Dadra & Nagar Haveli and Daman & Diu",
    "Jammu and Kashmir": "Jammu & Kashmir",
    "NCT of Delhi": "Delhi",
    "Delhi UT": "Delhi",
    "Orissa": "Odisha",
    "Pondicherry": "Puducherry",
    "Pondicherry (UT)": "Puducherry",
    "Uttaranchal": "Uttarakhand",
    # Lightning data spells this with an extra "h" -> "Chhattishgarh"
    "Chhattisgarh": "Chhattishgarh",
    "Chattisgarh": "Chhattishgarh",
}

deaths_all["State_Match"] = (
    deaths_all["State/UT"]
    .replace(state_name_corrections)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# ------------------------------------------------------------
# MANUAL DIVISION OVERRIDE
#
# Some states/UTs (e.g. Lakshadweep) have zero grid cells in the
# LIS lightning files, so no amount of name-matching will find
# them there. For these, assign the Division directly by hand
# instead of relying on the lightning-side lookup.
#
# EDIT THIS: set the correct Division name for Lakshadweep to
# match one of the four Division names printed in section 17
# ("DIVISIONS IDENTIFIED"). Lakshadweep is geographically closest
# to Kerala, so it should take on whichever Division Kerala is in.
# ------------------------------------------------------------
MANUAL_DIVISION_OVERRIDE = {
    "Lakshadweep": "REPLACE_WITH_KERALA_DIVISION_NAME",
}

# Fail fast and loud if the placeholder above was never edited, instead
# of silently producing a broken 5th "division" and empty panel (d).
for _state, _division in MANUAL_DIVISION_OVERRIDE.items():
    if _division.startswith("REPLACE_WITH"):
        raise ValueError(
            f"MANUAL_DIVISION_OVERRIDE for '{_state}' is still set to the "
            f"placeholder '{_division}'. Edit this dictionary near the top "
            f"of the script and set it to one of your actual Division names "
            f"(e.g. 'Southern India') before running."
        )


# ============================================================
# 12b. NORMALIZED FALLBACK MATCH (FIX 3)
#
# For anything the manual dictionary doesn't catch, try a
# normalized comparison against the lightning STNAME_SH values
# (case-insensitive, "&"->"and", punctuation stripped, and
# common filler words like "islands"/"state"/"ut" removed).
# If a normalized match is found, use the lightning-side name
# so the later merge succeeds automatically.
# ============================================================

def normalize_name(name):
    s = str(name).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\b(islands?|state|ut|of)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

lightning_states = state_division["STNAME_SH"].unique().tolist()
lightning_norm_map = {normalize_name(s): s for s in lightning_states}

def resolve_unmatched(name):
    norm = normalize_name(name)
    if norm in lightning_norm_map:
        return lightning_norm_map[norm]
    return name  # leave unchanged; will show up as unmatched below

still_needs_check = ~deaths_all["State_Match"].isin(lightning_states)
deaths_all.loc[still_needs_check, "State_Match"] = (
    deaths_all.loc[still_needs_check, "State_Match"].apply(resolve_unmatched)
)


# ============================================================
# 13. MERGE DEATH DATA WITH DIVISION
# ============================================================

deaths_division = deaths_all.merge(
    state_division.rename(columns={"STNAME_SH": "State_Match"}),
    on="State_Match",
    how="left"
)

# Apply manual overrides for states/UTs with no lightning-grid rows
for state_name, division_name in MANUAL_DIVISION_OVERRIDE.items():
    mask = (
        deaths_division["Division"].isna()
        & (deaths_division["State/UT"] == state_name)
    )
    deaths_division.loc[mask, "Division"] = division_name


# ============================================================
# 14. FIND UNMATCHED STATES
# ============================================================

unmatched = (
    deaths_division[deaths_division["Division"].isna()]["State/UT"]
    .drop_duplicates()
    .sort_values()
)

print("\n")
print("=" * 70)
print("STATE MATCHING")
print("=" * 70)

if len(unmatched) == 0:
    print("All death records successfully matched to divisions.")
else:
    print("Unmatched states/UTs:")
    for state in unmatched:
        # Suggest the closest lightning-side name using difflib,
        # so you can decide whether to add a dictionary entry.
        candidates = difflib.get_close_matches(
            normalize_name(state), lightning_norm_map.keys(), n=1, cutoff=0.5
        )
        if candidates:
            suggestion = lightning_norm_map[candidates[0]]
            print(f"    {state}  -->  closest lightning match: '{suggestion}' "
                  f"(add to state_name_corrections if correct)")
        else:
            print(f"    {state}  -->  no close match found in lightning data "
                  f"(this state/UT may genuinely be absent from the LIS grid)")


# ============================================================
# 15. DIVISION-WISE DEATH TOTAL
# ============================================================

deaths_division_agg = (
    deaths_division.dropna(subset=["Division"])
    .groupby(["Year", "Division"])["Total"]
    .sum()
    .reset_index(name="Deaths")
)


# ============================================================
# 16. MERGE FLASHES AND DEATHS
# ============================================================

division_data = pd.merge(
    flash_division,
    deaths_division_agg,
    on=["Year", "Division"],
    how="outer"
)

division_data["Flashes"] = division_data["Flashes"].fillna(0).astype(int)
division_data["Deaths"] = division_data["Deaths"].fillna(0).astype(int)


# ============================================================
# 17. IDENTIFY DIVISIONS
# ============================================================

divisions = sorted(division_data["Division"].dropna().unique())

print("\n")
print("=" * 70)
print("DIVISIONS IDENTIFIED")
print("=" * 70)

for division in divisions:
    print("   ", division)

if len(divisions) != 4:
    print("\nWARNING:")
    print(f"{len(divisions)} divisions were found.")
    print("The figure is configured for the four Indian divisions.")


# ============================================================
# 18. COMPLETE ANNUAL SERIES
# ============================================================

complete_data = []

for division in divisions:

    temp = (
        division_data[division_data["Division"] == division]
        .set_index("Year")
        .reindex(YEARS)
        .fillna(0)
        .reset_index()
    )

    temp["Division"] = division

    complete_data.append(temp[["Year", "Division", "Flashes", "Deaths"]])

division_data_complete = pd.concat(complete_data, ignore_index=True)


# ============================================================
# 19. DIVISION TOTALS
# ============================================================

division_totals = (
    division_data_complete.groupby("Division")
    .agg(Flashes=("Flashes", "sum"), Deaths=("Deaths", "sum"))
    .reset_index()
)


# ============================================================
# 20. PERCENTAGE CONTRIBUTION
# ============================================================

total_flashes = division_totals["Flashes"].sum()
total_deaths = division_totals["Deaths"].sum()

division_totals["Flash_Percent"] = division_totals["Flashes"] / total_flashes * 100
division_totals["Death_Percent"] = division_totals["Deaths"] / total_deaths * 100


# ============================================================
# 21. MORTALITY DISPROPORTIONALITY INDEX
# ============================================================

division_totals["Mortality_Disproportionality"] = (
    division_totals["Death_Percent"] / division_totals["Flash_Percent"]
)


# ============================================================
# 22. PEAK YEARS
# ============================================================

peak_records = []

for division in divisions:

    temp = division_data_complete[division_data_complete["Division"] == division]

    flash_peak = temp.loc[temp["Flashes"].idxmax()]
    death_peak = temp.loc[temp["Deaths"].idxmax()]

    peak_records.append({
        "Division": division,
        "Peak_Flash_Year": int(flash_peak["Year"]),
        "Peak_Flashes": int(flash_peak["Flashes"]),
        "Peak_Death_Year": int(death_peak["Year"]),
        "Peak_Deaths": int(death_peak["Deaths"])
    })

peak_data = pd.DataFrame(peak_records)


# ============================================================
# 23. SAVE EXCEL WORKBOOK
# ============================================================

excel_file = OUTPUT_DIR / "Lightning_Deaths_Division_Analysis_2000_2022.xlsx"

with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:

    division_data_complete.to_excel(writer, sheet_name="Annual_Data", index=False)
    division_totals.to_excel(writer, sheet_name="Division_Totals", index=False)
    peak_data.to_excel(writer, sheet_name="Peak_Years", index=False)
    state_division.to_excel(writer, sheet_name="State_Division", index=False)
    unmatched.to_frame(name="Unmatched_State").to_excel(
        writer, sheet_name="Unmatched_States", index=False
    )

print("\nExcel file saved:")
print(excel_file)


# ============================================================
# 23b. DIVISION SUMMARY TABLE (Area / Population / Derived Metrics) -> CSV
#
# Area and population are static reference facts for your division
# scheme, so they're hardcoded here. EDIT THESE VALUES if your
# division boundaries change. Flashes/Deaths come straight from
# division_totals (the real, current run's results), so the
# derived columns always reflect your latest data.
#
# Division names below MUST exactly match the Division names in
# division_totals (see "DIVISIONS IDENTIFIED" in the console output).
# ============================================================

DIVISION_REFERENCE = {
    "Central India":    {"Area_km2": 1_103_483, "Population": 313_547_206},
    "North East India": {"Area_km2":   524_808, "Population": 274_001_941},
    "North West India": {"Area_km2":   889_872, "Population": 368_791_165},
    "Southern India":   {"Area_km2":   648_218, "Population": 254_380_626},
}

summary_rows = []

for _, row in division_totals.iterrows():

    division = row["Division"]

    if division not in DIVISION_REFERENCE:
        print(f"WARNING: No Area/Population reference for '{division}' "
              f"- add it to DIVISION_REFERENCE to include it in the summary table.")
        continue

    area_km2 = DIVISION_REFERENCE[division]["Area_km2"]
    population = DIVISION_REFERENCE[division]["Population"]

    flashes = row["Flashes"]
    deaths = row["Deaths"]

    population_density = population / area_km2
    flashes_per_area = flashes / area_km2
    flashes_per_million_pop = flashes / (population / 1_000_000)
    deaths_per_million_pop = deaths / (population / 1_000_000)
    deaths_per_area = deaths / area_km2

    summary_rows.append({
        "Division": division,
        "Area (km2)": area_km2,
        "Total Population": population,
        "Population Density (per sq. km)": round(population_density, 2),
        "Total Flash Events Count": int(flashes),
        "Deaths": int(deaths),
        "Flashes per area": round(flashes_per_area, 2),
        "Flashes per million population": round(flashes_per_million_pop, 2),
        "Deaths per million population": round(deaths_per_million_pop, 2),
        "Death per Area": round(deaths_per_area, 2),
    })

division_summary_table = pd.DataFrame(summary_rows)

summary_csv_file = OUTPUT_DIR / "Division_Summary_Metrics_2000_2022.csv"
division_summary_table.to_csv(summary_csv_file, index=False)

print("\nDivision summary CSV saved:")
print(summary_csv_file)


# ============================================================
# 24. COLOURS  (matched to reference figure)
# ============================================================

FLASH_NORMAL = "royalblue"     # bright blue bars
FLASH_MAX = "#FF9900"          # orange highlight bar
DEATH_RED = "red"              # death line
DEATH_MAX = "#7F0000"          # dark red highlight dot
AXIS_BLUE = "navy"             # left axis text
GRID_GREY = "#BDBDBD"
TITLE_NAVY = "navy"


# ============================================================
# 25. CREATE LARGE FIGURE
# ============================================================

fig = plt.figure(figsize=(20, 22), facecolor="white")


# ============================================================
# 26. GRID LAYOUT
#
# 3 rows:
#   Row 1 = Division 1 + Division 2
#   Row 2 = Division 3 + Division 4
#   Row 3 = Flash % chart | Death % chart | legend key
# ============================================================

gs = fig.add_gridspec(
    nrows=3,
    ncols=2,
    height_ratios=[1.0, 1.0, 0.62],
    hspace=0.55,
    wspace=0.30,
    left=0.06,
    right=0.965,
    top=0.965,
    bottom=0.06
)


# ============================================================
# 27. FOUR DUAL-AXIS PANELS
#
# All four panels share the SAME y-axis scale (flash axis and
# death axis each use a common global max) so that (a)-(d) are
# directly comparable. No per-panel legends — a single shared
# legend is rendered once, in the bottom-right legend box.
# ============================================================

panel_labels = ["(a)", "(b)", "(c)", "(d)"]

# --------------------------------------------------------
# Global axis limits (same scale across all four panels)
# --------------------------------------------------------

global_max_flash = division_data_complete["Flashes"].max()
global_max_death = division_data_complete["Deaths"].max()

flash_ylim = (0, global_max_flash * 1.08)
death_ylim = (0, global_max_death * 1.15)

for i, division in enumerate(divisions[:4]):

    row = i // 2
    col = i % 2

    ax1 = fig.add_subplot(gs[row, col])

    temp = (
        division_data_complete[division_data_complete["Division"] == division]
        .sort_values("Year")
    )

    max_flash_idx = temp["Flashes"].idxmax()
    max_flash_year = int(temp.loc[max_flash_idx, "Year"])

    max_death_idx = temp["Deaths"].idxmax()
    max_death_year = int(temp.loc[max_death_idx, "Year"])

    bar_colors = [
        FLASH_MAX if year == max_flash_year else FLASH_NORMAL
        for year in temp["Year"]
    ]

    # -------------------- FLASH BARS --------------------
    ax1.bar(
        temp["Year"], temp["Flashes"],
        width=0.72, color=bar_colors,
        edgecolor="black", linewidth=0.4,
        alpha=0.92, zorder=2
    )

    # -------------------- TITLE (division name, black) --------------------
    ax1.set_title(division, fontsize=24, fontweight="bold", color="black", pad=12)

    # -------------------- PANEL LABEL (a)/(b)/(c)/(d) --------------------
    ax1.text(
        0.02, 1.10, panel_labels[i],
        transform=ax1.transAxes,
        fontsize=20, fontweight="bold", color="black",
        ha="left", va="top"
    )

    # -------------------- LEFT AXIS LABEL (black) — SAME SCALE FOR ALL --------------------
    ax1.set_ylabel("Lightning Flashes (Events)", fontsize=17, fontweight="bold",
                    color="black", labelpad=10)
    ax1.tick_params(axis="y", labelsize=15, colors=AXIS_BLUE, width=1.4, length=6)
    ax1.set_ylim(flash_ylim)

    ax1.set_xlabel("Year", fontsize=18, fontweight="bold", color="black", labelpad=10)
    ax1.set_xticks(YEARS)
    ax1.set_xticklabels(YEARS, rotation=45, ha="right", fontsize=13)
    ax1.tick_params(axis="x", labelsize=13, width=1.3, length=6)

    ax1.grid(axis="y", linestyle="--", linewidth=0.8, color=GRID_GREY, alpha=0.5, zorder=1)

    # -------------------- SECONDARY AXIS --------------------
    ax2 = ax1.twinx()

    ax2.plot(
        temp["Year"], temp["Deaths"],
        color=DEATH_RED, linewidth=3.0,
        marker="o", markersize=7,
        markerfacecolor=DEATH_RED, markeredgecolor="white",
        markeredgewidth=1.0, zorder=10
    )

    ax2.scatter(
        [max_death_year],
        [temp.loc[max_death_idx, "Deaths"]],
        s=190, color=DEATH_MAX, edgecolor="black", linewidth=1.3, zorder=20
    )

    ax2.set_ylabel("Total Deaths", fontsize=17, fontweight="bold",
                    color="black", labelpad=12)
    ax2.tick_params(axis="y", labelsize=15, colors=DEATH_RED, width=1.4, length=6)
    ax2.set_ylim(death_ylim)

    for spine in ax1.spines.values():
        spine.set_linewidth(1.5)
    for spine in ax2.spines.values():
        spine.set_linewidth(1.5)

    ax1.set_facecolor("white")
    ax2.set_facecolor("white")


# ============================================================
# 28. BOTTOM ROW — TWO SEPARATE CONTRIBUTION CHARTS + LEGEND KEY
# ============================================================

# Sub-gridspec: [flash chart | death chart | legend key]
gs_bottom = gs[2, :].subgridspec(1, 3, width_ratios=[1.0, 1.0, 0.42], wspace=0.15)

ax_flash = fig.add_subplot(gs_bottom[0, 0])
ax_death = fig.add_subplot(gs_bottom[0, 1])
ax_key = fig.add_subplot(gs_bottom[0, 2])
ax_key.axis("off")

bottom_data = division_totals.sort_values("Flash_Percent", ascending=True).copy()
y = np.arange(len(bottom_data))

# -------------------- FLASH CONTRIBUTION (left) --------------------
ax_flash.barh(
    y, bottom_data["Flash_Percent"],
    height=0.55, color=FLASH_NORMAL, edgecolor="black", linewidth=0.5
)

ax_flash.set_yticks(y)
ax_flash.set_yticklabels(bottom_data["Division"], fontsize=17, fontweight="bold", color="black")
ax_flash.set_xlim(0, 100)
ax_flash.set_xlabel("Contribution (%)", fontsize=18, fontweight="bold", color="black")
ax_flash.set_title("Lightning Flash Contribution to India Total (2000–2022)",
                    fontsize=16, fontweight="bold", color="black", pad=10)
ax_flash.tick_params(axis="x", labelsize=13, colors=AXIS_BLUE)
ax_flash.tick_params(axis="y", length=0)
ax_flash.grid(axis="x", linestyle="--", linewidth=0.7, color=GRID_GREY, alpha=0.5)
ax_flash.set_axisbelow(True)

ax_flash.text(
    0.02, 1.18, "(e)",
    transform=ax_flash.transAxes,
    fontsize=20, fontweight="bold", color="black",
    ha="left", va="top"
)

for yi, val in zip(y, bottom_data["Flash_Percent"]):
    ax_flash.text(val + 1.5, yi, f"{val:.1f}%", ha="left", va="center",
                   fontsize=15, fontweight="bold", color=AXIS_BLUE)

for spine in ax_flash.spines.values():
    spine.set_linewidth(1.5)

# -------------------- DEATH CONTRIBUTION (right) --------------------
ax_death.barh(
    y, bottom_data["Death_Percent"],
    height=0.55, color=DEATH_RED, edgecolor="black", linewidth=0.5
)

ax_death.set_yticks(y)
ax_death.set_yticklabels([])  # divisions already shown on left chart
ax_death.set_xlim(0, 100)
ax_death.set_xlabel("Contribution (%)", fontsize=18, fontweight="bold", color="black")
ax_death.set_title("Lightning Death Contribution to India Total (2000–2022)",
                    fontsize=16, fontweight="bold", color="black", pad=10)
ax_death.tick_params(axis="x", labelsize=13, colors=DEATH_RED)
ax_death.tick_params(axis="y", length=0)
ax_death.grid(axis="x", linestyle="--", linewidth=0.7, color=GRID_GREY, alpha=0.5)
ax_death.set_axisbelow(True)

ax_death.text(
    0.02, 1.18, "(f)",
    transform=ax_death.transAxes,
    fontsize=20, fontweight="bold", color="black",
    ha="left", va="top"
)

for yi, val in zip(y, bottom_data["Death_Percent"]):
    ax_death.text(val + 1.5, yi, f"{val:.1f}%", ha="left", va="center",
                   fontsize=15, fontweight="bold", color=DEATH_RED)

for spine in ax_death.spines.values():
    spine.set_linewidth(1.5)

# -------------------- SHARED LEGEND (bottom-right) --------------------
# Combines the panel (a-d) elements AND the bottom bar-chart colours
# into a single, properly formatted legend box.

legend_handles = [
    Patch(facecolor=FLASH_NORMAL, edgecolor="black", label="Lightning Flashes"),
    Patch(facecolor=FLASH_MAX, edgecolor="black", label="Highest Flash Year"),
    Line2D([0], [0], color=DEATH_RED, marker="o", linewidth=2.5,
           markersize=7, label="Total Deaths"),
    Line2D([0], [0], color=DEATH_MAX, marker="o", linewidth=0,
           markersize=9, label="Highest Death Year"),
    Patch(facecolor=FLASH_NORMAL, edgecolor="black", label="Flash Contribution (%)"),
    Patch(facecolor=DEATH_RED, edgecolor="black", label="Death Contribution (%)"),
]

legend = ax_key.legend(
    handles=legend_handles,
    loc="center",
    title="Legend",
    title_fontsize=16,
    fontsize=14,
    frameon=True,
    facecolor="white",
    edgecolor="black",
    framealpha=1.0,
    borderpad=1.1,
    handlelength=1.8,
    labelspacing=1.2,
    handletextpad=0.8
)

legend.get_frame().set_linewidth(1.6)
legend.get_title().set_fontweight("bold")


# ============================================================
# 29. WHITE BACKGROUND
# ============================================================

fig.patch.set_facecolor("white")
fig.patch.set_alpha(1.0)


# ============================================================
# 30. OUTPUT FILES
# ============================================================

png_file = OUTPUT_DIR / "India_Division_Lightning_Deaths_2000_2022.png"
tiff_file = OUTPUT_DIR / "India_Division_Lightning_Deaths_2000_2022.tiff"


# ============================================================
# 31. SAVE PNG
# ============================================================

fig.savefig(
    png_file, dpi=600, bbox_inches="tight",
    facecolor="white", edgecolor="none", format="png"
)


# ============================================================
# 32. SAVE TIFF
#
# NOTE: Saving TIFF directly via fig.savefig(..., format="tiff")
# at 600 dpi can raise "OSError: [Errno 22] Invalid argument" on
# Windows for large raw/uncompressed TIFFs. Instead, we re-save
# the already-written PNG through Pillow with LZW compression,
# which is far more reliable and produces a smaller file.
# ============================================================

from PIL import Image

# Your figure at 600 dpi legitimately exceeds Pillow's default
# decompression-bomb safety threshold (a guard against malicious
# images, not a real issue here) -> disable the limit.
Image.MAX_IMAGE_PIXELS = None

with Image.open(png_file) as im:
    im.save(
        tiff_file,
        format="TIFF",
        compression="tiff_lzw",
        dpi=(600, 600)
    )


# ============================================================
# 33. CLOSE
# ============================================================

plt.close(fig)


# ============================================================
# 34. FINAL OUTPUT
# ============================================================

print("\n")
print("=" * 70)
print("ANALYSIS COMPLETED")
print("=" * 70)

print("\nPNG:")
print(png_file)

print("\nTIFF:")
print(tiff_file)

print("\nExcel:")
print(excel_file)

print("\n")
print("Output formats:")
print("  ✓ PNG — 600 dpi")
print("  ✓ TIFF — 600 dpi")
print("  ✓ Excel — XLSX")
print("  ✗ PDF — not generated")

print("\nFigure:")
print("  ✓ White background")
print("  ✓ 2 × 2 annual dual-axis panels with centered navy titles")
print("  ✓ Per-panel legend box (top-left)")
print("  ✓ Blue/red axis colours matching flash/death axes")
print("  ✓ Bottom: separate Flash% and Death% horizontal bar charts")
print("  ✓ Colour-key legend box beside bottom charts")
print("  ✓ Peak flash / peak death highlighted")
print("  ✓ No figure title")
print("  ✓ No plot displayed")

print("=" * 70)