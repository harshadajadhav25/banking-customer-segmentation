# Customer Segmentation Model Card

## Model Overview

The Banking Customer Segmentation and Product Recommendation Platform uses K-Means clustering to group customers with similar historical banking behavior. The model creates five customer segments from behavioral, transactional, balance, cash-flow, and transaction-channel features.

The model is an unsupervised learning model. It does not predict a target variable and does not assign customers to known classes.

## Model Identification

| Property | Value |
|---|---|
| Model type | K-Means clustering |
| Model version | `kmeans_v1` |
| Number of clusters | 5 |
| Number of customers | 4,500 |
| Number of clustering features | 14 |
| Random state | 42 |
| K-Means initializations | 20 |
| Preprocessing | Outlier capping and Yeo-Johnson transformation with standardization |
| Training implementation | scikit-learn |
| Primary feature dataset | `analytics.mart_customer_segmentation_features` |

## Intended Purpose

The model is intended to identify broad customer-behavior patterns, support portfolio-level analysis, create interpretable segments, support explainable product-recommendation demonstrations, and power the project's dashboard and RAG assistant.

## Prohibited Uses

The model must not be used for loan approval or rejection, credit scoring, credit-limit decisions, product eligibility, pricing, adverse actions, fraud accusations, default prediction, or predictions presented as facts about an individual customer.

## Source Data

The project uses the anonymized historical PKDD'99 Czech banking dataset. It includes accounts, customers, account dispositions, transactions, loans, payment cards, scheduled payment orders, and district demographics.

The segmentation feature dataset contains 4,500 primary account owners derived from 1,056,320 transaction records. The data is historical and must not be presented as current banking activity. Monetary values retain the dataset's original currency context.

## Feature Dataset

The model reads one customer-level record per customer from:

```text
analytics.mart_customer_segmentation_features
```

## Clustering Features

The model uses these 14 features:

1. `customer_age_at_snapshot` - Customer age as of the historical snapshot.
2. `account_tenure_months` - Months between account opening and the snapshot date.
3. `days_since_last_transaction` - Days between the latest transaction and snapshot date.
4. `average_monthly_transaction_count` - Transaction count divided by active-month count.
5. `average_monthly_transaction_volume` - Total transaction volume divided by active-month count.
6. `average_transaction_amount` - Average monetary amount per transaction.
7. `net_cash_flow` - Total credited amount minus total debited amount.
8. `average_balance` - Average recorded account balance.
9. `latest_balance` - Balance associated with the latest available transaction.
10. `negative_balance_percentage` - Percentage of records associated with a negative balance.
11. `card_withdrawal_count` - Number of card-based cash withdrawals.
12. `cash_deposit_count` - Number of cash-deposit transactions.
13. `incoming_transfer_count` - Number of incoming transfers.
14. `outgoing_transfer_count` - Number of outgoing transfers.

## Excluded Product Features

Product-ownership fields such as `has_card`, `has_loan`, `payment_order_count`, and `banking_product_count` are intentionally excluded from training. They are used later to profile clusters and generate recommendations.

Product ownership may be examined after model training to interpret and label clusters, but it does not directly determine the K-Means assignments.

## Missing-Value Validation

Before training, the pipeline checks all clustering features for missing values. If any are present, the pipeline stops:

```python
if missing_values > 0:
    raise ValueError(
        f"Clustering features contain {missing_values} missing values."
    )
```

## Outlier Treatment

For each feature, observations are capped at the 1st and 99th percentiles. Values outside these limits are replaced by the appropriate boundary. This reduces the influence of extreme observations while retaining every customer record.

The clipping limits are saved so that future records can be processed consistently.

## Feature Transformation

After capping, the pipeline applies:

```python
PowerTransformer(
    method="yeo-johnson",
    standardize=True,
)
```

The Yeo-Johnson transformation reduces skewness and supports positive, zero, and negative values. Standardization prevents features with larger numeric scales from automatically dominating K-Means distance calculations.

## K-Means Configuration

Candidate and final models use:

```python
KMeans(
    n_clusters=cluster_count,
    random_state=42,
    n_init=20,
)
```

`random_state=42` supports reproducibility. `n_init=20` runs K-Means with 20 centroid initializations and retains the best clustering objective.

## Cluster-Count Evaluation

The pipeline evaluates candidate cluster counts from `k=2` through `k=8` using inertia, silhouette score, and Davies-Bouldin score.

| Clusters | Inertia | Silhouette Score | Davies-Bouldin Score |
|---:|---:|---:|---:|
| 2 | 45,918.68 | 0.2665 | 1.4649 |
| 3 | 40,234.79 | 0.2290 | 1.8095 |
| 4 | 35,121.94 | 0.2271 | 1.5786 |
| 5 | 31,240.28 | 0.2438 | 1.4554 |
| 6 | 28,436.12 | 0.2451 | 1.5098 |
| 7 | 26,361.99 | 0.2381 | 1.4293 |
| 8 | 24,886.08 | 0.2445 | 1.4099 |

The complete results are stored at:

```text
data/processed/segmentation/cluster_evaluation.csv
```

## Metric Interpretation

### Inertia

Inertia is the total squared distance between customers and their cluster centroids. Lower inertia indicates more compact clusters, but inertia naturally decreases as the number of clusters increases.

### Silhouette Score

The silhouette score compares similarity within a cluster with separation from other clusters. Higher is generally better. The highest tested value is 0.2665 for `k=2`, but two clusters are too broad for the project's behavioral and recommendation analysis.

### Davies-Bouldin Score

The Davies-Bouldin score measures within-cluster similarity and separation between clusters. Lower is generally better. The lowest tested value is 1.4099 for `k=8`, but eight clusters increase fragmentation and interpretation complexity.

## Final Model Selection

The selected model uses five clusters:

```text
Inertia: 31,240.28
Silhouette score: 0.2438
Davies-Bouldin score: 1.4554
```

Five clusters were selected as a practical balance among compactness, separation, segment size, interpretability, behavioral differentiation, and recommendation usefulness. Selection was not based on optimizing only one metric.

## Final Customer Segments

### Cluster 0: High-Value Multi-Product

Highly active customers with high balances, transaction volume, and strong post-training product-ownership rates.

```text
1,464 customers
32.53% of the portfolio
```

Product ownership supports the business label after clustering and is not a training feature.

### Cluster 1: Everyday Cash-Focused

Regular customers with moderate balances and transaction activity, strong cash-deposit behavior, and comparatively limited card or loan ownership.

```text
1,409 customers
31.31% of the portfolio
```

### Cluster 2: Mature Transfer-Focused

Older customers with lower transaction values whose activity is concentrated primarily in account transfers.

```text
1,188 customers
26.40% of the portfolio
```

### Cluster 3: High-Flow Financially Volatile

Customers with high transaction volume and cash flow but elevated historical negative-balance activity.

```text
260 customers
5.78% of the portfolio
```

The word volatile describes historical balance and transaction patterns. It is not a credit-risk, fraud, or financial-distress classification.

### Cluster 4: Low-Engagement Dormant

Customers with low transaction frequency, longer inactivity, and limited post-training recurring-payment and product engagement.

```text
179 customers
3.98% of the portfolio
```

The model does not determine why a customer has limited activity.

## Cluster Profiles

After assignment, the pipeline calculates aggregate profiles including customer count, age, tenure, recency, monthly transaction activity, transaction amounts, cash flow, balances, negative-balance activity, card withdrawals, cash deposits, transfers, card and loan ownership rates, payment-order counts, and product counts.

Cluster profiles describe group-level averages. They are not exact descriptions of every customer in a cluster.

## Model Outputs

Evaluation, profiles, and assignments are saved to:

```text
data/processed/segmentation/cluster_evaluation.csv
data/processed/segmentation/cluster_profiles.csv
data/processed/segmentation/customer_cluster_assignments.csv
```

The trained model and preprocessing artifacts are stored at:

```text
models/segmentation/customer_segmentation_pipeline.joblib
```

Database outputs are:

```text
ml.customer_segments
ml.cluster_profiles
```

## Saved Artifacts

The Joblib artifact contains:

```text
model
transformer
clipping_limits
feature_names
cluster_count
random_state
segment_names
segment_descriptions
```

Saving these components ensures that future records use the same feature order, clipping limits, transformation, standardization, trained model, and label mappings.

## Model Versioning

The current version is `kmeans_v1`. Each customer assignment includes `model_version`, `scored_at`, and `snapshot_date` for traceability.

## Known Limitations

### Historical dataset

The model uses historical anonymized data and must not be represented as a model trained on current banking behavior.

### Moderate separation

The silhouette scores show that the segments are not perfectly separated. Customer behavior often exists on a continuum, so cluster boundaries must not be treated as absolute.

### Sensitivity to preprocessing

Assignments may change when feature definitions, clipping limits, transformations, scaling, source data, cluster count, random initialization, or software versions change.

### Hard assignments

K-Means assigns every customer to exactly one cluster and does not express uncertainty or partial membership across segments.

### Human-created labels

K-Means produces numeric cluster identifiers. Segment names are human interpretations created after reviewing aggregate profiles.

### No causal interpretation

The model identifies similarities and associations. It does not establish that one behavior causes another.

### No individual prediction

A cluster assignment summarizes similarity to a centroid. It does not predict an individual's future actions.

### Limited context

The model does not include customer goals, satisfaction, current economic conditions, digital interactions, marketing responses, preferences, or reasons for inactivity.

## Monitoring Recommendations

When retraining or applying the pipeline to new data, monitor missing values, feature distributions, clipping limits, cluster sizes, profile changes, silhouette score, Davies-Bouldin score, inertia, segment stability, recommendation distribution, customer coverage, and model versions.

Unexpected changes should be reviewed before new outputs are published.

## Responsible AI Guidance

The RAG assistant may explain model design, selected features, preprocessing, metrics, segment profiles, and limitations.

It must not present cluster assignments as objective facts about a person, describe the model as a credit-risk model, claim that a segment predicts default or purchases, infer protected characteristics, make eligibility or lending decisions, make pricing decisions, or describe recommendation scores as probabilities.

The assistant must distinguish among individual historical values, aggregate segment patterns, human-created labels, rule-based recommendations, and predictions that this model does not produce.
