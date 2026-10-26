{{
    config(
        materialized='table'
    )
}}

with customer_360 as (

    select *
    from {{ ref('mart_customer_360') }}

),

segmentation_features as (

    select
        customer_id,
        account_id,
        snapshot_date,

        -- Customer and account characteristics
        customer_age_at_snapshot,
        account_tenure_months,

        -- Recency, frequency, and monetary behavior
        days_since_last_transaction,
        transaction_count,
        active_month_count,
        total_transaction_volume,
        average_transaction_amount,
        net_cash_flow,

        -- Balance behavior
        average_balance,
        minimum_balance,
        maximum_balance,
        latest_balance,
        negative_balance_percentage,

        -- Transaction-channel behavior
        card_withdrawal_count,
        cash_deposit_count,
        incoming_transfer_count,
        outgoing_transfer_count,

        -- Current product ownership
        card_count,
        has_card,
        has_loan,
        payment_order_count,
        banking_product_count,

        -- Derived behavioral features
        round(
            transaction_count::numeric
            / nullif(active_month_count, 0),
            2
        ) as average_monthly_transaction_count,

        round(
            total_transaction_volume
            / nullif(active_month_count, 0),
            2
        ) as average_monthly_transaction_volume,

        round(
            total_credit_amount
            / nullif(total_debit_amount, 0),
            4
        ) as credit_to_debit_ratio

    from customer_360

)

select *
from segmentation_features