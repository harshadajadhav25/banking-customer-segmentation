{{ config(
    materialized='table'
) }}

with customer_360 as (

    select *
    from {{ ref('mart_customer_360') }}

),

customer_segments as (

    select
        customer_id,
        account_id,
        cluster_id,
        segment_name,
        segment_description,
        model_version,
        scored_at
    from {{ source('ml_outputs', 'customer_segments') }}

)

select
    customer_360.*,
    customer_segments.cluster_id,
    customer_segments.segment_name,
    customer_segments.segment_description,
    customer_segments.model_version,
    customer_segments.scored_at
from customer_360
left join customer_segments
    on customer_360.customer_id = customer_segments.customer_id