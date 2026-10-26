with source_clients as (

    select *
    from {{ source('banking_raw', 'client') }}

),

normalized_clients as (

    select
        client_id,
        lpad(birth_number, 6, '0') as birth_number,
        district_id,
        _source_file,
        _batch_id,
        _ingested_at

    from source_clients

),

decoded_clients as (

    select
        client_id::bigint as client_id,
        birth_number as birth_number_code,
        district_id::integer as district_id,

        substring(
            birth_number from 1 for 2
        )::integer as birth_year_two_digit,

        substring(
            birth_number from 3 for 2
        )::integer as encoded_birth_month,

        substring(
            birth_number from 5 for 2
        )::integer as birth_day,

        case
            when substring(
                birth_number from 3 for 2
            )::integer > 50
                then 'Female'
            else 'Male'
        end as gender,

        _source_file,
        _batch_id,
        _ingested_at

    from normalized_clients

),

final_clients as (

    select
        client_id,
        birth_number_code,
        district_id,

        make_date(
            1900 + birth_year_two_digit,

            case
                when encoded_birth_month > 50
                    then encoded_birth_month - 50
                else encoded_birth_month
            end,

            birth_day
        ) as date_of_birth,

        gender,

        _source_file,
        _batch_id,
        _ingested_at

    from decoded_clients

)

select *
from final_clients