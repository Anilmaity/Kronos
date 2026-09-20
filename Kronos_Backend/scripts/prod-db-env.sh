#!/usr/bin/env bash
# Export DB_* for the live Kronos DB (Lightsail kronos-strategies-db) into the
# current shell. The master password is fetched live from Lightsail on every
# call (see docs/superpowers/RUNBOOK-2026-06-24-prod-rollout.md) — never
# written to disk.
#
#   source scripts/prod-db-env.sh            # then: python manage.py showmigrations apis
#   source scripts/prod-db-env.sh --unset    # clear the vars again
#
# Needs the `jegnus` AWS profile (~/.aws/credentials) and boto3 from this
# repo's .venv. Falls back to the aws CLI if boto3 isn't importable.

# Works when sourced from bash or zsh; refuses to run as a plain script
# (exports would be lost in the child shell).
if [[ -n "${ZSH_VERSION:-}" ]]; then
  _kb_self="${(%):-%x}"
  _kb_sourced=$([[ "$ZSH_EVAL_CONTEXT" == *:file* ]] && echo 1 || echo 0)
else
  _kb_self="${BASH_SOURCE[0]}"
  _kb_sourced=$([[ "$_kb_self" != "$0" ]] && echo 1 || echo 0)
fi
if [[ "$_kb_sourced" != 1 ]]; then
  echo "prod-db-env.sh: source this file, don't execute it:  source $0" >&2
  exit 1
fi
unset _kb_sourced

if [[ "$1" == "--unset" ]]; then
  unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD DB_SSLMODE AWS_PROFILE AWS_DEFAULT_REGION _kb_self
  echo "prod DB env cleared"
  return 0
fi

_kb_dir="$(cd "$(dirname "$_kb_self")/.." && pwd)"
_kb_py="$_kb_dir/.venv/bin/python"

export AWS_PROFILE="${AWS_PROFILE:-jegnus}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-south-1}"

if [[ -x "$_kb_py" ]] && "$_kb_py" -c 'import boto3' 2>/dev/null; then
  _kb_pw="$("$_kb_py" -c '
import boto3
print(boto3.client("lightsail").get_relational_database_master_user_password(
    relationalDatabaseName="kronos-strategies-db")["masterUserPassword"])')"
elif command -v aws >/dev/null; then
  _kb_pw="$(aws lightsail get-relational-database-master-user-password \
    --relational-database-name kronos-strategies-db \
    --query masterUserPassword --output text)"
else
  echo "prod-db-env.sh: need boto3 in $_kb_py or the aws CLI" >&2
  unset _kb_dir _kb_py _kb_self
  return 1
fi

if [[ -z "$_kb_pw" ]]; then
  echo "prod-db-env.sh: failed to fetch DB password from Lightsail (profile $AWS_PROFILE)" >&2
  unset _kb_dir _kb_py _kb_pw _kb_self
  return 1
fi

export DB_HOST="ls-c3002c4cc96130d24250133c280823179d61a1da.czomeckmiuze.ap-south-1.rds.amazonaws.com"
export DB_PORT="5432"
export DB_NAME="tsdb"
export DB_USER="dbmasteruser"
export DB_PASSWORD="$_kb_pw"
export DB_SSLMODE="require"
unset _kb_dir _kb_py _kb_pw _kb_self

echo "prod DB env set -> $DB_USER@$DB_HOST/$DB_NAME  (this is the LIVE database)"
