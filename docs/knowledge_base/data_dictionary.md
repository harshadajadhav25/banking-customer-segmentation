# Banking Customer Analytics Data Dictionary

## Purpose

This document defines the customer, account, transaction, balance, product, segmentation, and model-output fields used by the Banking Customer Segmentation and Product Recommendation Platform.

The principal customer-level dataset is `analytics.mart_customer_segments`. It contains one analytics record per customer and combines Customer 360 features with the latest segmentation output.

The source data is the anonymized historical PKDD'99 Czech banking dataset. Monetary values retain the dataset's original currency context and must not be presented as current customer activity.

## Identifier Fields

### `customer_id`

An anonymized unique identifier for a customer. It is used to connect the Customer 360 record, segment assignment, and product recommendations.

### `account_id`

An anonymized unique identifier for the account associated with the customer. The analytics mart is based on the primary account-owner relationship.

### `disposition_id`

Identifier for the relationship between a customer and an account. A disposition records whether a customer is an account owner or another authorized user.

## Customer Profile Fields

### `date_of_birth`

The customer's historical date of birth derived from the source data.

### `customer_age_at_snapshot`

The customer's calculated age as of the analytics snapshot date. It represents age within the historical dataset and not the customer's current real-world age.

### `gender`

Gender value provided or derived from the historical source dataset. It is retained for descriptive analysis and must not be used to make product eligibility, credit, pricing, or adverse-action decisions.

### `customer_district_id`

Identifier for the district associated with the customer.

### `district_name`

Business-readable name of the customer's district.

### `region_name`

Larger geographic region containing the customer's district.

## District Context Fields

District fields describe the historical geographic area and should not be treated as individual customer attributes.

### `district_population`

Historical population of the customer's district.

### `district_average_salary`

Historical average salary reported for the district.

### `unemployment_rate_1996`

District-level unemployment rate reported for 1996.

### `entrepreneurs_per_1000`

Historical number of entrepreneurs per 1,000 residents in the district.

### `crime_count_1996`

Historical district-level crime count reported for 1996. It must not be interpreted as evidence about an individual customer.

## Account Fields

### `account_opened_date`

Date when the account was opened.

### `statement_frequency`

Frequency with which account statements were issued in the source system.

### `account_tenure_months`

Number of months between the account-opened date and the analytics snapshot date.

## Transaction Activity Fields

### `first_transaction_date`

Date of the earliest available transaction associated with the account.

### `last_transaction_date`

Date of the most recent available transaction associated with the account.

### `days_since_last_transaction`

Number of days between the most recent transaction and the snapshot date. A larger value indicates less-recent account activity.

### `transaction_count`

Total number of available transactions associated with the account.

### `active_month_count`

Number of distinct calendar months in which the account had recorded transaction activity.

### `credit_transaction_count`

Number of transactions classified as credits or incoming funds.

### `debit_transaction_count`

Number of transactions classified as debits or outgoing funds.

## Transaction Amount Fields

### `total_credit_amount`

Total amount credited to the account across the available transaction history.

### `total_debit_amount`

Total amount debited from the account across the available transaction history.

### `total_transaction_volume`

Total absolute monetary activity across credit and debit transactions. It measures movement of funds and should not be interpreted as profit, income, or account value.

### `average_transaction_amount`

Average monetary amount per transaction.

### `average_credit_amount`

Average amount of transactions classified as credits.

### `average_debit_amount`

Average amount of transactions classified as debits.

### `net_cash_flow`

Difference between total credited funds and total debited funds:

```text
net cash flow = total credit amount - total debit amount
```

A positive value indicates that recorded credits exceeded recorded debits during the available period. It does not necessarily represent income, profit, or financial health.

## Balance Fields

### `average_balance`

Average recorded account balance across the available transaction history.

### `minimum_balance`

Lowest recorded account balance in the available transaction history.

### `maximum_balance`

Highest recorded account balance in the available transaction history.

### `latest_balance`

Balance associated with the most recent available transaction.

### `negative_balance_transaction_count`

Number of transaction records for which the recorded account balance was below zero.

### `negative_balance_percentage`

Percentage of available transaction records associated with a negative account balance.

This field describes historical balance behavior. It must not automatically be interpreted as financial distress, fraud, credit risk, or inability to repay debt.

## Transaction Channel Fields

### `card_withdrawal_count`

Number of transactions identified as card-based cash withdrawals.

### `cash_deposit_count`

Number of transactions identified as cash deposits.

### `incoming_transfer_count`

Number of transfer transactions representing incoming funds.

### `outgoing_transfer_count`

Number of transfer transactions representing outgoing funds.

These counts describe transaction-channel usage and help distinguish cash-focused, card-focused, and transfer-focused behavior.

## Payment Card Fields

### `card_count`

Number of payment cards associated with the account or primary customer relationship.

### `has_card`

Boolean indicator showing whether the customer currently has at least one recorded payment card.

### `highest_card_type`

Highest available card category associated with the customer based on the source card classifications.

### `first_card_issued_date`

Date when the earliest recorded card was issued.

### `most_recent_card_issued_date`

Date when the most recently recorded card was issued.

## Loan Fields

### `loan_id`

Identifier for the loan associated with the account, when one exists.

### `loan_start_date`

Date when the recorded loan began.

### `loan_amount`

Original monetary amount of the recorded loan.

### `loan_duration_months`

Contracted loan duration expressed in months.

### `monthly_payment`

Recorded monthly loan-payment amount.

### `loan_status`

Historical loan-status category from the source dataset.

### `has_loan`

Boolean indicator showing whether the customer currently has a recorded loan.

### `has_loan_repayment_problem`

Boolean indicator derived from historical loan status showing whether a repayment issue was recorded.

This field is retained for descriptive analysis. The segmentation and recommendation demonstration must not use it to make automated eligibility, credit, pricing, or adverse-action decisions.

## Scheduled Payment Fields

### `payment_order_count`

Number of scheduled payment orders associated with the account.

### `total_scheduled_payment_amount`

Total monetary amount represented by the recorded scheduled payment orders.

### `loan_payment_order_count`

Number of scheduled payment orders associated with loan payments.

### `household_payment_order_count`

Number of scheduled payment orders associated with household expenses.

### `insurance_payment_order_count`

Number of scheduled payment orders associated with insurance payments.

## Product Ownership Field

### `banking_product_count`

Count of the banking-product categories associated with the customer. It provides a simplified measure of product breadth and engagement.

It should not be interpreted as account profitability or customer value by itself.

## Snapshot Field

### `snapshot_date`

Date representing the point in time at which customer features were calculated. All recency, age, and tenure measures must be interpreted relative to this date.

## Segmentation Fields

### `cluster_id`

Numeric cluster assigned by the K-Means model. The model currently produces five cluster identifiers:

```text
0, 1, 2, 3, 4
```

The numeric identifier has no inherent ranking or business meaning.

### `segment_name`

Business-readable name mapped to the numeric cluster. Current segment names are:

- High-Value Multi-Product.
- Everyday Cash-Focused.
- Mature Transfer-Focused.
- High-Flow Financially Volatile.
- Low-Engagement Dormant.

### `segment_description`

Business-readable explanation of the dominant behavioral patterns associated with the segment.

The description summarizes group-level patterns and is not an exact description of every customer in the cluster.

### `model_version`

Version identifier for the segmentation model that produced the cluster assignment.

### `scored_at`

Timestamp indicating when the segmentation pipeline generated the customer assignment.

## Derived Recommendation Features

The recommendation pipeline derives two monthly activity measures from the customer mart.

### `average_monthly_transaction_count`

Calculated as:

```text
transaction_count / active_month_count
```

It represents average transaction frequency across months with recorded activity.

### `average_monthly_transaction_volume`

Calculated as:

```text
total_transaction_volume / active_month_count
```

It represents average transaction volume across months with recorded activity.

## Product Recommendation Output Fields

The recommendation dataset is stored in `ml.product_recommendations` and exposed through `analytics.mart_product_recommendations`.

### `recommendation_id`

Unique identifier for a generated recommendation record.

### `recommended_product`

Name of the product or service suggested by the rule engine. Current values include:

- Savings Account.
- Payment Card.
- Personal Loan Consultation.
- Overdraft Protection.
- Automatic Payment Setup.
- Account Re-Engagement Review.

### `recommendation_score`

Rule-based score used to prioritize eligible recommendations for a customer.

The score is not a probability, credit score, approval score, or prediction of purchase behavior.

### `recommendation_rank`

Priority of the retained recommendation for a customer. Valid values are 1, 2, and 3, where rank 1 is the highest-scoring retained recommendation.

### `recommendation_reason`

Human-readable explanation of the historical conditions that triggered the recommendation.

### `recommendation_version`

Version of the business-rule implementation used to generate the recommendation. The current version is `rules_v1`.

### `generated_at`

UTC timestamp indicating when the recommendation pipeline generated the output.

## Data Interpretation Rules

The AI assistant must follow these rules when using the data dictionary:

1. Treat all customer identifiers as anonymized identifiers.
2. Treat monetary values as historical values in the dataset's original currency context.
3. Do not present the dataset as current banking activity.
4. Do not infer a customer's motivation from transaction behavior.
5. Do not treat a segment average as an exact customer value.
6. Do not describe recommendation scores as probabilities.
7. Do not use demographic or district fields to make eligibility, lending, pricing, or adverse-action decisions.
8. Do not interpret transaction volume as income or profitability.
9. Do not interpret positive cash flow as proof of financial health.
10. Do not interpret negative-balance activity as proof of financial distress or credit risk.
11. Clearly distinguish individual customer values from segment-level summaries.
12. State when requested information is unavailable from the documented fields.
