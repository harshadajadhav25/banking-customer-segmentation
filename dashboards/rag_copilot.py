"""Streamlit interface for the Banking RAG Copilot."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from src.rag.answer_generator import generate_grounded_answer


EXAMPLE_QUESTIONS = [
    "Why were five customer segments selected?",
    (
        "Why was Customer 25 recommended "
        "Overdraft Protection?"
    ),
    (
        "What are the documented conditions for a "
        "Personal Loan Consultation recommendation?"
    ),
]


def configure_groq_secrets() -> None:
    """Expose Streamlit Cloud secrets to the Groq client."""

    try:
        groq_api_key = st.secrets.get("GROQ_API_KEY")
        groq_model = st.secrets.get(
            "GROQ_MODEL",
            "openai/gpt-oss-20b",
        )
    except FileNotFoundError:
        groq_api_key = None
        groq_model = "openai/gpt-oss-20b"

    if groq_api_key:
        os.environ["GROQ_API_KEY"] = str(
            groq_api_key
        )

    if groq_model:
        os.environ["GROQ_MODEL"] = str(
            groq_model
        )


def initialize_chat_history() -> None:
    """Create the chat history in Streamlit session state."""

    if "rag_chat_history" not in st.session_state:
        st.session_state.rag_chat_history = []


def clear_chat_history() -> None:
    """Remove the current RAG conversation."""

    st.session_state.rag_chat_history = []


def add_chat_message(
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add one message to the chat history."""

    st.session_state.rag_chat_history.append(
        {
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
    )


def display_message_metadata(
    metadata: dict[str, Any],
) -> None:
    """Display compact evidence metadata."""

    if not metadata:
        return

    route = metadata.get("route", "unknown")
    analytics_count = metadata.get(
        "analytics_count",
        0,
    )
    document_count = metadata.get(
        "document_count",
        0,
    )
    llm_called = metadata.get(
        "llm_called",
        False,
    )

    st.caption(
        f"Route: {route} · "
        f"Verified analytics: {analytics_count} · "
        f"Document sources: {document_count} · "
        f"LLM used: {'Yes' if llm_called else 'No'}"
    )


def display_chat_history() -> None:
    """Render all existing chat messages."""

    for message in st.session_state.rag_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant":
                display_message_metadata(
                    message.get("metadata", {})
                )


def get_selected_example() -> str | None:
    """Display example-question buttons."""

    st.markdown("#### Try an example")

    columns = st.columns(3)
    selected_question = None

    for index, question in enumerate(
        EXAMPLE_QUESTIONS
    ):
        button_label = (
            "Model selection"
            if index == 0
            else (
                "Customer recommendation"
                if index == 1
                else "Recommendation rules"
            )
        )

        if columns[index].button(
            button_label,
            key=f"rag_example_{index}",
            use_container_width=True,
            help=question,
        ):
            selected_question = question

    return selected_question


def answer_question(question: str) -> None:
    """Generate and store one grounded answer."""

    add_chat_message(
        role="user",
        content=question,
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Retrieving verified project evidence..."
        ):
            try:
                result = generate_grounded_answer(
                    question=question,
                    top_k=5,
                    minimum_score=0.20,
                    max_tokens=700,
                )

                answer = result["answer"]
                route_data = result.get("route") or {}

                metadata = {
                    "route": route_data.get(
                        "route_type",
                        "blocked",
                    ),
                    "analytics_count": len(
                        result.get(
                            "tool_results",
                            [],
                        )
                    ),
                    "document_count": len(
                        result.get(
                            "retrieved_chunks",
                            [],
                        )
                    ),
                    "llm_called": result.get(
                        "llm_called",
                        False,
                    ),
                }

                st.markdown(answer)
                display_message_metadata(metadata)

                add_chat_message(
                    role="assistant",
                    content=answer,
                    metadata=metadata,
                )

            except Exception as error:
                error_message = (
                    "The AI Copilot could not generate "
                    "a reliable answer. Check the Groq "
                    "API configuration and try again."
                )

                st.error(error_message)

                with st.expander(
                    "Technical details"
                ):
                    st.code(
                        f"{type(error).__name__}: "
                        f"{error}"
                    )

                add_chat_message(
                    role="assistant",
                    content=error_message,
                    metadata={
                        "route": "error",
                        "analytics_count": 0,
                        "document_count": 0,
                        "llm_called": False,
                    },
                )


def build_rag_copilot() -> None:
    """Build the complete AI Copilot dashboard section."""

    configure_groq_secrets()
    initialize_chat_history()

    header_left, header_right = st.columns(
        [5, 1]
    )

    with header_left:
        st.markdown(
            '<div class="section-label">'
            "Grounded AI assistant"
            "</div>",
            unsafe_allow_html=True,
        )
        st.subheader("Banking Analytics Copilot")
        st.write(
            "Ask questions about customer segments, "
            "recommendation rules, model design, and "
            "verified historical customer records."
        )

    with header_right:
        st.write("")
        st.write("")

        if st.button(
            "Clear chat",
            key="clear_rag_chat",
            use_container_width=True,
        ):
            clear_chat_history()
            st.rerun()

    st.info(
        "The Copilot answers from verified project "
        "documentation and controlled analytics tools. "
        "It does not make lending, eligibility, pricing, "
        "credit, fraud, or adverse-action decisions."
    )

    selected_example = get_selected_example()

    st.divider()

    if not st.session_state.rag_chat_history:
        st.markdown(
            "Ask a question below or choose an example "
            "to begin."
        )

    display_chat_history()

    typed_question = st.chat_input(
        "Ask about segments, recommendations, or the model",
        key="rag_question_input",
    )

    question = selected_example or typed_question

    if question:
        answer_question(question)