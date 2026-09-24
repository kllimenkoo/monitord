#!/usr/bin/env bash
#
# monitord installer
#
# Usage:
#   sudo ./install.sh              install or upgrade monitord
#   sudo ./install.sh --uninstall  remove the service, venv and CLI symlink
#   sudo ./install.sh --purge      like --uninstall, but also delete data and logs
#
# Assumes: a systemd-based Linux host (tested target: Ubuntu) with Python 3.11+
# and the python3-venv module available.

set -euo pipefail

APP="monitord"
INSTALL_DIR="/opt/${APP}"
VENV_DIR="${INSTALL_DIR}/venv"
UNIT_FILE="/etc/systemd/system/${APP}.service"
BIN_LINK="/usr/local/bin/${APP}"
SERVICE_USER="${APP}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

require_root() {
  [[ $EUID -eq 0 ]] || die "this script must be run as root (try: sudo bash ${BASH_SOURCE[0]})"
}

uninstall() {
  local purge="${1:-no}"
  require_root

  log "Stopping and disabling ${APP} service"
  systemctl disable --now "${APP}.service" 2>/dev/null || true
  rm -f "${UNIT_FILE}"
  systemctl daemon-reload

  log "Removing ${INSTALL_DIR} and ${BIN_LINK}"
  rm -rf "${INSTALL_DIR}"
  rm -f "${BIN_LINK}"

  if [[ "${purge}" == "yes" ]]; then
    log "Purging data, logs and service user"
    rm -rf "/var/lib/${APP}" "/var/log/${APP}"
    id "${SERVICE_USER}" &>/dev/null && userdel "${SERVICE_USER}" || true
  fi

  log "${APP} uninstalled"
  exit 0
}

case "${1:-}" in
--uninstall) uninstall no ;;
--purge) uninstall yes ;;
"") ;;
*) die "unknown option: $1" ;;
esac

require_root

# ---------------------------------------------------------------- preflight
log "Checking prerequisites"

[[ -d /run/systemd/system ]] || die "systemd is not running on this host"
command -v python3 >/dev/null || die "python3 not found"

# asyncio.TaskGroup (used by the daemon) requires Python 3.11+
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' ||
  die "Python 3.11 or newer is required (found $(python3 -V 2>&1))"

[[ -f "${SRC_DIR}/pyproject.toml" ]] ||
  die "pyproject.toml not found next to install.sh (${SRC_DIR})"

# ---------------------------------------------------------------- user
if ! id "${SERVICE_USER}" &>/dev/null; then
  log "Creating system user '${SERVICE_USER}'"
  useradd --system --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

# ---------------------------------------------------------------- venv
log "Creating virtual environment in ${VENV_DIR}"
mkdir -p "${INSTALL_DIR}"
python3 -m venv "${VENV_DIR}" ||
  die "could not create a virtual environment (on Ubuntu: apt install python3-venv)"

log "Installing monitord and its dependencies"
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet "${SRC_DIR}"
# Re-running the installer must pick up changed source even if the version
# number was not bumped, so reinstall the package itself without its deps.
"${VENV_DIR}/bin/pip" install --quiet --force-reinstall --no-deps "${SRC_DIR}"

ln -sf "${VENV_DIR}/bin/${APP}" "${BIN_LINK}"

# ---------------------------------------------------------------- systemd unit
log "Writing ${UNIT_FILE}"
cat >"${UNIT_FILE}" <<EOF
[Unit]
Description=monitord - lightweight Linux system health monitoring daemon
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_DIR}/bin/python -m monitord.daemon
Restart=on-failure
RestartSec=5

# systemd creates these directories and hands them to the service user
StateDirectory=${APP}
LogsDirectory=${APP}
UMask=0022
Environment=MONITORD_DB=/var/lib/${APP}/${APP}.db
Environment=MONITORD_ALERT_LOG=/var/log/${APP}/alerts.log

# Hardening: the daemon only reads /proc and writes to its own directories
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------- start
log "Enabling and starting the service"
systemctl daemon-reload
systemctl enable --now "${APP}.service"

for i in 1 2 3 4 5; do
  if systemctl is-active --quiet "${APP}.service"; then
    log "monitord is running"
    echo
    echo "  monitord status   show service status"
    echo "  monitord ui       open the terminal dashboard"
    echo "  monitord web      open the web dashboard"
    echo "  monitord alerts   show recent anomaly alerts"
    exit 0
  fi
  sleep 1
done

die "service failed to start - see: journalctl -u ${APP} -e"
