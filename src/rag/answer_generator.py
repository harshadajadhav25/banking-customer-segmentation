"""Generate grounded answers for the banking RAG assistant."""

from __future__ import annotations

import argparse
from typing import Any

from src.rag.llm_client import generate_response
from src.rag.prompt_builder import build_prompt_package


DEFAULT_MAX_TOKENS = 700
DEFAULT_TEMPERATURE = 0.1


def generate_grounded_answer(
    question: str,
    top_k: int = 5,
    minimum_score: float = 0.20,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict[str, Any]:
    """Generate one safe, evidence-grounded answer."""

    cleaned_question = str(question).strip()

    if not cleaned_question:
        raise ValueError("The question cannot be empty.")

    prompt_package = build_prompt_package(
        question=cleaned_question,
        top_k=top_k,
        minimum_score=minimum_score,
    )

    status = prompt_package["status"]

    if status != "ready":
        return {
            "status": status,
            "question": cleaned_question,
            "answer": prompt_package[
                "safe_response"
            ],
            "llm_called": False,
            "route": (
                prompt_package["context_package"]
                .get("route")
            ),
            "tool_results": (
                prompt_package["context_package"]
                .get("tool_results", [])
            ),
            "retrieved_chunks": (
                prompt_package["context_package"]
                .get("retrieved_chunks", [])
            ),
        }

    answer = generate_response(
        user_prompt=prompt_package[
            "user_prompt"
        ],
        system_prompt=prompt_package[
            "system_prompt"
        ],
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=max_tokens,
    )

    context_package = prompt_package[
        "context_package"
    ]

    return {
        "status": "answered",
        "question": cleaned_question,
        "answer": answer,
        "llm_called": True,
        "route": context_package.get("route"),
        "tool_results": context_package.get(
            "tool_results",
            [],
        ),
        "retrieved_chunks": context_package.get(
            "retrieved_chunks",
            [],
        ),
    }


def display_answer(result: dict[str, Any]) -> None:
    """Display an answer and its execution summary."""

    print("BANKING RAG ASSISTANT")
    print("-" * 72)
    print(f"Question: {result['question']}")
    print(f"Status: {result['status']}")
    print(f"LLM called: {result['llm_called']}")

    route = result.get("route")

    if route:
        print(
            "Route: "
            f"{route.get('route_type', 'unknown')}"
        )

    print(
        "Analytics results used: "
        f"{len(result.get('tool_results', []))}"
    )
    print(
        "Document chunks used: "
        f"{len(result.get('retrieved_chunks', []))}"
    )
    print("-" * 72)
    print(result["answer"])
    print("-" * 72)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Ask the grounded banking RAG assistant "
            "a question."
        )
    )

    parser.add_argument(
        "question",
        help="Question for the banking RAG assistant.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of document chunks.",
    )

    parser.add_argument(
        "--minimum-score",
        type=float,
        default=0.20,
        help="Minimum hybrid retrieval score.",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum completion tokens.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the grounded RAG assistant from the command line."""

    arguments = parse_arguments()

    try:
        result = generate_grounded_answer(
            question=arguments.question,
            top_k=arguments.top_k,
            minimum_score=arguments.minimum_score,
            max_tokens=arguments.max_tokens,
        )

        display_answer(result)

    except Exception as error:
        print("BANKING RAG ASSISTANT")
        print("-" * 72)
        print("Status: error")
        print(
            "The assistant could not generate "
            "a reliable answer."
        )
        print(
            f"Error type: "
            f"{type(error).__name__}"
        )
        print(f"Error: {error}")
        raise


if __name__ == "__main__":
    main()