#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo'; exit 1; }
BACKUP=/var/lib/aoj-os-backup
if [[ -f "$BACKUP/grub-settings.saved" ]]; then
  if [[ -f "$BACKUP/grub-settings.absent" ]]; then
    rm -f /etc/default/grub.d/90-aoj-branding.cfg
  elif [[ -f "$BACKUP/grub-settings.cfg" ]]; then
    cp "$BACKUP/grub-settings.cfg" /etc/default/grub.d/90-aoj-branding.cfg
  fi
  command -v update-grub >/dev/null && update-grub || true
fi
if [[ -f "$BACKUP/greeter.saved" ]]; then
  if [[ -f "$BACKUP/greeter.absent" ]]; then
    rm -f /etc/lightdm/lightdm-gtk-greeter.conf
  elif [[ -f "$BACKUP/greeter.conf" ]]; then
    cp "$BACKUP/greeter.conf" /etc/lightdm/lightdm-gtk-greeter.conf
  fi
fi
if [[ -f "$BACKUP/plymouth-theme" ]] && command -v plymouth-set-default-theme >/dev/null; then
  OLD=$(cat "$BACKUP/plymouth-theme")
  [[ -n "$OLD" && "$OLD" != 'aoj' ]] && plymouth-set-default-theme -R "$OLD" || true
fi
rm -f /usr/local/bin/aoj-session /usr/share/xsessions/aoj-session.desktop
rm -rf /opt/aoj-os /usr/share/plymouth/themes/aoj /usr/share/backgrounds/aoj
printf 'AOJ session and branding removed. Personal files, Debian and packages remain.\n'
