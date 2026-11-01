#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Run with sudo'; exit 1; fi
conf=/etc/default/grub
[[ -f "$conf" ]] || { echo 'GRUB configuration not found'; exit 1; }
command -v update-grub >/dev/null || { echo 'update-grub not available'; exit 1; }
backup="/etc/default/grub.aos-backup-$(date +%Y%m%d-%H%M%S)"
cp -a "$conf" "$backup"
python3 - "$conf" <<'PY'
from pathlib import Path
import re,sys,shlex
p=Path(sys.argv[1])
s=p.read_text()
pattern=r'(?m)^(GRUB_CMDLINE_LINUX_DEFAULT=)(["\'])(.*?)\2[ \t]*$'
m=re.search(pattern,s)
if not m: raise SystemExit('Could not safely identify GRUB_CMDLINE_LINUX_DEFAULT; no changes made')
tokens=shlex.split(m.group(3))
for token in ('quiet','splash','loglevel=3','systemd.show_status=false','udev.log_level=3'):
    if token not in tokens: tokens.append(token)
value=' '.join(tokens)
s=s[:m.start()]+f'GRUB_CMDLINE_LINUX_DEFAULT="{value}"'+s[m.end():]
p.write_text(s)
PY
update-grub
echo "Quiet splash enabled. Previous GRUB settings backed up to: $backup"
echo 'This hides routine boot messages; emergency errors may still appear.'
