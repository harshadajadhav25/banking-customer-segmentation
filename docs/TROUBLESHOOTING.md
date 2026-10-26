# Troubleshooting Guide

This document records technical issues encountered while developing the **Banking Customer Segmentation and Product Recommendation Platform**.

## PostgreSQL Password Authentication Failure

### Date

October 3, 2026

### Error

The Python ingestion pipeline failed while connecting to PostgreSQL:

```text
FATAL: password authentication failed for user "banking_user"
```

### Symptoms

The following command worked successfully because it connected to PostgreSQL from inside the Docker container:

```powershell
docker compose exec postgres psql -U banking_user -d banking_analytics
```

However, the Python application could not connect using the same database name, username, and password.

### Investigation

The `.env` configuration was checked first:

```text
POSTGRES_DB=banking_analytics
POSTGRES_USER=banking_user
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Python was confirmed to be reading the expected password. Password authentication was then tested from inside the container:

```powershell
docker compose exec -e PGPASSWORD=change_me postgres psql -h 127.0.0.1 -U banking_user -d banking_analytics -c "SELECT current_user, current_database();"
```

The test succeeded, proving that the Docker PostgreSQL username and password were valid.

The Windows process listening on port `5432` was inspected using:

```powershell
Get-NetTCPConnection -LocalPort 5432 -State Listen
```

The owning process was then identified using:

```powershell
Get-Process -Id 6332
```

The process name was `postgres`, confirming that a separate Windows PostgreSQL service was already using port `5432`.

### Root Cause

Python connections to `localhost:5432` and `127.0.0.1:5432` were reaching the existing Windows PostgreSQL service instead of the PostgreSQL database running inside the project's Docker container.

The existing Windows PostgreSQL instance did not recognize the project's `banking_user` credentials, which caused the authentication failure.

### Resolution

The project's `.env` configuration was changed to use a different host port:

```text
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
```

The Docker container was recreated so the new port mapping would take effect:

```powershell
docker compose down
docker compose up -d postgres
```

The final Docker port mapping became:

```text
Windows port 5433 -> Docker PostgreSQL port 5432
```

The Python connection was tested again and completed successfully.

### Final Result

The ingestion pipeline loaded and reconciled all eight source tables:

| Source table | Source rows | Database rows | Status |
|---|---:|---:|---|
| account | 4,500 | 4,500 | PASS |
| card | 892 | 892 | PASS |
| client | 5,369 | 5,369 | PASS |
| disposition | 5,369 | 5,369 | PASS |
| district | 77 | 77 | PASS |
| loan | 682 | 682 | PASS |
| order | 6,471 | 6,471 | PASS |
| transaction | 1,056,320 | 1,056,320 | PASS |

A total of **1,079,680 records** were loaded successfully.

### Lesson Learned

When database authentication fails despite verified credentials, confirm that the application is connecting to the intended database instance. Local database installations and Docker containers can compete for the same host port.

Testing the connection from both inside and outside the container helps determine whether a failure is caused by credentials, container networking, or a host-level port conflict.

