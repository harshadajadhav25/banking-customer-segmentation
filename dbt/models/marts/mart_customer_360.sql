with accounts as (

    select *
    from {{ ref('stg_accounts') }}

),

clients as (

    select *
    from {{ ref('stg_clients') }}

),

dispositions as (

    select *
    from {{ ref('stg_dispositions') }}

),

districts as (

    select *
    from {{ ref('stg_districts') }}

),

cards as (

    select *
    from {{ ref('stg_cards') }}

),

loans as (

    select *
    from {{ ref('stg_loans') }}

),

payment_orders as (

    select *
    from {{ ref('stg_payment_orders') }}

),

transaction_features as (

    select *
    from {{ ref('int_account_transaction_features') }}

),

primary_customers as (

    select
        dispositions.client_id as customer_id,
        dispositions.account_id,
        dispositions.disposition_id

    from dispositions

    where dispositions.is_account_owner = true

),

card_features as (

    select
        disposition_id,

        count(*)::integer as card_count,

        min(card_issued_date)
            as first_card_issued_date,

        max(card_issued_date)
            as most_recent_card_issued_date,

        case
            when bool_or(card_type = 'Gold')
                then 'Gold'
            when bool_or(card_type = 'Classic')
                then 'Classic'
            when bool_or(card_type = 'Junior')
                then 'Junior'
            else null
        end as highest_card_type

    from cards

    group by disposition_id

),

payment_order_features as (

    select
        account_id,

        count(*)::integer
            as payment_order_count,

        sum(payment_order_amount)
            as total_scheduled_payment_amount,

        count(*) filter (
            where payment_purpose = 'Loan Payment'
        )::integer as loan_payment_order_count,

        count(*) filter (
            where payment_purpose = 'Household Payment'
        )::integer as household_payment_order_count,

        count(*) filter (
            where payment_purpose = 'Insurance Payment'
        )::integer as insurance_payment_order_count

    from payment_orders

    group by account_id

),

customer_360 as (

    select
        primary_customers.customer_id,
        primary_customers.account_id,
        primary_customers.disposition_id,

        clients.date_of_birth,

        date_part(
            'year',
            age(
                transaction_features.snapshot_date,
                clients.date_of_birth
            )
        )::integer as customer_age_at_snapshot,

        clients.gender,

        clients.district_id as customer_district_id,
        districts.district_name,
        districts.region_name,
        districts.population as district_population,
        districts.average_salary as district_average_salary,
        districts.unemployment_rate_1996,
        districts.entrepreneurs_per_1000,
        districts.crime_count_1996,

        accounts.account_opened_date,
        accounts.statement_frequency,

        (
            date_part(
                'year',
                age(
                    transaction_features.snapshot_date,
                    accounts.account_opened_date
                )
            ) * 12
            +
            date_part(
                'month',
                age(
                    transaction_features.snapshot_date,
                    accounts.account_opened_date
                )
            )
        )::integer as account_tenure_months,

        transaction_features.first_transaction_date,
        transaction_features.last_transaction_date,
        transaction_features.days_since_last_transaction,
        transaction_features.transaction_count,
        transaction_features.active_month_count,
        transaction_features.credit_transaction_count,
        transaction_features.debit_transaction_count,

        coalesce(
            transaction_features.total_credit_amount,
            0
        ) as total_credit_amount,

        coalesce(
            transaction_features.total_debit_amount,
            0
        ) as total_debit_amount,

        coalesce(
            transaction_features.total_credit_amount,
            0
        )
        +
        coalesce(
            transaction_features.total_debit_amount,
            0
        ) as total_transaction_volume,

        transaction_features.average_transaction_amount,
        transaction_features.average_credit_amount,
        transaction_features.average_debit_amount,
        transaction_features.net_cash_flow,
        transaction_features.average_balance,
        transaction_features.minimum_balance,
        transaction_features.maximum_balance,
        transaction_features.latest_balance,
        transaction_features.negative_balance_transaction_count,
        transaction_features.negative_balance_percentage,
        transaction_features.card_withdrawal_count,
        transaction_features.cash_deposit_count,
        transaction_features.incoming_transfer_count,
        transaction_features.outgoing_transfer_count,

        coalesce(
            card_features.card_count,
            0
        ) as card_count,

        (
            coalesce(
                card_features.card_count,
                0
            ) > 0
        ) as has_card,

        card_features.highest_card_type,
        card_features.first_card_issued_date,
        card_features.most_recent_card_issued_date,

        loans.loan_id,
        loans.loan_start_date,
        loans.loan_amount,
        loans.loan_duration_months,
        loans.monthly_payment,
        loans.loan_status,

        (
            loans.loan_id is not null
        ) as has_loan,

        coalesce(
            loans.has_repayment_problem,
            false
        ) as has_loan_repayment_problem,

        coalesce(
            payment_order_features.payment_order_count,
            0
        ) as payment_order_count,

        coalesce(
            payment_order_features.total_scheduled_payment_amount,
            0
        ) as total_scheduled_payment_amount,

        coalesce(
            payment_order_features.loan_payment_order_count,
            0
        ) as loan_payment_order_count,

        coalesce(
            payment_order_features.household_payment_order_count,
            0
        ) as household_payment_order_count,

        coalesce(
            payment_order_features.insurance_payment_order_count,
            0
        ) as insurance_payment_order_count,

        (
            1
            + case
                when coalesce(
                    card_features.card_count,
                    0
                ) > 0 then 1
                else 0
            end
            + case
                when loans.loan_id is not null
                    then 1
                else 0
            end
        ) as banking_product_count,

        transaction_features.snapshot_date

    from primary_customers

    inner join clients
        on primary_customers.customer_id
        = clients.client_id

    inner join accounts
        on primary_customers.account_id
        = accounts.account_id

    left join districts
        on clients.district_id
        = districts.district_id

    inner join transaction_features
        on primary_customers.account_id
        = transaction_features.account_id

    left join card_features
        on primary_customers.disposition_id
        = card_features.disposition_id

    left join loans
        on primary_customers.account_id
        = loans.account_id

    left join payment_order_features
        on primary_customers.account_id
        = payment_order_features.account_id

)

select *
from customer_360