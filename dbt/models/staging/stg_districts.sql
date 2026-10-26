with source_districts as (

    select *
    from {{ source('banking_raw', 'district') }}

),

typed_districts as (

    select
        "A1"::integer as district_id,
        trim("A2") as district_name,
        trim("A3") as region_name,

        "A4"::integer as population,

        "A5"::integer
            as municipalities_under_500,

        "A6"::integer
            as municipalities_500_to_1999,

        "A7"::integer
            as municipalities_2000_to_9999,

        "A8"::integer
            as municipalities_10000_or_more,

        "A9"::integer as city_count,

        "A10"::numeric(6, 2)
            as urban_population_percentage,

        "A11"::numeric(12, 2)
            as average_salary,

        nullif(
            trim("A12"),
            '?'
        )::numeric(6, 2)
            as unemployment_rate_1995,

        nullif(
            trim("A13"),
            '?'
        )::numeric(6, 2)
            as unemployment_rate_1996,

        "A14"::numeric(10, 2)
            as entrepreneurs_per_1000,

        nullif(
            trim("A15"),
            '?'
        )::integer
            as crime_count_1995,

        nullif(
            trim("A16"),
            '?'
        )::integer
            as crime_count_1996,

        _source_file,
        _batch_id,
        _ingested_at

    from source_districts

)

select *
from typed_districts