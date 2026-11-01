"""Local declarative widget registry; deliberately does not execute downloaded code."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Widget:
    identifier:str
    label:str
    module:str

WIDGETS=(
    Widget('system','System Status','system'),
    Widget('network','Network','network'),
    Widget('activity','Recent Activity','activity'),
    Widget('game','Game Status','game'),
    Widget('briefing','Team Briefing','briefing'),
    Widget('shortcuts','Shortcuts','shortcuts'),
)

def get(identifier):
    return next((w for w in WIDGETS if w.identifier==identifier),None)
