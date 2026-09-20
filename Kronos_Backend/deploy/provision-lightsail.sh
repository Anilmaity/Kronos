#!/usr/bin/env bash
# Provision a Kronos_Backend environment on AWS Lightsail: key pair, Ubuntu box with
# Docker, static IP, firewall, and a managed PostgreSQL DB. Idempotent — re-running
# skips anything that already exists. Prints the values deploy.sh needs.
#
#   AWS_PROFILE=prijen deploy/provision-lightsail.sh
#
# Override any of these via env: NAME_PREFIX, REGION, AZ, INSTANCE_BUNDLE, DB_BUNDLE, DB_BLUEPRINT.
set -euo pipefail

NAME_PREFIX="${NAME_PREFIX:-kronos}"
REGION="${REGION:-ap-south-1}"
AZ="${AZ:-${REGION}a}"
INSTANCE_NAME="${NAME_PREFIX}-backend"
KEY_NAME="${NAME_PREFIX}-backend-key"
STATIC_IP_NAME="${NAME_PREFIX}-backend-ip"
DB_NAME_LS="${NAME_PREFIX}-db"
INSTANCE_BLUEPRINT="${INSTANCE_BLUEPRINT:-ubuntu_22_04}"
INSTANCE_BUNDLE="${INSTANCE_BUNDLE:-micro_3_1}"     # 1 GB RAM, ~$7/mo (new accounts are capped below 2 GB)
DB_BLUEPRINT="${DB_BLUEPRINT:-}"                    # auto: newest postgres blueprint
DB_BUNDLE="${DB_BUNDLE:-micro_2_0}"                 # 1 GB RAM / 40 GB, ~$15/mo
DB_MASTER_USER="${DB_MASTER_USER:-dbmasteruser}"
DB_MASTER_DB="${DB_MASTER_DB:-kronos}"
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"

export AWS_DEFAULT_REGION="$REGION"
lsail() { aws lightsail "$@"; }
log() { printf '\n==> %s\n' "$*"; }

# ---- key pair ---------------------------------------------------------------
log "key pair $KEY_NAME"
if lsail get-key-pair --key-pair-name "$KEY_NAME" >/dev/null 2>&1; then
  echo "exists"
  [[ -f "$KEY_PATH" ]] || { echo "ERROR: key pair exists in Lightsail but $KEY_PATH is missing locally." >&2; exit 1; }
else
  lsail create-key-pair --key-pair-name "$KEY_NAME" --query privateKeyBase64 --output text > "$KEY_PATH"
  chmod 600 "$KEY_PATH"
  echo "created -> $KEY_PATH"
fi

# ---- instance ---------------------------------------------------------------
log "instance $INSTANCE_NAME ($INSTANCE_BLUEPRINT / $INSTANCE_BUNDLE in $AZ)"
if lsail get-instance --instance-name "$INSTANCE_NAME" >/dev/null 2>&1; then
  echo "exists"
else
  USER_DATA='#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl rsync
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
systemctl enable --now docker
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab
touch /var/lib/cloud/kronos-bootstrap-done'
  lsail create-instances --instance-names "$INSTANCE_NAME" --availability-zone "$AZ" \
    --blueprint-id "$INSTANCE_BLUEPRINT" --bundle-id "$INSTANCE_BUNDLE" \
    --key-pair-name "$KEY_NAME" --user-data "$USER_DATA" \
    --tags key=project,value=kronos >/dev/null
  echo "created"
fi

# ---- static IP --------------------------------------------------------------
log "static IP $STATIC_IP_NAME"
if ! lsail get-static-ip --static-ip-name "$STATIC_IP_NAME" >/dev/null 2>&1; then
  lsail allocate-static-ip --static-ip-name "$STATIC_IP_NAME" >/dev/null
  echo "allocated"
fi
ATTACHED_TO=$(lsail get-static-ip --static-ip-name "$STATIC_IP_NAME" --query 'staticIp.attachedTo' --output text)
if [[ "$ATTACHED_TO" != "$INSTANCE_NAME" ]]; then
  echo "waiting for instance to be running before attaching IP..."
  until [[ "$(lsail get-instance --instance-name "$INSTANCE_NAME" --query 'instance.state.name' --output text)" == "running" ]]; do sleep 10; done
  lsail attach-static-ip --static-ip-name "$STATIC_IP_NAME" --instance-name "$INSTANCE_NAME" >/dev/null
  echo "attached"
fi
PUBLIC_IP=$(lsail get-static-ip --static-ip-name "$STATIC_IP_NAME" --query 'staticIp.ipAddress' --output text)
echo "IP: $PUBLIC_IP"

# ---- firewall: 22, 80, 443 only ---------------------------------------------
log "firewall (22/80/443)"
lsail put-instance-public-ports --instance-name "$INSTANCE_NAME" --port-infos \
  'fromPort=22,toPort=22,protocol=tcp' 'fromPort=80,toPort=80,protocol=tcp' 'fromPort=443,toPort=443,protocol=tcp' >/dev/null
echo "set"

# ---- managed PostgreSQL -----------------------------------------------------
log "database $DB_NAME_LS ($DB_BUNDLE)"
if lsail get-relational-database --relational-database-name "$DB_NAME_LS" >/dev/null 2>&1; then
  echo "exists"
else
  if [[ -z "$DB_BLUEPRINT" ]]; then
    DB_BLUEPRINT=$(lsail get-relational-database-blueprints --query 'blueprints[?engine==`postgres`] | sort_by(@,&engineVersion)[-1].blueprintId' --output text)
  fi
  echo "blueprint: $DB_BLUEPRINT"
  lsail create-relational-database --relational-database-name "$DB_NAME_LS" --availability-zone "$AZ" \
    --relational-database-blueprint-id "$DB_BLUEPRINT" --relational-database-bundle-id "$DB_BUNDLE" \
    --master-database-name "$DB_MASTER_DB" --master-username "$DB_MASTER_USER" \
    --no-publicly-accessible --tags key=project,value=kronos >/dev/null
  echo "created (private: reachable only from Lightsail instances in this account/region)"
fi

# ---- wait for readiness -----------------------------------------------------
log "waiting for instance + database to be available (DB can take ~10-15 min)"
until [[ "$(lsail get-instance --instance-name "$INSTANCE_NAME" --query 'instance.state.name' --output text)" == "running" ]]; do sleep 10; done
echo "instance: running"
until [[ "$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.state' --output text)" == "available" ]]; do
  printf '.'; sleep 20
done
echo; echo "database: available"

# ---- normalise master password ----------------------------------------------
# Lightsail generates passwords full of shell/URL metacharacters ($ & ( > { ...),
# which break .env parsing and postgres:// URLs. Rotate once to alphanumeric.
log "master password"
CUR_PW=$(lsail get-relational-database-master-user-password --relational-database-name "$DB_NAME_LS" --query masterUserPassword --output text)
if [[ "$CUR_PW" =~ ^[A-Za-z0-9]+$ ]]; then
  echo "already alphanumeric"
else
  NEW_PW=$(python3 -c 'import secrets,string; a=string.ascii_letters+string.digits; print("".join(secrets.choice(a) for _ in range(32)))')
  lsail update-relational-database --relational-database-name "$DB_NAME_LS" --master-user-password "$NEW_PW" --apply-immediately >/dev/null
  printf 'rotating'
  until [[ "$(lsail get-relational-database-master-user-password --relational-database-name "$DB_NAME_LS" --query masterUserPassword --output text)" == "$NEW_PW" ]]; do printf '.'; sleep 10; done
  until [[ "$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.state' --output text)" == "available" ]]; do printf '.'; sleep 10; done
  echo " done"
fi
unset CUR_PW NEW_PW

DB_HOST=$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.masterEndpoint.address' --output text)
DB_PORT=$(lsail get-relational-database --relational-database-name "$DB_NAME_LS" --query 'relationalDatabase.masterEndpoint.port' --output text)

log "done"
cat <<SUMMARY
INSTANCE_NAME=$INSTANCE_NAME
PUBLIC_IP=$PUBLIC_IP
SSH_KEY=$KEY_PATH
DB_NAME_LS=$DB_NAME_LS
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_USER=$DB_MASTER_USER
DB_NAME=$DB_MASTER_DB

Next:  AWS_PROFILE=$AWS_PROFILE deploy/deploy.sh
SUMMARY
