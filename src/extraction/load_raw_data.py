from __future__ import annotations

import os
import uuid
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


CONFIG_PATH = Path("config/source_tables.yml")
CHUNK_SIZE = 2_000

TARGET_TABLES = {
    "account": "account",
    "card": "card",
    "client": "client",
    "disposition": "disposition",
    "district": "district",
    "loan": "loan",
    "order": "payment_order",
    "transaction": "bank_transaction",
}


def load_configuration() -> dict:
    """Load the source-table configuration file."""
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def create_database_engine() -> Engine:
    """Create a reusable PostgreSQL connection."""
    database_user = os.getenv("POSTGRES_USER", "banking_user")
    database_password = os.getenv("POSTGRES_PASSWORD", "change_me")
    database_host = os.getenv("POSTGRES_HOST", "localhost")
    database_port = os.getenv("POSTGRES_PORT", "5432")
    database_name = os.getenv("POSTGRES_DB", "banking_analytics")

    connection_url = (
        f"postgresql+psycopg2://{database_user}:{database_password}"
        f"@{database_host}:{database_port}/{database_name}"
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
    )


def clear_raw_tables(engine: Engine) -> None:
    """Remove records from a previous ingestion run."""
    table_names = ", ".join(
        f"raw.{table_name}" for table_name in TARGET_TABLES.values()
    )

    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names}")
        )


def load_source_table(
    engine: Engine,
    table_name: str,
    source_file: Path,
    delimiter: str,
    batch_id: str,
) -> int:
    """Load one source file into its corresponding raw table."""
    target_table = TARGET_TABLES[table_name]
    loaded_rows = 0

    print(
        f"Loading {source_file.name} "
        f"into raw.{target_table}..."
    )

    for dataframe in pd.read_csv(
        source_file,
        sep=delimiter,
        dtype=str,
        chunksize=CHUNK_SIZE,
        keep_default_na=True,
    ):
        dataframe["_source_file"] = source_file.name
        dataframe["_batch_id"] = batch_id

        dataframe.to_sql(
            name=target_table,
            con=engine,
            schema="raw",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=CHUNK_SIZE,
        )

        loaded_rows += len(dataframe)
        print(f"  Loaded {loaded_rows:,} rows", end="\r")

    print(f"  Loaded {loaded_rows:,} rows")
    return loaded_rows


def database_row_count(
    engine: Engine,
    target_table: str,
) -> int:
    """Return the number of records in one raw table."""
    query = text(
        f"SELECT COUNT(*) FROM raw.{target_table}"
    )

    with engine.connect() as connection:
        return int(connection.execute(query).scalar_one())


def main() -> int:
    """Load and reconcile all configured banking source files."""
    load_dotenv()

    configuration = load_configuration()
    delimiter = configuration["delimiter"]
    raw_data_directory = Path(
        os.getenv("RAW_DATA_DIR", "data/raw")
    )

    batch_id = str(uuid.uuid4())
    engine = create_database_engine()

    print(f"Ingestion batch ID: {batch_id}")
    print("Testing PostgreSQL connection...")

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    print("PostgreSQL connection successful.")
    print("Clearing previous raw data...")
    clear_raw_tables(engine)

    reconciliation_results = []

    for table_name, table_config in configuration["tables"].items():
        source_file = (
            raw_data_directory / table_config["file"]
        )

        if not source_file.exists():
            raise FileNotFoundError(
                f"Source file not found: {source_file}"
            )

        source_row_count = load_source_table(
            engine=engine,
            table_name=table_name,
            source_file=source_file,
            delimiter=delimiter,
            batch_id=batch_id,
        )

        target_table = TARGET_TABLES[table_name]
        target_row_count = database_row_count(
            engine,
            target_table,
        )

        row_counts_match = (
            source_row_count == target_row_count
        )

        reconciliation_results.append(
            {
                "source_table": table_name,
                "target_table": f"raw.{target_table}",
                "source_rows": source_row_count,
                "database_rows": target_row_count,
                "status": (
                    "PASS" if row_counts_match else "FAIL"
                ),
            }
        )

    print()
    print("ROW-COUNT RECONCILIATION")
    print("-" * 78)

    for result in reconciliation_results:
        print(
            f"{result['source_table']:<15}"
            f"{result['source_rows']:>12,} source  "
            f"{result['database_rows']:>12,} database  "
            f"{result['status']}"
        )

    failures = [
        result
        for result in reconciliation_results
        if result["status"] == "FAIL"
    ]

    if failures:
        print("Ingestion failed row-count reconciliation.")
        return 1

    print("-" * 78)
    print("All tables loaded and reconciled successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())