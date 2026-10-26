"""Generate customer product recommendations from customer segments."""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine


RECOMMENDATION_VERSION = "rules_v1"


def create_database_engine():
    """Create a SQLAlchemy connection using values from the .env file."""

    load_dotenv()

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )

    return create_engine(database_url)


def load_customer_data(engine):
    """Load customer segments and product-ownership information."""

    query = """
        SELECT
            customer_id,
            account_id,
            cluster_id,
            segment_name,
            days_since_last_transaction,
            (
                transaction_count::numeric
                / NULLIF(active_month_count, 0)
            ) AS average_monthly_transaction_count,
            (
                total_transaction_volume
                / NULLIF(active_month_count, 0)
            ) AS average_monthly_transaction_volume,
            net_cash_flow,
            average_balance,
            latest_balance,
            negative_balance_percentage,
            has_card,
            has_loan,
            payment_order_count,
            banking_product_count,
            snapshot_date
        FROM analytics.mart_customer_segments
        ORDER BY customer_id
    """

    customer_data = pd.read_sql(query, engine)

    print(
        f"Loaded {len(customer_data):,} customers "
        "for product recommendations."
    )

    return customer_data

def generate_recommendations(customer_data):
    """Generate eligible product recommendations for each customer."""

    recommendations = []

    for _, customer in customer_data.iterrows():
        customer_recommendations = []

        def add_recommendation(
            product_name,
            recommendation_score,
            recommendation_reason,
        ):
            customer_recommendations.append(
                {
                    "customer_id": customer["customer_id"],
                    "account_id": customer["account_id"],
                    "cluster_id": customer["cluster_id"],
                    "segment_name": customer["segment_name"],
                    "recommended_product": product_name,
                    "recommendation_score": recommendation_score,
                    "recommendation_reason": recommendation_reason,
                    "recommendation_version": RECOMMENDATION_VERSION,
                    "snapshot_date": customer["snapshot_date"],
                }
            )

        # Recommend a payment card only when the customer has no card.
        if not bool(customer["has_card"]):
            score = 70

            if customer["average_monthly_transaction_count"] >= 5:
                score += 10

            if customer["segment_name"] == "High-Value Multi-Product":
                score += 10

            add_recommendation(
                "Payment Card",
                score,
                (
                    "The customer does not currently have a card and "
                    "shows transaction activity that may benefit from "
                    "card-based payments."
                ),
            )

        # Recommend a loan consultation, not automatic loan approval.
        if (
            not bool(customer["has_loan"])
            and customer["days_since_last_transaction"] <= 30
            and customer["net_cash_flow"] > 0
            and customer["negative_balance_percentage"] <= 1
        ):
            score = 60

            if customer["average_balance"] >= 30000:
                score += 10

            if customer["segment_name"] == "High-Value Multi-Product":
                score += 10

            add_recommendation(
                "Personal Loan Consultation",
                score,
                (
                    "The customer is active, has positive net cash flow "
                    "and does not currently have a loan. This is an "
                    "invitation for review, not an approval decision."
                ),
            )

        # Recommend a savings product when cash flow and balances are positive.
        if (
            customer["net_cash_flow"] > 0
            and customer["latest_balance"] > 0
        ):
            score = 55

            if customer["average_balance"] >= 30000:
                score += 15

            if customer["net_cash_flow"] >= 50000:
                score += 10

            add_recommendation(
                "Savings Account",
                score,
                (
                    "Positive cash flow and account balances indicate "
                    "an opportunity to move available funds into savings."
                ),
            )

        # Recommend protection when negative-balance activity is present.
        if customer["negative_balance_percentage"] > 0:
            score = min(
                95,
                70 + int(customer["negative_balance_percentage"] * 5),
            )

            add_recommendation(
                "Overdraft Protection",
                score,
                (
                    "Negative-balance activity indicates that balance "
                    "protection and account alerts may be useful."
                ),
            )

        # Recommend recurring-payment setup when none currently exists.
        if (
            customer["payment_order_count"] == 0
            and customer["days_since_last_transaction"] <= 30
        ):
            add_recommendation(
                "Automatic Payment Setup",
                55,
                (
                    "The customer is active but has no scheduled payment "
                    "orders, so automatic payments may add convenience."
                ),
            )

        # Offer a re-engagement product to inactive customers.
        if customer["days_since_last_transaction"] > 30:
            score = min(
                95,
                70 + int(customer["days_since_last_transaction"] / 10),
            )

            add_recommendation(
                "Account Re-Engagement Review",
                score,
                (
                    "The account has had an extended period without "
                    "transactions and may benefit from a service review."
                ),
            )

        customer_recommendations.sort(
            key=lambda item: item["recommendation_score"],
            reverse=True,
        )

        for rank, recommendation in enumerate(
            customer_recommendations[:3],
            start=1,
        ):
            recommendation["recommendation_rank"] = rank
            recommendations.append(recommendation)

    recommendation_data = pd.DataFrame(recommendations)

    print(
        f"Generated {len(recommendation_data):,} recommendations "
        f"for {recommendation_data['customer_id'].nunique():,} customers."
    )

    return recommendation_data

def validate_recommendations(
    customer_data,
    recommendation_data,
):
    """Validate coverage, ranking, scores and recommendation uniqueness."""

    total_customers = customer_data["customer_id"].nunique()

    recommended_customers = (
        recommendation_data["customer_id"].nunique()
    )

    missing_customers = total_customers - recommended_customers

    duplicate_recommendations = int(
        recommendation_data.duplicated(
            subset=["customer_id", "recommended_product"]
        ).sum()
    )

    invalid_scores = int(
        (
            (recommendation_data["recommendation_score"] < 0)
            | (recommendation_data["recommendation_score"] > 100)
        ).sum()
    )

    invalid_ranks = int(
        (
            (recommendation_data["recommendation_rank"] < 1)
            | (recommendation_data["recommendation_rank"] > 3)
        ).sum()
    )

    recommendations_per_customer = (
        recommendation_data
        .groupby("customer_id")
        .size()
    )

    customers_over_limit = int(
        (recommendations_per_customer > 3).sum()
    )

    print("\nRECOMMENDATION VALIDATION")
    print("-" * 72)
    print(f"Input customers: {total_customers:,}")
    print(f"Customers with recommendations: {recommended_customers:,}")
    print(f"Customers without recommendations: {missing_customers:,}")
    print(f"Duplicate customer-product pairs: {duplicate_recommendations:,}")
    print(f"Invalid scores: {invalid_scores:,}")
    print(f"Invalid ranks: {invalid_ranks:,}")
    print(f"Customers with more than 3 recommendations: {customers_over_limit:,}")

    print("\nRECOMMENDATIONS BY PRODUCT")
    print(
        recommendation_data["recommended_product"]
        .value_counts()
        .to_string()
    )

    if any(
        [
            missing_customers,
            duplicate_recommendations,
            invalid_scores,
            invalid_ranks,
            customers_over_limit,
        ]
    ):
        raise ValueError("Recommendation validation failed.")

    print("\nRecommendation validation passed.")

def save_recommendations(
    engine,
    recommendation_data,
):
    """Save validated recommendations to CSV and PostgreSQL."""

    generated_at = pd.Timestamp.now(tz="UTC")

    saved_recommendations = recommendation_data.copy()
    saved_recommendations["generated_at"] = generated_at

    output_directory = "data/processed/recommendations"
    os.makedirs(output_directory, exist_ok=True)

    output_path = os.path.join(
        output_directory,
        "customer_product_recommendations.csv",
    )

    saved_recommendations.to_csv(
        output_path,
        index=False,
    )

    saved_recommendations.to_sql(
        name="product_recommendations",
        con=engine,
        schema="ml",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    print("\nRECOMMENDATION OUTPUT")
    print("-" * 72)
    print(f"CSV saved to: {output_path}")
    print(
        f"Wrote {len(saved_recommendations):,} rows "
        "to ml.product_recommendations"
    )

def main():
    """Run the product-recommendation pipeline."""

    engine = create_database_engine()

    try:
        customer_data = load_customer_data(engine)
        recommendation_data = generate_recommendations(customer_data)

        validate_recommendations(
            customer_data,
            recommendation_data,
        )
        save_recommendations(
            engine,
            recommendation_data,
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()