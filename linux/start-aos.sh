#!/bin/sh
# Launch current AOS with persistent diagnostics on the user's home directory.
set -u
LOGDIR="${XDG_STATE_HOME:-$HOME/.local/state}/aos"
mkdir -p "$LOGDIR" || exit 1
LOGFILE="$LOGDIR/desktop.log"
{
  printf '\n===== AOS 3.9.0: %s =====\n' "$(date -Is)"
  printf 'User: %s  Display: %s  Session: %s\n' "$(id -un)" "${DISPLAY:-unset}" "${XDG_SESSION_TYPE:-unset}"
  cd /opt/aos || exit 1
  export PYTHONUNBUFFERED=1
  export QT_X11_NO_MITSHM=1
  /opt/aos/.venv/bin/python /opt/aos/main.py --desktop
  code=$?
  printf 'AOS exit status: %s\n' "$code"
  exit "$code"
} >> "$LOGFILE" 2>&1
