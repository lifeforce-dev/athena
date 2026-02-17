# Athena Database Schema

> Auto-maintained reference. Updated whenever migrations change the schema.

## Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ commitments : "has"
    users ||--o{ balance_snapshots : "has"
    users ||--o{ transactions : "has"
    users ||--o{ gmail_subscriptions : "has"

    users {
        bigint id PK
        varchar(32) discord_id UK
        varchar(128) discord_username
        varchar(128) display_name
        timestamptz created_at
        timestamptz updated_at
    }

    commitments {
        bigint id PK
        bigint user_id FK
        varchar(255) name
        numeric(12_2) amount "signed: negative = expense"
        varchar(32) frequency "daily | weekly | biweekly | monthly | once"
        int day_of_month "nullable, for monthly"
        date anchor_date "nullable, for weekly/biweekly"
        date one_time_date "nullable, for one-time"
        date start_date
        date end_date "nullable"
        boolean is_paycheck
        boolean is_active "soft delete flag"
        timestamptz created_at
        timestamptz updated_at
    }

    balance_snapshots {
        bigint id PK
        bigint user_id FK
        numeric(12_2) balance
        varchar(64) account_label
        timestamptz observed_at
        varchar(32) source "gmail | manual"
        varchar(64) gmail_message_id "nullable, idempotency"
        timestamptz created_at
    }

    transactions {
        bigint id PK
        bigint user_id FK
        numeric(12_2) amount
        text merchant
        varchar(4) card_last_four
        timestamptz purchase_date
        varchar(64) gmail_message_id "nullable, idempotency"
        timestamptz created_at
    }

    gmail_subscriptions {
        bigint id PK
        bigint user_id FK
        varchar(255) gmail_address
        varchar(64) history_id
        timestamptz watch_expiry
        timestamptz created_at
        timestamptz updated_at
    }
```

## Tables

### `users`
Discord-authenticated application users.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `discord_id` | `VARCHAR(32)` | UNIQUE, NOT NULL | Discord snowflake ID |
| `discord_username` | `VARCHAR(128)` | NOT NULL | |
| `display_name` | `VARCHAR(128)` | | Optional display name |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

**Indexes:** `idx_users_discord_id (discord_id)`

---

### `commitments`
Recurring expenses, income, and one-time payments. Uses signed amounts (negative = expense) and flat recurrence columns. The repository layer converts to/from the domain model's discriminated union.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `user_id` | `BIGINT` | FK -> users.id, NOT NULL | |
| `name` | `VARCHAR(255)` | NOT NULL | |
| `amount` | `NUMERIC(12,2)` | NOT NULL | Signed: negative = outflow |
| `frequency` | `VARCHAR(32)` | NOT NULL | `daily`, `weekly`, `biweekly`, `monthly`, `once` |
| `day_of_month` | `INTEGER` | | For `monthly` frequency |
| `anchor_date` | `DATE` | | For `weekly`/`biweekly` cadence alignment |
| `one_time_date` | `DATE` | | For `once` frequency |
| `start_date` | `DATE` | NOT NULL | |
| `end_date` | `DATE` | | |
| `is_paycheck` | `BOOLEAN` | NOT NULL, DEFAULT false | Pay-period grouping flag |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Soft delete flag |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

**Indexes:** `idx_commitments_user_id (user_id)`, `idx_commitments_user_active (user_id, is_active)`

---

### `balance_snapshots`
Real-time balance observations from bank notification emails or manual entry.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `user_id` | `BIGINT` | FK -> users.id, NOT NULL | |
| `balance` | `NUMERIC(12,2)` | NOT NULL | |
| `account_label` | `VARCHAR(64)` | | e.g. "Account - 1787" |
| `observed_at` | `TIMESTAMPTZ` | NOT NULL | When the bank reported the balance |
| `source` | `VARCHAR(32)` | NOT NULL, DEFAULT 'gmail' | `gmail` or `manual` |
| `gmail_message_id` | `VARCHAR(64)` | | For idempotent Gmail processing |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

**Indexes:** `idx_balance_user_time (user_id, observed_at DESC)`
**Constraints:** `UNIQUE (user_id, gmail_message_id)`

---

### `transactions`
Debit card usage notifications parsed from bank emails.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `user_id` | `BIGINT` | FK -> users.id, NOT NULL | |
| `amount` | `NUMERIC(12,2)` | NOT NULL | |
| `merchant` | `TEXT` | | e.g. "PL*SENSEFLOWER -DAEJEON" |
| `card_last_four` | `VARCHAR(4)` | | |
| `purchase_date` | `TIMESTAMPTZ` | NOT NULL | |
| `gmail_message_id` | `VARCHAR(64)` | | For idempotent Gmail processing |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

**Indexes:** `idx_transactions_user_date (user_id, purchase_date DESC)`
**Constraints:** `UNIQUE (user_id, gmail_message_id)`

---

### `gmail_subscriptions`
Tracks Gmail Pub/Sub push notification watch state per user.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGSERIAL` | PK | |
| `user_id` | `BIGINT` | FK -> users.id, NOT NULL | |
| `gmail_address` | `VARCHAR(255)` | NOT NULL | |
| `history_id` | `VARCHAR(64)` | | Last processed Gmail history ID |
| `watch_expiry` | `TIMESTAMPTZ` | | When the current watch expires |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | |

---

*Migration: `6c52f14865f5_initial_schema.py`*
