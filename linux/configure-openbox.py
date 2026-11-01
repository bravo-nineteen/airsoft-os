#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET
src=Path('/etc/xdg/openbox/rc.xml')
dest=Path.home()/'.config/aoj-os/openbox-rc.xml'
dest.parent.mkdir(parents=True,exist_ok=True)
if not src.exists(): raise SystemExit('Openbox default config not found')
root=ET.parse(src).getroot()
theme=root.find('theme')
if theme is None:theme=ET.SubElement(root,'theme')
name=theme.find('name')
if name is None:name=ET.SubElement(theme,'name')
name.text='AOJ-Tactical'
font=theme.find('font')
if font is None:font=ET.SubElement(theme,'font',place='ActiveWindow')
for place in ('ActiveWindow','InactiveWindow'):
    f=next((x for x in theme.findall('font') if x.get('place')==place),None)
    if f is None:f=ET.SubElement(theme,'font',place=place)
    n=f.find('name')
    if n is None:n=ET.SubElement(f,'name')
    n.text='DejaVu Sans'
    z=f.find('size')
    if z is None:z=ET.SubElement(f,'size')
    z.text='12'
keyboard=root.find('keyboard')
if keyboard is None:keyboard=ET.SubElement(root,'keyboard')
for key,cmd in [('C-A-t','xfce4-terminal'),('A-F2','xfce4-terminal'),('W-e','thunar')]:
    for node in list(keyboard.findall('keybind')):
        if node.get('key')==key:keyboard.remove(node)
    binding=ET.SubElement(keyboard,'keybind',key=key)
    action=ET.SubElement(binding,'action',name='Execute')
    ET.SubElement(action,'command').text=cmd
ET.indent(root,space='  ')
ET.ElementTree(root).write(dest,encoding='utf-8',xml_declaration=True)
