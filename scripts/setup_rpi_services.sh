#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [--project-dir DIR] [--python PATH] [--http-dir DIR] [--http-port PORT] [--user USER] [--dry-run]

Installs two systemd services on a Raspberry Pi:
- cauldron-web.service -> runs: python -m cauldron.web.server.server
- cauldron-client.service -> runs: python -m http.server

Defaults:
  --project-dir   Current directory where Cauldron project is located (default: current dir)
  --python        /usr/bin/python3
  --http-dir      <project-dir>/cauldron/web/client
  --http-port     8000
  --user          current non-root user (auto-detected)
  --dry-run       Print generated unit files instead of installing

Example:
  sudo ./scripts/setup_rpi_services.sh --project-dir /home/pi/Cauldron --python /home/pi/venv/bin/python3

EOF
}

# Defaults
PROJECT_DIR="$(pwd)"
PYTHON_CMD="/usr/bin/python3"
HTTP_PORT=8000
HTTP_DIR=""
DRY_RUN=0
TARGET_USER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2;;
    --python) PYTHON_CMD="$2"; shift 2;;
    --http-dir) HTTP_DIR="$2"; shift 2;;
    --http-port) HTTP_PORT="$2"; shift 2;;
    --user) TARGET_USER="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift 1;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1"; usage; exit 1;;
  esac
done

if [[ -z "$HTTP_DIR" ]]; then
  HTTP_DIR="$PROJECT_DIR/cauldron/web/client"
fi

# Determine user to run services as
if [[ -z "$TARGET_USER" ]]; then
  if [[ -n "${SUDO_USER-}" ]]; then
    TARGET_USER="$SUDO_USER"
  else
    TARGET_USER="$(whoami)"
  fi
fi

CAULDRON_WEB_UNIT="/etc/systemd/system/cauldron-web.service"
CAULDRON_CLIENT_UNIT="/etc/systemd/system/cauldron-client.service"

# If the provided python looks like it's from a virtualenv, locate the activate script
VENV_DIR=""
ACTIVATE_SCRIPT=""
if [[ "${PYTHON_CMD}" == */bin/python* ]]; then
  # python path like /path/to/venv/bin/python or /path/to/venv/bin/python3
  maybe_bin_dir=$(dirname "${PYTHON_CMD}")
  maybe_venv_dir=$(dirname "${maybe_bin_dir}")
  if [[ -f "${maybe_venv_dir}/bin/activate" ]]; then
    VENV_DIR="${maybe_venv_dir}"
    ACTIVATE_SCRIPT="${maybe_venv_dir}/bin/activate"
  fi
fi

if [[ -n "${VENV_DIR}" ]]; then
  echo "Detected virtualenv at: ${VENV_DIR} (activate: ${ACTIVATE_SCRIPT})"
fi

generate_web_unit() {
  if [[ -n "${ACTIVATE_SCRIPT}" ]]; then
    exec_start="/bin/bash -lc 'source \"${ACTIVATE_SCRIPT}\" >/dev/null 2>&1 && cd \"${PROJECT_DIR}\" && exec \"${PYTHON_CMD}\" -m cauldron.web.server.server'"
  else
    exec_start="/bin/bash -lc 'cd \"${PROJECT_DIR}\" && exec \"${PYTHON_CMD}\" -m cauldron.web.server.server'"
  fi

  cat <<EOF
[Unit]
Description=Cauldron Web Server
After=network.target

[Service]
Type=simple
User=${TARGET_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${exec_start}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
}

generate_client_unit() {
  if [[ -n "${ACTIVATE_SCRIPT}" ]]; then
    exec_start="/bin/bash -lc 'source \"${ACTIVATE_SCRIPT}\" >/dev/null 2>&1 && cd \"${HTTP_DIR}\" && exec \"${PYTHON_CMD}\" -m http.server ${HTTP_PORT} --directory \"${HTTP_DIR}\"'"
  else
    exec_start="/bin/bash -lc 'cd \"${HTTP_DIR}\" && exec \"${PYTHON_CMD}\" -m http.server ${HTTP_PORT} --directory \"${HTTP_DIR}\"'"
  fi

  cat <<EOF
[Unit]
Description=Cauldron Static HTTP Server
After=network.target

[Service]
Type=simple
User=${TARGET_USER}
WorkingDirectory=${HTTP_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${exec_start}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
}

if [[ $DRY_RUN -eq 1 ]]; then
  echo "--- cauldron-web.service (preview) ---"
  generate_web_unit
  echo
  echo "--- cauldron-client.service (preview) ---"
  generate_client_unit
  exit 0
fi

# Must be root to write to /etc/systemd/system
if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo. Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

echo "Installing services as root. Project dir: ${PROJECT_DIR}, python: ${PYTHON_CMD}, http-dir: ${HTTP_DIR}, user: ${TARGET_USER}"

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Error: project directory ${PROJECT_DIR} does not exist." >&2
  exit 1
fi

if [[ ! -x "${PYTHON_CMD}" && ! -f "${PYTHON_CMD}" ]]; then
  echo "Warning: python executable ${PYTHON_CMD} not found or not executable. Proceeding anyway." >&2
fi

if [[ ! -d "${HTTP_DIR}" ]]; then
  echo "Warning: http directory ${HTTP_DIR} does not exist. The http service may fail." >&2
fi

echo "Writing ${CAULDRON_WEB_UNIT}"
generate_web_unit > "${CAULDRON_WEB_UNIT}"
chmod 644 "${CAULDRON_WEB_UNIT}"

echo "Writing ${CAULDRON_CLIENT_UNIT}"
generate_client_unit > "${CAULDRON_CLIENT_UNIT}"
chmod 644 "${CAULDRON_CLIENT_UNIT}"

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling services to start at boot..."
systemctl enable cauldron-web.service
systemctl enable cauldron-client.service

echo "Starting (or restarting) services now..."
systemctl restart cauldron-web.service || true
systemctl restart cauldron-client.service || true

echo "Done. Check status with: systemctl status cauldron-web.service cauldron-client.service"
