with source_dispositions as (

    select *
    from {{ source('banking_raw', 'disposition') }}

),

typed_dispositions as (

    select
        disp_id::bigint as disposition_id,
        client_id::bigint as client_id,
        account_id::bigint as account_id,

        type as disposition_type_code,

        case trim(type)
            when 'OWNER'
                then 'Account Owner'
            when 'DISPONENT'
                then 'Authorized User'
            else 'Unknown'
        end as disposition_type,

        case
            when trim(type) = 'OWNER'
                then true
            else false
        end as is_account_owner,

        _source_file,
        _batch_id,
        _ingested_at

    from source_dispositions

)

select *
from typed_dispositions