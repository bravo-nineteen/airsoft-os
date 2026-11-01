#!/bin/sh
cd /opt/aoj-os || exit 1
exec /opt/aoj-os/.venv/bin/python /opt/aoj-os/main.py --desktop
