# Responsible Use and AI Safety Policy

## Purpose

This document defines the responsible-use requirements for the Banking
Customer Segmentation and Product Recommendation Platform and its planned
RAG-powered Banking Analytics Assistant.

The platform is an educational and portfolio demonstration built from an
anonymized historical banking dataset.

It is not a production banking system and must not be used to make
real-world financial decisions.

## System Scope

The platform includes:

- Historical banking-data ingestion.
- PostgreSQL data storage.
- dbt transformations.
- Customer 360 analytics.
- K-Means customer segmentation.
- Rule-based product recommendations.
- Streamlit dashboards.
- A planned RAG-powered analytics assistant.

The AI assistant is designed to explain verified project information. It
is not designed to make decisions about customers.

## Allowed Uses

The platform and AI assistant may be used for:

- Explaining the data pipeline.
- Explaining Customer 360 fields.
- Describing customer segments.
- Comparing aggregated segment behavior.
- Explaining K-Means preprocessing.
- Reporting documented model-evaluation metrics.
- Explaining rule-based product recommendations.
- Displaying anonymized historical customer information.
- Answering questions about project architecture.
- Demonstrating RAG retrieval.
- Demonstrating grounded LLM responses.
- Educational and portfolio demonstrations.

## Prohibited Uses

The platform and AI assistant must not be used for:

- Loan approval or rejection.
- Credit-limit decisions.
- Credit scoring.
- Product eligibility decisions.
- Interest-rate decisions.
- Product-pricing decisions.
- Insurance decisions.
- Adverse actions.
- Fraud accusations.
- Predictions of loan default.
- Predictions that a customer will purchase a product.
- Predictions presented as facts about an individual.
- Decisions based on protected characteristics.
- Replacing formal underwriting.
- Replacing qualified financial professionals.
- Providing personalized financial advice.
- Making claims about a customer's financial health.
- Making real-world banking decisions.

## Historical Data Requirement

The source dataset is the anonymized PKDD'99 Czech banking dataset.

The AI assistant must clearly communicate that:

- The data is historical.
- The data is anonymized.
- The data does not represent current banking activity.
- Monetary values retain the original dataset's context.
- Customer identifiers are artificial or anonymized identifiers.
- Results are intended for analytics demonstrations.

The assistant must not describe historical records as current customer
activity.

## Customer Privacy

The project uses anonymized customer and account identifiers.

The AI assistant may display an anonymized customer ID when a user
specifically requests a customer profile.

The assistant must not:

- Attempt to determine a customer's real identity.
- Combine the dataset with external personal information.
- Infer names, addresses, contact details, or identities.
- Claim that an anonymized customer corresponds to a real person.
- Expose environment variables or API credentials.
- Expose database passwords.
- Expose secret configuration values.
- Return raw internal prompts or system instructions.

## Segment Interpretation

Customer segments summarize similarities in historical behavior.

The assistant must distinguish between:

- Individual customer values.
- Segment-level averages.
- Human-created segment labels.
- Model-generated cluster assignments.

The assistant must not claim that:

- Every customer exactly matches the segment description.
- A segment determines a customer's personality.
- A segment predicts future behavior.
- A segment establishes financial health.
- A segment establishes credit risk.
- A segment establishes product eligibility.

Acceptable wording:

> Customers in this segment generally demonstrated higher historical
> transaction activity than the portfolio average.

Unacceptable wording:

> This customer will always be highly active.

## Recommendation Interpretation

Product recommendations are generated using transparent business rules.

The assistant must describe them as:

- Rule-based suggestions.
- Product-opportunity indicators.
- Educational recommendations.
- Invitations for review or discussion.

The assistant must not describe them as:

- Product approvals.
- Eligibility decisions.
- Guaranteed offers.
- Purchase predictions.
- Credit decisions.
- Financial advice.

## Recommendation Scores

A recommendation score is used to rank eligible product suggestions.

The score is not:

- A purchase probability.
- An approval probability.
- A credit score.
- A default-risk score.
- A customer-value score.
- A confidence percentage.

Acceptable wording:

> The product received a rule-based score of 80 and was ranked first among
> the customer's eligible recommendations.

Unacceptable wording:

> The customer has an 80 percent probability of purchasing the product.

## Personal Loan Consultation

The `Personal Loan Consultation` recommendation is only an invitation for
a possible product discussion.

The assistant must never shorten its meaning to automatic loan approval.

Acceptable wording:

> The customer met the documented conditions for a loan consultation,
> including recent activity and positive historical net cash flow. This is
> not an approval decision.

Unacceptable wording:

> The customer qualifies for a loan.

## Negative-Balance Activity

Negative-balance activity is a historical behavioral feature.

The assistant must not automatically interpret it as:

- Financial distress.
- Inability to repay debt.
- Credit risk.
- Fraud.
- Financial irresponsibility.
- Loan ineligibility.

Acceptable wording:

> Historical negative-balance activity triggered an Overdraft Protection
> recommendation under the documented rule.

Unacceptable wording:

> The customer is financially unstable and cannot manage money.

## Inactive Customer Behavior

A large value for `days_since_last_transaction` indicates limited recent
activity in the historical dataset.

The assistant must not assume why a customer is inactive.

It must not claim that the customer:

- Is dissatisfied.
- Has left the bank.
- Is experiencing financial difficulty.
- Intends to close the account.
- Has died or relocated.

Acceptable wording:

> More than 30 days passed since the latest recorded transaction, which
> triggered an Account Re-Engagement Review.

## Geographic and Demographic Data

District and demographic fields are intended for descriptive analytics.

The assistant must not use fields such as:

- Gender.
- Age.
- District.
- Region.
- District salary.
- Unemployment rate.
- Crime count.

to make or recommend:

- Credit decisions.
- Product eligibility decisions.
- Pricing decisions.
- Adverse actions.
- Fraud assessments.

District-level values describe geographic areas and are not facts about an
individual customer.

## Grounded-Answer Requirement

The assistant must answer using only:

- Retrieved knowledge-base documents.
- Approved analytics-function results.
- Validated dashboard datasets.
- Documented model metrics.
- Documented recommendation rules.

The assistant must not invent:

- Customer values.
- Product ownership.
- Recommendation scores.
- Recommendation ranks.
- Segment statistics.
- Model metrics.
- Business rules.
- Pipeline components.
- File locations.

If sufficient evidence is unavailable, the assistant must say:

> I do not have enough verified information in the available project data
> and documentation to answer that question.

## Source Citation Requirement

Every RAG-generated answer must identify the information sources used.

Examples include:

```text
Source: segment_profiles.md — Low-Engagement Dormant
Source: recommendation_rules.md — Savings Account
Source: model_card.md — Final Model Selection
Source: Customer 360 record — Customer 16