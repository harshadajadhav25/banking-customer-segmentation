"""Approved analytics tools for the Banking Analytics Copilot."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DASHBOARD_DATA_DIRECTORY = (
    PROJECT_ROOT / "data" / "dashboard"
)

CUSTOMER_FILE = (
    DASHBOARD_DATA_DIRECTORY
    / "customer_segments.csv"
)

RECOMMENDATION_FILE = (
    DASHBOARD_DATA_DIRECTORY
    / "product_recommendations.csv"
)


MODEL_EVALUATION = [
    {
        "cluster_count": 2,
        "inertia": 45918.6764,
        "silhouette_score": 0.2665,
        "davies_bouldin_score": 1.4649,
    },
    {
        "cluster_count": 3,
        "inertia": 40234.7857,
        "silhouette_score": 0.2290,
        "davies_bouldin_score": 1.8095,
    },
    {
        "cluster_count": 4,
        "inertia": 35121.9422,
        "silhouette_score": 0.2271,
        "davies_bouldin_score": 1.5786,
    },
    {
        "cluster_count": 5,
        "inertia": 31240.2805,
        "silhouette_score": 0.2438,
        "davies_bouldin_score": 1.4554,
    },
    {
        "cluster_count": 6,
        "inertia": 28436.1181,
        "silhouette_score": 0.2451,
        "davies_bouldin_score": 1.5098,
    },
    {
        "cluster_count": 7,
        "inertia": 26361.9944,
        "silhouette_score": 0.2381,
        "davies_bouldin_score": 1.4293,
    },
    {
        "cluster_count": 8,
        "inertia": 24886.0813,
        "silhouette_score": 0.2445,
        "davies_bouldin_score": 1.4099,
    },
]


def convert_to_native(value):
    """Convert Pandas and NumPy values to JSON-compatible values."""

    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return value


def round_optional(value, digits=2):
    """Round a numeric value while preserving missing values."""

    if pd.isna(value):
        return None

    return round(float(value), digits)


def parse_boolean_series(series):
    """Convert common CSV boolean values into Python booleans."""

    if series.dtype == bool:
        return series

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
        .fillna(False)
        .astype(bool)
    )


class BankingAnalyticsTools:
    """Provide controlled access to validated dashboard datasets."""

    def __init__(
        self,
        customer_file=CUSTOMER_FILE,
        recommendation_file=RECOMMENDATION_FILE,
    ):
        self.customer_file = Path(customer_file)
        self.recommendation_file = Path(
            recommendation_file
        )

        self.customers = None
        self.recommendations = None

        self._load_data()

    def _validate_files(self):
        """Verify that required dashboard datasets exist."""

        required_files = [
            self.customer_file,
            self.recommendation_file,
        ]

        missing_files = [
            str(file_path)
            for file_path in required_files
            if not file_path.exists()
        ]

        if missing_files:
            raise FileNotFoundError(
                "Missing dashboard datasets: "
                + ", ".join(missing_files)
                + ". Run "
                "`python dashboards/export_dashboard_data.py` "
                "before using the analytics tools."
            )

    def _load_data(self):
        """Load and validate customer and recommendation data."""

        self._validate_files()

        self.customers = pd.read_csv(
            self.customer_file
        )

        self.recommendations = pd.read_csv(
            self.recommendation_file
        )

        required_customer_columns = [
            "customer_id",
            "account_id",
            "region_name",
            "account_tenure_months",
            "days_since_last_transaction",
            "transaction_count",
            "total_transaction_volume",
            "average_transaction_amount",
            "net_cash_flow",
            "average_balance",
            "latest_balance",
            "negative_balance_percentage",
            "card_withdrawal_count",
            "cash_deposit_count",
            "incoming_transfer_count",
            "outgoing_transfer_count",
            "has_card",
            "has_loan",
            "payment_order_count",
            "banking_product_count",
            "cluster_id",
            "segment_name",
            "segment_description",
        ]

        missing_customer_columns = [
            column
            for column in required_customer_columns
            if column not in self.customers.columns
        ]

        if missing_customer_columns:
            raise ValueError(
                "Customer dataset is missing columns: "
                + ", ".join(missing_customer_columns)
            )

        required_recommendation_columns = [
            "customer_id",
            "recommended_product",
            "recommendation_score",
            "recommendation_rank",
            "recommendation_reason",
            "recommendation_version",
        ]

        missing_recommendation_columns = [
            column
            for column in required_recommendation_columns
            if column not in self.recommendations.columns
        ]

        if missing_recommendation_columns:
            raise ValueError(
                "Recommendation dataset is missing columns: "
                + ", ".join(
                    missing_recommendation_columns
                )
            )

        self.customers["has_card"] = (
            parse_boolean_series(
                self.customers["has_card"]
            )
        )

        self.customers["has_loan"] = (
            parse_boolean_series(
                self.customers["has_loan"]
            )
        )

        self.customers["customer_id"] = (
            self.customers["customer_id"].astype(int)
        )

        self.recommendations["customer_id"] = (
            self.recommendations[
                "customer_id"
            ].astype(int)
        )

        if self.customers["customer_id"].duplicated().any():
            raise ValueError(
                "Customer dataset contains duplicate "
                "customer IDs."
            )

        if self.recommendations.duplicated(
            subset=[
                "customer_id",
                "recommended_product",
            ]
        ).any():
            raise ValueError(
                "Recommendation dataset contains duplicate "
                "customer-product records."
            )

    def get_available_segments(self):
        """Return all valid segment names."""

        return sorted(
            self.customers["segment_name"]
            .dropna()
            .unique()
            .tolist()
        )

    def resolve_segment_name(self, segment_name):
        """Resolve a segment name without case sensitivity."""

        requested_name = str(
            segment_name
        ).strip()

        if not requested_name:
            raise ValueError(
                "Segment name cannot be empty."
            )

        available_segments = (
            self.get_available_segments()
        )

        exact_matches = [
            segment
            for segment in available_segments
            if segment.lower()
            == requested_name.lower()
        ]

        if exact_matches:
            return exact_matches[0]

        partial_matches = [
            segment
            for segment in available_segments
            if requested_name.lower()
            in segment.lower()
        ]

        if len(partial_matches) == 1:
            return partial_matches[0]

        raise ValueError(
            f"Unknown or ambiguous segment: "
            f"{requested_name}. Available segments: "
            + ", ".join(available_segments)
        )

    def get_customer_profile(self, customer_id):
        """Return the approved Customer 360 fields for one customer."""

        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Customer ID must be an integer."
            ) from error

        customer_records = self.customers.loc[
            self.customers["customer_id"]
            == customer_id
        ]

        if customer_records.empty:
            raise ValueError(
                f"Customer {customer_id} was not found."
            )

        customer = customer_records.iloc[0]

        return {
            "customer_id": customer_id,
            "account_id": int(
                customer["account_id"]
            ),
            "segment": customer["segment_name"],
            "segment_description": customer[
                "segment_description"
            ],
            "cluster_id": int(
                customer["cluster_id"]
            ),
            "region": customer["region_name"],
            "account_tenure_months": int(
                customer["account_tenure_months"]
            ),
            "days_since_last_transaction": int(
                customer[
                    "days_since_last_transaction"
                ]
            ),
            "transaction_count": int(
                customer["transaction_count"]
            ),
            "total_transaction_volume": (
                round_optional(
                    customer[
                        "total_transaction_volume"
                    ]
                )
            ),
            "average_transaction_amount": (
                round_optional(
                    customer[
                        "average_transaction_amount"
                    ]
                )
            ),
            "net_cash_flow": round_optional(
                customer["net_cash_flow"]
            ),
            "average_balance": round_optional(
                customer["average_balance"]
            ),
            "latest_balance": round_optional(
                customer["latest_balance"]
            ),
            "negative_balance_percentage": (
                round_optional(
                    customer[
                        "negative_balance_percentage"
                    ]
                )
            ),
            "card_withdrawal_count": int(
                customer[
                    "card_withdrawal_count"
                ]
            ),
            "cash_deposit_count": int(
                customer["cash_deposit_count"]
            ),
            "incoming_transfer_count": int(
                customer[
                    "incoming_transfer_count"
                ]
            ),
            "outgoing_transfer_count": int(
                customer[
                    "outgoing_transfer_count"
                ]
            ),
            "has_card": bool(
                customer["has_card"]
            ),
            "has_loan": bool(
                customer["has_loan"]
            ),
            "payment_order_count": int(
                customer["payment_order_count"]
            ),
            "banking_product_count": int(
                customer[
                    "banking_product_count"
                ]
            ),
            "data_context": (
                "Historical anonymized Customer 360 record."
            ),
            "source": (
                "data/dashboard/customer_segments.csv"
            ),
        }

    def get_customer_recommendations(
        self,
        customer_id,
    ):
        """Return retained rule-based recommendations for a customer."""

        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Customer ID must be an integer."
            ) from error

        if customer_id not in set(
            self.customers["customer_id"]
        ):
            raise ValueError(
                f"Customer {customer_id} was not found."
            )

        customer_recommendations = (
            self.recommendations.loc[
                self.recommendations["customer_id"]
                == customer_id
            ]
            .sort_values("recommendation_rank")
        )

        recommendation_records = []

        for _, recommendation in (
            customer_recommendations.iterrows()
        ):
            recommendation_records.append(
                {
                    "rank": int(
                        recommendation[
                            "recommendation_rank"
                        ]
                    ),
                    "product": recommendation[
                        "recommended_product"
                    ],
                    "score": round_optional(
                        recommendation[
                            "recommendation_score"
                        ]
                    ),
                    "reason": recommendation[
                        "recommendation_reason"
                    ],
                    "version": recommendation[
                        "recommendation_version"
                    ],
                }
            )

        return {
            "customer_id": customer_id,
            "recommendation_count": len(
                recommendation_records
            ),
            "recommendations": (
                recommendation_records
            ),
            "interpretation": (
                "Scores prioritize rule-based suggestions. "
                "They are not approval or purchase "
                "probabilities."
            ),
            "source": (
                "data/dashboard/"
                "product_recommendations.csv"
            ),
        }

    def get_segment_summary(self, segment_name):
        """Return aggregated metrics for one customer segment."""

        resolved_segment = self.resolve_segment_name(
            segment_name
        )

        segment_customers = self.customers.loc[
            self.customers["segment_name"]
            == resolved_segment
        ]

        customer_count = int(
            segment_customers[
                "customer_id"
            ].nunique()
        )

        portfolio_customer_count = int(
            self.customers[
                "customer_id"
            ].nunique()
        )

        segment_description = (
            segment_customers[
                "segment_description"
            ]
            .dropna()
            .iloc[0]
        )

        return {
            "segment": resolved_segment,
            "description": segment_description,
            "customer_count": customer_count,
            "portfolio_share_percentage": round(
                customer_count
                / portfolio_customer_count
                * 100,
                2,
            ),
            "average_account_tenure_months": (
                round_optional(
                    segment_customers[
                        "account_tenure_months"
                    ].mean()
                )
            ),
            "average_days_since_last_transaction": (
                round_optional(
                    segment_customers[
                        "days_since_last_transaction"
                    ].mean()
                )
            ),
            "average_transaction_count": (
                round_optional(
                    segment_customers[
                        "transaction_count"
                    ].mean()
                )
            ),
            "total_transaction_count": int(
                segment_customers[
                    "transaction_count"
                ].sum()
            ),
            "average_transaction_volume": (
                round_optional(
                    segment_customers[
                        "total_transaction_volume"
                    ].mean()
                )
            ),
            "total_transaction_volume": (
                round_optional(
                    segment_customers[
                        "total_transaction_volume"
                    ].sum()
                )
            ),
            "average_net_cash_flow": (
                round_optional(
                    segment_customers[
                        "net_cash_flow"
                    ].mean()
                )
            ),
            "average_balance": round_optional(
                segment_customers[
                    "average_balance"
                ].mean()
            ),
            "average_latest_balance": (
                round_optional(
                    segment_customers[
                        "latest_balance"
                    ].mean()
                )
            ),
            "average_negative_balance_percentage": (
                round_optional(
                    segment_customers[
                        "negative_balance_percentage"
                    ].mean()
                )
            ),
            "card_ownership_rate_percentage": (
                round_optional(
                    segment_customers[
                        "has_card"
                    ].mean()
                    * 100
                )
            ),
            "loan_ownership_rate_percentage": (
                round_optional(
                    segment_customers[
                        "has_loan"
                    ].mean()
                    * 100
                )
            ),
            "average_payment_order_count": (
                round_optional(
                    segment_customers[
                        "payment_order_count"
                    ].mean()
                )
            ),
            "average_banking_product_count": (
                round_optional(
                    segment_customers[
                        "banking_product_count"
                    ].mean()
                )
            ),
            "average_card_withdrawal_count": (
                round_optional(
                    segment_customers[
                        "card_withdrawal_count"
                    ].mean()
                )
            ),
            "average_cash_deposit_count": (
                round_optional(
                    segment_customers[
                        "cash_deposit_count"
                    ].mean()
                )
            ),
            "average_incoming_transfer_count": (
                round_optional(
                    segment_customers[
                        "incoming_transfer_count"
                    ].mean()
                )
            ),
            "average_outgoing_transfer_count": (
                round_optional(
                    segment_customers[
                        "outgoing_transfer_count"
                    ].mean()
                )
            ),
            "interpretation": (
                "These are aggregated historical "
                "segment-level values and are not exact "
                "descriptions of every customer."
            ),
            "source": (
                "data/dashboard/customer_segments.csv"
            ),
        }

    def compare_segments(
        self,
        segment_1,
        segment_2,
    ):
        """Return summaries for two customer segments."""

        first_summary = self.get_segment_summary(
            segment_1
        )

        second_summary = self.get_segment_summary(
            segment_2
        )

        if (
            first_summary["segment"]
            == second_summary["segment"]
        ):
            raise ValueError(
                "Select two different segments "
                "for comparison."
            )

        comparison_fields = [
            "customer_count",
            "portfolio_share_percentage",
            "average_account_tenure_months",
            "average_days_since_last_transaction",
            "average_transaction_count",
            "average_transaction_volume",
            "average_net_cash_flow",
            "average_balance",
            "average_latest_balance",
            "average_negative_balance_percentage",
            "card_ownership_rate_percentage",
            "loan_ownership_rate_percentage",
            "average_payment_order_count",
            "average_banking_product_count",
        ]

        metric_comparison = {}

        for field in comparison_fields:
            first_value = first_summary[field]
            second_value = second_summary[field]

            difference = None

            if (
                first_value is not None
                and second_value is not None
            ):
                difference = round(
                    float(first_value)
                    - float(second_value),
                    2,
                )

            metric_comparison[field] = {
                first_summary["segment"]: (
                    first_value
                ),
                second_summary["segment"]: (
                    second_value
                ),
                "difference_first_minus_second": (
                    difference
                ),
            }

        return {
            "segment_1": first_summary,
            "segment_2": second_summary,
            "metric_comparison": metric_comparison,
            "interpretation": (
                "Differences describe historical "
                "aggregated behavior and do not determine "
                "individual customer outcomes."
            ),
        }

    def get_portfolio_summary(self):
        """Return high-level metrics for the complete portfolio."""

        customer_count = int(
            self.customers[
                "customer_id"
            ].nunique()
        )

        return {
            "customer_count": customer_count,
            "segment_count": int(
                self.customers[
                    "segment_name"
                ].nunique()
            ),
            "transaction_count": int(
                self.customers[
                    "transaction_count"
                ].sum()
            ),
            "total_transaction_volume": (
                round_optional(
                    self.customers[
                        "total_transaction_volume"
                    ].sum()
                )
            ),
            "average_balance": round_optional(
                self.customers[
                    "average_balance"
                ].mean()
            ),
            "card_adoption_percentage": (
                round_optional(
                    self.customers[
                        "has_card"
                    ].mean()
                    * 100
                )
            ),
            "loan_adoption_percentage": (
                round_optional(
                    self.customers[
                        "has_loan"
                    ].mean()
                    * 100
                )
            ),
            "recommendation_count": int(
                len(self.recommendations)
            ),
            "recommended_customer_count": int(
                self.recommendations[
                    "customer_id"
                ].nunique()
            ),
            "available_segments": (
                self.get_available_segments()
            ),
            "source": (
                "Validated deployment CSV snapshot."
            ),
        }

    def get_model_evaluation(self):
        """Return the documented cluster evaluation results."""

        return {
            "selected_cluster_count": 5,
            "selected_model_version": "kmeans_v1",
            "selected_metrics": {
                "inertia": 31240.2805,
                "silhouette_score": 0.2438,
                "davies_bouldin_score": 1.4554,
            },
            "candidate_results": MODEL_EVALUATION,
            "selection_reason": (
                "Five clusters were selected as a "
                "practical balance among compactness, "
                "separation, segment size, business "
                "interpretability, behavioral "
                "differentiation, and recommendation "
                "usefulness."
            ),
            "interpretation": (
                "The final selection was not based on "
                "optimizing only one evaluation metric."
            ),
            "source": (
                "data/processed/segmentation/"
                "cluster_evaluation.csv and model_card.md"
            ),
        }

    def execute_tool(
        self,
        tool_name,
        arguments=None,
    ):
        """Execute one approved analytics tool by name."""

        arguments = arguments or {}

        approved_tools = {
            "get_customer_profile": (
                self.get_customer_profile
            ),
            "get_customer_recommendations": (
                self.get_customer_recommendations
            ),
            "get_segment_summary": (
                self.get_segment_summary
            ),
            "compare_segments": (
                self.compare_segments
            ),
            "get_portfolio_summary": (
                self.get_portfolio_summary
            ),
            "get_model_evaluation": (
                self.get_model_evaluation
            ),
        }

        if tool_name not in approved_tools:
            raise ValueError(
                f"Unknown or prohibited analytics tool: "
                f"{tool_name}"
            )

        return approved_tools[tool_name](
            **arguments
        )


def print_json(data):
    """Print JSON-formatted analytics output."""

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=convert_to_native,
        )
    )


def parse_arguments():
    """Create command-line test options."""

    parser = argparse.ArgumentParser(
        description=(
            "Test approved Banking Analytics "
            "Copilot tools."
        )
    )

    subparsers = parser.add_subparsers(
        dest="tool",
        required=True,
    )

    customer_parser = subparsers.add_parser(
        "customer-profile"
    )

    customer_parser.add_argument(
        "customer_id",
        type=int,
    )

    recommendation_parser = (
        subparsers.add_parser(
            "customer-recommendations"
        )
    )

    recommendation_parser.add_argument(
        "customer_id",
        type=int,
    )

    segment_parser = subparsers.add_parser(
        "segment-summary"
    )

    segment_parser.add_argument(
        "segment_name",
        type=str,
    )

    comparison_parser = subparsers.add_parser(
        "compare-segments"
    )

    comparison_parser.add_argument(
        "segment_1",
        type=str,
    )

    comparison_parser.add_argument(
        "segment_2",
        type=str,
    )

    subparsers.add_parser(
        "portfolio-summary"
    )

    subparsers.add_parser(
        "model-evaluation"
    )

    return parser.parse_args()


def main():
    """Run one approved analytics tool from the terminal."""

    arguments = parse_arguments()

    analytics_tools = BankingAnalyticsTools()

    if arguments.tool == "customer-profile":
        result = (
            analytics_tools.get_customer_profile(
                arguments.customer_id
            )
        )

    elif arguments.tool == (
        "customer-recommendations"
    ):
        result = (
            analytics_tools
            .get_customer_recommendations(
                arguments.customer_id
            )
        )

    elif arguments.tool == "segment-summary":
        result = (
            analytics_tools.get_segment_summary(
                arguments.segment_name
            )
        )

    elif arguments.tool == "compare-segments":
        result = (
            analytics_tools.compare_segments(
                arguments.segment_1,
                arguments.segment_2,
            )
        )

    elif arguments.tool == "portfolio-summary":
        result = (
            analytics_tools.get_portfolio_summary()
        )

    elif arguments.tool == "model-evaluation":
        result = (
            analytics_tools.get_model_evaluation()
        )

    else:
        raise ValueError(
            f"Unsupported tool: {arguments.tool}"
        )

    print_json(result)


if __name__ == "__main__":
    main()