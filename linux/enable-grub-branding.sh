#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo'; exit 1; }
[[ -f /opt/aoj-os/linux/branding/grub-background.png ]] || { echo 'AOJ OS not installed'; exit 1; }
mkdir -p /var/lib/aoj-os-backup /boot/grub
if [[ ! -f /var/lib/aoj-os-backup/grub-settings.saved ]]; then
  if [[ -f /etc/default/grub.d/90-aoj-branding.cfg ]]; then
    cp /etc/default/grub.d/90-aoj-branding.cfg /var/lib/aoj-os-backup/grub-settings.cfg
  else
    touch /var/lib/aoj-os-backup/grub-settings.absent
  fi
  touch /var/lib/aoj-os-backup/grub-settings.saved
fi
install -m 644 /opt/aoj-os/linux/branding/grub-background.png /boot/grub/aoj-background.png
mkdir -p /etc/default/grub.d
cat > /etc/default/grub.d/90-aoj-branding.cfg <<'CFG'
GRUB_BACKGROUND=/boot/grub/aoj-background.png
GRUB_COLOR_NORMAL=light-gray/black
GRUB_COLOR_HIGHLIGHT=white/red
CFG
update-grub
echo 'AOJ GRUB background enabled. Boot entries and recovery menu preserved.'
