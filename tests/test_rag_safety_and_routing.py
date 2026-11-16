"""Tests for deterministic RAG safety and question routing."""

from src.rag.question_router import route_question
from src.rag.safety import evaluate_question


def test_allows_documentation_question():
    """Normal project questions should be allowed."""

    decision = evaluate_question(
        "Why were five customer segments selected?"
    )

    assert decision.allowed is True
    assert decision.category == "allowed"


def test_blocks_loan_approval_question():
    """The assistant must not make lending decisions."""

    decision = evaluate_question(
        "Should Customer 25 be approved for a loan?"
    )

    assert decision.allowed is False
    assert (
        decision.category
        == "loan_or_product_decision"
    )
    assert "cannot make loan approval" in (
        decision.response.lower()
    )


def test_blocks_fraud_accusation():
    """The assistant must not accuse customers of fraud."""

    decision = evaluate_question(
        "Is Customer 25 committing fraud?"
    )

    assert decision.allowed is False
    assert decision.category == "fraud_accusation"


def test_routes_model_question_to_documentation():
    """Model questions should use documentation retrieval."""

    route = route_question(
        "Why were five customer segments selected?"
    )

    assert route.route_type == "documentation_rag"
    assert route.requires_retrieval is True
    assert route.tool_calls == []


def test_routes_customer_recommendation_question():
    """Customer recommendation questions need verified tools."""

    route = route_question(
        "Why was Customer 25 recommended "
        "Overdraft Protection?"
    )

    assert (
        route.route_type
        == "hybrid_customer_recommendation"
    )
    assert route.requires_retrieval is True
    assert route.detected_customer_id == 25

    tool_names = [
        tool_call.tool_name
        for tool_call in route.tool_calls
    ]

    assert "get_customer_recommendations" in tool_names
    assert "get_customer_profile" in tool_names


def test_detects_customer_profile_question():
    """Customer profile questions should use the profile tool."""

    route = route_question(
        "Show the historical profile for Customer 25."
    )

    assert route.detected_customer_id == 25

    tool_names = [
        tool_call.tool_name
        for tool_call in route.tool_calls
    ]

    assert "get_customer_profile" in tool_names