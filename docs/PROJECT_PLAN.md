# Project Implementation Plan

## Final outcome

The finished system will ingest eight relational banking files, validate and load them into PostgreSQL, transform them into a Customer 360 mart, assign explainable behavioral segments, generate responsible product recommendations, and expose the results through Streamlit and Power BI.

## Milestone 1 - Foundation

- Repository structure
- Dockerized PostgreSQL
- Environment configuration
- Source manifest
- Architecture and project documentation

## Milestone 2 - Data acquisition and profiling

- Download the source archive from a documented source
- Preserve source files unchanged
- Create row-count and schema profiles
- Document encoded fields and historical limitations

## Milestone 3 - Ingestion and validation

- Create raw database tables
- Implement idempotent Python loading
- Add batch IDs and ingestion timestamps
- Reconcile file and table row counts
- Quarantine invalid records

## Milestone 4 - Warehouse and Customer 360

- Create dbt staging models
- Create customer, account, transaction, loan, card, and district dimensions/facts
- Add uniqueness, null, accepted-value, and relationship tests
- Build a one-row-per-customer analytical mart

## Milestone 5 - Segmentation

- Build RFM and banking behavior features
- Treat skew and scale numerical features
- Compare candidate cluster counts
- Evaluate silhouette score and cluster stability
- Name clusters from evidence, not assumptions

## Milestone 6 - Recommendations

- Map segment characteristics to transparent product rules
- Attach explanations and exclusions to every recommendation
- Avoid credit eligibility or pricing decisions

## Milestone 7 - Presentation layer

- Streamlit executive overview
- Segment explorer
- Customer 360 view
- Recommendation view
- Power BI star schema and dashboard specification

## Milestone 8 - Portfolio release

- Automated tests and CI
- Dockerized run instructions
- Data dictionary and model card
- Architecture diagram and screenshots
- Resume bullets and interview explanation

