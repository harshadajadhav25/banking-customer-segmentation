CREATE TABLE IF NOT EXISTS raw.account (
    account_id TEXT PRIMARY KEY,
    district_id TEXT,
    frequency TEXT,
    date TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.card (
    card_id TEXT PRIMARY KEY,
    disp_id TEXT,
    type TEXT,
    issued TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.client (
    client_id TEXT PRIMARY KEY,
    birth_number TEXT,
    district_id TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.disposition (
    disp_id TEXT PRIMARY KEY,
    client_id TEXT,
    account_id TEXT,
    type TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.district (
    "A1" TEXT PRIMARY KEY,
    "A2" TEXT,
    "A3" TEXT,
    "A4" TEXT,
    "A5" TEXT,
    "A6" TEXT,
    "A7" TEXT,
    "A8" TEXT,
    "A9" TEXT,
    "A10" TEXT,
    "A11" TEXT,
    "A12" TEXT,
    "A13" TEXT,
    "A14" TEXT,
    "A15" TEXT,
    "A16" TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.loan (
    loan_id TEXT PRIMARY KEY,
    account_id TEXT,
    date TEXT,
    amount TEXT,
    duration TEXT,
    payments TEXT,
    status TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.payment_order (
    order_id TEXT PRIMARY KEY,
    account_id TEXT,
    bank_to TEXT,
    account_to TEXT,
    amount TEXT,
    k_symbol TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.bank_transaction (
    trans_id TEXT PRIMARY KEY,
    account_id TEXT,
    date TEXT,
    type TEXT,
    operation TEXT,
    amount TEXT,
    balance TEXT,
    k_symbol TEXT,
    bank TEXT,
    account TEXT,
    _source_file TEXT NOT NULL,
    _batch_id TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);