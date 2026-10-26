with source_cards as (

    select *
    from {{ source('banking_raw', 'card') }}

),

typed_cards as (

    select
        card_id::bigint as card_id,
        disp_id::bigint as disposition_id,

        type as card_type_code,
        initcap(trim(type)) as card_type,

        to_timestamp(
            '19' || issued,
            'YYYYMMDD HH24:MI:SS'
        )::date as card_issued_date,

        _source_file,
        _batch_id,
        _ingested_at

    from source_cards

)

select *
from typed_cards