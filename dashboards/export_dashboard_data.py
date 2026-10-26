"""Export deployment-safe data files for the Streamlit dashboard."""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "dashboard"


CUSTOMER_QUERY = """
    SELECT
        customer_id,
        account_id,
        district_name,
        region_name,
        account_tenure_months,
        days_since_last_transaction,
        transaction_count,
        total_transaction_volume,
        average_transaction_amount,
        net_cash_flow,
        average_balance,
        latest_balance,
        negative_balance_percentage,
        card_withdrawal_count,
        cash_deposit_count,
        incoming_transfer_count,
        outgoing_transfer_count,
        has_card,
        has_loan,
        payment_order_count,
        banking_product_count,
        cluster_id,
        segment_name,
        segment_description
    FROM analytics.mart_customer_segments
    ORDER BY customer_id
"""


RECOMMENDATION_QUERY = """
    SELECT
        recommendation_id,
        customer_id,
        account_id,
        cluster_id,
        segment_name,
        recommended_product,
        recommendation_score,
        recommendation_rank,
        recommendation_reason,
        recommendation_version,
        snapshot_date,
        generated_at
    FROM analytics.mart_product_recommendations
    ORDER BY customer_id, recommendation_rank
"""


def create_database_engine():
    """Create a PostgreSQL connection using values from the local .env file."""

    load_dotenv(PROJECT_ROOT / ".env")

    required_variables = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ]
    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing_variables)
        )

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )

    return create_engine(database_url)


def validate_customers(customers):
    """Validate the exported customer-level dataset."""

    if customers.empty:
        raise ValueError("The customer export is empty.")

    if customers["customer_id"].isna().any():
        raise ValueError("The customer export contains missing customer IDs.")

    if customers["customer_id"].duplicated().any():
        raise ValueError("The customer export contains duplicate customer IDs.")

    if customers["segment_name"].isna().any():
        raise ValueError("The customer export contains missing segment names.")


def validate_recommendations(recommendations, customers):
    """Validate recommendation integrity and customer coverage."""

    if recommendations.empty:
        raise ValueError("The recommendation export is empty.")

    required_columns = [
        "customer_id",
        "recommended_product",
        "recommendation_score",
        "recommendation_rank",
        "recommendation_reason",
    ]

    if recommendations[required_columns].isna().any().any():
        raise ValueError("The recommendation export contains missing values.")

    duplicate_pairs = recommendations.duplicated(
        subset=["customer_id", "recommended_product"]
    ).sum()
    if duplicate_pairs:
        raise ValueError(
            f"The recommendation export contains {duplicate_pairs} "
            "duplicate customer-product pairs."
        )

    if not recommendations["recommendation_score"].between(0, 100).all():
        raise ValueError("Recommendation scores must be between 0 and 100.")

    if not recommendations["recommendation_rank"].between(1, 3).all():
        raise ValueError("Recommendation ranks must be between 1 and 3.")

    unknown_customers = set(recommendations["customer_id"]) - set(
        customers["customer_id"]
    )
    if unknown_customers:
        raise ValueError(
            "Recommendations contain customer IDs that are absent from "
            "the customer export."
        )


def export_dashboard_data():
    """Read validated marts and write deployment-ready CSV files."""

    engine = create_database_engine()

    try:
        customers = pd.read_sql(CUSTOMER_QUERY, engine)
        recommendations = pd.read_sql(RECOMMENDATION_QUERY, engine)
    finally:
        engine.dispose()

    validate_customers(customers)
    validate_recommendations(recommendations, customers)

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    customer_output = OUTPUT_DIRECTORY / "customer_segments.csv"
    recommendation_output = (
        OUTPUT_DIRECTORY / "product_recommendations.csv"
    )

    customers.to_csv(customer_output, index=False)
    recommendations.to_csv(recommendation_output, index=False)

    print("DASHBOARD DATA EXPORT")
    print("-" * 72)
    print(f"Customers exported: {len(customers):,}")
    print(f"Segments exported: {customers['segment_name'].nunique():,}")
    print(f"Recommendations exported: {len(recommendations):,}")
    print(
        "Customers with recommendations: "
        f"{recommendations['customer_id'].nunique():,}"
    )
    print(f"Customer file: {customer_output}")
    print(f"Recommendation file: {recommendation_output}")
    print("Dashboard data export completed successfully.")


if __name__ == "__main__":
    export_dashboard_data()
