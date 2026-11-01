#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run: sudo bash linux/install.sh"; exit 1; fi
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
[[ -f "$SOURCE/main.py" ]] || { echo 'Extract the AOS package first'; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y xorg xinit openbox lightdm lightdm-gtk-greeter plymouth plymouth-themes   python3 python3-venv python3-pip python3-dev libxcb-cursor0 libegl1 libopengl0   libxkbcommon-x11-0 libglib2.0-0 libdbus-1-3 xdg-utils network-manager   network-manager-gnome nm-connection-editor blueman arandr pavucontrol xfce4-power-manager   xfce4-terminal xfce4-appfinder thunar thunar-volman gvfs gvfs-backends udisks2   xterm openssl adwaita-icon-theme gnome-themes-extra
install -d -m 755 /opt/aos
cp -a "$SOURCE/main.py" "$SOURCE/team_ops.py" "$SOURCE/cyber_native.py"  "$SOURCE/aos_management.py" "$SOURCE/aos_updates.py" "$SOURCE/aos_network.py" "$SOURCE/aos_network_gui.py" "$SOURCE/aos_field_sync.py" "$SOURCE/aos_live.py" "$SOURCE/aos_live_gui.py" "$SOURCE/aos_devices.py" "$SOURCE/aos_release.py" "$SOURCE/aos_github.py" "$SOURCE/aos_widgets.py" "$SOURCE/aos_planning.py" "$SOURCE/aos_apply_update.py" "$SOURCE/aos_doctor.py" "$SOURCE/VERSION" "$SOURCE/requirements.txt"  "$SOURCE/assets" "$SOURCE/linux" /opt/aos/
if [[ ! -x /opt/aos/.venv/bin/python ]]; then python3 -m venv /opt/aos/.venv; fi
/opt/aos/.venv/bin/python -m pip install -r /opt/aos/requirements.txt
install -d -m 755 /usr/share/themes/AOJ-Tactical/openbox-3
cp -a "$SOURCE/linux/theme/AOJ-Tactical/openbox-3/." /usr/share/themes/AOJ-Tactical/openbox-3/
chmod 755 /opt/aos/linux/start-aos.sh
install -m 755 "$SOURCE/linux/aos-session" /usr/local/bin/aos-session
install -m 644 "$SOURCE/linux/aos-session.desktop" /usr/share/xsessions/aos-session.desktop
# Redirect legacy Alpha 0.4 login sessions and launchers, rather than leaving them active.
chmod 755 /opt/aos/linux/migrate-legacy.sh
bash /opt/aos/linux/migrate-legacy.sh
install -d -m 755 /usr/share/backgrounds/aos /usr/share/plymouth/themes/aos
install -m 644 "$SOURCE/linux/branding/login-background.png" /usr/share/backgrounds/aos/login.png
install -m 644 "$SOURCE/linux/branding/boot-background.png" /usr/share/plymouth/themes/aos/boot-background.png
install -m 644 "$SOURCE/linux/branding/aos.plymouth" "$SOURCE/linux/branding/aos.script" /usr/share/plymouth/themes/aos/
# Never overwrite existing greeter configuration without backing it up.
if [[ -f /etc/lightdm/lightdm-gtk-greeter.conf ]]; then
    cp -n /etc/lightdm/lightdm-gtk-greeter.conf /etc/lightdm/lightdm-gtk-greeter.conf.before-aos || true
fi
cat > /etc/lightdm/lightdm-gtk-greeter.conf <<'GREETER'
[greeter]
background=/usr/share/backgrounds/aos/login.png
theme-name=Adwaita-dark
icon-theme-name=Adwaita
font-name=DejaVu Sans 10
indicators=~host;~spacer;~clock;~spacer;~power
GREETER
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
    plymouth-set-default-theme -R aos || true
fi
cat <<'DONE'
Airsoft OS 3.9.0 installed.
At the login screen, select 'Airsoft OS 3.9.0'.
Legacy AOJ launcher paths now run the installed AOS version. The original Alpha launch files are backed up.
Keep a separate Debian desktop session as fallback.
Optional quiet boot (GRUB backup first):
    sudo bash /opt/aos/linux/enable-quiet-boot.sh
Use Ctrl+Alt+F2 for emergency text console access.
DONE
