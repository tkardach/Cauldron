#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [--service NAME] [--all] [--dry-run]

Stops, disables and removes systemd unit files for the Cauldron services.

Options:
  --service NAME   Remove a specific service (can be provided multiple times)
  --all            Remove both default services: cauldron-web.service and cauldron-client.service
  --dry-run        Print actions but don't perform them
  -h, --help       Show this help

Default: --all

Example:
  sudo ./scripts/remove_rpi_services.sh --all
  sudo ./scripts/remove_rpi_services.sh --service cauldron-web.service
  ./scripts/remove_rpi_services.sh --all --dry-run

EOF
}

DRY_RUN=0
SELECTED=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service)
      SELECTED+=("$2")
      shift 2
      ;;
    --all)
      SELECTED=("cauldron-web.service" "cauldron-client.service")
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  SELECTED=("cauldron-web.service" "cauldron-client.service")
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "Dry run: would remove the following services: ${SELECTED[*]}"
  for svc in "${SELECTED[@]}"; do
    echo "  - stop: sudo systemctl stop $svc"
    echo "  - disable: sudo systemctl disable $svc"
    echo "  - remove file: /etc/systemd/system/$svc"
  done
  echo "  - reload systemd: sudo systemctl daemon-reload"
  exit 0
fi

# Need root to manipulate systemd unit files in /etc/systemd/system
if [[ $EUID -ne 0 ]]; then
  echo "This script needs to run as root. Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

echo "Removing services: ${SELECTED[*]}"

for svc in "${SELECTED[@]}"; do
  UNIT_PATH="/etc/systemd/system/${svc}"

  if systemctl list-unit-files --type=service --no-legend | grep -q "^${svc}" || [[ -f "${UNIT_PATH}" ]]; then
    echo "Stopping $svc (if running)..."
    systemctl stop "$svc" || true

    echo "Disabling $svc..."
    systemctl disable "$svc" || true

    if [[ -f "${UNIT_PATH}" ]]; then
      echo "Removing unit file ${UNIT_PATH}"
      rm -f "${UNIT_PATH}"
    else
      echo "Unit file ${UNIT_PATH} not found; skipping remove"
    fi
  else
    echo "Service $svc not found (not installed). Skipping."
  fi
done

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Done. You can now re-run the installer with a different --python path."
