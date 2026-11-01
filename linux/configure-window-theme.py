#!/usr/bin/env python3
import json
from pathlib import Path
import xml.etree.ElementTree as ET
home=Path.home()
prefs=home/'.config/aoj-os/window.json'
try: height=max(26,min(54,int(json.loads(prefs.read_text()).get('titlebar_size',36))))
except (OSError,ValueError,TypeError): height=36
# Openbox titlebar height is controlled by font size and padding, not a direct height property.
source=Path('/usr/share/themes/AOJ-Tactical/openbox-3/themerc')
target=home/'.local/share/themes/AOJ-Tactical/openbox-3/themerc'
if source.exists():
    target.parent.mkdir(parents=True,exist_ok=True)
    content=source.read_text()
    content += '\nwindow.title.height: '+str(height)+'\n'
    content += 'padding.height: '+str(max(5,(height-17)//2))+'\n'
    target.write_text(content)
