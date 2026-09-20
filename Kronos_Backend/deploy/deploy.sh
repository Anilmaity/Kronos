#!/usr/bin/env bash
# Deploy Kronos_Backend to the Lightsail box created by provision-lightsail.sh:
# rsync the code, write the on-box .env (DB creds fetched live from Lightsail, never
# stored locally), build + start Django behind nginx, run migrations, smoke-test.
#
#   AWS_PROFILE=prijen deploy/deploy.sh
#
# Same NAME_PREFIX/REGION overrides as provision-lightsail.sh.
set -euo pipefail

NAME_PREFIX="${NAME_PREFIX:-kronos}"
REGION="${REGION:-ap-south-1}"
INSTANCE_NAME="${NAME_PREFIX}-backend"
KEY_NAME="${NAME_PREFIX}-backend-key"
STATIC_IP_NAME="${NAME_PREFIX}-backend-ip"
DB_NAME_LS="${NAME_PREFIX}-db"
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"
REMOTE_DIR="/home/ubuntu/Kronos_Backend"
COMPOSE="docker compose -p kronos-backend -f deploy/compose.prod.yml"

export AWS_DEFAULT_REGION="$REGION"
lsail() { aws lightsail "$@"; }
log() { printf '\n==> %s\n' "$*"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$REPO_DIR/manage.py" ]] || { echo "ERROR: $REPO_DIR is not the Kronos_Backend root" >&2; exit 1; }
[[ -f "$KEY_PATH" ]] || { echo "ERROR: SSH key $KEY_PATH missing — run provision-lightsail.sh first" >&2; exit 1; }

log "resolving infrastructure"
PUBLIC_IP=$(lsail get-static-ip --static-ip-name "$STATIC_IP_NAME" --query 'staticIp.ipAddress' --output text)
DB_HOST=$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.masterEndpoint.address' --output text)
DB_PORT=$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.masterEndpoint.port' --output text)
DB_USER=$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.masterUsername' --output text)
DB_NAME=$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.masterDatabaseName' --output text)
DB_PASSWORD=$(lsail get-relational-database-master-user-password --relational-database-name "$DB_NAME_LS" --query masterUserPassword --output text)
[[ -n "$DB_PASSWORD" && "$DB_PASSWORD" != "None" ]] || { echo "ERROR: could not fetch DB master password" >&2; exit 1; }
echo "box: ubuntu@$PUBLIC_IP   db: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

SSH_OPTS=(-F /dev/null -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o BatchMode=yes)
rssh() { ssh "${SSH_OPTS[@]}" "ubuntu@$PUBLIC_IP" "$@"; }

log "waiting for SSH + Docker bootstrap on the box"
for i in $(seq 1 60); do
  if rssh 'test -f /var/lib/cloud/kronos-bootstrap-done && docker --version' >/dev/null 2>&1; then break; fi
  printf '.'; sleep 10
  [[ $i -eq 60 ]] && { echo; echo "ERROR: box not ready after 10 min" >&2; exit 1; }
done
echo; echo "ready"

log "syncing code -> $REMOTE_DIR"
rssh "mkdir -p $REMOTE_DIR"
rsync -az --delete -e "ssh ${SSH_OPTS[*]}" \
  --exclude '.git' --exclude '.venv' --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.env' --exclude '.env.*' --exclude 'staticfiles' --exclude 'media' --exclude '.pytest_cache' \
  --exclude 'account*.txt' --exclude '*.session' \
  "$REPO_DIR/" "ubuntu@$PUBLIC_IP:$REMOTE_DIR/"
echo "synced"

log "writing on-box .env (SECRET_KEY is generated once and kept across deploys)"
rssh "set -e; cd $REMOTE_DIR
  if [ -f .env ] && grep -q '^SECRET_KEY=' .env; then SK=\$(grep '^SECRET_KEY=' .env | cut -d= -f2-); else SK=\$(python3 -c 'import secrets;print(secrets.token_urlsafe(50))'); fi
  umask 077
  cat > .env <<ENV
SECRET_KEY=\$SK
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
EXTRA_ALLOWED_HOSTS=$PUBLIC_IP
ENV
  echo written"

log "building + starting containers"
rssh "cd $REMOTE_DIR && $COMPOSE up -d --build --remove-orphans 2>&1 | tail -5"

log "running migrations"
rssh "cd $REMOTE_DIR && $COMPOSE exec -T web python manage.py migrate --noinput 2>&1 | tail -15"

log "collectstatic"
rssh "cd $REMOTE_DIR && $COMPOSE exec -T web python manage.py collectstatic --noinput 2>&1 | tail -2" || echo "(collectstatic failed — non-fatal with DEBUG=True runserver)"

log "smoke test"
for i in $(seq 1 12); do
  if BODY=$(curl -fsS -m 10 -X POST "http://$PUBLIC_IP/graphql/" -H 'Content-Type: application/json' -d '{"query":"{ __typename }"}' 2>/dev/null); then
    echo "GraphQL OK: $BODY"; break
  fi
  printf '.'; sleep 5
  [[ $i -eq 12 ]] && { echo; echo "ERROR: GraphQL endpoint not responding; check: ssh -F /dev/null -i $KEY_PATH ubuntu@$PUBLIC_IP 'cd $REMOTE_DIR && $COMPOSE logs --tail=50 web'" >&2; exit 1; }
done
rssh "cd $REMOTE_DIR && $COMPOSE ps"

log "done"
echo "GraphQL: http://$PUBLIC_IP/graphql/"
echo "Admin:   http://$PUBLIC_IP/admin/   (create a superuser: ssh in, then '$COMPOSE exec web python manage.py createsuperuser')"
echo "SSH:     ssh -F /dev/null -i $KEY_PATH ubuntu@$PUBLIC_IP"
