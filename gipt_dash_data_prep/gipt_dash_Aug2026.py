"""Prepare the August 2026 GIPT data for the dashboard outputs."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


# The integrated and solar source workbooks are stored in the repository root.
# The cumulative coal workbook is stored alongside this preparation script.
DATA_PREP_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = DATA_PREP_DIRECTORY.parent
PUBLIC_ASSETS_DIRECTORY = REPOSITORY_ROOT / "public" / "assets"
PUBLIC_DATA_DIRECTORY = PUBLIC_ASSETS_DIRECTORY / "data"

GIPT_FILE = REPOSITORY_ROOT / "Global Integrated Power August 2026.xlsx"
SOLAR_FILE = REPOSITORY_ROOT / "Global-Solar-Power-Tracker-February-2026.xlsx"
COAL_HISTORY_FILE = (
    DATA_PREP_DIRECTORY
    / "Cumulative coal-fired power capacity by year.xlsx"
)

OUTPUT_VERSION = "augI2026"
TEXT_CONFIG_INITIALIZER_FILE = (
    DATA_PREP_DIRECTORY / f"gipt_textconfig_{OUTPUT_VERSION}.json"
)
TICKER_OUTPUT_FILE = (
    PUBLIC_DATA_DIRECTORY / f"gipt_data_ticker_{OUTPUT_VERSION}.json"
)
MAP_OUTPUT_FILE = (
    PUBLIC_DATA_DIRECTORY
    / f"operating_plants_map_{OUTPUT_VERSION}.json"
)
# The dashboard uses a manually curated map-bounds_edit.json. Keep newly
# calculated bounds separate so they can be inspected before any live change.
MAP_BOUNDS_REVIEW_FILE = (
    PUBLIC_ASSETS_DIRECTORY / f"map-bounds_{OUTPUT_VERSION}.json"
)
CAPACITY_HISTORY_CSV_FILE = (
    PUBLIC_DATA_DIRECTORY / f"GEM_capacity_stacked_{OUTPUT_VERSION}.csv"
)
CAPACITY_HISTORY_JSON_FILE = (
    PUBLIC_DATA_DIRECTORY / f"GEM_capacity_stacked_{OUTPUT_VERSION}.json"
)
NET_CAPACITY_CSV_FILE = (
    PUBLIC_DATA_DIRECTORY / f"net_capacity_{OUTPUT_VERSION}.csv"
)
NET_CAPACITY_JSON_FILE = (
    PUBLIC_DATA_DIRECTORY / f"net_capacity_{OUTPUT_VERSION}.json"
)
DEVELOPMENT_CSV_FILE = (
    PUBLIC_DATA_DIRECTORY / f"gipt_dev_{OUTPUT_VERSION}.csv"
)
DEVELOPMENT_JSON_FILE = (
    PUBLIC_DATA_DIRECTORY / f"gipt_development_{OUTPUT_VERSION}.json"
)
FOSSIL_SPLIT_JSON_FILE = (
    PUBLIC_DATA_DIRECTORY / f"gipt_fossil_nonfossil_{OUTPUT_VERSION}.json"
)
FOSSIL_SHARE_CSV_FILE = (
    PUBLIC_DATA_DIRECTORY / f"gipt_share_{OUTPUT_VERSION}.csv"
)
AGE_BREAKDOWN_JSON_FILE = (
    PUBLIC_DATA_DIRECTORY / f"age_breakdown_{OUTPUT_VERSION}.json"
)
AGE_BREAKDOWN_CSV_FILE = (
    PUBLIC_DATA_DIRECTORY / f"age_breakdown_{OUTPUT_VERSION}.csv"
)
OWNERSHIP_JSON_FILE = (
    PUBLIC_DATA_DIRECTORY / f"ownership_{OUTPUT_VERSION}.json"
)
OWNERSHIP_CSV_FILE = (
    PUBLIC_DATA_DIRECTORY / f"ownership_{OUTPUT_VERSION}.csv"
)

POWER_FACILITIES_SHEET = "Power facilities"
REGIONS_SHEET = "Regions, area, and countries"
REGION_COUNTRY_COLUMN = "GEM Standard Country Name/Area"
SOLAR_SHEET = "Utility-Scale (1 MW+)"
SOLAR_COLUMNS = [
    "Country/Area",
    "Capacity (MW)",
    "Capacity Rating",
    "Subregion",
    "Region",
    "GEM phase ID",
    "Other IDs (location)",
    "Other IDs (unit/phase)",
]

SOLAR_DC_TO_AC_FACTOR = 0.87
SOLAR_PROBABILITY_MINIMUM_SAMPLE = 30

DASHBOARD_GROUPS = ["BRICS", "EU27", "G7", "G20", "OECD", "African Union"]
GROUP_MEMBERSHIP_COLUMNS = {
    # The dashboard's BRICS grouping follows the ten-member BRICS+ definition
    # used in the August workbook, while retaining the shorter display label.
    "BRICS": (
        "BRICS+ (Brazil, Russia, India, China, South Africa, Ethiopia, the "
        "United Arab Emirates, Iran, Egypt, and Indonesia)"
    ),
    "EU27": "EU27",
    "G7": "G7 (including EU27)",
    "G20": "G20 (including EU27 and African Union)",
    "OECD": "OECD",
    "African Union": "African Union",
}
FOSSIL_TYPES = {"coal", "oil/gas"}

# The historical charts use complete calendar years only. The August 2026
# release is therefore shown through the end of 2025.
HISTORY_START_YEAR = 2000
HISTORY_END_YEAR = 2025
AGE_REFERENCE_YEAR = 2026


################################################################################
# LOAD AND PREPARE GIPT
################################################################################

if not GIPT_FILE.is_file():
    raise FileNotFoundError(f"GIPT workbook not found: {GIPT_FILE}")

gipt = pd.read_excel(
    GIPT_FILE,
    sheet_name=POWER_FACILITIES_SHEET,
    dtype={"Unit / Phase name": str},
)

# Load dashboard group membership from the same GIPT release. This keeps the
# data preparation self-contained and uses the workbook's explicit conventions
# for groups such as G7 including EU27 and G20 including EU27/African Union.
gipt_regions = pd.read_excel(
    GIPT_FILE,
    sheet_name=REGIONS_SHEET,
    usecols=[REGION_COUNTRY_COLUMN, *GROUP_MEMBERSHIP_COLUMNS.values()],
)
gipt_regions = gipt_regions.dropna(subset=[REGION_COUNTRY_COLUMN]).copy()

if gipt_regions[REGION_COUNTRY_COLUMN].duplicated().any():
    duplicate_region_countries = sorted(
        gipt_regions.loc[
            gipt_regions[REGION_COUNTRY_COLUMN].duplicated(keep=False),
            REGION_COUNTRY_COLUMN,
        ].unique()
    )
    raise ValueError(
        "GIPT regions tab contains duplicate country/area names: "
        f"{duplicate_region_countries}"
    )

for membership_column in GROUP_MEMBERSHIP_COLUMNS.values():
    populated_membership = gipt_regions[membership_column].dropna()
    if not populated_membership.eq(1).all():
        unexpected_values = sorted(populated_membership.unique())
        raise ValueError(
            f"Unexpected values in {membership_column}: {unexpected_values}"
        )

gipt_region_countries = set(gipt_regions[REGION_COUNTRY_COLUMN])
gipt_data_countries = set(gipt["Country/area"].dropna())
for hydropower_country_column in [
    "Country/area 1 (hydropower only)",
    "Country/area 2 (hydropower only)",
]:
    gipt_data_countries.update(gipt[hydropower_country_column].dropna())

countries_missing_from_regions = sorted(
    gipt_data_countries - gipt_region_countries
)
if countries_missing_from_regions:
    raise ValueError(
        "GIPT data contains countries/areas absent from its regions tab: "
        f"{countries_missing_from_regions}"
    )

# Coerce the literal "not found" year values to NaN. Capacity is already
# numeric in this release, but coercion preserves the March script's guard.
for column in ("Capacity (MW)", "Start year", "Retired year"):
    gipt[column] = pd.to_numeric(gipt[column], errors="coerce")
gipt["Capacity (MW)"] = gipt["Capacity (MW)"].fillna(0.0)

# The dashboard combines inferred and explicit shelved/cancelled statuses.
gipt["Status"] = gipt["Status"].replace(
    {
        "cancelled - inferred 4 y": "cancelled",
        "shelved - inferred 2 y": "shelved",
    }
)

# Countries/areas omitted from the dashboard's individual-country selector.
exclude = [
    "American Samoa",
    "Aruba",
    "Bahamas",
    "Bonaire, Sint Eustatius, and Saba",
    "Christmas Island",
    "Comoros",
    "Dominica",
    "Grenada",
    "Greenland",
    "Guam",
    "Guernsey",
    "Holy See",
    "Isle of Man",
    "Jersey",
    "Åland Islands",
    "Tonga",
    "Timor-Leste",
    "Saint Lucia",
    "Saint Kitts and Nevis",
    "British Indian Ocean Territory",
]

all_countries = np.sort(
    gipt.loc[~gipt["Country/area"].isin(exclude), "Country/area"].unique()
)
all_countries_in_dash = all_countries.copy()


################################################################################
# SOLAR CAPACITY NORMALISATION (MWdc/MWp TO MWac)
################################################################################

if not SOLAR_FILE.is_file():
    raise FileNotFoundError(f"Solar workbook not found: {SOLAR_FILE}")

solar_raw = pd.read_excel(
    SOLAR_FILE,
    sheet_name=SOLAR_SHEET,
    usecols=SOLAR_COLUMNS,
    dtype={"GEM phase ID": str},
)
solar_raw["Capacity (MW)"] = pd.to_numeric(
    solar_raw["Capacity (MW)"], errors="raise"
)

solar = solar_raw.loc[solar_raw["Capacity (MW)"].ge(1)].copy()
solar["Capacity (MW) original"] = solar["Capacity (MW)"]
solar["Capacity Rating original"] = solar["Capacity Rating"]

expected_ratings = {"MWac", "MWp/dc", "unknown"}
actual_ratings = set(solar["Capacity Rating"].dropna().unique())
unexpected_ratings = sorted(actual_ratings - expected_ratings)
if solar["Capacity Rating"].isna().any() or unexpected_ratings:
    raise ValueError(
        "Unexpected solar capacity ratings: "
        f"missing={int(solar['Capacity Rating'].isna().sum())}, "
        f"values={unexpected_ratings}"
    )


def remove_wepp_wksl(value):
    """Remove WEPP/Wiki-Solar IDs before building AC/DC probabilities."""
    if pd.isna(value) or value == "":
        return ""

    parts = [part.strip() for part in str(value).split(",")]
    return ",".join(
        part
        for part in parts
        if part and not part.startswith(("WEPP", "WKSL"))
    )


for column in ["Other IDs (location)", "Other IDs (unit/phase)"]:
    solar[column] = solar[column].apply(remove_wepp_wksl)

known_dc = solar["Capacity Rating"].eq("MWp/dc")
solar.loc[known_dc, "Capacity (MW)"] = (
    solar.loc[known_dc, "Capacity (MW) original"] * SOLAR_DC_TO_AC_FACTOR
)

# Exclude rows linked to non-WEPP/Wiki-Solar datasets from the probability
# sample so that government datasets do not bias the AC/DC proportions.
probability_base = solar.loc[
    solar["Other IDs (location)"].eq("")
    & solar["Other IDs (unit/phase)"].eq("")
    & solar["Capacity Rating"].isin(["MWac", "MWp/dc"])
].copy()

# Region probabilities. A region with no eligible known ratings receives
# an even 0.5 prior.
solar_regions = pd.Index(solar["Region"].dropna().unique(), name="Region")
region_counts = (
    probability_base.groupby(["Region", "Capacity Rating"])
    .size()
    .unstack(fill_value=0)
    .reindex(
        index=solar_regions,
        columns=["MWac", "MWp/dc"],
        fill_value=0,
    )
)
region_total = region_counts["MWac"] + region_counts["MWp/dc"]
region_probability = (region_counts["MWac"] / region_total).fillna(0.5)

# Subregion probabilities, falling back to the enclosing region when the
# eligible sample contains fewer than 30 observations.
solar_subregions = pd.Index(
    solar["Subregion"].dropna().unique(), name="Subregion"
)
subregion_counts = (
    probability_base.groupby(["Subregion", "Capacity Rating"])
    .size()
    .unstack(fill_value=0)
    .reindex(
        index=solar_subregions,
        columns=["MWac", "MWp/dc"],
        fill_value=0,
    )
)
subregion_total = subregion_counts["MWac"] + subregion_counts["MWp/dc"]
subregion_probability = subregion_counts["MWac"] / subregion_total
subregion_to_region = (
    solar[["Subregion", "Region"]]
    .drop_duplicates("Subregion")
    .set_index("Subregion")["Region"]
)
small_subregions = subregion_total.lt(SOLAR_PROBABILITY_MINIMUM_SAMPLE)
small_subregion_names = small_subregions.index[small_subregions]
subregion_probability.loc[small_subregion_names] = (
    subregion_to_region.reindex(small_subregion_names).map(region_probability)
)

if subregion_probability.isna().any():
    missing_subregions = subregion_probability.index[
        subregion_probability.isna()
    ].tolist()
    raise ValueError(
        "Solar subregions lack an MWac fallback probability: "
        f"{missing_subregions}"
    )

# Country probabilities, falling back to the enclosing subregion when the
# eligible sample contains fewer than 30 observations. Reindexing to every
# country ensures zero-observation countries also follow this hierarchy.
solar_countries = pd.Index(
    solar["Country/Area"].dropna().unique(), name="Country/Area"
)
country_counts = (
    probability_base.groupby(["Country/Area", "Capacity Rating"])
    .size()
    .unstack(fill_value=0)
    .reindex(
        index=solar_countries,
        columns=["MWac", "MWp/dc"],
        fill_value=0,
    )
)
country_total = country_counts["MWac"] + country_counts["MWp/dc"]
country_probability = country_counts["MWac"] / country_total
country_to_subregion = (
    solar[["Country/Area", "Subregion"]]
    .drop_duplicates("Country/Area")
    .set_index("Country/Area")["Subregion"]
)
small_countries = country_total.lt(SOLAR_PROBABILITY_MINIMUM_SAMPLE)
small_country_names = small_countries.index[small_countries]
country_probability.loc[small_country_names] = (
    country_to_subregion.reindex(small_country_names).map(subregion_probability)
)

if country_probability.isna().any():
    missing_countries = country_probability.index[
        country_probability.isna()
    ].tolist()
    raise ValueError(
        "Solar countries lack an MWac fallback probability: "
        f"{missing_countries}"
    )

unknown_rating = solar["Capacity Rating"].eq("unknown")
probability_for_row = solar["Country/Area"].map(country_probability)
missing_probability = unknown_rating & probability_for_row.isna()
if missing_probability.any():
    missing_countries = sorted(
        solar.loc[missing_probability, "Country/Area"]
        .fillna("<missing>")
        .unique()
    )
    raise ValueError(
        "Unknown-rating solar rows lack an MWac probability: "
        f"{missing_countries}"
    )

# If p is the probability that an unknown rating is already MWac, its expected
# multiplier is p * 1 + (1 - p) * 0.87 = 0.87 + 0.13p.
solar.loc[unknown_rating, "Capacity (MW)"] = (
    (
        SOLAR_DC_TO_AC_FACTOR
        + (1 - SOLAR_DC_TO_AC_FACTOR)
        * probability_for_row.loc[unknown_rating]
    )
    * solar.loc[unknown_rating, "Capacity (MW) original"]
)
solar["Capacity Rating"] = "MWac"

solar_ids = solar["GEM phase ID"]
if solar_ids.isna().any() or not solar_ids.is_unique:
    raise ValueError(
        "GSPT phase IDs must be complete and unique: "
        f"missing={int(solar_ids.isna().sum())}, "
        f"duplicates={int(solar_ids.duplicated().sum())}"
    )

gipt_ids = gipt["GEM unit/phase ID"]
if gipt_ids.isna().any() or not gipt_ids.is_unique:
    raise ValueError(
        "GIPT unit/phase IDs must be complete and unique before solar matching"
    )

gipt_id_set = set(gipt_ids)
solar_id_set = set(solar_ids)
missing_from_gipt = sorted(solar_id_set - gipt_id_set)
gipt_solar_ids = set(
    gipt.loc[
        gipt["Type"].eq("utility-scale solar"),
        "GEM unit/phase ID",
    ]
)
missing_from_solar = sorted(gipt_solar_ids - solar_id_set)
if missing_from_gipt or missing_from_solar:
    raise ValueError(
        "Solar-to-GIPT ID validation failed: "
        f"GSPT IDs absent from GIPT={len(missing_from_gipt)}, "
        f"GIPT solar IDs absent from GSPT={len(missing_from_solar)}"
    )

solar_capacity_by_id = solar.set_index("GEM phase ID")["Capacity (MW)"]
gipt = gipt.set_index("GEM unit/phase ID", drop=False)
gipt.loc[solar_capacity_by_id.index, "Capacity (MW)"] = solar_capacity_by_id
gipt = gipt.reset_index(drop=True)

print(f"Solar rows harmonized to MWac: {len(solar):,}")


################################################################################
# 1: TEXT CONFIG (for initialising the list of countries)
################################################################################

dashboard_selections = ["World", *DASHBOARD_GROUPS, *list(all_countries)]
text_config_initializer = pd.DataFrame(
    {
        "Country": dashboard_selections,
        "overall_summary": " ",
    }
)
text_config_initializer.to_json(
    TEXT_CONFIG_INITIALIZER_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)


################################################################################
# 2: TICKERS
################################################################################

group_members = {
    group: set(
        gipt_regions.loc[
            gipt_regions[membership_column].eq(1), REGION_COUNTRY_COLUMN
        ].dropna()
    )
    for group, membership_column in GROUP_MEMBERSHIP_COLUMNS.items()
}

group_member_counts = {
    group: len(members) for group, members in group_members.items()
}
print(f"Dashboard group membership loaded from GIPT: {group_member_counts}")

# Country and group summaries use each country's share of binational hydro.
# World totals remain unchanged because the two shares sum to the source row.
country_1 = "Country/area 1 (hydropower only)"
country_2 = "Country/area 2 (hydropower only)"
capacity_1 = "Country/area 1 Capacity (MW) (hydropower only)"
capacity_2 = "Country/area 2 Capacity (MW) (hydropower only)"

binational = gipt[country_2].notna()
share_1 = pd.to_numeric(gipt.loc[binational, capacity_1], errors="raise")
share_2 = pd.to_numeric(gipt.loc[binational, capacity_2], errors="raise")
source_capacity = gipt.loc[binational, "Capacity (MW)"]

split_difference = (share_1 + share_2 - source_capacity).abs()
if not split_difference.le(1e-6).all():
    raise ValueError("Binational hydropower country shares do not sum to total")

country_rows = [gipt.loc[~binational].copy()]
for country_column, capacity_column in [
    (country_1, capacity_1),
    (country_2, capacity_2),
]:
    share = gipt.loc[binational].copy()
    share["Country/area"] = share[country_column]
    share["Capacity (MW)"] = pd.to_numeric(
        share[capacity_column], errors="raise"
    )
    share = share.loc[
        share["Country/area"].notna() & share["Capacity (MW)"].gt(0)
    ]
    country_rows.append(share)

gipt_country = pd.concat(country_rows, ignore_index=True)
if not np.isclose(
    gipt_country["Capacity (MW)"].sum(),
    gipt["Capacity (MW)"].sum(),
    rtol=0,
    atol=1e-6,
):
    raise ValueError("Country allocation changed total GIPT capacity")

construction = gipt_country.loc[gipt_country["Status"].eq("construction")]

ticker_scopes = [("World", None)]
ticker_scopes.extend(
    (group, group_members[group]) for group in DASHBOARD_GROUPS
)
ticker_scopes.extend((country, {country}) for country in all_countries)

ticker_rows = []
for label, countries in ticker_scopes:
    rows = construction
    if countries is not None:
        rows = rows.loc[rows["Country/area"].isin(countries)]

    fossil = rows["Type"].isin(FOSSIL_TYPES)
    ticker_rows.append(
        {
            "Country": label,
            "summary_1": rows.loc[~fossil, "Capacity (MW)"].sum() / 1_000,
            "summary_2": rows.loc[fossil, "Capacity (MW)"].sum() / 1_000,
        }
    )

ticker_numeric = pd.DataFrame(ticker_rows)

if ticker_numeric["Country"].duplicated().any():
    raise ValueError("Ticker output contains duplicate country/group rows")
if set(ticker_numeric["Country"]) != set(dashboard_selections):
    raise ValueError("Ticker rows do not match text-config selections")


def round_dashboard_number(number):
    """Apply the existing ticker rounding convention."""
    if number >= 100:
        return int(round(number))
    if number >= 1:
        return round(number, 1)
    return round(number, 2)


ticker_data = ticker_numeric.copy()
ticker_data["summary_1"] = [
    "<span>{{"
    + str(round_dashboard_number(value))
    + "}} GW</span><br>non-fossil power capacity<br>under construction"
    for value in ticker_data["summary_1"]
]
ticker_data["summary_2"] = [
    "<span>{{"
    + str(round_dashboard_number(value))
    + "}} GW</span><br>fossil fuel capacity<br>under construction"
    for value in ticker_data["summary_2"]
]
ticker_data.to_json(
    TICKER_OUTPUT_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)


################################################################################
# 3: MAP
################################################################################

gipt_map_source = gipt.loc[gipt["Status"].eq("operating")].copy()

required_plant_fields = [
    "Country/area",
    "Plant / Project name",
    "GEM location ID",
]
if gipt_map_source[required_plant_fields].isna().any().any():
    raise ValueError("Operating map rows contain missing plant identifiers")

for column in ["Capacity (MW)", "Latitude", "Longitude"]:
    gipt_map_source[column] = pd.to_numeric(
        gipt_map_source[column], errors="raise"
    )

if not np.isfinite(
    gipt_map_source[["Capacity (MW)", "Latitude", "Longitude"]].to_numpy()
).all():
    raise ValueError("Operating map rows contain non-finite numeric values")
if not gipt_map_source["Latitude"].between(-90, 90).all():
    raise ValueError("Operating map rows contain invalid latitudes")
if not gipt_map_source["Longitude"].between(-180, 180).all():
    raise ValueError("Operating map rows contain invalid longitudes")

# A location ID must resolve to one country/name. Some multi-phase plants
# intentionally have multiple coordinate pairs, which remain separate map
# markers rather than being discarded or replaced with an invented centroid.
stable_columns = ["Country/area", "Plant / Project name"]
metadata_counts = gipt_map_source.groupby("GEM location ID")[
    stable_columns
].nunique(dropna=False)
inconsistent_locations = metadata_counts.gt(1).any(axis=1)
if inconsistent_locations.any():
    raise ValueError(
        "Operating locations contain inconsistent country/name metadata: "
        f"{int(inconsistent_locations.sum())}"
    )

gipt_map_source["Technology"] = gipt_map_source["Technology"].fillna("unknown")
gipt_map_source["Type"] = gipt_map_source["Type"].str.capitalize()
gipt_map_source["Plant total capacity (MW)"] = gipt_map_source.groupby(
    "GEM location ID"
)["Capacity (MW)"].transform("sum")


def combine_technologies(values):
    """Combine technologies without losing mixed-technology site information."""
    technologies = sorted(
        {
            str(value).strip()
            for value in values
            if pd.notna(value) and str(value).strip()
        }
    )
    return "; ".join(technologies) if technologies else "unknown"


gipt_map = (
    gipt_map_source.groupby(
        ["GEM location ID", "Type", "Latitude", "Longitude"],
        as_index=False,
    )
    .agg(
        {
            "Capacity (MW)": "sum",
            "Plant total capacity (MW)": "first",
            "Technology": combine_technologies,
            "Country/area": "first",
            "Plant / Project name": "first",
        }
    )
    .sort_values(
        ["Plant / Project name", "Country/area", "Type", "GEM location ID"],
        kind="stable",
    )
    .reset_index(drop=True)
)

if not np.isclose(
    gipt_map["Capacity (MW)"].sum(),
    gipt_map_source["Capacity (MW)"].sum(),
    rtol=0,
    atol=1e-6,
):
    raise ValueError("Map aggregation changed total operating capacity")

country_to_groups = {}
for country in gipt_map["Country/area"].unique():
    memberships = [
        group for group in DASHBOARD_GROUPS if country in group_members[group]
    ]
    country_to_groups[country] = memberships or None

gipt_map["Region"] = gipt_map["Country/area"].map(country_to_groups)

map_columns = [
    "Type",
    "Longitude",
    "Latitude",
    "Capacity (MW)",
    "Plant total capacity (MW)",
    "Plant / Project name",
    "Country/area",
    "Region",
    "Technology",
]
map_records = gipt_map[map_columns].to_dict(orient="records")

with MAP_OUTPUT_FILE.open("w", encoding="utf-8") as output_file:
    json.dump(
        map_records,
        output_file,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )


def calculate_bounds(rows, padding=0.5, decimals=2):
    """Calculate padded map bounds for one country or group."""
    coordinates = rows[["Latitude", "Longitude"]].dropna()
    if coordinates.empty:
        return None
    return {
        "lat_min": round(coordinates["Latitude"].min() - padding, decimals),
        "lat_max": round(coordinates["Latitude"].max() + padding, decimals),
        "lng_min": round(coordinates["Longitude"].min() - padding, decimals),
        "lng_max": round(coordinates["Longitude"].max() + padding, decimals),
    }


map_bounds = {}
for country, country_rows in gipt_map.groupby("Country/area"):
    country_bounds = calculate_bounds(country_rows)
    if country_bounds:
        map_bounds[country] = country_bounds

for group in DASHBOARD_GROUPS:
    group_rows = gipt_map.loc[
        gipt_map["Region"].apply(
            lambda memberships: isinstance(memberships, list)
            and group in memberships
        )
    ]
    group_bounds = calculate_bounds(group_rows)
    if group_bounds:
        map_bounds[group] = group_bounds

world_bounds = calculate_bounds(gipt_map)
if world_bounds:
    map_bounds["World"] = world_bounds

with MAP_BOUNDS_REVIEW_FILE.open("w", encoding="utf-8") as output_file:
    json.dump(
        map_bounds,
        output_file,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )

print(f"Text-config selections written: {len(text_config_initializer):,}")
print(f"Ticker rows written: {len(ticker_data):,}")
print(f"Operating map rows written: {len(gipt_map):,}")


################################################################################
# 4: HISTORICAL OPERATING-CAPACITY TIMESERIES
################################################################################

# These labels are shared by sections 4, 5, and 6 and match chart-config.json.
type_display_names = {
    "coal": "Coal",
    "oil/gas": "Oil and gas",
    "utility-scale solar": "Utility-scale solar",
    "wind": "Wind",
    "hydropower": "Hydropower",
    "nuclear": "Nuclear",
    "bioenergy": "Bioenergy",
    "geothermal": "Geothermal",
}
dashboard_type_order = [
    "coal",
    "oil/gas",
    "utility-scale solar",
    "wind",
    "hydropower",
    "nuclear",
    "bioenergy",
    "geothermal",
]
dashboard_display_type_order = [
    type_display_names[facility_type]
    for facility_type in dashboard_type_order
]
history_years = list(range(HISTORY_START_YEAR, HISTORY_END_YEAR + 1))

# Reconstruct annual operating capacity from commissioned and retired units for
# every technology except coal. Coal uses the July 2026 GCPT cumulative-capacity
# workbook below.
historical_gipt_types = [
    facility_type
    for facility_type in dashboard_type_order
    if facility_type != "coal"
]
history_statuses = {"operating", "retired"}
history_missing_start = gipt_country.loc[
    gipt_country["Type"].isin(historical_gipt_types)
    & gipt_country["Status"].isin(history_statuses)
    & gipt_country["Start year"].isna()
]
history_retired_missing_year = gipt_country.loc[
    gipt_country["Type"].isin(historical_gipt_types)
    & gipt_country["Status"].eq("retired")
    & gipt_country["Start year"].notna()
    & gipt_country["Retired year"].isna()
]

print(
    "Non-coal historical rows excluded because Start year is missing: "
    f"{len(history_missing_start):,} "
    f"({history_missing_start['Capacity (MW)'].sum():,.1f} MW)"
)
print(
    "Non-coal retired rows excluded because Retired year is missing: "
    f"{len(history_retired_missing_year):,} "
    f"({history_retired_missing_year['Capacity (MW)'].sum():,.1f} MW)"
)

history_source = gipt_country.loc[
    gipt_country["Type"].isin(historical_gipt_types)
    & gipt_country["Status"].isin(history_statuses)
    & gipt_country["Start year"].notna()
    & ~(
        gipt_country["Status"].eq("retired")
        & gipt_country["Retired year"].isna()
    )
].copy()

historical_capacity_parts = []

for facility_type in historical_gipt_types:
    type_rows = history_source.loc[
        history_source["Type"].eq(facility_type),
        [
            "Country/area",
            "Capacity (MW)",
            "Start year",
            "Retired year",
            "Status",
        ],
    ]

    active_records = []
    for (
        country,
        capacity,
        start_year,
        retired_year,
        facility_status,
    ) in type_rows.itertuples(index=False, name=None):
        first_year = max(int(start_year), HISTORY_START_YEAR)
        last_year = HISTORY_END_YEAR

        if facility_status == "retired":
            last_year = min(int(retired_year) - 1, HISTORY_END_YEAR)

        if first_year > last_year:
            continue

        active_records.extend(
            (country, year, capacity)
            for year in range(first_year, last_year + 1)
        )

    annual_by_country = pd.DataFrame(
        active_records,
        columns=["Country/area", "Year", "Capacity (MW)"],
    )
    annual_by_country = (
        annual_by_country.groupby(["Country/area", "Year"], as_index=False)[
            "Capacity (MW)"
        ].sum()
    )

    country_history = annual_by_country.loc[
        annual_by_country["Country/area"].isin(all_countries)
    ].copy()
    country_history["Area"] = country_history["Country/area"]
    country_history["Type"] = facility_type
    country_history = country_history.rename(columns={"Capacity (MW)": "GEM"})
    historical_capacity_parts.append(
        country_history[["Area", "Year", "GEM", "Type"]]
    )

    for group in DASHBOARD_GROUPS:
        group_history = (
            annual_by_country.loc[
                annual_by_country["Country/area"].isin(group_members[group])
            ]
            .groupby("Year", as_index=False)["Capacity (MW)"]
            .sum()
            .rename(columns={"Capacity (MW)": "GEM"})
        )
        group_history["Area"] = group
        group_history["Type"] = facility_type
        historical_capacity_parts.append(
            group_history[["Area", "Year", "GEM", "Type"]]
        )

    world_history = (
        annual_by_country.groupby("Year", as_index=False)["Capacity (MW)"]
        .sum()
        .rename(columns={"Capacity (MW)": "GEM"})
    )
    world_history["Area"] = "World"
    world_history["Type"] = facility_type
    historical_capacity_parts.append(
        world_history[["Area", "Year", "GEM", "Type"]]
    )

# Load the published July 2026 GCPT cumulative coal-capacity series. The source
# workbook is in GW and includes an H1 2026 row, while this dashboard uses only
# complete calendar years through 2025.
coal_history = pd.read_excel(
    COAL_HISTORY_FILE,
    skiprows=7,
    usecols="A:C",
)
coal_history.columns = ["Area", "Year", "GEM"]
coal_history["Year"] = pd.to_numeric(
    coal_history["Year"], errors="coerce"
)
coal_history["GEM"] = pd.to_numeric(
    coal_history["GEM"], errors="coerce"
)
coal_history = coal_history.loc[
    coal_history["Year"].between(
        HISTORY_START_YEAR, HISTORY_END_YEAR, inclusive="both"
    )
].copy()
coal_history["Year"] = coal_history["Year"].astype(int)
coal_history["Area"] = coal_history["Area"].replace({"Global": "World"})

# Convert the source GW values to MW so this section retains one unit until the
# combined historical table is converted back to GW below.
coal_history["GEM"] = coal_history["GEM"] * 1_000

# Use the published country rows directly. Do not use the coal workbook's
# aggregate BRICS, G7, G20, or OECD rows because their memberships differ from
# the dashboard definitions in the August GIPT Regions tab.
coal_country_history = coal_history.loc[
    coal_history["Area"].isin(all_countries)
].copy()
coal_country_history["Type"] = "coal"
historical_capacity_parts.append(
    coal_country_history[["Area", "Year", "GEM", "Type"]]
)

for group in DASHBOARD_GROUPS:
    group_history = (
        coal_country_history.loc[
            coal_country_history["Area"].isin(group_members[group])
        ]
        .groupby("Year", as_index=False)["GEM"]
        .sum()
    )
    group_history["Area"] = group
    group_history["Type"] = "coal"
    historical_capacity_parts.append(
        group_history[["Area", "Year", "GEM", "Type"]]
    )

# Retain the source workbook's published Global series rather than summing its
# rounded country rows.
coal_world_history = coal_history.loc[
    coal_history["Area"].eq("World")
].copy()
coal_world_history["Type"] = "coal"
historical_capacity_parts.append(
    coal_world_history[["Area", "Year", "GEM", "Type"]]
)

gipt_annual = pd.concat(historical_capacity_parts, ignore_index=True)
gipt_annual["Type"] = gipt_annual["Type"].map(type_display_names)
gipt_annual["GEM"] = gipt_annual["GEM"] / 1_000

capacity_history = (
    gipt_annual.pivot_table(
        index=["Area", "Year"],
        columns="Type",
        values="GEM",
        aggfunc="sum",
        fill_value=0.0,
    )
    .reindex(columns=dashboard_display_type_order, fill_value=0.0)
    .reset_index()
    .rename(columns={"Area": "Country"})
)
capacity_history.columns.name = None

# Preserve the March behavior of omitting years with no tracked capacity.
capacity_history = capacity_history.loc[
    capacity_history[dashboard_display_type_order].sum(axis=1).ne(0)
].copy()

selection_order = {
    selection: position
    for position, selection in enumerate(dashboard_selections)
}
capacity_history["_selection_order"] = capacity_history["Country"].map(
    selection_order
)
if capacity_history["_selection_order"].isna().any():
    unexpected_areas = sorted(
        capacity_history.loc[
            capacity_history["_selection_order"].isna(), "Country"
        ].unique()
    )
    raise ValueError(
        f"Historical capacity contains unexpected areas: {unexpected_areas}"
    )

capacity_history = (
    capacity_history.sort_values(["_selection_order", "Year"])
    .drop(columns="_selection_order")
    .reset_index(drop=True)
)

if capacity_history.duplicated(["Country", "Year"]).any():
    raise ValueError("Historical capacity contains duplicate Country/Year rows")
if not np.isfinite(
    capacity_history[dashboard_display_type_order].to_numpy()
).all():
    raise ValueError("Historical capacity contains non-finite values")
if capacity_history[dashboard_display_type_order].lt(0).any().any():
    raise ValueError("Historical operating capacity cannot be negative")

capacity_history.to_csv(
    CAPACITY_HISTORY_CSV_FILE,
    index=False,
    encoding="utf-8-sig",
)
capacity_history.to_json(
    CAPACITY_HISTORY_JSON_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)

print(f"Historical capacity rows written: {len(capacity_history):,}")


################################################################################
# 5: ANNUAL CAPACITY ADDITIONS AND RETIREMENTS
################################################################################

# A commissioned unit remains an historical addition even if it has since
# retired or is currently mothballed. Retirement events still require the
# explicit retired status; populated planned retirement years are not counted.
commissioned_statuses = {"operating", "retired", "mothballed"}

additions_by_country = (
    gipt_country.loc[
        gipt_country["Status"].isin(commissioned_statuses)
        & gipt_country["Start year"].between(
            HISTORY_START_YEAR, HISTORY_END_YEAR, inclusive="both"
        )
    ]
    .groupby(["Country/area", "Start year", "Type"], as_index=False)[
        "Capacity (MW)"
    ]
    .sum()
)

retirements_by_country = (
    gipt_country.loc[
        gipt_country["Status"].eq("retired")
        & gipt_country["Retired year"].between(
            HISTORY_START_YEAR, HISTORY_END_YEAR, inclusive="both"
        )
    ]
    .groupby(["Country/area", "Retired year", "Type"], as_index=False)[
        "Capacity (MW)"
    ]
    .sum()
)

scope_memberships = [("World", None)]
scope_memberships.extend(
    (group, group_members[group]) for group in DASHBOARD_GROUPS
)
scope_memberships.extend(
    (country, {country}) for country in all_countries
)

net_capacity_parts = []

for selection, member_countries in scope_memberships:
    scope_additions = additions_by_country
    scope_retirements = retirements_by_country

    if member_countries is not None:
        scope_additions = scope_additions.loc[
            scope_additions["Country/area"].isin(member_countries)
        ]
        scope_retirements = scope_retirements.loc[
            scope_retirements["Country/area"].isin(member_countries)
        ]

    additions_wide = (
        scope_additions.groupby(["Start year", "Type"])["Capacity (MW)"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(
            index=history_years,
            columns=dashboard_type_order,
            fill_value=0.0,
        )
    )
    retirements_wide = (
        scope_retirements.groupby(["Retired year", "Type"])["Capacity (MW)"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(
            index=history_years,
            columns=dashboard_type_order,
            fill_value=0.0,
        )
    )

    selection_capacity = pd.DataFrame(
        {
            "Year": history_years,
            "Country": selection,
        }
    )

    for facility_type in dashboard_type_order:
        display_type = type_display_names[facility_type]
        selection_capacity[display_type] = (
            additions_wide[facility_type].to_numpy(dtype=float) / 1_000
        )
        selection_capacity[f"{display_type} retired"] = (
            -retirements_wide[facility_type].to_numpy(dtype=float) / 1_000
        )

    # Solar probabilities can produce long decimals; retain the March output
    # convention of four decimal places for both solar series.
    selection_capacity["Utility-scale solar"] = selection_capacity[
        "Utility-scale solar"
    ].round(4)
    selection_capacity["Utility-scale solar retired"] = selection_capacity[
        "Utility-scale solar retired"
    ].round(4)

    selection_capacity["Net fossil"] = selection_capacity[
        ["Coal", "Oil and gas", "Coal retired", "Oil and gas retired"]
    ].sum(axis=1)
    selection_capacity["Net non-fossil"] = selection_capacity[
        [
            "Utility-scale solar",
            "Wind",
            "Hydropower",
            "Nuclear",
            "Bioenergy",
            "Geothermal",
            "Utility-scale solar retired",
            "Wind retired",
            "Hydropower retired",
            "Nuclear retired",
            "Bioenergy retired",
            "Geothermal retired",
        ]
    ].sum(axis=1)

    net_capacity_parts.append(selection_capacity)

net_capacity = pd.concat(net_capacity_parts, ignore_index=True)

# For groups whose complete membership is available as displayed country rows,
# sum those rounded country components back to the group. This keeps BRICS and
# other complete groups exactly equal to what users can add up on the dashboard.
rollup_component_columns = [
    *dashboard_display_type_order,
    *[
        f"{display_type} retired"
        for display_type in dashboard_display_type_order
    ],
]
displayed_country_names = set(all_countries)

for group in DASHBOARD_GROUPS:
    if not group_members[group].issubset(displayed_country_names):
        continue

    group_row_index = net_capacity.index[net_capacity["Country"].eq(group)]
    if len(group_row_index) != len(history_years):
        raise ValueError(f"Net-capacity group is missing years: {group}")

    member_totals = (
        net_capacity.loc[
            net_capacity["Country"].isin(group_members[group])
        ]
        .groupby("Year")[rollup_component_columns]
        .sum()
        .reindex(history_years, fill_value=0.0)
    )
    net_capacity.loc[
        group_row_index, rollup_component_columns
    ] = member_totals.to_numpy()
    net_capacity.loc[group_row_index, "Net fossil"] = net_capacity.loc[
        group_row_index,
        ["Coal", "Oil and gas", "Coal retired", "Oil and gas retired"],
    ].sum(axis=1)
    net_capacity.loc[group_row_index, "Net non-fossil"] = net_capacity.loc[
        group_row_index,
        [
            "Utility-scale solar",
            "Wind",
            "Hydropower",
            "Nuclear",
            "Bioenergy",
            "Geothermal",
            "Utility-scale solar retired",
            "Wind retired",
            "Hydropower retired",
            "Nuclear retired",
            "Bioenergy retired",
            "Geothermal retired",
        ],
    ].sum(axis=1)

net_capacity_columns = [
    "Year",
    "Country",
    "Net fossil",
    "Net non-fossil",
    *dashboard_display_type_order,
    *[
        f"{display_type} retired"
        for display_type in dashboard_display_type_order
    ],
]
net_capacity = net_capacity[net_capacity_columns]

if len(net_capacity) != len(dashboard_selections) * len(history_years):
    raise ValueError("Net-capacity output is missing Country/Year rows")
if net_capacity.duplicated(["Country", "Year"]).any():
    raise ValueError("Net-capacity output contains duplicate Country/Year rows")
if net_capacity.isna().any().any():
    raise ValueError("Net-capacity output contains missing values")

addition_columns = dashboard_display_type_order
retirement_columns = [
    f"{display_type} retired"
    for display_type in dashboard_display_type_order
]
if net_capacity[addition_columns].lt(0).any().any():
    raise ValueError("Capacity additions cannot be negative")
if net_capacity[retirement_columns].gt(0).any().any():
    raise ValueError("Capacity retirements must be zero or negative")

expected_net_fossil = net_capacity[
    ["Coal", "Oil and gas", "Coal retired", "Oil and gas retired"]
].sum(axis=1)
expected_net_non_fossil = net_capacity[
    [
        "Utility-scale solar",
        "Wind",
        "Hydropower",
        "Nuclear",
        "Bioenergy",
        "Geothermal",
        "Utility-scale solar retired",
        "Wind retired",
        "Hydropower retired",
        "Nuclear retired",
        "Bioenergy retired",
        "Geothermal retired",
    ]
].sum(axis=1)
if not np.allclose(net_capacity["Net fossil"], expected_net_fossil):
    raise ValueError("Net fossil values do not match their component series")
if not np.allclose(
    net_capacity["Net non-fossil"], expected_net_non_fossil
):
    raise ValueError(
        "Net non-fossil values do not match their component series"
    )

net_capacity.to_csv(
    NET_CAPACITY_CSV_FILE,
    index=False,
    encoding="utf-8-sig",
)
net_capacity.to_json(
    NET_CAPACITY_JSON_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)

print(f"Net-capacity rows written: {len(net_capacity):,}")


################################################################################
# 6: CAPACITY IN DEVELOPMENT
################################################################################

prospective_statuses = ["construction", "pre-construction", "announced"]
development_type_order = sorted(
    dashboard_type_order,
    key=lambda facility_type: type_display_names[facility_type],
)

development_by_country = (
    gipt_country.loc[gipt_country["Status"].isin(prospective_statuses)]
    .groupby(["Country/area", "Type", "Status"], as_index=False)[
        "Capacity (MW)"
    ]
    .sum()
)

development_parts = []

# Keep the section's scope setup local and use alphabetical source order to
# match the existing development chart's category order.
development_scopes = [("World", None)]
development_scopes.extend(
    (group, group_members[group]) for group in DASHBOARD_GROUPS
)
development_scopes.extend(
    (country, {country}) for country in all_countries
)

for selection, member_countries in development_scopes:
    scope_development = development_by_country
    if member_countries is not None:
        scope_development = scope_development.loc[
            scope_development["Country/area"].isin(member_countries)
        ]

    development_wide = (
        scope_development.groupby(["Type", "Status"])["Capacity (MW)"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(
            index=development_type_order,
            columns=prospective_statuses,
            fill_value=0.0,
        )
    )

    selection_development = pd.DataFrame(
        {
            "Country": selection,
            "Source": [
                type_display_names[facility_type]
                for facility_type in development_type_order
            ],
            "Construction": development_wide["construction"].to_numpy(
                dtype=float
            ),
            "Pre-construction": development_wide[
                "pre-construction"
            ].to_numpy(dtype=float),
            "Announced": development_wide["announced"].to_numpy(
                dtype=float
            ),
        }
    )
    development_parts.append(selection_development)

development_capacity = pd.concat(development_parts, ignore_index=True)

# Store every public summary-table capacity in GW. The Flourish development
# visualisation must therefore use these values directly, without dividing by
# 1,000 again.
development_value_columns = [
    "Construction",
    "Pre-construction",
    "Announced",
]
development_capacity[development_value_columns] = (
    development_capacity[development_value_columns] / 1_000
)

if len(development_capacity) != len(dashboard_selections) * len(
    dashboard_type_order
):
    raise ValueError("Development output is missing Country/Source rows")
if development_capacity.duplicated(["Country", "Source"]).any():
    raise ValueError("Development output contains duplicate Country/Source rows")
if development_capacity.isna().any().any():
    raise ValueError("Development output contains missing values")
if not np.isfinite(
    development_capacity[development_value_columns].to_numpy()
).all():
    raise ValueError("Development output contains non-finite capacity")
if development_capacity[development_value_columns].lt(0).any().any():
    raise ValueError("Development output contains negative capacity")

expected_world_development = (
    gipt.loc[gipt["Status"].isin(prospective_statuses)]
    .groupby(["Type", "Status"])["Capacity (MW)"]
    .sum()
    .unstack(fill_value=0.0)
    .reindex(
        index=development_type_order,
        columns=prospective_statuses,
        fill_value=0.0,
    )
    / 1_000
)
actual_world_development = (
    development_capacity.loc[development_capacity["Country"].eq("World")]
    .set_index("Source")
    .reindex(
        [
            type_display_names[facility_type]
            for facility_type in development_type_order
        ]
    )[["Construction", "Pre-construction", "Announced"]]
)
if not np.allclose(
    actual_world_development.to_numpy(),
    expected_world_development[
        ["construction", "pre-construction", "announced"]
    ].to_numpy(),
):
    raise ValueError("World development totals changed during country allocation")

development_capacity.to_json(
    DEVELOPMENT_JSON_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)
development_capacity.to_csv(
    DEVELOPMENT_CSV_FILE,
    index=False,
    encoding="utf-8-sig",
)

print(f"Development rows written: {len(development_capacity):,}")


################################################################################
# 7: FOSSIL / NON-FOSSIL SPLIT
################################################################################

fossil_status_order = [
    "announced",
    "pre-construction",
    "construction",
    "operating",
]
fossil_status_labels = {
    "announced": "Announced",
    "pre-construction": "Pre-construction",
    "construction": "Construction",
    "operating": "Operating",
}

fossil_split_source = gipt_country.loc[
    gipt_country["Status"].isin(fossil_status_order),
    ["Country/area", "Status", "Type", "Capacity (MW)"],
].copy()
fossil_split_source["Fuel group"] = np.where(
    fossil_split_source["Type"].isin(FOSSIL_TYPES),
    "Fossil",
    "Non-fossil",
)

fossil_by_country = (
    fossil_split_source.groupby(
        ["Country/area", "Status", "Fuel group"], as_index=False
    )["Capacity (MW)"]
    .sum()
)

fossil_scopes = [("World", None)]
fossil_scopes.extend(
    (group, group_members[group]) for group in DASHBOARD_GROUPS
)
fossil_scopes.extend((country, {country}) for country in all_countries)

fossil_split_parts = []

for selection, member_countries in fossil_scopes:
    scope_fossil = fossil_by_country
    if member_countries is not None:
        scope_fossil = scope_fossil.loc[
            scope_fossil["Country/area"].isin(member_countries)
        ]

    fossil_wide = (
        scope_fossil.groupby(["Status", "Fuel group"])["Capacity (MW)"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(
            index=fossil_status_order,
            columns=["Non-fossil", "Fossil"],
            fill_value=0.0,
        )
    )

    selection_fossil = pd.DataFrame(
        {
            "Country": selection,
            "Status": [
                fossil_status_labels[status]
                for status in fossil_status_order
            ],
            "Non-fossil": fossil_wide["Non-fossil"].to_numpy(dtype=float),
            "Fossil": fossil_wide["Fossil"].to_numpy(dtype=float),
        }
    )
    fossil_split_parts.append(selection_fossil)

fossil_split = pd.concat(fossil_split_parts, ignore_index=True)
fossil_capacity_columns = ["Non-fossil", "Fossil"]
fossil_split[fossil_capacity_columns] = (
    fossil_split[fossil_capacity_columns] / 1_000
)

if len(fossil_split) != len(dashboard_selections) * len(
    fossil_status_order
):
    raise ValueError("Fossil split is missing Country/Status rows")
if fossil_split.duplicated(["Country", "Status"]).any():
    raise ValueError("Fossil split contains duplicate Country/Status rows")
if fossil_split.isna().any().any():
    raise ValueError("Fossil split contains missing values")
if fossil_split[["Non-fossil", "Fossil"]].lt(0).any().any():
    raise ValueError("Fossil split contains negative capacity")

expected_world_fossil = (
    gipt.loc[gipt["Status"].isin(fossil_status_order)]
    .assign(
        **{
            "Fuel group": np.where(
                gipt.loc[
                    gipt["Status"].isin(fossil_status_order), "Type"
                ].isin(FOSSIL_TYPES),
                "Fossil",
                "Non-fossil",
            )
        }
    )
    .groupby(["Status", "Fuel group"])["Capacity (MW)"]
    .sum()
    .unstack(fill_value=0.0)
    .reindex(
        index=fossil_status_order,
        columns=["Non-fossil", "Fossil"],
        fill_value=0.0,
    )
    / 1_000
)
actual_world_fossil = (
    fossil_split.loc[fossil_split["Country"].eq("World")]
    .set_index("Status")
    .reindex(
        [fossil_status_labels[status] for status in fossil_status_order]
    )[["Non-fossil", "Fossil"]]
)
if not np.allclose(
    actual_world_fossil.to_numpy(), expected_world_fossil.to_numpy()
):
    raise ValueError("World fossil split changed during country allocation")

fossil_split.to_json(
    FOSSIL_SPLIT_JSON_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)

fossil_share = fossil_split.copy()
fossil_total = fossil_share["Non-fossil"] + fossil_share["Fossil"]
fossil_share["Non-fossil share (%)"] = 100 * np.divide(
    fossil_share["Non-fossil"],
    fossil_total,
    out=np.zeros(len(fossil_share), dtype=float),
    where=fossil_total.ne(0),
)
fossil_share["Fossil share (%)"] = 100 * np.divide(
    fossil_share["Fossil"],
    fossil_total,
    out=np.zeros(len(fossil_share), dtype=float),
    where=fossil_total.ne(0),
)
fossil_share = fossil_share.rename(
    columns={
        "Non-fossil": "Non-fossil (GW)",
        "Fossil": "Fossil (GW)",
    }
)
fossil_share_percentage_columns = [
    "Non-fossil share (%)",
    "Fossil share (%)",
]
if not fossil_share[fossil_share_percentage_columns].apply(
    lambda column: column.between(0, 100)
).all().all():
    raise ValueError("Fossil/non-fossil percentages fall outside 0 to 100")
positive_fossil_total = fossil_total.gt(0)
if not np.allclose(
    fossil_share.loc[
        positive_fossil_total, fossil_share_percentage_columns
    ].sum(axis=1),
    100,
):
    raise ValueError("Positive fossil/non-fossil percentages do not sum to 100")
fossil_share.to_csv(
    FOSSIL_SHARE_CSV_FILE,
    index=False,
    encoding="utf-8-sig",
)

print(f"Fossil/non-fossil rows written: {len(fossil_split):,}")


################################################################################
# 8: OPERATING CAPACITY BY AGE
################################################################################

age_categories = [
    "0-9 years",
    "10-19 years",
    "20-29 years",
    "30-39 years",
    "40-49 years",
    "50+ years",
]

age_operating_source = gipt_country.loc[
    gipt_country["Status"].eq("operating"),
    ["Country/area", "Type", "Capacity (MW)", "Start year"],
].copy()

age_missing_start = age_operating_source.loc[
    age_operating_source["Start year"].isna()
]
age_future_start = age_operating_source.loc[
    age_operating_source["Start year"].gt(AGE_REFERENCE_YEAR)
]

print(
    "Operating age rows excluded because Start year is missing: "
    f"{len(age_missing_start):,} "
    f"({age_missing_start['Capacity (MW)'].sum():,.1f} MW)"
)
print(
    f"Operating age rows excluded because Start year is after {AGE_REFERENCE_YEAR}: "
    f"{len(age_future_start):,} "
    f"({age_future_start['Capacity (MW)'].sum():,.1f} MW)"
)

age_known_source = age_operating_source.loc[
    age_operating_source["Start year"].notna()
    & age_operating_source["Start year"].le(AGE_REFERENCE_YEAR)
].copy()
age_known_source["Age"] = (
    AGE_REFERENCE_YEAR - age_known_source["Start year"]
)
if age_known_source["Age"].lt(0).any():
    raise ValueError("Operating age calculation produced a negative age")

age_known_source["Age Category"] = pd.cut(
    age_known_source["Age"],
    bins=[-1, 9, 19, 29, 39, 49, np.inf],
    labels=age_categories,
    ordered=True,
)

age_by_country = (
    age_known_source.groupby(
        ["Country/area", "Type", "Age Category"],
        observed=True,
        as_index=False,
    )["Capacity (MW)"]
    .sum()
)
operating_totals_by_country = (
    age_operating_source.groupby("Country/area", as_index=False)[
        "Capacity (MW)"
    ]
    .sum()
)

age_scopes = [("World", None)]
age_scopes.extend(
    (group, group_members[group]) for group in DASHBOARD_GROUPS
)
age_scopes.extend((country, {country}) for country in all_countries)

age_breakdown_parts = []

for selection, member_countries in age_scopes:
    scope_age = age_by_country
    scope_operating_totals = operating_totals_by_country

    if member_countries is not None:
        scope_age = scope_age.loc[
            scope_age["Country/area"].isin(member_countries)
        ]
        scope_operating_totals = scope_operating_totals.loc[
            scope_operating_totals["Country/area"].isin(member_countries)
        ]

    scope_total_capacity = scope_operating_totals["Capacity (MW)"].sum()
    if scope_age.empty or scope_total_capacity <= 0:
        continue

    age_grouped = scope_age.groupby(
        ["Type", "Age Category"], observed=True
    )["Capacity (MW)"].sum()
    present_types = [
        facility_type
        for facility_type in dashboard_type_order
        if facility_type in age_grouped.index.get_level_values("Type")
    ]
    if not present_types:
        continue

    complete_age_index = pd.MultiIndex.from_product(
        [present_types, age_categories],
        names=["Type", "Age Category"],
    )
    selection_age = (
        age_grouped.reindex(complete_age_index, fill_value=0.0)
        .rename("Capacity (MW)")
        .reset_index()
    )
    selection_age["Country"] = selection
    selection_age["Type"] = selection_age["Type"].map(type_display_names)
    selection_age["Capacity (GW)"] = (
        selection_age["Capacity (MW)"] / 1_000
    )

    # Use all operating capacity as the denominator, including rows whose age
    # is unknown. Known age bubbles therefore do not falsely sum to 100% when
    # some operating capacity lacks a Start year.
    selection_age["Capacity %"] = (
        selection_age["Capacity (MW)"] / scope_total_capacity * 100
    )
    age_breakdown_parts.append(
        selection_age[
            [
                "Country",
                "Type",
                "Age Category",
                "Capacity (GW)",
                "Capacity %",
            ]
        ]
    )

age_breakdown = pd.concat(age_breakdown_parts, ignore_index=True)

if age_breakdown.duplicated(
    ["Country", "Type", "Age Category"]
).any():
    raise ValueError("Age breakdown contains duplicate category rows")
if age_breakdown.isna().any().any():
    raise ValueError("Age breakdown contains missing values")
if not np.isfinite(
    age_breakdown[["Capacity (GW)", "Capacity %"]].to_numpy()
).all():
    raise ValueError("Age breakdown contains non-finite values")
if age_breakdown["Capacity (GW)"].lt(0).any():
    raise ValueError("Age breakdown contains negative capacity")
if not age_breakdown["Capacity %"].between(0, 100).all():
    raise ValueError("Age breakdown percentages must be between 0 and 100")

world_known_age_capacity = age_breakdown.loc[
    age_breakdown["Country"].eq("World"), "Capacity (GW)"
].sum()
world_operating_capacity = age_operating_source["Capacity (MW)"].sum() / 1_000
if not np.isclose(
    world_known_age_capacity,
    age_known_source["Capacity (MW)"].sum() / 1_000,
):
    raise ValueError("World age buckets do not conserve known-age capacity")

age_breakdown.to_csv(
    AGE_BREAKDOWN_CSV_FILE,
    index=False,
    encoding="utf-8-sig",
)
age_breakdown.to_json(
    AGE_BREAKDOWN_JSON_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)

age_coverage = (
    world_known_age_capacity / world_operating_capacity
    if world_operating_capacity
    else 0.0
)
print(
    "World operating capacity with a usable Start year: "
    f"{age_coverage:.2%}"
)
print(f"Age-breakdown rows written: {len(age_breakdown):,}")


################################################################################
# 9: OPERATING CAPACITY BY PARENT / OWNER
################################################################################

ownership_percentage_pattern = re.compile(
    r"^(.*?)\s*\[\s*(\d+(?:\.\d+)?)\s*%\s*\]\s*$"
)


def parse_ownership_entries(value):
    """Split one entity cell into names and optional percentage shares."""
    if pd.isna(value) or not str(value).strip():
        return []

    entries = []
    for raw_entry in str(value).split(";"):
        raw_entry = raw_entry.strip()
        if not raw_entry:
            continue

        match = ownership_percentage_pattern.match(raw_entry)
        if match:
            name = match.group(1).strip()
            percentage = float(match.group(2))
        else:
            name = raw_entry
            percentage = None

        if name:
            entries.append((name, percentage))

    return entries


def normalize_ownership_name(value):
    """Harmonize only explicit unknown/other ownership labels."""
    name = " ".join(str(value).split()).strip()
    if not name or name.casefold() in {
        "nan",
        "unknown",
        "not found",
        "not available",
        "n/a",
    }:
        return "Unknown"
    if name.casefold() in {"other", "others"}:
        return "Others"
    return name


def allocate_ownership_capacity(entries, capacity):
    """Allocate one unit's capacity across the real entities listed."""
    if not entries:
        return [("Unknown", capacity)], "unknown"

    normalized_entries = [
        (normalize_ownership_name(name), percentage)
        for name, percentage in entries
    ]

    # Ignore placeholder unknowns when at least one real entity is listed.
    # If every entry is unknown-like, retain one Unknown allocation.
    real_entries = [
        (name, percentage)
        for name, percentage in normalized_entries
        if name != "Unknown"
    ]
    if real_entries:
        normalized_entries = real_entries
    else:
        return [("Unknown", capacity)], "unknown"

    # Consolidate duplicate names before allocating. If the same entity is
    # listed both with and without a percentage, retain its stated percentage
    # and do not also treat it as an unpercentaged entity.
    entries_by_name = {}
    for name, percentage in normalized_entries:
        if name not in entries_by_name:
            entries_by_name[name] = []
        if percentage is not None:
            entries_by_name[name].append(percentage)
    normalized_entries = [
        (
            name,
            sum(percentages) if percentages else None,
        )
        for name, percentages in entries_by_name.items()
    ]

    explicit_entries = [
        (name, percentage)
        for name, percentage in normalized_entries
        if percentage is not None
    ]
    unspecified_names = [
        name
        for name, percentage in normalized_entries
        if percentage is None
    ]
    unspecified_names = list(dict.fromkeys(unspecified_names))
    all_names = list(
        dict.fromkeys(name for name, _ in normalized_entries)
    )

    if not explicit_entries:
        equal_share = capacity / len(all_names)
        allocations = [(name, equal_share) for name in all_names]
        method = (
            "single_unspecified"
            if len(all_names) == 1
            else "equal_split_no_shares"
        )
    else:
        explicit_total = sum(
            percentage for _, percentage in explicit_entries
        )
        all_entries_have_percentages = not unspecified_names
        allocations = []

        if all_entries_have_percentages:
            if explicit_total > 0:
                # Preserve reported relative shares while scaling incomplete
                # or over-100 totals back to exactly 100%.
                allocations = [
                    (name, capacity * percentage / explicit_total)
                    for name, percentage in explicit_entries
                ]
                method = (
                    "explicit_complete"
                    if np.isclose(explicit_total, 100, rtol=0, atol=1e-9)
                    else "normalized_all_percentages"
                )
            else:
                equal_share = capacity / len(all_names)
                allocations = [(name, equal_share) for name in all_names]
                method = "equal_split_zero_percentages"
        elif explicit_total < 100 and not np.isclose(
            explicit_total, 100, rtol=0, atol=1e-9
        ):
            # Keep every stated percentage, then divide the genuinely
            # unallocated remainder equally among the unpercentaged entities.
            allocations = [
                (name, capacity * percentage / 100)
                for name, percentage in explicit_entries
            ]
            remaining_capacity = capacity * (1 - explicit_total / 100)
            equal_remainder = remaining_capacity / len(unspecified_names)
            allocations.extend(
                (name, equal_remainder) for name in unspecified_names
            )
            method = "mixed_remainder_split"
        else:
            # A 100% or over-100 stated total cannot also accommodate owners
            # with no stated percentage. Treat those percentages as unusable
            # and split the unit equally among all actual listed entities.
            equal_share = capacity / len(all_names)
            allocations = [(name, equal_share) for name in all_names]
            method = "equal_split_conflicting_mixed"

    allocation_frame = pd.DataFrame(
        allocations,
        columns=["Parent", "Capacity (MW)"],
    )
    allocation_frame = (
        allocation_frame.groupby("Parent", as_index=False)["Capacity (MW)"]
        .sum()
    )
    allocations = list(
        allocation_frame[["Parent", "Capacity (MW)"]].itertuples(
            index=False, name=None
        )
    )

    if not np.isclose(
        sum(value for _, value in allocations),
        capacity,
        rtol=0,
        atol=max(abs(capacity) * 1e-9, 1e-7),
    ):
        raise ValueError("Ownership allocation changed a unit's capacity")

    return allocations, method


ownership_source = gipt_country.loc[
    gipt_country["Status"].eq("operating"),
    [
        "Country/area",
        "Type",
        "Capacity (MW)",
        "Parent(s)",
        "Parent(s) GEM Entity ID",
        "Owner(s)",
    ],
].copy()

ownership_records = []
ownership_method_counts = {}
parent_id_alignment_mismatches = 0
parent_percentage_conflicts = 0
parent_rows_used = 0
owner_fallback_rows = 0

for (
    country,
    facility_type,
    capacity,
    parent_value,
    parent_id_value,
    owner_value,
) in ownership_source.itertuples(index=False, name=None):
    parent_entries = parse_ownership_entries(parent_value)
    has_real_parent = any(
        normalize_ownership_name(parent_name) != "Unknown"
        for parent_name, _ in parent_entries
    )

    if has_real_parent:
        parent_rows_used += 1
        parent_id_entries = parse_ownership_entries(parent_id_value)

        if parent_id_entries and len(parent_id_entries) == len(parent_entries):
            parent_percentage_conflicts += sum(
                1
                for (_, name_percentage), (_, id_percentage) in zip(
                    parent_entries, parent_id_entries
                )
                if name_percentage is not None
                and id_percentage is not None
                and not np.isclose(name_percentage, id_percentage)
            )
            parent_entries = [
                (
                    parent_name,
                    id_percentage
                    if id_percentage is not None
                    else name_percentage,
                )
                for (
                    (parent_name, name_percentage),
                    (_, id_percentage),
                ) in zip(parent_entries, parent_id_entries)
            ]
        elif parent_id_entries:
            parent_id_alignment_mismatches += 1

        ownership_entries = parent_entries
    else:
        # Owner ID order is not reliably aligned with Owner names in this
        # release, so never zip those columns. Shares attached directly to an
        # Owner name remain usable; missing shares are handled by the explicit
        # equal-split rules above.
        owner_fallback_rows += 1
        ownership_entries = parse_ownership_entries(owner_value)

    allocations, allocation_method = allocate_ownership_capacity(
        ownership_entries,
        float(capacity),
    )
    ownership_method_counts[allocation_method] = (
        ownership_method_counts.get(allocation_method, 0) + 1
    )

    for parent_name, allocated_capacity in allocations:
        ownership_records.append(
            {
                "Country/area": country,
                "Type": facility_type,
                "Parent": parent_name,
                "Capacity (MW)": allocated_capacity,
            }
        )

ownership_allocated = pd.DataFrame(ownership_records)
ownership_allocated = (
    ownership_allocated.groupby(
        ["Country/area", "Type", "Parent"], as_index=False
    )["Capacity (MW)"]
    .sum()
)

ownership_source_totals = ownership_source.groupby(
    ["Country/area", "Type"]
)["Capacity (MW)"].sum()
ownership_allocated_totals = ownership_allocated.groupby(
    ["Country/area", "Type"]
)["Capacity (MW)"].sum()
ownership_total_check = pd.concat(
    [ownership_source_totals, ownership_allocated_totals],
    axis=1,
    keys=["source", "allocated"],
).fillna(0.0)
if not np.allclose(
    ownership_total_check["source"],
    ownership_total_check["allocated"],
    rtol=0,
    atol=1e-6,
):
    raise ValueError("Ownership allocation changed country/type capacity")

ownership_scopes = [("World", None)]
ownership_scopes.extend(
    (group, group_members[group]) for group in DASHBOARD_GROUPS
)
ownership_scopes.extend((country, {country}) for country in all_countries)
ownership_type_order = sorted(
    dashboard_type_order,
    key=lambda facility_type: type_display_names[facility_type],
)

ownership_output_parts = []
world_unknown_ownership_capacity_mw = 0.0

for selection, member_countries in ownership_scopes:
    scope_ownership = ownership_allocated
    if member_countries is not None:
        scope_ownership = scope_ownership.loc[
            scope_ownership["Country/area"].isin(member_countries)
        ]

    if selection == "World":
        # Unknown ownership dominates the global hierarchy and obscures the
        # named entities. Exclude it before ranking so it cannot be folded
        # into Others; retain Unknown for every regional and country view.
        world_unknown_ownership_capacity_mw = scope_ownership.loc[
            scope_ownership["Parent"].eq("Unknown"), "Capacity (MW)"
        ].sum()
        scope_ownership = scope_ownership.loc[
            ~scope_ownership["Parent"].eq("Unknown")
        ]

    scope_ownership = (
        scope_ownership.groupby(["Type", "Parent"], as_index=False)[
            "Capacity (MW)"
        ]
        .sum()
    )

    for facility_type in ownership_type_order:
        type_ownership = scope_ownership.loc[
            scope_ownership["Type"].eq(facility_type)
            & scope_ownership["Capacity (MW)"].gt(0)
        ].copy()
        if type_ownership.empty:
            continue

        type_ownership = type_ownership.sort_values(
            ["Capacity (MW)", "Parent"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)

        top_owners = type_ownership.iloc[:20].copy()
        remaining_capacity = type_ownership.iloc[20:]["Capacity (MW)"].sum()

        if remaining_capacity > 0:
            if top_owners["Parent"].eq("Others").any():
                top_owners.loc[
                    top_owners["Parent"].eq("Others"), "Capacity (MW)"
                ] += remaining_capacity
            else:
                top_owners = pd.concat(
                    [
                        top_owners,
                        pd.DataFrame(
                            {
                                "Type": [facility_type],
                                "Parent": ["Others"],
                                "Capacity (MW)": [remaining_capacity],
                            }
                        ),
                    ],
                    ignore_index=True,
                )

        top_owners = (
            top_owners.groupby(["Type", "Parent"], as_index=False)[
                "Capacity (MW)"
            ]
            .sum()
        )

        if not np.isclose(
            top_owners["Capacity (MW)"].sum(),
            type_ownership["Capacity (MW)"].sum(),
            rtol=0,
            atol=1e-6,
        ):
            raise ValueError(
                f"Top-20 ownership roll-up changed capacity: {selection}, "
                f"{facility_type}"
            )

        top_owners["Country"] = selection
        top_owners["Type"] = type_display_names[facility_type]
        top_owners["Capacity (GW)"] = top_owners["Capacity (MW)"] / 1_000
        top_owners["_others_last"] = top_owners["Parent"].eq("Others")
        top_owners = top_owners.sort_values(
            ["_others_last", "Capacity (GW)", "Parent"],
            ascending=[True, False, True],
            kind="stable",
        )
        ownership_output_parts.append(
            top_owners[["Country", "Type", "Parent", "Capacity (GW)"]]
        )

ownership_output = pd.concat(ownership_output_parts, ignore_index=True)

if ownership_output.duplicated(["Country", "Type", "Parent"]).any():
    raise ValueError("Ownership output contains duplicate parent rows")
if ownership_output.isna().any().any():
    raise ValueError("Ownership output contains missing values")
if not np.isfinite(ownership_output["Capacity (GW)"]).all():
    raise ValueError("Ownership output contains non-finite capacity")
if not ownership_output["Capacity (GW)"].gt(0).all():
    raise ValueError("Ownership output capacity must be positive")

ownership_group_sizes = ownership_output.groupby(["Country", "Type"]).size()
if ownership_group_sizes.gt(21).any():
    raise ValueError("Ownership output contains more than top 20 plus Others")

world_ownership_mask = ownership_output["Country"].eq("World")
if ownership_output.loc[
    world_ownership_mask, "Parent"
].eq("Unknown").any():
    raise ValueError("World ownership output contains Unknown")
world_ownership_capacity = ownership_output.loc[
    world_ownership_mask, "Capacity (GW)"
].sum()
expected_world_ownership_capacity = (
    ownership_allocated.loc[
        ownership_allocated["Parent"].ne("Unknown"), "Capacity (MW)"
    ].sum()
    / 1_000
)
if not np.isclose(
    world_ownership_capacity,
    expected_world_ownership_capacity,
    rtol=0,
    atol=1e-6,
):
    raise ValueError(
        "World ownership output does not conserve known operating capacity"
    )

ownership_output.to_csv(
    OWNERSHIP_CSV_FILE,
    index=False,
    encoding="utf-8-sig",
)
ownership_output.to_json(
    OWNERSHIP_JSON_FILE,
    orient="records",
    indent=2,
    force_ascii=False,
)

print(
    "Ownership entity source rows: "
    f"parents={parent_rows_used:,}, owner fallback={owner_fallback_rows:,}, "
    f"parent-ID alignment mismatches={parent_id_alignment_mismatches:,}, "
    f"parent percentage conflicts={parent_percentage_conflicts:,}"
)
print(f"Ownership allocation methods: {ownership_method_counts}")
print(
    "World ownership capacity excluded because owner is Unknown: "
    f"{world_unknown_ownership_capacity_mw / 1_000:,.3f} GW"
)
print(f"Ownership rows written: {len(ownership_output):,}")
