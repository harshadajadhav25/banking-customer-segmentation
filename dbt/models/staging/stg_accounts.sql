with source_accounts as (

    select *
    from {{ source('banking_raw', 'account') }}

),

typed_accounts as (

    select
        account_id::bigint as account_id,
        district_id::integer as district_id,

        to_date(
            '19' || date,
            'YYYYMMDD'
        ) as account_opened_date,

        frequency as statement_frequency_code,

        case trim(frequency)
            when 'POPLATEK MESICNE'
                then 'Monthly'
            when 'POPLATEK TYDNE'
                then 'Weekly'
            when 'POPLATEK PO OBRATU'
                then 'After Transaction'
            else 'Unknown'
        end as statement_frequency,

        _source_file,
        _batch_id,
        _ingested_at

    from source_accounts

)

select *
from typed_accounts