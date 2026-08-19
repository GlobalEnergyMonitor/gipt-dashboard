"""Push the six August 2026 dashboard summary CSVs to Google Sheets.

The default run is a local dry run: it loads the CSVs, checks their columns,
and prints the target worksheet for each file. Use ``--publish`` only after
reviewing that output.

Authentication uses the same service-account approach as the GIPT summary
notebook. Pass the JSON credential path with ``--credentials`` or set the
``GIPT_GOOGLE_SERVICE_ACCOUNT_FILE`` environment variable. Keep that JSON file
outside this repository.
"""

import argparse
import os
from pathlib import Path

import pandas as pd


DATA_PREP_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = DATA_PREP_DIRECTORY.parent
PUBLIC_DATA_DIRECTORY = REPOSITORY_ROOT / "public" / "assets" / "data"

OUTPUT_VERSION = "augII2026"
SPREADSHEET_ID = "123CcBbKi0h7nbQ4KXDOudtvzgigeEAtsosY3JK7NjXk"
CREDENTIALS_ENVIRONMENT_VARIABLE = "GIPT_GOOGLE_SERVICE_ACCOUNT_FILE"

# Publishing is disabled unless the script is run with --publish. This constant
# can also be set to True for an intentionally publication-only local copy.
PUBLISH_TO_GOOGLE_SHEETS = False


# Keep the file-to-tab mapping explicit so it is easy to review and update.
CSV_UPLOADS = [
    {
        "csv_file": PUBLIC_DATA_DIRECTORY
        / f"GEM_capacity_stacked_{OUTPUT_VERSION}.csv",
        "tab_name": "Operating capacity over time (GW)",
        "expected_columns": [
            "Country",
            "Year",
            "Coal",
            "Oil and gas",
            "Utility-scale solar",
            "Wind",
            "Hydropower",
            "Nuclear",
            "Bioenergy",
            "Geothermal",
        ],
    },
    {
        "csv_file": PUBLIC_DATA_DIRECTORY / f"net_capacity_{OUTPUT_VERSION}.csv",
        "tab_name": "Additions/retirements over time (GW)",
        "expected_columns": [
            "Year",
            "Country",
            "Net fossil",
            "Net non-fossil",
            "Coal",
            "Oil and gas",
            "Utility-scale solar",
            "Wind",
            "Hydropower",
            "Nuclear",
            "Bioenergy",
            "Geothermal",
            "Coal retired",
            "Oil and gas retired",
            "Utility-scale solar retired",
            "Wind retired",
            "Hydropower retired",
            "Nuclear retired",
            "Bioenergy retired",
            "Geothermal retired",
        ],
    },
    {
        "csv_file": PUBLIC_DATA_DIRECTORY / f"gipt_dev_{OUTPUT_VERSION}.csv",
        "tab_name": "In-development (GW)",
        "expected_columns": [
            "Country",
            "Source",
            "Construction",
            "Pre-construction",
            "Announced",
        ],
    },
    {
        "csv_file": PUBLIC_DATA_DIRECTORY / f"gipt_share_{OUTPUT_VERSION}.csv",
        "tab_name": "Proportion",
        "expected_columns": [
            "Country",
            "Status",
            "Non-fossil (GW)",
            "Fossil (GW)",
            "Non-fossil share (%)",
            "Fossil share (%)",
        ],
    },
    {
        "csv_file": PUBLIC_DATA_DIRECTORY
        / f"age_breakdown_{OUTPUT_VERSION}.csv",
        "tab_name": "Age breakdown",
        "expected_columns": [
            "Country",
            "Type",
            "Age Category",
            "Capacity (GW)",
            "Capacity %",
        ],
    },
    {
        "csv_file": PUBLIC_DATA_DIRECTORY / f"ownership_{OUTPUT_VERSION}.csv",
        "tab_name": "Ownership",
        "expected_columns": [
            "Country",
            "Type",
            "Parent",
            "Capacity (GW)",
        ],
    },
]


def load_csvs():
    """Load the six generated CSVs and confirm that their schemas are current."""
    loaded_uploads = []

    for upload in CSV_UPLOADS:
        csv_file = upload["csv_file"]
        if not csv_file.is_file():
            raise FileNotFoundError(
                f"Missing generated CSV: {csv_file}\n"
                "Run gipt_dash_Aug2026.py before publishing."
            )

        dataframe = pd.read_csv(csv_file, keep_default_na=False)
        actual_columns = dataframe.columns.tolist()
        if actual_columns != upload["expected_columns"]:
            raise ValueError(
                f"Unexpected columns in {csv_file.name}.\n"
                f"Expected: {upload['expected_columns']}\n"
                f"Actual:   {actual_columns}"
            )
        if dataframe.empty:
            raise ValueError(f"Generated CSV is empty: {csv_file}")

        loaded_uploads.append({**upload, "dataframe": dataframe})

    return loaded_uploads


def resolve_credentials_file(command_line_path):
    """Resolve the service-account JSON without storing its path in Git."""
    credentials_value = command_line_path or os.environ.get(
        CREDENTIALS_ENVIRONMENT_VARIABLE
    )
    if not credentials_value:
        raise ValueError(
            "Publishing requires a Google service-account JSON file. Pass "
            "--credentials PATH or set "
            f"{CREDENTIALS_ENVIRONMENT_VARIABLE}."
        )

    credentials_file = Path(credentials_value).expanduser().resolve()
    if not credentials_file.is_file():
        raise FileNotFoundError(
            f"Google service-account file not found: {credentials_file}"
        )
    return credentials_file


def publish_csvs(loaded_uploads, credentials_file):
    """Replace the values in each target worksheet while retaining formatting."""
    try:
        import pygsheets
    except ImportError as error:
        raise ImportError(
            "pygsheets is required for publishing. Install it with "
            "`python -m pip install pygsheets`."
        ) from error

    google_client = pygsheets.authorize(service_file=str(credentials_file))
    spreadsheet = google_client.open_by_key(SPREADSHEET_ID)

    for upload in loaded_uploads:
        dataframe = upload["dataframe"]
        tab_name = upload["tab_name"]
        worksheet = spreadsheet.worksheet("title", tab_name)

        # Clear cell values only. Existing formatting, frozen rows, and column
        # widths remain, while extend=True adds rows if the new CSV is longer.
        worksheet.clear(start="A1", fields="userEnteredValue")
        worksheet.set_dataframe(
            dataframe,
            start=(1, 1),
            copy_index=False,
            copy_head=True,
            extend=True,
            fit=False,
            escape_formulae=True,
            nan="",
        )

        print(
            f"PUBLISHED - {tab_name}: "
            f"{len(dataframe):,} data rows x {len(dataframe.columns)} columns"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Push the six August 2026 dashboard CSVs to Google Sheets."
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Write to Google Sheets. Without this flag, perform a dry run.",
    )
    parser.add_argument(
        "--credentials",
        help=(
            "Path to the Google service-account JSON file. Alternatively set "
            f"{CREDENTIALS_ENVIRONMENT_VARIABLE}."
        ),
    )
    arguments = parser.parse_args()

    loaded_uploads = load_csvs()
    print(f"Target spreadsheet: {SPREADSHEET_ID}")
    print("CSV upload plan:")
    for upload in loaded_uploads:
        dataframe = upload["dataframe"]
        print(
            f"  {upload['csv_file'].name} -> {upload['tab_name']} "
            f"({len(dataframe):,} data rows x "
            f"{len(dataframe.columns)} columns)"
        )

    should_publish = PUBLISH_TO_GOOGLE_SHEETS or arguments.publish
    if not should_publish:
        print("Dry run only. Re-run with --publish to update Google Sheets.")
        return

    credentials_file = resolve_credentials_file(arguments.credentials)
    publish_csvs(loaded_uploads, credentials_file)
    print("All six Google Sheets tabs were updated successfully.")


if __name__ == "__main__":
    main()
