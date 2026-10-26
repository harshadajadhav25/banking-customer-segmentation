with source_transactions as (

    select *
    from {{ source('banking_raw', 'bank_transaction') }}

),

typed_transactions as (

    select
        trans_id::bigint as transaction_id,
        account_id::bigint as account_id,

        to_date(
            '19' || date,
            'YYYYMMDD'
        ) as transaction_date,

        type as transaction_type_code,

        case trim(type)
            when 'PRIJEM'
                then 'Credit'
            when 'VYDAJ'
                then 'Debit'
            else 'Unknown'
        end as transaction_type,

        operation as operation_code,

        case trim(operation)
            when 'VYBER KARTOU'
                then 'Card Withdrawal'
            when 'VKLAD'
                then 'Cash Deposit'
            when 'PREVOD Z UCTU'
                then 'Incoming Bank Transfer'
            when 'VYBER'
                then 'Cash Withdrawal'
            when 'PREVOD NA UCET'
                then 'Outgoing Bank Transfer'
            when ''
                then 'Unspecified'
            else 'Other'
        end as operation_type,

        amount::numeric(14, 2)
            as transaction_amount,

        case trim(type)
            when 'PRIJEM'
                then amount::numeric(14, 2)
            when 'VYDAJ'
                then -amount::numeric(14, 2)
            else null
        end as signed_amount,

        balance::numeric(14, 2)
            as balance_after_transaction,

        nullif(
            trim(k_symbol),
            ''
        ) as transaction_purpose_code,

        case trim(k_symbol)
            when 'POJISTNE'
                then 'Insurance Payment'
            when 'SLUZBY'
                then 'Statement Fee'
            when 'UROK'
                then 'Interest Credit'
            when 'SANKC. UROK'
                then 'Penalty Interest'
            when 'SIPO'
                then 'Household Payment'
            when 'DUCHOD'
                then 'Pension'
            when 'UVER'
                then 'Loan Payment'
            when ''
                then 'Unspecified'
            else 'Other'
        end as transaction_purpose,

        nullif(
            trim(bank),
            ''
        ) as external_bank_code,

        nullif(
            trim(account),
            ''
        ) as external_account_number,

        case
            when trim(type) = 'PRIJEM'
                then true
            else false
        end as is_credit,

        case
            when trim(type) = 'VYDAJ'
                then true
            else false
        end as is_debit,

        _source_file,
        _batch_id,
        _ingested_at

    from source_transactions

)

select *
from typed_transactions