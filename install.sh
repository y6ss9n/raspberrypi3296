#!/usr/bin/env bash

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/opt/pi_backend"
VENV_DIR="$TARGET_DIR/venv"
SERVICE_NAME="pi-backend.service"
SERVICE_FILE="$SOURCE_DIR/$SERVICE_NAME"
SYSTEMD_FILE="/etc/systemd/system/$SERVICE_NAME"
VENV_BACKUP_DIR=""

log() {
  printf '[pi-backend] %s\n' "$1"
}

require_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "This installer must be run as root." >&2
    exit 1
  fi
}

install_system_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    bluetooth \
    bluez \
    python3 \
    python3-pip \
    python3-venv \
    rsync
}

sync_source() {
  mkdir -p "$TARGET_DIR"
  rsync -a --delete \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '.venv/' \
    --exclude 'venv/' \
    --exclude 'android-app/' \
    --exclude 'src/' \
    "$SOURCE_DIR/" "$TARGET_DIR/"
}

backup_existing_venv() {
  if [[ -d "$VENV_DIR" ]]; then
    VENV_BACKUP_DIR="$(mktemp -d /tmp/pi_backend_venv_backup.XXXXXX)"
    mv "$VENV_DIR" "$VENV_BACKUP_DIR/venv"
  fi
}

restore_existing_venv() {
  if [[ -n "$VENV_BACKUP_DIR" && -d "$VENV_BACKUP_DIR/venv" && ! -e "$VENV_DIR" ]]; then
    mv "$VENV_BACKUP_DIR/venv" "$VENV_DIR"
  fi
  if [[ -n "$VENV_BACKUP_DIR" && -d "$VENV_BACKUP_DIR" ]]; then
    rm -rf "$VENV_BACKUP_DIR"
    VENV_BACKUP_DIR=""
  fi
}

create_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Virtual environment is missing or corrupted at $VENV_DIR" >&2
    exit 1
  fi
  "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
  "$VENV_DIR/bin/pip" install --no-cache-dir -r "$TARGET_DIR/requirements.txt"
}

configure_permissions() {
  chown -R root:root "$TARGET_DIR"
  chmod -R go-rwx "$TARGET_DIR"
  chmod 755 "$TARGET_DIR"
  chmod 755 "$TARGET_DIR/main.py"
  chmod 644 "$TARGET_DIR/requirements.txt"
  chmod 644 "$TARGET_DIR/pi-backend.service"
  chmod 755 "$TARGET_DIR/install.sh"
}

install_service() {
  cp "$SERVICE_FILE" "$SYSTEMD_FILE"
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
}

main() {
  require_root
  trap 'if [[ -n "$VENV_BACKUP_DIR" && -d "$VENV_BACKUP_DIR/venv" && ! -e "$VENV_DIR" ]]; then mv "$VENV_BACKUP_DIR/venv" "$VENV_DIR"; fi; if [[ -n "$VENV_BACKUP_DIR" && -d "$VENV_BACKUP_DIR" ]]; then rm -rf "$VENV_BACKUP_DIR"; fi' EXIT
  log "Installing system dependencies"
  install_system_packages
  log "Backing up existing virtual environment if present"
  backup_existing_venv
  log "Copying backend source to $TARGET_DIR"
  sync_source
  log "Restoring virtual environment if one existed"
  restore_existing_venv
  log "Creating virtual environment and installing Python dependencies"
  create_venv
  log "Setting permissions"
  configure_permissions
  log "Installing systemd service"
  install_service
  log "Installation complete"
}

main "$@"