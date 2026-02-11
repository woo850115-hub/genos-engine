#!/bin/bash
set -e

# Create additional game databases (genos_tbamud is created by POSTGRES_DB)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE genos_10woongi OWNER $POSTGRES_USER;
EOSQL
