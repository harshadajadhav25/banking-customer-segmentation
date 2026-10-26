with source_orders as (

    select *
    from {{ source('banking_raw', 'payment_order') }}

),

typed_orders as (

    select
        order_id::bigint as payment_order_id,
        account_id::bigint as account_id,

        nullif(
            trim(bank_to),
            ''
        ) as recipient_bank_code,

        nullif(
            trim(account_to),
            ''
        ) as recipient_account_number,

        amount::numeric(14, 2)
            as payment_order_amount,

        nullif(
            trim(k_symbol),
            ''
        ) as payment_purpose_code,

        case trim(k_symbol)
            when 'POJISTNE'
                then 'Insurance Payment'
            when 'SIPO'
                then 'Household Payment'
            when 'LEASING'
                then 'Leasing Payment'
            when 'UVER'
                then 'Loan Payment'
            when ''
                then 'Unspecified'
            else 'Other'
        end as payment_purpose,

        _source_file,
        _batch_id,
        _ingested_at

    from source_orders

)

select *
from typed_orders