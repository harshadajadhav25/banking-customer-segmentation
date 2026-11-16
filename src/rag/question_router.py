"""Route user questions to approved analytics tools and RAG retrieval."""

import argparse
import json
import re
from dataclasses import asdict, dataclass, field


SEGMENT_ALIASES = {
    "High-Value Multi-Product": [
        "high-value multi-product",
        "high value multi product",
        "high-value",
        "high value",
        "multi-product",
        "multi product",
    ],
    "Everyday Cash-Focused": [
        "everyday cash-focused",
        "everyday cash focused",
        "everyday cash",
        "cash-focused",
        "cash focused",
    ],
    "Mature Transfer-Focused": [
        "mature transfer-focused",
        "mature transfer focused",
        "mature transfer",
        "transfer-focused",
        "transfer focused",
    ],
    "High-Flow Financially Volatile": [
        "high-flow financially volatile",
        "high flow financially volatile",
        "high-flow",
        "high flow",
        "financially volatile",
        "volatile segment",
    ],
    "Low-Engagement Dormant": [
        "low-engagement dormant",
        "low engagement dormant",
        "low-engagement",
        "low engagement",
        "dormant segment",
        "dormant",
    ],
}


RECOMMENDATION_TERMS = {
    "recommend",
    "recommended",
    "recommendation",
    "recommendations",
    "product suggestion",
    "product suggestions",
    "ranked product",
    "ranked products",
    "overdraft protection",
    "savings account",
    "payment card",
    "personal loan consultation",
    "automatic payment setup",
    "account re-engagement review",
}


CUSTOMER_PROFILE_TERMS = {
    "profile",
    "customer 360",
    "balance",
    "transactions",
    "transaction count",
    "transaction volume",
    "cash flow",
    "region",
    "segment",
    "has card",
    "has loan",
    "product ownership",
    "account activity",
    "account tenure",
    "last transaction",
}


MODEL_TERMS = {
    "model evaluation",
    "model metrics",
    "cluster evaluation",
    "silhouette",
    "davies-bouldin",
    "davies bouldin",
    "inertia",
    "why five clusters",
    "why 5 clusters",
    "selected clusters",
    "cluster count",
    "k-means evaluation",
    "kmeans evaluation",
}


PORTFOLIO_TERMS = {
    "portfolio summary",
    "portfolio overview",
    "total customers",
    "how many customers",
    "total transactions",
    "overall average balance",
    "card adoption",
    "loan adoption",
    "number of segments",
    "total recommendations",
}


COMPARISON_TERMS = {
    "compare",
    "comparison",
    "compared",
    "versus",
    " vs ",
    "difference",
    "different",
    "higher than",
    "lower than",
}


SEGMENT_METRIC_TERMS = {
    "summary",
    "average",
    "customers",
    "customer count",
    "portfolio share",
    "balance",
    "transactions",
    "transaction volume",
    "cash flow",
    "card ownership",
    "loan ownership",
    "product count",
    "inactivity",
    "activity",
    "metrics",
    "statistics",
}


@dataclass(frozen=True)
class ToolCall:
    """One approved analytics-tool request."""

    tool_name: str
    arguments: dict
    purpose: str


@dataclass
class RouteDecision:
    """Routing result for one user question."""

    route_type: str
    requires_retrieval: bool
    tool_calls: list[ToolCall] = field(
        default_factory=list
    )
    detected_customer_id: int | None = None
    detected_segments: list[str] = field(
        default_factory=list
    )
    reason: str = ""


def normalize_question(question):
    """Normalize question text for deterministic routing."""

    normalized_question = str(question).strip().lower()

    return re.sub(
        r"\s+",
        " ",
        normalized_question,
    )


def contains_any_term(text, terms):
    """Return True when text contains one configured term."""

    return any(
        term in text
        for term in terms
    )


def extract_customer_id(question):
    """Extract an explicitly identified customer ID."""

    patterns = [
        r"\bcustomer\s+id\s*[:#-]?\s*(\d+)\b",
        r"\bcustomer\s*[:#-]?\s*(\d+)\b",
        r"\bcustomer\s+#\s*(\d+)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            question,
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

    return None


def find_mentioned_segments(question):
    """Find business segment names or aliases in a question."""

    normalized_question = normalize_question(
        question
    )

    matched_segments = []

    for segment_name, aliases in (
        SEGMENT_ALIASES.items()
    ):
        possible_names = [
            segment_name.lower(),
            *aliases,
        ]

        if any(
            alias in normalized_question
            for alias in possible_names
        ):
            matched_segments.append(segment_name)

    return matched_segments


def route_customer_question(
    normalized_question,
    customer_id,
):
    """Create tool calls for a customer-specific question."""

    tool_calls = []

    if contains_any_term(
        normalized_question,
        RECOMMENDATION_TERMS,
    ):
        tool_calls.append(
            ToolCall(
                tool_name=(
                    "get_customer_recommendations"
                ),
                arguments={
                    "customer_id": customer_id,
                },
                purpose=(
                    "Retrieve the customer's verified "
                    "rule-based recommendations."
                ),
            )
        )

        tool_calls.append(
            ToolCall(
                tool_name="get_customer_profile",
                arguments={
                    "customer_id": customer_id,
                },
                purpose=(
                    "Retrieve supporting historical "
                    "Customer 360 values."
                ),
            )
        )

        return RouteDecision(
            route_type="hybrid_customer_recommendation",
            requires_retrieval=True,
            tool_calls=tool_calls,
            detected_customer_id=customer_id,
            reason=(
                "The question names a customer and asks "
                "about product recommendations."
            ),
        )

    if contains_any_term(
        normalized_question,
        CUSTOMER_PROFILE_TERMS,
    ):
        tool_calls.append(
            ToolCall(
                tool_name="get_customer_profile",
                arguments={
                    "customer_id": customer_id,
                },
                purpose=(
                    "Retrieve the customer's approved "
                    "historical Customer 360 profile."
                ),
            )
        )

        return RouteDecision(
            route_type="hybrid_customer_profile",
            requires_retrieval=True,
            tool_calls=tool_calls,
            detected_customer_id=customer_id,
            reason=(
                "The question names a customer and asks "
                "about historical account behavior."
            ),
        )

    tool_calls.append(
        ToolCall(
            tool_name="get_customer_profile",
            arguments={
                "customer_id": customer_id,
            },
            purpose=(
                "Retrieve the customer's approved "
                "historical Customer 360 profile."
            ),
        )
    )

    return RouteDecision(
        route_type="hybrid_customer_general",
        requires_retrieval=True,
        tool_calls=tool_calls,
        detected_customer_id=customer_id,
        reason=(
            "The question names a customer, so the "
            "approved customer-profile tool is required."
        ),
    )


def route_segment_question(
    normalized_question,
    detected_segments,
):
    """Create tool calls for segment questions."""

    if (
        len(detected_segments) >= 2
        and contains_any_term(
            normalized_question,
            COMPARISON_TERMS,
        )
    ):
        return RouteDecision(
            route_type="hybrid_segment_comparison",
            requires_retrieval=True,
            tool_calls=[
                ToolCall(
                    tool_name="compare_segments",
                    arguments={
                        "segment_1": (
                            detected_segments[0]
                        ),
                        "segment_2": (
                            detected_segments[1]
                        ),
                    },
                    purpose=(
                        "Retrieve a verified comparison "
                        "of two customer segments."
                    ),
                )
            ],
            detected_segments=(
                detected_segments[:2]
            ),
            reason=(
                "The question identifies two segments "
                "and requests a comparison."
            ),
        )

    if (
        len(detected_segments) == 1
        and contains_any_term(
            normalized_question,
            SEGMENT_METRIC_TERMS,
        )
    ):
        return RouteDecision(
            route_type="hybrid_segment_summary",
            requires_retrieval=True,
            tool_calls=[
                ToolCall(
                    tool_name="get_segment_summary",
                    arguments={
                        "segment_name": (
                            detected_segments[0]
                        ),
                    },
                    purpose=(
                        "Retrieve verified aggregated "
                        "metrics for the segment."
                    ),
                )
            ],
            detected_segments=detected_segments,
            reason=(
                "The question identifies one segment "
                "and requests its metrics or summary."
            ),
        )

    return None


def route_question(question):
    """Route a question to RAG and approved analytics tools."""

    normalized_question = normalize_question(
        question
    )

    if not normalized_question:
        return RouteDecision(
            route_type="invalid_empty_question",
            requires_retrieval=False,
            reason="The question is empty.",
        )

    customer_id = extract_customer_id(
        normalized_question
    )

    if customer_id is not None:
        return route_customer_question(
            normalized_question,
            customer_id,
        )

    detected_segments = find_mentioned_segments(
        normalized_question
    )

    segment_decision = route_segment_question(
        normalized_question,
        detected_segments,
    )

    if segment_decision is not None:
        return segment_decision

    if contains_any_term(
        normalized_question,
        MODEL_TERMS,
    ):
        return RouteDecision(
            route_type="hybrid_model_evaluation",
            requires_retrieval=True,
            tool_calls=[
                ToolCall(
                    tool_name="get_model_evaluation",
                    arguments={},
                    purpose=(
                        "Retrieve verified K-Means "
                        "evaluation metrics."
                    ),
                )
            ],
            reason=(
                "The question asks about model selection "
                "or evaluation metrics."
            ),
        )

    if contains_any_term(
        normalized_question,
        PORTFOLIO_TERMS,
    ):
        return RouteDecision(
            route_type="hybrid_portfolio_summary",
            requires_retrieval=True,
            tool_calls=[
                ToolCall(
                    tool_name="get_portfolio_summary",
                    arguments={},
                    purpose=(
                        "Retrieve verified portfolio-level "
                        "metrics."
                    ),
                )
            ],
            reason=(
                "The question asks for portfolio-level "
                "counts or metrics."
            ),
        )

    return RouteDecision(
        route_type="documentation_rag",
        requires_retrieval=True,
        detected_segments=detected_segments,
        reason=(
            "The question can be answered from the "
            "project knowledge base."
        ),
    )


def display_route(question, decision):
    """Print the routing decision for local testing."""

    print("RAG QUESTION ROUTER")
    print("-" * 72)
    print(f"Question: {question}")
    print(
        json.dumps(
            asdict(decision),
            indent=2,
            ensure_ascii=False,
        )
    )


def parse_arguments():
    """Parse a question for router testing."""

    parser = argparse.ArgumentParser(
        description=(
            "Route a Banking Analytics Copilot "
            "question."
        )
    )

    parser.add_argument(
        "question",
        type=str,
        help="Question to route.",
    )

    return parser.parse_args()


def main():
    """Run a local question-routing test."""

    arguments = parse_arguments()

    decision = route_question(
        arguments.question
    )

    display_route(
        arguments.question,
        decision,
    )


if __name__ == "__main__":
    main()