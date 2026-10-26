"""Evaluate possible K-Means cluster counts for customer segmentation."""

import os
import joblib
import pandas as pd
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import PowerTransformer
from sqlalchemy import URL, create_engine


# These behavioral variables will determine the customer segments.
# Product-ownership variables are intentionally excluded because they will
# later be used to generate product recommendations.
CLUSTER_FEATURES = [
    "customer_age_at_snapshot",
    "account_tenure_months",
    "days_since_last_transaction",
    "average_monthly_transaction_count",
    "average_monthly_transaction_volume",
    "average_transaction_amount",
    "net_cash_flow",
    "average_balance",
    "latest_balance",
    "negative_balance_percentage",
    "card_withdrawal_count",
    "cash_deposit_count",
    "incoming_transfer_count",
    "outgoing_transfer_count",
]
FINAL_CLUSTER_COUNT = 5
RANDOM_STATE = 42

SEGMENT_NAMES = {
    0: "High-Value Multi-Product",
    1: "Everyday Cash-Focused",
    2: "Mature Transfer-Focused",
    3: "High-Flow Financially Volatile",
    4: "Low-Engagement Dormant",
}

SEGMENT_DESCRIPTIONS = {
    0: (
        "Highly active customers with high balances, transaction volume, "
        "card ownership, loan ownership and overall product usage."
    ),
    1: (
        "Regular customers with moderate balances and transaction activity, "
        "strong cash-deposit behavior and limited card or loan ownership."
    ),
    2: (
        "Older customers with lower transaction values whose banking "
        "activity is concentrated primarily in account transfers."
    ),
    3: (
        "Customers with high transaction volume and cash flow but elevated "
        "negative-balance activity, indicating greater financial volatility."
    ),
    4: (
        "Customers with low transaction frequency, longer inactivity and "
        "limited recurring-payment and product engagement."
    ),
}


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


def load_customer_features(engine):
    """Read the customer segmentation feature mart from PostgreSQL."""

    query = """
        SELECT *
        FROM analytics.mart_customer_segmentation_features
        ORDER BY customer_id
    """

    customer_data = pd.read_sql(query, engine)

    print(f"Loaded {len(customer_data):,} customer records.")
    print(f"Selected {len(CLUSTER_FEATURES)} clustering features.")

    return customer_data


def clip_outliers(feature_data):
    """
    Cap extreme observations at the 1st and 99th percentiles.

    Returns both the clipped data and the limits so the same limits can
    be applied later when assigning segments to new customers.
    """

    clipped_data = feature_data.copy()
    clipping_limits = {}

    for column in CLUSTER_FEATURES:
        lower_limit = float(clipped_data[column].quantile(0.01))
        upper_limit = float(clipped_data[column].quantile(0.99))

        clipping_limits[column] = {
            "lower": lower_limit,
            "upper": upper_limit,
        }

        clipped_data[column] = clipped_data[column].clip(
            lower=lower_limit,
            upper=upper_limit,
        )

    return clipped_data, clipping_limits


def prepare_features(customer_data):
    """Validate, cap, transform and scale the clustering features."""

    feature_data = customer_data[CLUSTER_FEATURES].copy()

    missing_values = int(feature_data.isna().sum().sum())

    if missing_values > 0:
        raise ValueError(
            f"Clustering features contain {missing_values} missing values."
        )

    clipped_data, clipping_limits = clip_outliers(feature_data)

    transformer = PowerTransformer(
        method="yeo-johnson",
        standardize=True,
    )

    transformed_features = transformer.fit_transform(clipped_data)

    print("Feature preparation completed.")
    print("Applied 1st/99th percentile outlier capping.")
    print("Applied Yeo-Johnson transformation and standardization.")

    return transformed_features, transformer, clipping_limits


def evaluate_cluster_counts(transformed_features):
    """Evaluate K-Means models for cluster counts from 2 through 8."""

    evaluation_results = []

    print("\nCLUSTER EVALUATION")
    print("-" * 72)

    for cluster_count in range(2, 9):
        model = KMeans(
            n_clusters=cluster_count,
            random_state=42,
            n_init=20,
        )

        cluster_labels = model.fit_predict(transformed_features)

        silhouette = silhouette_score(
            transformed_features,
            cluster_labels,
        )

        davies_bouldin = davies_bouldin_score(
            transformed_features,
            cluster_labels,
        )

        evaluation_results.append(
            {
                "cluster_count": cluster_count,
                "inertia": model.inertia_,
                "silhouette_score": silhouette,
                "davies_bouldin_score": davies_bouldin,
            }
        )

        print(
            f"k={cluster_count} | "
            f"inertia={model.inertia_:,.2f} | "
            f"silhouette={silhouette:.4f} | "
            f"davies_bouldin={davies_bouldin:.4f}"
        )

    return pd.DataFrame(evaluation_results)


def save_evaluation_results(evaluation_results):
    """Save evaluation metrics for documentation and model selection."""

    output_directory = "data/processed/segmentation"
    os.makedirs(output_directory, exist_ok=True)

    output_path = os.path.join(
        output_directory,
        "cluster_evaluation.csv",
    )

    evaluation_results.to_csv(output_path, index=False)

    print("-" * 72)
    print(f"Evaluation results saved to: {output_path}")

def train_final_model(transformed_features):
    """Train the selected K-Means model and report its quality."""

    model = KMeans(
        n_clusters=FINAL_CLUSTER_COUNT,
        random_state=RANDOM_STATE,
        n_init=20,
    )

    cluster_labels = model.fit_predict(transformed_features)

    silhouette = silhouette_score(
        transformed_features,
        cluster_labels,
    )

    davies_bouldin = davies_bouldin_score(
        transformed_features,
        cluster_labels,
    )

    cluster_sizes = (
        pd.Series(cluster_labels)
        .value_counts()
        .sort_index()
    )

    print("\nFINAL MODEL VALIDATION")
    print("-" * 72)
    print(f"Selected cluster count: {FINAL_CLUSTER_COUNT}")
    print(f"Silhouette score: {silhouette:.4f}")
    print(f"Davies-Bouldin score: {davies_bouldin:.4f}")
    print("\nCUSTOMERS PER CLUSTER")

    for cluster_id, customer_count in cluster_sizes.items():
        percentage = customer_count / len(cluster_labels) * 100

        print(
            f"Cluster {cluster_id}: "
            f"{customer_count:,} customers "
            f"({percentage:.2f}%)"
        )

    return model, cluster_labels

def create_cluster_profiles(customer_data, cluster_labels):
    """Create business profiles for the generated customer clusters."""

    segmented_customers = customer_data.copy()
    segmented_customers["cluster_id"] = cluster_labels

    segmented_customers["segment_name"] = (
        segmented_customers["cluster_id"].map(SEGMENT_NAMES)
    )

    segmented_customers["segment_description"] = (
        segmented_customers["cluster_id"].map(SEGMENT_DESCRIPTIONS)
    )

    cluster_profiles = (
        segmented_customers
        .groupby("cluster_id")
        .agg(
            customer_count=("customer_id", "count"),
            average_customer_age=(
                "customer_age_at_snapshot",
                "mean",
            ),
            average_account_tenure_months=(
                "account_tenure_months",
                "mean",
            ),
            average_days_since_last_transaction=(
                "days_since_last_transaction",
                "mean",
            ),
            average_monthly_transaction_count=(
                "average_monthly_transaction_count",
                "mean",
            ),
            average_monthly_transaction_volume=(
                "average_monthly_transaction_volume",
                "mean",
            ),
            average_transaction_amount=(
                "average_transaction_amount",
                "mean",
            ),
            average_net_cash_flow=(
                "net_cash_flow",
                "mean",
            ),
            average_account_balance=(
                "average_balance",
                "mean",
            ),
            average_latest_balance=(
                "latest_balance",
                "mean",
            ),
            average_negative_balance_percentage=(
                "negative_balance_percentage",
                "mean",
            ),
            average_card_withdrawal_count=(
                "card_withdrawal_count",
                "mean",
            ),
            average_cash_deposit_count=(
                "cash_deposit_count",
                "mean",
            ),
            average_incoming_transfer_count=(
                "incoming_transfer_count",
                "mean",
            ),
            average_outgoing_transfer_count=(
                "outgoing_transfer_count",
                "mean",
            ),
            card_ownership_rate=("has_card", "mean"),
            loan_ownership_rate=("has_loan", "mean"),
            average_payment_order_count=(
                "payment_order_count",
                "mean",
            ),
            average_banking_product_count=(
                "banking_product_count",
                "mean",
            ),
        )
        .reset_index()
    )
    cluster_profiles["segment_name"] = (
        cluster_profiles["cluster_id"].map(SEGMENT_NAMES)
    )

    cluster_profiles["segment_description"] = (
        cluster_profiles["cluster_id"].map(SEGMENT_DESCRIPTIONS)
    )

    cluster_profiles["customer_percentage"] = (
        cluster_profiles["customer_count"]
        / len(segmented_customers)
        * 100
    )

    percentage_columns = [
        "card_ownership_rate",
        "loan_ownership_rate",
    ]

    cluster_profiles[percentage_columns] = (
        cluster_profiles[percentage_columns] * 100
    )

    numeric_columns = cluster_profiles.select_dtypes(
        include="number"
    ).columns

    cluster_profiles[numeric_columns] = (
        cluster_profiles[numeric_columns].round(2)
    )

    output_directory = "data/processed/segmentation"
    os.makedirs(output_directory, exist_ok=True)

    profile_path = os.path.join(
        output_directory,
        "cluster_profiles.csv",
    )

    assignment_path = os.path.join(
        output_directory,
        "customer_cluster_assignments.csv",
    )

    cluster_profiles.to_csv(profile_path, index=False)

    segmented_customers[
        [
            "customer_id",
            "account_id",
            "cluster_id",
            "segment_name",
            "segment_description",
            "snapshot_date",
        ]
    ].to_csv(assignment_path, index=False)

    print("\nCluster profiles:")
    print(cluster_profiles.to_string(index=False))
    print(f"\nCluster profiles saved to: {profile_path}")
    print(f"Customer assignments saved to: {assignment_path}")

    return segmented_customers, cluster_profiles

def save_model_artifacts(
    model,
    transformer,
    clipping_limits,
):
    """Save the model and preprocessing objects for future predictions."""

    model_directory = "models/segmentation"
    os.makedirs(model_directory, exist_ok=True)

    artifact_path = os.path.join(
        model_directory,
        "customer_segmentation_pipeline.joblib",
    )

    model_artifacts = {
        "model": model,
        "transformer": transformer,
        "clipping_limits": clipping_limits,
        "feature_names": CLUSTER_FEATURES,
        "cluster_count": FINAL_CLUSTER_COUNT,
        "random_state": RANDOM_STATE,
        "segment_names": SEGMENT_NAMES,
        "segment_descriptions": SEGMENT_DESCRIPTIONS,
    }

    joblib.dump(model_artifacts, artifact_path)

    print(f"Model artifacts saved to: {artifact_path}")

def write_results_to_database(
    engine,
    segmented_customers,
    cluster_profiles,
):
    """Write customer segment results to PostgreSQL."""

    scored_at = pd.Timestamp.now(tz="UTC")
    model_version = "kmeans_v1"

    customer_segments = segmented_customers[
        [
            "customer_id",
            "account_id",
            "cluster_id",
            "segment_name",
            "segment_description",
            "snapshot_date",
        ]
    ].copy()

    customer_segments["model_version"] = model_version
    customer_segments["scored_at"] = scored_at

    database_profiles = cluster_profiles.copy()
    database_profiles["model_version"] = model_version
    database_profiles["generated_at"] = scored_at

    customer_segments.to_sql(
        name="customer_segments",
        con=engine,
        schema="ml",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    database_profiles.to_sql(
        name="cluster_profiles",
        con=engine,
        schema="ml",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    print("\nDATABASE OUTPUT")
    print("-" * 72)
    print(
        f"Wrote {len(customer_segments):,} rows "
        "to ml.customer_segments"
    )
    print(
        f"Wrote {len(database_profiles):,} rows "
        "to ml.cluster_profiles"
    )

def main():
    """Run the cluster-count evaluation pipeline."""

    engine = create_database_engine()

    try:
        customer_data = load_customer_features(engine)
        transformed_features, transformer, clipping_limits = prepare_features(
    customer_data
    )

        evaluation_results = evaluate_cluster_counts(
            transformed_features
        )

        save_evaluation_results(evaluation_results)
        final_model, cluster_labels = train_final_model(
            transformed_features
        )
        segmented_customers, cluster_profiles = create_cluster_profiles(
            customer_data,
            cluster_labels,
        )

        save_model_artifacts(
            final_model,
            transformer,
            clipping_limits,
        )

        write_results_to_database(
            engine,
            segmented_customers,
            cluster_profiles,
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()