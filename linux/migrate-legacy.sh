#!/usr/bin/env bash
# Bridges AOJ Alpha startup paths to AOS; never deletes user data.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run this as root'; exit 1; }
[[ -x /opt/aos/linux/start-aos.sh ]] || { echo 'AOS is not installed under /opt/aos'; exit 1; }
backup_root='/var/lib/aos/legacy-migration'
mkdir -p "$backup_root"
backup_once() {
  local source="$1" name="$2"
  if [[ -f "$source" && ! -e "$backup_root/$name" ]]; then
    cp -a "$source" "$backup_root/$name"
  fi
}
# Existing Alpha sessions use this executable even after newer versions install.
backup_once /usr/local/bin/aoj-session original-aoj-session
cat > /usr/local/bin/aoj-session <<'SESSION'
#!/bin/sh
exec /usr/local/bin/aos-session "$@"
SESSION
chmod 755 /usr/local/bin/aoj-session

# Existing LightDM session identifier continues to work for saved logins.
backup_once /usr/share/xsessions/aoj-session.desktop original-aoj-session.desktop
cat > /usr/share/xsessions/aoj-session.desktop <<'DESKTOP'
[Desktop Entry]
Name=Airsoft OS 3.9.0 (AOJ compatibility)
Comment=Legacy AOJ session redirected to current Airsoft OS
Exec=/usr/local/bin/aos-session
Type=Application
DesktopNames=AOS
DESKTOP

# Redirect legacy direct launchers while retaining the old directory and data.
if [[ -d /opt/aoj-os && ! -L /opt/aoj-os ]]; then
  backup_once /opt/aoj-os/main.py original-alpha-main.py
  if [[ -d /opt/aoj-os/linux ]]; then
    backup_once /opt/aoj-os/linux/start-aoj.sh original-alpha-start-aoj.sh
    cat > /opt/aoj-os/linux/start-aoj.sh <<'LAUNCH'
#!/bin/sh
exec /opt/aos/linux/start-aos.sh "$@"
LAUNCH
    chmod 755 /opt/aoj-os/linux/start-aoj.sh
    backup_once /opt/aoj-os/linux/aoj-session original-alpha-linux-session
    cat > /opt/aoj-os/linux/aoj-session <<'SESSION'
#!/bin/sh
exec /usr/local/bin/aos-session "$@"
SESSION
    chmod 755 /opt/aoj-os/linux/aoj-session
  fi
  # Some Alpha launchers call python /opt/aoj-os/main.py directly.
  cat > /opt/aoj-os/main.py <<'PYTHON'
#!/usr/bin/env python3
"""Legacy AOJ entry point. Automatically run the current AOS interpreter."""
import os
import sys
os.execv('/opt/aos/.venv/bin/python', ['/opt/aos/.venv/bin/python', '/opt/aos/main.py', *sys.argv[1:]])
PYTHON
fi

# Avoid modifying /home user databases, widget layouts or profiles.
echo 'AOJ Alpha startup compatibility redirected to current AOS.'
echo "Original Alpha launch files backed up at: $backup_root"
