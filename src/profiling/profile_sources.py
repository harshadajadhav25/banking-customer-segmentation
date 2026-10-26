from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv


CONFIG_PATH = Path("config/source_tables.yml")
OUTPUT_DIRECTORY = Path("data/processed/profiles")


def load_source_configuration() -> dict:
    """Read the list of expected source tables from the YAML configuration."""
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def profile_table(
    table_name: str,
    file_path: Path,
    delimiter: str,
    primary_key: str,
) -> tuple[dict, list[dict]]:
    """Create table-level and column-level profiling statistics."""
    print(f"Profiling {table_name}: {file_path.name}")

    dataframe = pd.read_csv(
        file_path,
        sep=delimiter,
        low_memory=False,
    )

    table_profile = {
        "table_name": table_name,
        "file_name": file_path.name,
        "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "duplicate_rows": int(dataframe.duplicated().sum()),
        "missing_cells": int(dataframe.isna().sum().sum()),
        "memory_usage_mb": round(
            dataframe.memory_usage(deep=True).sum() / (1024 * 1024),
            2,
        ),
        "primary_key": primary_key,
        "primary_key_exists": primary_key in dataframe.columns,
        "primary_key_missing": (
            int(dataframe[primary_key].isna().sum())
            if primary_key in dataframe.columns
            else None
        ),
        "primary_key_duplicates": (
            int(dataframe[primary_key].duplicated().sum())
            if primary_key in dataframe.columns
            else None
        ),
    }

    column_profiles = []

    for column_name in dataframe.columns:
        column = dataframe[column_name]

        column_profiles.append(
            {
                "table_name": table_name,
                "column_name": column_name,
                "data_type": str(column.dtype),
                "row_count": int(len(column)),
                "missing_count": int(column.isna().sum()),
                "missing_percentage": round(
                    float(column.isna().mean() * 100),
                    2,
                ),
                "unique_count": int(column.nunique(dropna=True)),
                "sample_value": (
                    str(column.dropna().iloc[0])
                    if not column.dropna().empty
                    else None
                ),
            }
        )

    return table_profile, column_profiles


def main() -> int:
    """Profile every configured banking source file."""
    load_dotenv()

    raw_data_directory = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    configuration = load_source_configuration()
    delimiter = configuration["delimiter"]

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    table_profiles = []
    column_profiles = []

    for table_name, table_config in configuration["tables"].items():
        file_path = raw_data_directory / table_config["file"]

        if not file_path.exists():
            print(f"ERROR: Missing source file: {file_path}")
            return 1

        table_profile, table_columns = profile_table(
            table_name=table_name,
            file_path=file_path,
            delimiter=delimiter,
            primary_key=table_config["primary_key"],
        )

        table_profiles.append(table_profile)
        column_profiles.extend(table_columns)

    table_output = OUTPUT_DIRECTORY / "table_profile.json"
    column_output = OUTPUT_DIRECTORY / "column_profile.csv"

    with table_output.open("w", encoding="utf-8") as output_file:
        json.dump(table_profiles, output_file, indent=2)

    pd.DataFrame(column_profiles).to_csv(column_output, index=False)

    print()
    print("Profiling completed successfully.")
    print(f"Table profile: {table_output}")
    print(f"Column profile: {column_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())