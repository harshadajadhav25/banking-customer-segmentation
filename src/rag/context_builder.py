"""Build verified evidence packages for Banking Analytics Copilot."""

import argparse
import json

from src.rag.analytics_tools import BankingAnalyticsTools
from src.rag.question_router import route_question
from src.rag.retriever import KnowledgeRetriever
from src.rag.safety import evaluate_question


DEFAULT_TOP_K = 5
DEFAULT_MINIMUM_SCORE = 0.25


class RAGContextBuilder:
    """Combine safety, routing, analytics, and document retrieval."""

    def __init__(
        self,
        retriever=None,
        analytics_tools=None,
    ):
        self._retriever = retriever
        self._analytics_tools = analytics_tools

    def get_retriever(self):
        """Load the semantic retriever only when required."""

        if self._retriever is None:
            self._retriever = KnowledgeRetriever()

        return self._retriever

    def get_analytics_tools(self):
        """Load approved analytics tools only when required."""

        if self._analytics_tools is None:
            self._analytics_tools = (
                BankingAnalyticsTools()
            )

        return self._analytics_tools

    def execute_analytics_tools(
        self,
        tool_calls,
    ):
        """Execute all approved tool calls from the router."""

        tool_results = []
        tool_errors = []

        if not tool_calls:
            return tool_results, tool_errors

        analytics_tools = self.get_analytics_tools()

        for tool_call in tool_calls:
            try:
                result = analytics_tools.execute_tool(
                    tool_name=tool_call.tool_name,
                    arguments=tool_call.arguments,
                )

                tool_results.append(
                    {
                        "tool_name": (
                            tool_call.tool_name
                        ),
                        "arguments": (
                            tool_call.arguments
                        ),
                        "purpose": (
                            tool_call.purpose
                        ),
                        "result": result,
                    }
                )

            except (
                ValueError,
                FileNotFoundError,
                KeyError,
            ) as error:
                tool_errors.append(
                    {
                        "tool_name": (
                            tool_call.tool_name
                        ),
                        "arguments": (
                            tool_call.arguments
                        ),
                        "error": str(error),
                    }
                )

        return tool_results, tool_errors

    def retrieve_documents(
        self,
        question,
        requires_retrieval,
        top_k,
        minimum_score,
    ):
        """Retrieve knowledge chunks when the route requires RAG."""

        if not requires_retrieval:
            return []

        retriever = self.get_retriever()

        return retriever.retrieve(
            question=question,
            top_k=top_k,
            minimum_score=minimum_score,
        )

    def format_analytics_context(
        self,
        tool_results,
    ):
        """Format approved analytics results for an LLM prompt."""

        if not tool_results:
            return (
                "No approved analytics tool was required "
                "for this question."
            )

        formatted_results = []

        for result_number, tool_result in enumerate(
            tool_results,
            start=1,
        ):
            formatted_results.append(
                "\n".join(
                    [
                        (
                            f"[Analytics Result "
                            f"{result_number}]"
                        ),
                        (
                            "Tool: "
                            f"{tool_result['tool_name']}"
                        ),
                        (
                            "Purpose: "
                            f"{tool_result['purpose']}"
                        ),
                        "Verified result:",
                        json.dumps(
                            tool_result["result"],
                            indent=2,
                            ensure_ascii=False,
                        ),
                    ]
                )
            )

        return "\n\n---\n\n".join(
            formatted_results
        )

    def format_document_context(
        self,
        retrieved_chunks,
    ):
        """Format retrieved documentation for an LLM prompt."""

        if not retrieved_chunks:
            return (
                "No sufficiently relevant verified "
                "document context was retrieved."
            )

        retriever = self.get_retriever()

        return retriever.format_context(
            retrieved_chunks
        )

    def build(
        self,
        question,
        top_k=DEFAULT_TOP_K,
        minimum_score=DEFAULT_MINIMUM_SCORE,
    ):
        """Build one complete verified context package."""

        safety_decision = evaluate_question(
            question
        )

        if not safety_decision.allowed:
            return {
                "status": "blocked",
                "question": str(question).strip(),
                "safety": {
                    "allowed": False,
                    "category": (
                        safety_decision.category
                    ),
                    "reason": safety_decision.reason,
                },
                "safe_response": (
                    safety_decision.response
                ),
                "route": None,
                "tool_results": [],
                "tool_errors": [],
                "retrieved_chunks": [],
                "analytics_context": "",
                "document_context": "",
            }

        route_decision = route_question(
            question
        )

        tool_results, tool_errors = (
            self.execute_analytics_tools(
                route_decision.tool_calls
            )
        )

        retrieved_chunks = (
            self.retrieve_documents(
                question=question,
                requires_retrieval=(
                    route_decision
                    .requires_retrieval
                ),
                top_k=top_k,
                minimum_score=minimum_score,
            )
        )

        analytics_context = (
            self.format_analytics_context(
                tool_results
            )
        )

        document_context = (
            self.format_document_context(
                retrieved_chunks
            )
        )

        if tool_errors and not tool_results:
            status = "analytics_error"

        elif (
            not tool_results
            and not retrieved_chunks
        ):
            status = "insufficient_context"

        else:
            status = "ready"

        return {
            "status": status,
            "question": str(question).strip(),
            "safety": {
                "allowed": True,
                "category": (
                    safety_decision.category
                ),
                "reason": safety_decision.reason,
            },
            "route": {
                "route_type": (
                    route_decision.route_type
                ),
                "reason": (
                    route_decision.reason
                ),
                "detected_customer_id": (
                    route_decision
                    .detected_customer_id
                ),
                "detected_segments": (
                    route_decision
                    .detected_segments
                ),
                "requires_retrieval": (
                    route_decision
                    .requires_retrieval
                ),
            },
            "tool_results": tool_results,
            "tool_errors": tool_errors,
            "retrieved_chunks": (
                retrieved_chunks
            ),
            "analytics_context": (
                analytics_context
            ),
            "document_context": (
                document_context
            ),
        }


def display_context_summary(context_package):
    """Print a readable summary for local testing."""

    print("RAG VERIFIED CONTEXT BUILDER")
    print("-" * 72)
    print(
        f"Question: "
        f"{context_package['question']}"
    )
    print(
        f"Status: "
        f"{context_package['status']}"
    )
    print(
        "Safety allowed: "
        f"{context_package['safety']['allowed']}"
    )
    print(
        "Safety category: "
        f"{context_package['safety']['category']}"
    )

    if context_package["status"] == "blocked":
        print("-" * 72)
        print("Safe response:")
        print(
            context_package["safe_response"]
        )
        return

    print(
        "Route: "
        f"{context_package['route']['route_type']}"
    )

    print(
        "Analytics tools executed: "
        f"{len(context_package['tool_results'])}"
    )

    for tool_result in (
        context_package["tool_results"]
    ):
        print(
            "  - "
            f"{tool_result['tool_name']} "
            f"{tool_result['arguments']}"
        )

    if context_package["tool_errors"]:
        print(
            "Analytics tool errors: "
            f"{len(context_package['tool_errors'])}"
        )

        for tool_error in (
            context_package["tool_errors"]
        ):
            print(
                "  - "
                f"{tool_error['tool_name']}: "
                f"{tool_error['error']}"
            )

    print(
        "Document chunks retrieved: "
        f"{len(context_package['retrieved_chunks'])}"
    )

    for chunk in (
        context_package["retrieved_chunks"]
    ):
        print(
            "  - "
            f"Rank {chunk['rank']} | "
            f"{chunk['source_file']} | "
            f"{chunk['section_path']} | "
            f"score={chunk['hybrid_score']:.4f}"
        )

    print("-" * 72)
    print("Analytics context:")
    print(
        context_package["analytics_context"]
    )

    print("-" * 72)
    print("Document context preview:")

    document_preview = (
        context_package["document_context"]
    )

    if len(document_preview) > 1500:
        document_preview = (
            document_preview[:1497] + "..."
        )

    print(document_preview)


def parse_arguments():
    """Parse command-line context-builder options."""

    parser = argparse.ArgumentParser(
        description=(
            "Build verified context for a Banking "
            "Analytics Copilot question."
        )
    )

    parser.add_argument(
        "question",
        type=str,
        help="Question to process.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Maximum document chunks to retrieve.",
    )

    parser.add_argument(
        "--minimum-score",
        type=float,
        default=DEFAULT_MINIMUM_SCORE,
        help="Minimum hybrid retrieval score.",
    )

    return parser.parse_args()


def main():
    """Run a local context-building test."""

    arguments = parse_arguments()

    context_builder = RAGContextBuilder()

    context_package = context_builder.build(
        question=arguments.question,
        top_k=arguments.top_k,
        minimum_score=(
            arguments.minimum_score
        ),
    )

    display_context_summary(
        context_package
    )


if __name__ == "__main__":
    main()