# Garden Roots — DB Migration Plan (Cloud)

## Overview

This document describes the exact script execution order, known issues found during review,
and steps required to migrate the Garden Roots Oracle schema from a local XE instance to any
Oracle Cloud (ATP / Autonomous Database) or other Oracle 12c+ cloud environment.

---

## Script Inventory

| File | Type | Purpose |
|------|------|---------|
| `00_drop_all.sql` | Reset | Drops all 18 tables safely (idempotent, ignores ORA-00942) |
| `01_create_tables.sql` | DDL | Creates 17 base tables in FK-dependency order |
| `02_create_indexes.sql` | DDL | Creates performance indexes on all base tables |
| `03_seed_data.sql` | DML | Inserts default admin user and head-office warehouse (MERGE, idempotent) |
| `04_verify.sql` | Verification | Checks all 18 tables, constraints, indexes, and seed data |
| `05_add_users.sql` | Migration | Creates USERS table + adds user_id FK to orders |
| `06_order_pickup_and_notes.sql` | Migration | Adds delivery_type, pickup_location_id, customer_notes to orders |
| `07_order_delivery_feedback.sql` | Migration | Adds delivery_feedback column to orders |
| `08_order_shipment_link.sql` | Migration | Adds shipment_id FK to orders for reconciliation |
| `run_all.sql` | Orchestrator | Runs scripts 01→02→03→05→06→07→08 in sequence |

---

## Execution Order (Fresh Install)

Run these in order from the `db_scripts/` directory using SQL*Plus or SQLcl:

```
Step 0  (optional – fresh slate only)   @00_drop_all.sql
Step 1  base tables                     @01_create_tables.sql
Step 2  indexes                         @02_create_indexes.sql
Step 3  seed data                       @03_seed_data.sql
Step 4  migration 05 – users            @05_add_users.sql
Step 5  migration 06 – pickup/notes     @06_order_pickup_and_notes.sql
Step 6  migration 07 – feedback         @07_order_delivery_feedback.sql
Step 7  migration 08 – shipment link    @08_order_shipment_link.sql
Step 8  verify                          @04_verify.sql
```

Or run the full sequence with a single command:

```sql
@00_drop_all.sql
@run_all.sql
@04_verify.sql
```

---

## Issues Found & Fixed

| # | File | Issue | Fix Applied |
|---|------|-------|-------------|
| 1 | `run_all.sql` | Only ran scripts 01–03; migrations 05–08 were never included | Added steps 4–7 to orchestrate all migrations |
| 2 | `00_drop_all.sql` | Missing `USERS` table (added by migration 05) — re-run would error on FK | Added `DROP TABLE users` in correct position (after orders, before product_variants) |
| 3 | `04_verify.sql` | Only checked 17 base tables; missed USERS and migration columns on ORDERS | Updated to check 18 tables + added migration column check (section 6) |

---

## Environment-Specific Connection Commands

### Cloud (Oracle ATP — wallet) — PRIMARY

The wallet lives at `garden-roots-backend/wallet/`. The TNS names are defined in
`wallet/tnsnames.ora`. Use `gardenroots2026_tp` for the application workload.

**SQL*Plus:**
```bash
export TNS_ADMIN=/absolute/path/to/garden-roots-backend/wallet
sqlplus ADMIN/<atp_password>@gardenroots2026_tp
@run_all.sql
```

**SQLcl:**
```bash
export TNS_ADMIN=/absolute/path/to/garden-roots-backend/wallet
sql ADMIN/<atp_password>@gardenroots2026_tp
@run_all.sql
```

Available TNS aliases (all point to the same ATP instance):

| Alias | Use case |
|-------|----------|
| `gardenroots2026_tp` | Application / API (recommended) |
| `gardenroots2026_tpurgent` | Priority OLTP |
| `gardenroots2026_high` | Reporting / analytics (max resources) |
| `gardenroots2026_medium` | Batch jobs |
| `gardenroots2026_low` | Background / dev queries |

### Local (Oracle XE / XEPDB1) — development only
```bash
sqlplus system/Oracle123@localhost:1521/XEPDB1
@run_all.sql
```

> **Note:** `run_all.sql` contains no hardcoded connection string — connect first,
> then run `@run_all.sql` from the `db_scripts/` directory.

---

## Pre-Flight Checklist

Before running on any environment:

- [ ] Connect as the **schema owner** (not SYS/SYSTEM in production ATP)
- [ ] Replace `REPLACE_WITH_BCRYPT_HASH` in `03_seed_data.sql` with a real bcrypt hash
  ```python
  # Generate hash:
  from passlib.context import CryptContext
  ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')
  print(ctx.hash('YourStrongPassword'))
  ```
- [ ] For a fresh cloud schema: run `00_drop_all.sql` first if any tables already exist
- [ ] Confirm Oracle 12c+ is available (`GENERATED ALWAYS AS IDENTITY` requires 12c+)
- [ ] On ATP: ensure user has `CREATE TABLE`, `CREATE INDEX` privileges
- [ ] Run `04_verify.sql` after setup — expected: 18 tables, 0 disabled constraints, 0 missing tables

---

## Post-Setup Verification Expected Output

| Check | Expected |
|-------|----------|
| Tables found | 18 rows, all status = OK |
| Missing tables | 0 rows |
| admin_users row count | 1 (seed row) |
| pickup_locations row count | 1 (Head Office Warehouse) |
| Disabled constraints | 0 rows |
| Migration columns on ORDERS | 6 columns present |
| Password status | "Hash looks set" (not placeholder) |

---

## Rollback / Reset

To completely reset any environment back to empty:

```sql
@00_drop_all.sql
```

This is safe to run on a schema that is already empty — all drops are wrapped in
PL/SQL blocks that silently skip ORA-00942 (table does not exist).
