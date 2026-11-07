# Product Recommendation Rules

## Purpose

This document explains the transparent business rules used by the Banking Customer Segmentation and Product Recommendation Platform.

The recommendation engine is implemented in `src/recommendations/generate_recommendations.py`. The current recommendation version is `rules_v1`.

The engine generates product suggestions from historical account behavior, customer-segment assignments, account balances, cash flow, activity, and existing product ownership.

The recommendations are not predictions of customer behavior. They are not product approvals, eligibility decisions, credit decisions, pricing decisions, or adverse-action decisions.

## Recommendation Inputs

The recommendation engine uses the following customer-level fields:

| Field | Meaning |
|---|---|
| `customer_id` | Anonymized customer identifier |
| `account_id` | Account associated with the customer |
| `cluster_id` | Numeric K-Means cluster identifier |
| `segment_name` | Business-friendly customer segment |
| `days_since_last_transaction` | Number of days since the customer's latest transaction |
| `average_monthly_transaction_count` | Transaction count divided by active-month count |
| `average_monthly_transaction_volume` | Total transaction volume divided by active-month count |
| `net_cash_flow` | Total credits minus total debits |
| `average_balance` | Average historical account balance |
| `latest_balance` | Most recently observed account balance |
| `negative_balance_percentage` | Percentage of transactions associated with a negative balance |
| `has_card` | Whether the customer currently has a payment card |
| `has_loan` | Whether the customer currently has a loan |
| `payment_order_count` | Number of scheduled payment orders |
| `banking_product_count` | Number of banking products associated with the customer |
| `snapshot_date` | Date represented by the Customer 360 snapshot |

## General Recommendation Process

For every customer, the engine:

1. Evaluates all six product rules.
2. Creates every recommendation for which the customer satisfies the required conditions.
3. Calculates a recommendation score for each eligible product.
4. Sorts recommendations from highest score to lowest score.
5. Keeps a maximum of three recommendations per customer.
6. Assigns ranks starting with rank 1.
7. Stores the recommendation version and snapshot date.
8. Validates coverage, uniqueness, scores, and ranks.
9. Saves the results to a CSV file and PostgreSQL.

A higher recommendation score indicates that more of the rule's supporting conditions were satisfied. It is not a probability that the customer will purchase or qualify for the product.

## Payment Card

### Required Condition

A Payment Card recommendation is generated only when the customer does not currently have a card:

```python
not bool(customer["has_card"])
```

### Score Calculation

The starting score is 70.

Add 10 points when:

```text
average_monthly_transaction_count >= 5
```

Add another 10 points when:

```text
segment_name == "High-Value Multi-Product"
```

Possible scores are 70, 80, or 90.

### Recommendation Reason

The customer does not currently have a card and shows transaction activity that may benefit from card-based payments.

### Interpretation

This recommendation identifies an opportunity to discuss card-based payments with a customer who does not currently have a card. It does not determine card eligibility or guarantee that a card will be issued.

## Personal Loan Consultation

### Required Conditions

A Personal Loan Consultation recommendation is generated only when all the following conditions are true:

```text
has_loan == False
days_since_last_transaction <= 30
net_cash_flow > 0
negative_balance_percentage <= 1
```

This means:

- The customer does not currently have a loan.
- The customer has transacted within the last 30 days.
- The customer has positive net cash flow.
- The customer's negative-balance activity is no more than 1 percent.

### Score Calculation

The starting score is 60.

Add 10 points when:

```text
average_balance >= 30000
```

Add another 10 points when:

```text
segment_name == "High-Value Multi-Product"
```

Possible scores are 60, 70, or 80.

### Recommendation Reason

The customer is active, has positive net cash flow, and does not currently have a loan. The recommendation is an invitation for review and not an approval decision.

### Interpretation

This recommendation means that a customer may be suitable for an optional conversation about loan products.

It must never be described as:

- A loan approval.
- A guarantee of eligibility.
- A creditworthiness assessment.
- A pricing decision.
- A replacement for formal underwriting.

## Savings Account

### Required Conditions

A Savings Account recommendation is generated when both conditions are true:

```text
net_cash_flow > 0
latest_balance > 0
```

### Score Calculation

The starting score is 55.

Add 15 points when:

```text
average_balance >= 30000
```

Add 10 points when:

```text
net_cash_flow >= 50000
```

Possible scores are 55, 65, 70, or 80.

### Recommendation Reason

Positive cash flow and account balances indicate an opportunity to move available funds into savings.

### Interpretation

This recommendation identifies a potential savings opportunity from positive historical cash flow and balances. The rule does not determine how much a customer should save and does not provide financial advice.

## Overdraft Protection

### Required Condition

An Overdraft Protection recommendation is generated when:

```text
negative_balance_percentage > 0
```

### Score Calculation

The score is calculated as:

```python
min(
    95,
    70 + int(negative_balance_percentage * 5),
)
```

The score starts from a base of 70, increases as negative-balance activity increases, and is capped at 95.

### Recommendation Reason

Negative-balance activity indicates that balance protection and account alerts may be useful.

### Interpretation

This recommendation identifies a possible need for balance-management services or account alerts.

Negative-balance activity must not automatically be interpreted as:

- Financial distress.
- Credit risk.
- Fraud.
- Inability to repay debt.
- Product eligibility.

## Automatic Payment Setup

### Required Conditions

An Automatic Payment Setup recommendation is generated when both conditions are true:

```text
payment_order_count == 0
days_since_last_transaction <= 30
```

### Score Calculation

The recommendation uses a fixed score of 55.

### Recommendation Reason

The customer is active but has no scheduled payment orders, so automatic payments may add convenience.

### Interpretation

This recommendation identifies an opportunity to explain scheduled or automatic payment services to an active customer who does not currently use them.

## Account Re-Engagement Review

### Required Condition

An Account Re-Engagement Review recommendation is generated when:

```text
days_since_last_transaction > 30
```

### Score Calculation

The score is calculated as:

```python
min(
    95,
    70 + int(days_since_last_transaction / 10),
)
```

The score starts from a base of 70, increases with the number of inactive days, and is capped at 95.

### Recommendation Reason

The account has had an extended period without transactions and may benefit from a service review.

### Interpretation

This recommendation identifies an opportunity for an account review or appropriate re-engagement communication. The rule does not establish why the customer is inactive. It must not claim that the customer is dissatisfied, experiencing financial difficulty, or planning to close the account.

## Ranking Logic

A customer may satisfy more than three product rules. The engine sorts all eligible recommendations by recommendation score in descending order:

```python
customer_recommendations.sort(
    key=lambda item: item["recommendation_score"],
    reverse=True,
)
```

It then keeps only the first three recommendations:

```python
customer_recommendations[:3]
```

Ranks are assigned as:

```text
Rank 1 = highest-scoring retained recommendation
Rank 2 = second-highest retained recommendation
Rank 3 = third-highest retained recommendation
```

When two recommendations have the same score, Python's stable sorting preserves the order in which the rules were evaluated.

The rule-evaluation order is:

1. Payment Card.
2. Personal Loan Consultation.
3. Savings Account.
4. Overdraft Protection.
5. Automatic Payment Setup.
6. Account Re-Engagement Review.

## Current Recommendation Output

The current validated output contains:

```text
12,175 recommendations
4,500 customers with recommendations
6 product types
Maximum of 3 recommendations per customer
```

Current recommendation counts by product are:

| Recommended Product | Recommendation Count |
|---|---:|
| Savings Account | 4,452 |
| Payment Card | 3,607 |
| Personal Loan Consultation | 3,566 |
| Overdraft Protection | 287 |
| Automatic Payment Setup | 188 |
| Account Re-Engagement Review | 75 |

These counts represent the current dataset and recommendation version. They may change when source data, customer features, segments, or business rules change.

## Validation Rules

Before the results are saved, the pipeline validates:

- Every input customer has at least one retained recommendation.
- No duplicate customer-product combinations exist.
- Recommendation scores are between 0 and 100.
- Recommendation ranks are between 1 and 3.
- No customer has more than three recommendations.

The current validated output has:

```text
Customers without recommendations: 0
Duplicate customer-product pairs: 0
Invalid scores: 0
Invalid ranks: 0
Customers with more than 3 recommendations: 0
```

## Output Locations

The validated recommendations are saved to:

```text
data/processed/recommendations/customer_product_recommendations.csv
```

They are also written to:

```text
ml.product_recommendations
```

The analytics-ready dbt model is:

```text
analytics.mart_product_recommendations
```

## Responsible Use

The recommendation engine is intended for:

- Portfolio demonstrations.
- Product-opportunity analysis.
- Explainable marketing-rule demonstrations.
- Customer-service discussion support.
- Educational and portfolio purposes.

It must not be used for:

- Automatic loan approval or rejection.
- Credit-limit decisions.
- Product eligibility decisions.
- Interest-rate or pricing decisions.
- Adverse actions.
- Claims about financial health.
- Predictions that a customer will purchase a product.
- Replacing human review in high-impact financial decisions.

The AI assistant must clearly identify recommendations as rule-based suggestions and must never describe a recommendation score as a purchase probability, approval probability, or credit score.
