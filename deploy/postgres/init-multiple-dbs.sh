#!/bin/bash
# Create multiple Postgres databases from POSTGRES_MULTIPLE_DATABASES env var
# (comma-separated). The default POSTGRES_USER owns all of them.
set -euo pipefail

create_db() {
  local db="$1"
  echo "Creating database: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE "$db"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
    GRANT ALL PRIVILEGES ON DATABASE "$db" TO "$POSTGRES_USER";
EOSQL
}

if [[ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]]; then
  for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
    create_db "$db"
  done
fi
