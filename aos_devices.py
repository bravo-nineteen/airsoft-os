"""Safe local hardware simulator and JSON telemetry validator.
No automatic network commands are sent to physical devices.
"""
import json
import time
from dataclasses import dataclass

@dataclass(frozen=True)
class Telemetry:
    device_id: str
    kind: str
    battery: int
    online: bool
    timestamp: float


def validate(data):
    if not isinstance(data, dict): raise ValueError('Object expected')
    device_id=data.get('device_id');kind=data.get('kind');battery=data.get('battery');online=data.get('online')
    if not isinstance(device_id,str) or not 1<=len(device_id)<=40 or not all(c.isalnum() or c in '-_' for c in device_id):raise ValueError('Invalid device id')
    if kind not in ('checkpoint','scoreboard','sensor','gateway','prop'):raise ValueError('Invalid kind')
    if type(battery) is not int or not 0<=battery<=100:raise ValueError('Invalid battery')
    if type(online) is not bool:raise ValueError('Invalid online state')
    return Telemetry(device_id,kind,battery,online,time.time())


def simulated():
    return [validate({'device_id':'SIM-CP-01','kind':'checkpoint','battery':92,'online':True}),validate({'device_id':'SIM-SCORE-01','kind':'scoreboard','battery':100,'online':True})]
