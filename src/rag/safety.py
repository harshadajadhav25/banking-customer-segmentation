"""Deterministic safety checks for Banking Analytics Copilot questions."""

import argparse
import re
from dataclasses import dataclass


GENERAL_DISCLAIMER = (
    "This assistant explains an educational analytics project built "
    "from historical anonymized data. It does not provide financial "
    "advice or make eligibility, lending, pricing, credit, or adverse "
    "banking decisions."
)


@dataclass(frozen=True)
class SafetyDecision:
    """Result returned by the question-safety classifier."""

    allowed: bool
    category: str
    reason: str
    response: str
    matched_rule: str | None = None


def normalize_question(question):
    """Normalize a user question for deterministic pattern checks."""

    normalized_question = str(question).strip().lower()

    normalized_question = re.sub(
        r"\s+",
        " ",
        normalized_question,
    )

    return normalized_question


def matches_any_pattern(text, patterns):
    """Return the first matching regular-expression pattern."""

    for pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return pattern

    return None


CREDENTIAL_PATTERNS = [
    (
        r"\b(show|give|tell|reveal|display|print|return|expose|"
        r"share|find|get)\b.{0,40}"
        r"\b(api[\s_-]*key|password|secret|token|credential|"
        r"database password|environment variable)\b"
    ),
    (
        r"\b(api[\s_-]*key|password|secret|token|credential)\b"
        r".{0,40}\b(show|give|reveal|display|print|return|"
        r"expose|share)\b"
    ),
    r"\bwhat is the (api[\s_-]*key|password|secret|token)\b",
]


PROMPT_INJECTION_PATTERNS = [
    r"\bignore (all |any )?(previous|prior|system|developer) "
    r"(instructions|rules|prompts)\b",
    r"\bdisregard (all |any )?(previous|prior|system|developer) "
    r"(instructions|rules|prompts)\b",
    r"\boverride (the )?(safety|system|developer|responsible use) "
    r"(rules|instructions|prompt)\b",
    r"\bbypass (the )?(safety|security|guardrail|restrictions)\b",
    r"\breveal (the )?(system|developer|hidden) prompt\b",
    r"\bshow (me )?(the )?(system|developer|hidden) prompt\b",
    r"\bjailbreak\b",
    r"\bdeveloper mode\b",
]


LOAN_DECISION_PATTERNS = [
    (
        r"\b(should|can|would|will|must)\b.{0,60}"
        r"\b(customer|client|person|applicant)\b.{0,60}"
        r"\b(approve|approved|reject|rejected|deny|denied|"
        r"qualify|qualified|eligible|eligibility)\b.{0,40}"
        r"\b(loan|credit|mortgage|card|product)\b"
    ),
    (
        r"\b(should|can|would|will|must)\b.{0,60}"
        r"\b(approve|approved|reject|rejected|deny|denied|"
        r"qualify|qualified|eligible|eligibility)\b.{0,60}"
        r"\b(customer|client|person|applicant|loan|credit|"
        r"mortgage|card|product)\b"
    ),
    (
        r"\b(is|are)\b.{0,50}"
        r"\b(customer|client|person|applicant)\b.{0,50}"
        r"\b(eligible|qualified|approved)\b.{0,40}"
        r"\b(loan|credit|mortgage|card|product)\b"
    ),
    (
        r"\b(approve|reject|deny)\b.{0,40}"
        r"\b(customer|client|loan|credit|application)\b"
    ),
]


ADVERSE_ACTION_PATTERNS = [
    (
        r"\bwhich (customer|customers|client|clients|people)\b"
        r".{0,60}\b(deny|denied|reject|rejected|exclude|"
        r"block|refuse)\b"
    ),
    (
        r"\bwho should be\b.{0,40}"
        r"\b(denied|rejected|excluded|blocked|refused)\b"
    ),
    (
        r"\bfind\b.{0,40}"
        r"\b(customer|customers|client|clients)\b.{0,40}"
        r"\b(to deny|to reject|to exclude|to block)\b"
    ),
]


PRICING_DECISION_PATTERNS = [
    (
        r"\b(what|which|how much)\b.{0,50}"
        r"\b(interest rate|price|pricing|fee|premium)\b"
        r".{0,50}\b(customer|client|charge|offer)\b"
    ),
    (
        r"\b(should|must)\b.{0,40}"
        r"\b(customer|client)\b.{0,40}"
        r"\b(pay|be charged|receive)\b.{0,40}"
        r"\b(rate|price|fee|premium|interest)\b"
    ),
]


FRAUD_ACCUSATION_PATTERNS = [
    (
        r"\b(is|are)\b.{0,40}"
        r"\b(customer|client|account)\b.{0,40}"
        r"\b(fraud|fraudulent|criminal|money laundering)\b"
    ),
    (
        r"\bwhich\b.{0,30}"
        r"\b(customer|customers|client|clients|accounts)\b"
        r".{0,40}\b(fraud|fraudulent|criminal|"
        r"money laundering)\b"
    ),
    (
        r"\bidentify\b.{0,40}"
        r"\b(fraudsters|criminals|fraudulent customers)\b"
    ),
]


PROTECTED_ATTRIBUTE_PATTERNS = [
    (
        r"\b(use|based on|because of|consider)\b.{0,30}"
        r"\b(gender|sex|race|ethnicity|religion|age|"
        r"nationality|disability|marital status)\b"
        r".{0,60}\b(approve|reject|deny|eligible|eligibility|"
        r"price|pricing|loan|credit|product)\b"
    ),
    (
        r"\b(approve|reject|deny|eligible|eligibility|"
        r"price|pricing)\b.{0,60}"
        r"\b(gender|sex|race|ethnicity|religion|age|"
        r"nationality|disability|marital status)\b"
    ),
]


IDENTITY_PATTERNS = [
    (
        r"\b(find|reveal|identify|tell|show|give)\b.{0,40}"
        r"\b(real name|real identity|home address|phone number|"
        r"email address|contact information)\b"
        r".{0,50}\b(customer|client|account)\b"
    ),
    (
        r"\bwho is customer\b.{0,20}\b(in real life|really)\b"
    ),
    r"\bdeanonymi[sz]e\b",
]


DESTRUCTIVE_SQL_PATTERNS = [
    r"\bdrop\s+(table|schema|database)\b",
    r"\btruncate\s+table\b",
    r"\bdelete\s+from\b",
    r"\balter\s+table\b",
    r"\bgrant\s+.+\s+to\b",
    r"\brevoke\s+.+\s+from\b",
    r"\bexecute\b.{0,30}\b(destructive|delete|drop|truncate)\b",
]


PERSONAL_FINANCIAL_ADVICE_PATTERNS = [
    (
        r"\bhow much should\b.{0,40}"
        r"\b(customer|client|i|they|he|she)\b.{0,40}"
        r"\b(save|invest|borrow|spend|repay)\b"
    ),
    (
        r"\bshould\b.{0,30}"
        r"\b(customer|client|i|they|he|she)\b.{0,30}"
        r"\b(buy|sell|invest|borrow)\b"
    ),
]


SAFETY_RULES = [
    {
        "category": "credentials_and_secrets",
        "patterns": CREDENTIAL_PATTERNS,
        "reason": (
            "The question requests credentials, secrets, "
            "tokens, or private configuration."
        ),
        "response": (
            "I cannot provide API keys, passwords, tokens, "
            "credentials, environment variables, or private "
            "configuration values."
        ),
    },
    {
        "category": "prompt_injection",
        "patterns": PROMPT_INJECTION_PATTERNS,
        "reason": (
            "The question attempts to override or reveal "
            "system safety instructions."
        ),
        "response": (
            "I cannot ignore safety rules, reveal hidden "
            "instructions, or bypass the project's responsible-use "
            "controls. I can still answer supported questions about "
            "the banking analytics project."
        ),
    },
    {
        "category": "loan_or_product_decision",
        "patterns": LOAN_DECISION_PATTERNS,
        "reason": (
            "The question requests a loan, credit, or product "
            "approval or eligibility decision."
        ),
        "response": (
            "I cannot make loan approval, credit, or product "
            "eligibility decisions. I can explain whether the "
            "historical record triggered a rule-based Personal "
            "Loan Consultation recommendation and show its "
            "documented reason. A consultation recommendation is "
            "not an approval decision."
        ),
    },
    {
        "category": "adverse_action",
        "patterns": ADVERSE_ACTION_PATTERNS,
        "reason": (
            "The question requests denial, exclusion, or another "
            "adverse action against customers."
        ),
        "response": (
            "I cannot recommend denying, excluding, or taking "
            "adverse action against customers. I can provide "
            "descriptive, aggregated information about the "
            "historical customer segments."
        ),
    },
    {
        "category": "pricing_decision",
        "patterns": PRICING_DECISION_PATTERNS,
        "reason": (
            "The question requests an individual pricing or "
            "interest-rate decision."
        ),
        "response": (
            "I cannot make pricing, interest-rate, fee, or premium "
            "decisions. I can explain the project's historical "
            "analytics and documented recommendation rules."
        ),
    },
    {
        "category": "fraud_accusation",
        "patterns": FRAUD_ACCUSATION_PATTERNS,
        "reason": (
            "The question asks the assistant to accuse or classify "
            "a customer as fraudulent or criminal."
        ),
        "response": (
            "I cannot accuse or classify customers as fraudulent "
            "or criminal. This project does not contain a validated "
            "fraud-detection model."
        ),
    },
    {
        "category": "protected_attribute_decision",
        "patterns": PROTECTED_ATTRIBUTE_PATTERNS,
        "reason": (
            "The question requests a decision using a protected "
            "or sensitive personal characteristic."
        ),
        "response": (
            "I cannot make lending, eligibility, pricing, or "
            "product decisions using protected or sensitive "
            "personal characteristics."
        ),
    },
    {
        "category": "identity_or_privacy",
        "patterns": IDENTITY_PATTERNS,
        "reason": (
            "The question attempts to identify an anonymized "
            "customer or obtain personal contact information."
        ),
        "response": (
            "I cannot identify anonymized customers or provide "
            "real names, addresses, phone numbers, email addresses, "
            "or other personal contact information."
        ),
    },
    {
        "category": "destructive_sql",
        "patterns": DESTRUCTIVE_SQL_PATTERNS,
        "reason": (
            "The question requests destructive or unauthorized "
            "database activity."
        ),
        "response": (
            "I cannot execute or provide assistance with destructive "
            "database operations in this application. The AI "
            "assistant has no unrestricted SQL access."
        ),
    },
    {
        "category": "personal_financial_advice",
        "patterns": PERSONAL_FINANCIAL_ADVICE_PATTERNS,
        "reason": (
            "The question requests personalized financial advice."
        ),
        "response": (
            "I cannot provide personalized financial advice. I can "
            "explain the project's historical analytics and "
            "rule-based product suggestions."
        ),
    },
]


def evaluate_question(question):
    """Evaluate whether a question is allowed for the AI assistant."""

    normalized_question = normalize_question(
        question
    )

    if not normalized_question:
        return SafetyDecision(
            allowed=False,
            category="empty_question",
            reason="The question is empty.",
            response=(
                "Please enter a question about the banking "
                "analytics project."
            ),
        )

    if len(normalized_question) > 2000:
        return SafetyDecision(
            allowed=False,
            category="question_too_long",
            reason=(
                "The question exceeds the supported "
                "character limit."
            ),
            response=(
                "Please shorten the question to fewer than "
                "2,000 characters."
            ),
        )

    for safety_rule in SAFETY_RULES:
        matched_pattern = matches_any_pattern(
            normalized_question,
            safety_rule["patterns"],
        )

        if matched_pattern:
            return SafetyDecision(
                allowed=False,
                category=safety_rule["category"],
                reason=safety_rule["reason"],
                response=(
                    safety_rule["response"]
                    + "\n\n"
                    + GENERAL_DISCLAIMER
                ),
                matched_rule=matched_pattern,
            )

    return SafetyDecision(
        allowed=True,
        category="allowed",
        reason=(
            "No prohibited deterministic safety pattern matched."
        ),
        response="",
    )


def display_decision(question, decision):
    """Print a safety-classification result."""

    print("RAG QUESTION SAFETY CHECK")
    print("-" * 72)
    print(f"Question: {question}")
    print(f"Allowed: {decision.allowed}")
    print(f"Category: {decision.category}")
    print(f"Reason: {decision.reason}")

    if decision.matched_rule:
        print(
            "Matched rule: "
            f"{decision.matched_rule}"
        )

    if decision.response:
        print("-" * 72)
        print("Safe response:")
        print(decision.response)


def parse_arguments():
    """Parse the test question from the command line."""

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a question against the Banking "
            "Analytics Copilot safety rules."
        )
    )

    parser.add_argument(
        "question",
        type=str,
        help="Question to evaluate.",
    )

    return parser.parse_args()


def main():
    """Run a local safety-classification test."""

    arguments = parse_arguments()

    decision = evaluate_question(
        arguments.question
    )

    display_decision(
        arguments.question,
        decision,
    )


if __name__ == "__main__":
    main()