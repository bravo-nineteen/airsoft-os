#!/bin/sh
cd /opt/aos || exit 1
exec /opt/aos/.venv/bin/python /opt/aos/main.py --desktop
