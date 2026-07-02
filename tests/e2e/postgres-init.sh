#!/usr/bin/env bash
# Apply the ledger schema migrations (000-013) in numeric order on first init.
# Mounted at /docker-entrypoint-initdb.d/ by docker-compose; runs as the
# POSTGRES_USER (bridge_worker), which owns the resulting tables.
set -euo pipefail

PSQL=(psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB")

# gen_random_uuid() needs pgcrypto; create it if available (idempotent).
"${PSQL[@]}" <<'SQL' || echo "pgcrypto unavailable (gen_random_uuid may use the built-in)"
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SQL

# Apply migrations in numeric order. Glob explicitly; fail if none found.
shopt -s nullglob
migrations=(/migrations/*.sql)
shopt -u nullglob
if [ "${#migrations[@]}" -eq 0 ]; then
  echo "FATAL: no migrations found at /migrations" >&2
  exit 1
fi
for sql in "${migrations[@]}"; do
  echo "applying migration: $(basename "$sql")"
  "${PSQL[@]}" -f "$sql"
done

echo "all migrations applied"
