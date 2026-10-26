{{ config(
    materialized='table'
) }}

with customer_context as (

    select
        customer_id,
        account_id,
        segment_name,
        district_name,
        region_name,
        days_since_last_transaction,
        transaction_count,
        total_transaction_volume,
        net_cash_flow,
        average_balance,
        latest_balance,
        negative_balance_percentage,
        has_card,
        has_loan,
        payment_order_count,
        banking_product_count
    from {{ ref('mart_customer_segments') }}

),

recommendations as (

    select
        customer_id,
        account_id,
        cluster_id,
        recommended_product,
        recommendation_score,
        recommendation_reason,
        recommendation_rank,
        recommendation_version,
        snapshot_date,
        generated_at
    from {{ source('ml_outputs', 'product_recommendations') }}

)

select
    md5(
        concat(
            recommendations.customer_id::text,
            '|',
            recommendations.recommended_product,
            '|',
            recommendations.recommendation_version
        )
    ) as recommendation_id,
    recommendations.customer_id,
    recommendations.account_id,
    recommendations.cluster_id,
    customer_context.segment_name,
    customer_context.district_name,
    customer_context.region_name,
    recommendations.recommended_product,
    recommendations.recommendation_score,
    recommendations.recommendation_rank,
    recommendations.recommendation_reason,
    recommendations.recommendation_version,
    customer_context.days_since_last_transaction,
    customer_context.transaction_count,
    customer_context.total_transaction_volume,
    customer_context.net_cash_flow,
    customer_context.average_balance,
    customer_context.latest_balance,
    customer_context.negative_balance_percentage,
    customer_context.has_card,
    customer_context.has_loan,
    customer_context.payment_order_count,
    customer_context.banking_product_count,
    recommendations.snapshot_date,
    recommendations.generated_at
from recommendations
inner join customer_context
    on recommendations.customer_id = customer_context.customer_id
    and recommendations.account_id = customer_context.account_id