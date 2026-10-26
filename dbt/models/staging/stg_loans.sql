with source_loans as (

    select *
    from {{ source('banking_raw', 'loan') }}

),

typed_loans as (

    select
        loan_id::bigint as loan_id,
        account_id::bigint as account_id,

        to_date(
            '19' || date,
            'YYYYMMDD'
        ) as loan_start_date,

        amount::numeric(14, 2) as loan_amount,
        duration::integer as loan_duration_months,
        payments::numeric(14, 2) as monthly_payment,

        status as loan_status_code,

        case trim(status)
            when 'A'
                then 'Completed - Repaid'
            when 'B'
                then 'Completed - Not Repaid'
            when 'C'
                then 'Active - Performing'
            when 'D'
                then 'Active - In Debt'
            else 'Unknown'
        end as loan_status,

        case
            when trim(status) in ('A', 'B')
                then true
            else false
        end as is_completed_loan,

        case
            when trim(status) in ('B', 'D')
                then true
            else false
        end as has_repayment_problem,

        _source_file,
        _batch_id,
        _ingested_at

    from source_loans

)

select *
from typed_loans