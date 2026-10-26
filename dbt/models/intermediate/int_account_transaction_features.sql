{{ config(materialized='table') }}

with transactions as (

    select *
    from {{ ref('stg_transactions') }}

),

dataset_snapshot as (

    select
        max(transaction_date) as snapshot_date
    from transactions

),

latest_account_balance as (

    select
        account_id,
        balance_after_transaction as latest_balance

    from (

        select
            account_id,
            balance_after_transaction,

            row_number() over (
                partition by account_id
                order by
                    transaction_date desc,
                    transaction_id desc
            ) as row_number

        from transactions

    ) ranked_transactions

    where row_number = 1

),

account_aggregates as (

    select
        transactions.account_id,

        min(
            transactions.transaction_date
        ) as first_transaction_date,

        max(
            transactions.transaction_date
        ) as last_transaction_date,

        dataset_snapshot.snapshot_date,

        dataset_snapshot.snapshot_date
            - max(transactions.transaction_date)
            as days_since_last_transaction,

        count(*)::bigint
            as transaction_count,

        count(
            distinct date_trunc(
                'month',
                transactions.transaction_date
            )
        )::integer as active_month_count,

        count(*) filter (
            where transactions.is_credit
        )::bigint as credit_transaction_count,

        count(*) filter (
            where transactions.is_debit
        )::bigint as debit_transaction_count,

        sum(
            transactions.transaction_amount
        ) filter (
            where transactions.is_credit
        ) as total_credit_amount,

        sum(
            transactions.transaction_amount
        ) filter (
            where transactions.is_debit
        ) as total_debit_amount,

        avg(
            transactions.transaction_amount
        ) as average_transaction_amount,

        avg(
            transactions.transaction_amount
        ) filter (
            where transactions.is_credit
        ) as average_credit_amount,

        avg(
            transactions.transaction_amount
        ) filter (
            where transactions.is_debit
        ) as average_debit_amount,

        sum(
            transactions.signed_amount
        ) as net_cash_flow,

        avg(
            transactions.balance_after_transaction
        ) as average_balance,

        min(
            transactions.balance_after_transaction
        ) as minimum_balance,

        max(
            transactions.balance_after_transaction
        ) as maximum_balance,

        count(*) filter (
            where transactions.balance_after_transaction < 0
        )::bigint as negative_balance_transaction_count,

        round(
            100.0
            * count(*) filter (
                where transactions.balance_after_transaction < 0
            )
            / nullif(count(*), 0),
            2
        ) as negative_balance_percentage,

        count(*) filter (
            where transactions.operation_type = 'Card Withdrawal'
        )::bigint as card_withdrawal_count,

        count(*) filter (
            where transactions.operation_type = 'Cash Deposit'
        )::bigint as cash_deposit_count,

        count(*) filter (
            where transactions.operation_type = 'Incoming Bank Transfer'
        )::bigint as incoming_transfer_count,

        count(*) filter (
            where transactions.operation_type = 'Outgoing Bank Transfer'
        )::bigint as outgoing_transfer_count

    from transactions

    cross join dataset_snapshot

    group by
        transactions.account_id,
        dataset_snapshot.snapshot_date

),

final as (

    select
        account_aggregates.*,
        latest_account_balance.latest_balance

    from account_aggregates

    left join latest_account_balance
        on account_aggregates.account_id
        = latest_account_balance.account_id

)

select *
from final