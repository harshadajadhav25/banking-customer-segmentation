"""Groq LLM client for the banking RAG assistant."""

from __future__ import annotations

import argparse
import os
import tomllib
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 500


def load_local_secrets() -> dict[str, Any]:
    """Load settings from .streamlit/secrets.toml when available."""

    if not SECRETS_FILE.exists():
        return {}

    with SECRETS_FILE.open("rb") as secrets_file:
        return tomllib.load(secrets_file)


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from environment variables or Streamlit secrets."""

    environment_value = os.getenv(name)

    if environment_value:
        return environment_value

    secrets = load_local_secrets()
    secret_value = secrets.get(name)

    if secret_value is not None:
        return str(secret_value)

    return default


def create_groq_client() -> Groq:
    """Create an authenticated Groq client."""

    load_dotenv(ENV_FILE)

    api_key = get_setting("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY was not found. Add it to "
            ".streamlit/secrets.toml or the environment variables."
        )

    return Groq(api_key=api_key)


def generate_response(
    user_prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Generate one response using the configured Groq model."""

    if not user_prompt or not user_prompt.strip():
        raise ValueError("The user prompt cannot be empty.")

    selected_model = (
        model
        or get_setting("GROQ_MODEL", DEFAULT_MODEL)
        or DEFAULT_MODEL
    )

    messages: list[dict[str, str]] = []

    if system_prompt:
        messages.append(
            {
                "role": "system",
                "content": system_prompt.strip(),
            }
        )

    messages.append(
        {
            "role": "user",
            "content": user_prompt.strip(),
        }
    )

    client = create_groq_client()

    completion = client.chat.completions.create(
        model=selected_model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )

    response_text = completion.choices[0].message.content

    if not response_text:
        raise RuntimeError("Groq returned an empty response.")

    return response_text.strip()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Test the Groq LLM connection."
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        default=(
            "Reply with exactly: "
            "Groq connection successful."
        ),
        help="Prompt to send to Groq.",
    )

    return parser.parse_args()


def main() -> None:
    """Run a safe Groq connection test."""

    arguments = parse_arguments()

    print("GROQ LLM CONNECTION TEST")
    print("-" * 72)
    print(
        f"Model: "
        f"{get_setting('GROQ_MODEL', DEFAULT_MODEL)}"
    )
    print("Sending test request...")

    response = generate_response(
        user_prompt=arguments.prompt,
        system_prompt=(
            "Follow the user's formatting instruction exactly. "
            "Do not add explanations."
        ),
    )

    print("-" * 72)
    print(response)
    print("-" * 72)
    print("Groq connection test completed successfully.")


if __name__ == "__main__":
    main()