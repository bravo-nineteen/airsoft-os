"""Airsoft Operating System — native Debian desktop shell."""
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psutil
from PySide6.QtCore import Qt, QTimer, QRect, QRectF, Signal, QEvent, QSize, QPointF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPainterPath, QPalette
from aos_planning import PlanningDialog
from team_ops import TeamOperations
from aos_management import OperationsManager
from aos_updates import UpdateChecker
from aos_network_gui import NetworkViewer
from cyber_native import CyberOperations
from PySide6.QtWidgets import (QApplication, QFrame, QWidget, QLabel, QPushButton, QStyleFactory,
    QVBoxLayout, QHBoxLayout, QGridLayout, QProgressBar, QTextEdit, QLineEdit,
    QDialog, QFormLayout, QMessageBox, QFileDialog, QScrollArea, QSizeGrip,
    QComboBox, QCheckBox, QSpinBox, QColorDialog, QTabWidget, QSlider, QInputDialog, QMenu, QStyle, QSizePolicy)

BASE = Path(__file__).resolve().parent
CONFIG = Path.home() / '.config' / 'aoj-os' / 'layout.json'
PREFS = CONFIG.parent / 'preferences.json'
PROFILES = CONFIG.parent / 'profiles'
PROFILES.mkdir(parents=True, exist_ok=True)
CONFIG.parent.mkdir(parents=True, exist_ok=True)
RED = '#db3c35'
GREEN = '#78d899'
AMBER = '#e3b75d'
TEXT = '#e4e9e8'
MUTED = '#a3b0ad'

STYLE = f"""
QWidget {{ background-color: #10191b; color: {TEXT}; font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 12px; }}
QFrame#panel {{ background-color: rgba(12, 21, 23, 239); border: 1px solid #354649; border-radius: 7px; }}
QFrame#top, QFrame#dock {{ background-color: rgba(10, 17, 19, 248); border: 1px solid #2d3b3d; }}
QPushButton {{ background: #182629; border: 1px solid #39494b; border-radius: 5px; padding: 7px; text-align: center; }}
QPushButton:hover {{ background: #283b3e; border-color: #bc4b47; }}
QPushButton:pressed {{ background: #472c2c; }}
QPushButton#primary {{ background: #5d2627; border-color: #b9413b; }}
QLabel#muted {{ color: {MUTED}; }}
QProgressBar {{ border: 1px solid #354649; border-radius: 3px; background: #121c1f; height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: #62c38a; border-radius: 2px; }}
QTextEdit, QLineEdit, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget, QComboBox, QSpinBox {{ background: #101b1d; color: #edf3f1; selection-background-color: #a33e39; selection-color: white; border: 1px solid #425659; padding: 6px; border-radius: 4px; }}
QDialog, QMessageBox, QFileDialog, QTabWidget, QScrollArea, QMenu {{ background-color: #10191b; color: #eaf0ee; }}
QTabWidget::pane {{ border: 1px solid #415457; background: #111c1e; }}
QTabBar::tab {{ background: #1c2b2e; color: #d9e6e2; padding: 9px 14px; border: 1px solid #3c5152; }}
QTabBar::tab:selected {{ background: #5c2726; color: white; }}
QCheckBox, QRadioButton {{ color: #e5efec; spacing: 8px; }}
QScrollBar:vertical {{ background: #101b1d; width: 14px; }}
QScrollBar::handle:vertical {{ background: #506769; min-height: 26px; border-radius: 4px; }}
QToolTip {{ background: #172628; color: #f2f6f4; border: 1px solid #607c7a; }}

QPushButton#dockTile {{ background: #0b1316; border: 1px solid #344649; border-radius: 7px; color: #e8f2f0; font-size: 14px; font-weight: 700; padding: 5px; }}
QPushButton#dockTile:hover {{ background: #253237; border: 1px solid #dd4b43; }}
QPushButton#dockTile[editing="true"] {{ background: #5b2425; border: 2px solid #e45d55; }}
QFrame#panel {{ border: 1px solid #486064; border-left: 2px solid #b83a36; }}
QFrame#panel[editing="true"] {{ border: 2px dashed #db6b56; }}
QFrame#top {{ border-bottom: 2px solid #8f302c; }}
QFrame#dock {{ border-top: 2px solid #8f302c; }}
QMenu::item {{ padding: 10px 22px; }}
QMenu::item:selected {{ background: #612b2a; }}
QLabel {{ background: transparent; }}
QWidget#desktop {{ background-color: #0a1113; }}
QWidget#panelBody {{ background: transparent; }}
QFrame#panel QLabel {{ background: transparent; }}
QTabWidget QWidget {{ color: #f1f5f4; }}
QHeaderView::section {{ background: #203135; color: #f1f5f4; padding: 7px; border: 1px solid #40585a; }}
QTableWidget::item {{ background: #122125; color: #f1f5f4; }}
QTableWidget::item:selected {{ background: #7b302d; color: white; }}
QFrame#sidebar {{ background: #080f12; border-right: 2px solid #96332e; }}
QPushButton#sideIcon {{ background: #101a1e; border: 1px solid #324448;
  color: #eef3f2; font-size: 24px; padding: 1px; border-radius: 6px; }}
QPushButton#sideIcon:hover {{ background: #392021; border: 1px solid #d95148; }}
QPushButton#sideIcon:pressed {{ background: #6a2926; }}

"""

class CircularGauge(QWidget):
    """Responsive percentage ring; legible at compact widget dimensions."""
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.value = None
        self.setMinimumSize(45, 47)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setToolTip(f'{name}: waiting for live system measurement')

    def setValue(self, value):
        self.value = None if value is None else max(0, min(100, float(value)))
        self.setToolTip(f'{self.name}: ' + ('not available' if self.value is None else f'{self.value:.0f}%'))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = max(24.0, min(float(self.width()-6), float(self.height()-16), 90.0))
        r = QRectF((self.width()-side)/2.0, 2, side, side)
        thickness = max(3, min(8, int(side/12)))
        p.setPen(QPen(QColor('#34474c'), thickness, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, 0, 360*16)
        if self.value is not None:
            alert = (self.value >= 85 and self.name != 'BATTERY') or (self.name == 'BATTERY' and self.value < 20)
            p.setPen(QPen(QColor('#ed665c' if alert else '#70dba1'), thickness, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r, 90*16, -int(self.value*3.6*16))
        p.setPen(QColor('#f0f5f4'))
        p.setFont(QFont('Sans', max(8, min(14, int(side/5))), QFont.Bold))
        p.drawText(r, Qt.AlignCenter, 'N/A' if self.value is None else f'{self.value:.0f}%')
        p.setFont(QFont('Sans', max(7, min(10, int(side/8))), QFont.Bold))
        p.setPen(QColor('#a9bdb9'))
        p.drawText(QRectF(0, r.bottom(), self.width(), max(15, self.height()-r.bottom())), Qt.AlignCenter, self.name)
        p.end()


def label(text, size=12, color=TEXT, bold=False):
    w = QLabel(text)
    w.setStyleSheet(f'color:{color};font-size:{size}px;font-weight:{"700" if bold else "400"};')
    return w

def command_available(name):
    return shutil.which(name) is not None

class GridBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo = QPixmap(str(BASE / 'assets' / 'aos_logo.jpg'))
        self.grid_step = 20
        self.grid_enabled = True
        self.accent = '#db3c35'
        self.wallpaper = ''
        self.interface_scale = 12
        self.titlebar_size = 36
        self.wallpaper_pixmap = QPixmap()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#0a1113'))
        if not self.wallpaper_pixmap.isNull():
            p.setOpacity(.48)
            p.drawPixmap(self.rect(), self.wallpaper_pixmap)
            p.setOpacity(1)
        p.setPen(QPen(QColor(35, 49, 50, 105), 1))
        if self.grid_enabled:
            for x in range(0, self.width(), self.grid_step): p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), self.grid_step): p.drawLine(0, y, self.width(), y)
        p.setPen(QPen(QColor(68, 86, 82, 75), 1))
        if self.grid_enabled:
            for x in range(0, self.width(), self.grid_step*5): p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), self.grid_step*5): p.drawLine(0, y, self.width())
        if not self.logo.isNull():
            image = self.logo.scaled(420, 310, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.setOpacity(.26)
            p.drawPixmap((self.width()-image.width())//2+50, (self.height()-image.height())//2, image)
            p.setOpacity(1)
        p.setPen(QColor('#496064'))
        p.setFont(QFont('Consolas', 9))
        p.drawText(90, self.height()-40, 'AOS // AIRSOFT OPERATING SYSTEM')
        p.drawText(90, self.height()-24, 'VERSION 3.9.0    •    FIELD OPERATIONS')
        p.end()

class ResizeCorner(QWidget):
    """Drag the lower-right corner of a widget while desktop EDIT mode is on."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setToolTip('Drag to resize this widget')
        self.start = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor('#642c29'))
        p.setPen(QPen(QColor('#ee7568'), 1))
        p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 4, 4)
        p.setPen(QPen(QColor('#ffe4db'), 2, Qt.SolidLine, Qt.RoundCap))
        for offset in (9, 15, 21):
            p.drawLine(offset, 22, 22, offset)
        p.end()

    def mousePressEvent(self, event):
        panel = self.parentWidget()
        desktop = panel.parentWidget()
        if event.button() == Qt.LeftButton and desktop.edit_mode and not desktop.widgets_locked:
            self.start = (event.globalPosition().toPoint(), panel.width(), panel.height())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start is not None:
            origin, old_w, old_h = self.start
            delta = event.globalPosition().toPoint() - origin
            panel = self.parentWidget()
            desktop = panel.parentWidget()
            max_w = max(panel.minimumWidth(), desktop.width() - panel.x() - 8)
            max_h = max(panel.minimumHeight(), desktop.height() - panel.y() - 8)
            w = min(max_w, max(panel.minimumWidth(), old_w + delta.x()))
            h = min(max_h, max(panel.minimumHeight(), old_h + delta.y()))
            if desktop.snap_enabled:
                step = max(1, int(desktop.grid_step))
                w = min(max_w, max(panel.minimumWidth(), round(w/step)*step))
                h = min(max_h, max(panel.minimumHeight(), round(h/step)*step))
            panel.resize(w, h)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start is not None:
            self.start = None
            self.parentWidget().changed.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class WidgetPanel(QFrame):
    changed = Signal()

    def __init__(self, title, parent, x, y, w, h, content_builder):
        super().__init__(parent)
        self.title = title
        self.default_size = (w, h)
        self.setObjectName('panel')
        self.setGeometry(x, y, w, h)
        self.setMinimumSize(165, 145)
        self._drag = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(7, 6, 7, 6)
        outer.setSpacing(3)
        header = QHBoxLayout()
        self.title_label = label('▣  ' + title.upper(), 11, TEXT, True)
        self.title_label.setToolTip('In EDIT mode, drag this title to move the widget')
        self.title_label.installEventFilter(self)
        header.addWidget(self.title_label)
        header.addStretch()
        self.close_button = QPushButton('×')
        self.close_button.setFixedSize(22, 22)
        self.close_button.setToolTip('Hide widget; restore from Widgets')
        self.close_button.clicked.connect(self.hide_panel)
        header.addWidget(self.close_button)
        outer.addLayout(header)
        body = QWidget(self)
        body.setObjectName('panelBody')
        outer.addWidget(body, 1)
        content_builder(body)
        self.resize_corner = ResizeCorner(self)
        self.set_edit_mode(False)
        self.show()

    def set_edit_mode(self, enabled):
        self.close_button.setVisible(enabled)
        self.resize_corner.setVisible(enabled)
        self.resize_corner.setEnabled(enabled)
        self.setProperty('editing', bool(enabled))
        self.style().unpolish(self)
        self.style().polish(self)
        self.resize_corner.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'resize_corner'):
            self.resize_corner.move(self.width()-27, self.height()-27)
            self.resize_corner.raise_()
        desktop = self.parentWidget()
        if hasattr(desktop, 'on_widget_resized'):
            desktop.on_widget_resized(self)

    def hide_panel(self):
        self.hide()
        self.changed.emit()

    def _move_drag(self, global_pos):
        if self._drag is None:
            return
        desktop = self.parentWidget()
        point = global_pos - self._drag
        nx = max(80, min(point.x(), desktop.width()-self.width()-8))
        ny = max(82, min(point.y(), desktop.height()-self.height()-8))
        if desktop.snap_enabled:
            step = max(1, int(desktop.grid_step))
            nx = round(nx/step)*step
            ny = round(ny/step)*step
        self.move(nx, ny)

    def eventFilter(self, watched, event):
        if watched is self.title_label:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                desktop = self.parentWidget()
                if desktop.edit_mode and not desktop.widgets_locked:
                    self._drag = event.globalPosition().toPoint() - self.pos()
                    self.raise_()
                    return True
            elif event.type() == QEvent.MouseMove and self._drag is not None:
                self._move_drag(event.globalPosition().toPoint())
                return True
            elif event.type() == QEvent.MouseButtonRelease and self._drag is not None:
                self._drag = None
                self.changed.emit()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 34:
            desktop = self.parentWidget()
            if desktop.edit_mode and not desktop.widgets_locked:
                self._drag = event.globalPosition().toPoint() - self.pos()
                self.raise_()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            self._move_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag is not None:
            self._drag = None
            self.changed.emit()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        desktop = self.parentWidget()
        if not desktop.edit_mode or desktop.widgets_locked:
            return super().contextMenuEvent(event)
        menu = QMenu(self)
        for name, dimensions in (('Compact', (185, 195)), ('Standard', self.default_size), ('Large', (420, 340))):
            action = menu.addAction(f'{name}  ({dimensions[0]}×{dimensions[1]})')
            action.triggered.connect(lambda checked=False, size=dimensions: self.resize_to_preset(*size))
        menu.addSeparator()
        menu.addAction('Hide widget', self.hide_panel)
        menu.exec(event.globalPos())

    def resize_to_preset(self, width, height):
        desktop = self.parentWidget()
        max_w = max(self.minimumWidth(), desktop.width()-self.x()-8)
        max_h = max(self.minimumHeight(), desktop.height()-self.y()-8)
        self.resize(min(max_w, max(self.minimumWidth(), width)),
                    min(max_h, max(self.minimumHeight(), height)))
        self.changed.emit()


class DockTile(QPushButton):
    """Native vector icon tile: no emoji or font-dependent symbols."""
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.setObjectName('dockTile')
        self.setMinimumSize(70, 66)
        self.setToolTip(name.title())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        active = bool(self.property('editing'))
        hover = self.underMouse()
        border = QColor('#ed625a') if active or hover else QColor('#3d5558')
        p.setPen(QPen(border, 1.4))
        p.setBrush(QColor('#442122') if active else QColor('#19282c') if hover else QColor('#0d1719'))
        r = self.rect().adjusted(2, 2, -2, -2)
        p.drawRoundedRect(r, 6, 6)
        p.setPen(QPen(QColor('#f47a70') if active or hover else QColor('#e5eeee'), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        x = self.width()/2; y = 23
        def line(*coords): p.drawLine(QPointF(coords[0],coords[1]),QPointF(coords[2],coords[3]))
        name=self.name
        if name == 'HOME':
            path=QPainterPath(QPointF(x-15,y));path.lineTo(x,y-13);path.lineTo(x+15,y);p.drawPath(path)
            p.drawRect(int(x-10),int(y),20,15);p.drawRect(int(x-3),int(y+7),6,8)
        elif name == 'GAME':
            p.drawEllipse(QPointF(x,y),14,14);p.drawEllipse(QPointF(x,y),6,6)
            line(x-19,y,x-10,y);line(x+10,y,x+19,y);line(x,y-19,x,y-10);line(x,y+10,x,y+19)
        elif name == 'CYBER':
            line(x-16,y-10,x-5,y);line(x-5,y,x-16,y+10);line(x+1,y+10,x+15,y+10)
        elif name == 'DEVICES':
            p.drawEllipse(QPointF(x,y+9),2,2)
            for a in (9,16):
                p.drawArc(int(x-a),int(y+9-a),a*2,a*2,40*16,100*16)
                p.drawArc(int(x-a),int(y+9-a),a*2,a*2,220*16,100*16)
        elif name == 'DISPLAYS':
            p.drawRoundedRect(int(x-17),int(y-13),34,24,2,2);line(x,y+11,x,y+17);line(x-9,y+17,x+9,y+17)
        elif name == 'FILES':
            path=QPainterPath(QPointF(x-17,y-7));path.lineTo(x-5,y-7);path.lineTo(x,y-2);path.lineTo(x+17,y-2);path.lineTo(x+17,y+13);path.lineTo(x-17,y+13);path.closeSubpath();p.drawPath(path)
        elif name == 'SETTINGS':
            p.drawEllipse(QPointF(x,y),13,13);p.drawEllipse(QPointF(x,y),5,5)
            for dx,dy in ((-19,0),(19,0),(0,-19),(0,19)):
                line(x+dx*.65,y+dy*.65,x+dx,y+dy)
        elif name == 'EDIT':
            line(x-12,y+12,x+12,y-12);line(x-14,y+15,x-5,y+13);line(x+8,y-15,x+15,y-8)
        elif name == 'MORE':
            for dx in (-9,0,9):
                for dy in (-9,0,9):p.drawRect(int(x+dx-2),int(y+dy-2),4,4)
        p.setPen(QColor('#f0f4f2'))
        font=QFont('Noto Sans',9);font.setBold(True);p.setFont(font)
        p.drawText(self.rect().adjusted(0,43,0,-4),Qt.AlignCenter,name)
        p.end()

class AOJDesktop(GridBackground):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Airsoft OS 3.9.0 — Resizable Widgets')
        self.setObjectName('desktop')
        self.resize(1024, 768)
        self.setMinimumSize(800, 600)
        self.setStyleSheet(STYLE)
        self.activity = []
        self.widgets = {}
        self.edit_mode = False
        self.shortcuts = self.read_shortcuts()
        self.team = 'AOS'
        self.game_running = False
        self.widgets_locked = False
        self.snap_enabled = True
        self.load_preferences()
        try:
            self.team = json.loads(PREFS.read_text(encoding='utf-8')).get('team', 'AOS')
        except (OSError, ValueError, TypeError):
            self.team = 'AOS'
        self.build_chrome()
        self.create_widgets()
        self.restore_layout()
        # All six tactical panels are shown on the redesigned default workspace.
        self.apply_accent()
        for panel in self.widgets.values(): panel.set_edit_mode(False)
        self.apply_team()
        self.log('AOS desktop shell initialised')
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def build_chrome(self):
        self.top = QFrame(self)
        self.top.setObjectName('top')
        top = QHBoxLayout(self.top)
        top.setContentsMargins(18, 5, 18, 5)
        self.brand = QLabel()
        self.brand.setPixmap(QPixmap(str(BASE / 'assets' / 'aos_logo.jpg')).scaled(128, 55, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        top.addWidget(self.brand)
        top.addWidget(label('AIRSOFT OS  /  3.9.0  •  COMMAND DESKTOP', 12, MUTED))
        top.addSpacing(30)
        self.unit_label = label('UNIT  AOJ-001', 11, MUTED)
        top.addWidget(self.unit_label)
        top.addSpacing(18)
        top.addWidget(label('●  SYSTEM READY', 11, GREEN, True))
        top.addStretch()
        self.top_status = label('NETWORK —   BATTERY —', 11, MUTED)
        top.addWidget(self.top_status)
        top.addSpacing(20)
        self.clock = label('', 18, TEXT, True)
        top.addWidget(self.clock)
        # AOS is the only desktop navigation bar: icon-only, with hover labels.
        self.sidebar = QFrame(self)
        self.sidebar.setObjectName('sidebar')
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(12, 4, 12, 4)
        side.setSpacing(3)
        self.nav_buttons = {}
        actions = [
            ('HOME', '⌂', self.show_all),
            ('EVENTS / ROSTERS', '▦', self.operations_window),
            ('GAME CONTROL', '◎', self.game_window),
            ('LIVE OPS', '◷', self.live_ops_window),
            ('CYBER OPERATIONS', '⌘', self.hack_window),
            ('DEVICES', '◉', self.device_window),
            ('MAP PLANNER', '⌖', self.planning_window),
            ('DISPLAYS', '▣', self.display_window),
            ('FILES', '▤', self.files_window),
            ('APPLICATIONS', '⊞', self.applications_menu),
            ('TERMINAL', '>_', self.open_terminal),
            ('SETTINGS', '⚙', self.settings_window),
            ('LAN SYNC', '⇄', self.lan_sync_window),
            ('UPDATES', '↻', self.updates_window),
        ]
        for name, symbol, callback in actions:
            btn = QPushButton(symbol)
            btn.setObjectName('sideIcon')
            btn.setFixedSize(48, 39)
            btn.setToolTip(name.title())
            btn.setAccessibleName(name)
            btn.clicked.connect(callback)
            side.addWidget(btn)
            self.nav_buttons[name] = btn
        side.addStretch()
        self.edit_button = QPushButton('✎')
        self.edit_button.setObjectName('sideIcon')
        self.edit_button.setFixedSize(48, 39)
        self.edit_button.setToolTip('EDIT MODE: drag widget titles to move; drag red corner to resize; right-click for presets')
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        side.addWidget(self.edit_button)
        more = QPushButton('⋯')
        more.setObjectName('sideIcon')
        more.setFixedSize(48, 39)
        more.setToolTip('More AOS tools')
        menu = QMenu(more)
        for title, callback in [
            ('Choose widgets', self.choose_widgets),
            ('Add shortcut', self.add_shortcut),
            ('Assign team', self.select_team),
            ('Layouts', self.profiles_window),
            ('Team operations', self.team_window),
            ('Network settings', self.network_window),
        ]:
            menu.addAction(title, callback)
        more.setMenu(menu)
        side.addWidget(more)
        self.dock_status = label('●', 12, GREEN)
        self.dock_status.setToolTip('AOS running')
        side.addWidget(self.dock_status, 0, Qt.AlignCenter)

    def live_ops_window(self):
        from aos_live_gui import LiveConsole
        dialog = LiveConsole(self)
        dialog.exec()

    def lan_sync_window(self):
        dialog = NetworkViewer(self)
        dialog.exec()

    def applications_menu(self):
        self.open_system_tool(['xfce4-appfinder', 'rofi', 'dmenu_run'])

    def open_terminal(self):
        self.open_system_tool(['xfce4-terminal', 'xterm'])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'top'):
            self.top.setGeometry(0, 0, self.width(), 72)
            self.sidebar.setGeometry(0, 72, 74, self.height()-72)

    def on_widget_resized(self, panel):
        # The compact System Status uses only the four circles; other data
        # remains available in gauge tooltips and the full panel preset.
        if panel.title == 'System Status' and hasattr(self, 'sys_extra'):
            self.sys_extra.setVisible(panel.height() >= 245)

    def make_panel(self, name, geometry, build):
        panel = WidgetPanel(name, self, *geometry, build)
        panel.changed.connect(self.save_layout)
        self.widgets[name] = panel

    def create_widgets(self):
        def system(body):
            l=QVBoxLayout(body)
            l.setContentsMargins(1, 1, 1, 1)
            l.setSpacing(0)
            grid=QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(1)
            self.sys_values={}
            for index,name in enumerate(('CPU','RAM','DISK','BATTERY')):
                gauge=CircularGauge(name)
                grid.addWidget(gauge,index//2,index%2)
                self.sys_values[name]=gauge
            l.addLayout(grid)
            self.sys_extra=label('',9,MUTED)
            self.sys_extra.setWordWrap(True)
            l.addWidget(self.sys_extra)
        def network(body):
            l = QVBoxLayout(body)
            self.network_info = label('Detecting interfaces...', 12, MUTED)
            self.network_info.setWordWrap(True)
            l.addWidget(self.network_info)
            l.addStretch()
            b = QPushButton('NETWORK DETAILS')
            b.clicked.connect(self.network_window)
            l.addWidget(b)
        def activity(body):
            l = QVBoxLayout(body)
            self.activity_text = QLabel('')
            self.activity_text.setWordWrap(True)
            self.activity_text.setAlignment(Qt.AlignTop)
            l.addWidget(self.activity_text)
            l.addStretch()
        def game(body):
            l = QVBoxLayout(body)
            self.game_state = label('●  STANDBY', 14, AMBER, True)
            l.addWidget(self.game_state)
            l.addWidget(label('Session: Local demo', 11, MUTED))
            self.game_btn = QPushButton('START DEMO SESSION')
            self.game_btn.setObjectName('primary')
            self.game_btn.clicked.connect(self.toggle_game)
            l.addStretch()
            l.addWidget(self.game_btn)
        self.make_panel('System Status', (90, 112, 284, 310), system)
        self.make_panel('Network', (704, 112, 290, 240), network)
        self.make_panel('Recent Activity', (90, 445, 284, 202), activity)
        self.make_panel('Game Status', (704, 382, 290, 265), game)
        self.make_panel('Team Briefing', (394, 382, 290, 265), self.team_widget)
        self.make_panel('Shortcuts', (394, 112, 290, 240), self.shortcuts_widget)
        self.make_panel('Schedule', (90, 112, 284, 240), self.schedule_widget)
        self.make_panel('Roster', (394, 382, 290, 265), self.roster_widget)
        self.make_panel('Planning Map', (704, 382, 290, 265), self.map_widget)
        for name in ('Schedule','Roster','Planning Map'):
            self.widgets[name].hide()


    def schedule_widget(self, body):
        layout=QVBoxLayout(body)
        layout.addWidget(label('EVENT SCHEDULE',12,GREEN,True))
        self.schedule_list=QLabel('Select OPEN SCHEDULE to view and manage events.')
        self.schedule_list.setWordWrap(True)
        layout.addWidget(self.schedule_list)
        layout.addStretch()
        button=QPushButton('OPEN SCHEDULE')
        button.clicked.connect(self.operations_window)
        layout.addWidget(button)

    def roster_widget(self, body):
        layout=QVBoxLayout(body)
        layout.addWidget(label('TEAM ROSTER',12,GREEN,True))
        text=QLabel('View and edit attendance, players and team assignments.')
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()
        button=QPushButton('OPEN ROSTER')
        button.clicked.connect(self.operations_window)
        layout.addWidget(button)

    def map_widget(self, body):
        layout=QVBoxLayout(body)
        text=QLabel('Import a field image, add colour-coded markers, waypoints and routes, then save or export your plan.')
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()
        button=QPushButton('OPEN INTERACTIVE MAP')
        button.clicked.connect(self.planning_window)
        layout.addWidget(button)

    def planning_window(self):
        dialog=PlanningDialog(self)
        dialog.exec()

    def read_shortcuts(self):
        path = CONFIG.parent / 'shortcuts.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict) and isinstance(x.get('name'), str) and isinstance(x.get('command'), str)][:20]
        except (OSError, ValueError):
            pass
        return [{'name':'Files', 'command':'thunar'}, {'name':'Terminal','command':'xfce4-terminal'}]

    def save_shortcuts(self):
        (CONFIG.parent / 'shortcuts.json').write_text(json.dumps(self.shortcuts, indent=2), encoding='utf-8')

    def shortcuts_widget(self, body):
        self.shortcut_layout = QVBoxLayout(body)
        self.render_shortcuts()

    def render_shortcuts(self):
        while self.shortcut_layout.count():
            item = self.shortcut_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for entry in self.shortcuts:
            b = QPushButton('↗  ' + entry['name'])
            b.clicked.connect(lambda checked=False, command=entry['command']: self.run_shortcut(command))
            self.shortcut_layout.addWidget(b)
        self.shortcut_layout.addStretch()

    def run_shortcut(self, command):
        # Commands are executable names, not shell expressions.
        import shlex
        try:
            argv = shlex.split(command)
            if not argv or not shutil.which(argv[0]): raise ValueError('Executable unavailable')
            subprocess.Popen(argv, start_new_session=True)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Shortcut', str(exc))

    def add_shortcut(self):
        if not self.edit_mode:
            QMessageBox.information(self, 'Edit home screen', 'Enable EDIT mode to add shortcuts.')
            return
        name, ok = QInputDialog.getText(self, 'New shortcut', 'Shortcut name:')
        if not ok or not name.strip(): return
        command, ok = QInputDialog.getText(self, 'New shortcut', 'Executable and arguments (no shell):')
        if not ok or not command.strip(): return
        if len(self.shortcuts) >= 20:
            QMessageBox.warning(self, 'Shortcuts', 'Maximum 20 shortcuts.')
            return
        self.shortcuts.append({'name':name.strip()[:35], 'command':command.strip()[:300]})
        self.save_shortcuts()
        self.render_shortcuts()
        self.widgets['Shortcuts'].show()
        self.save_layout()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        for panel in self.widgets.values():
            panel.set_edit_mode(self.edit_mode and not self.widgets_locked)
        self.edit_button.setProperty('editing', self.edit_mode)
        self.edit_button.style().unpolish(self.edit_button)
        self.edit_button.style().polish(self.edit_button)
        self.log('EDIT: drag panel titles or red resize corners; right-click for size presets' if self.edit_mode else 'Home screen layout saved')
        if not self.edit_mode: self.save_layout()

    def select_team(self):
        teams = ['AOS', 'AOJ', 'Black Talon', 'Task Force']
        selected, ok = QInputDialog.getItem(self, 'Terminal assignment', 'Assigned unit:', teams, max(0, teams.index(self.team) if self.team in teams else 0), False)
        if ok:
            self.team = selected
            self.save_preferences()
            self.apply_team()

    def apply_team(self):
        colours = {'AOS':'#db3c35', 'AOJ':'#db3c35', 'Black Talon':'#d8dfe2', 'Task Force':'#d8ad45'}
        accent = colours.get(self.team, '#db3c35')
        self.accent = accent
        self.apply_accent()
        if hasattr(self, 'unit_label'):
            self.unit_label.setText('UNIT  ' + self.team.upper())
            self.unit_label.setStyleSheet('color:' + accent + ';font-weight:700')
        logo = {'Black Talon':'black_talon.jpg', 'Task Force':'task_force.png'}.get(self.team)
        self.logo = QPixmap(str(BASE / 'assets' / logo)) if logo else QPixmap(str(BASE / 'assets' / 'aos_logo.jpg'))
        self.update()

    def team_widget(self, body):
        l = QVBoxLayout(body)
        l.addWidget(label("BLACK TALON / TASK FORCE", 11, GREEN, True))
        l.addWidget(label("Offline schedules & messaging", 10, MUTED))
        b=QPushButton("OPEN TEAM OPERATIONS")
        b.clicked.connect(self.team_window)
        l.addWidget(b)

    def team_window(self):
        dialog=TeamOperations(self)
        dialog.exec()

    def toggle_game(self):
        self.game_running = not self.game_running
        self.game_state.setText('●  DEMO ACTIVE' if self.game_running else '●  STANDBY')
        self.game_state.setStyleSheet(f'color:{GREEN if self.game_running else AMBER};font-weight:bold;font-size:14px')
        self.game_btn.setText('STOP DEMO SESSION' if self.game_running else 'START DEMO SESSION')
        self.log('Demo session started' if self.game_running else 'Demo session stopped')

    def log(self, message):
        self.activity.insert(0, f'{datetime.now():%H:%M:%S}  {message}')
        self.activity = self.activity[:6]
        self.activity_text.setText('\n\n'.join(self.activity))

    def refresh(self):
        battery = psutil.sensors_battery()
        disk = psutil.disk_usage(str(Path.home().anchor or '/'))
        values = {'CPU': psutil.cpu_percent(), 'RAM': psutil.virtual_memory().percent,
                  'DISK': disk.percent, 'BATTERY': battery.percent if battery else 0}
        for key, value in values.items():
            self.sys_values[key].setValue(value if key != 'BATTERY' or battery else None)
        self.sys_extra.setText(f'CPU: {platform.processor()[:36] or "Unknown"}   •   Uptime: {self.uptime()}')
        addresses = psutil.net_if_addrs()
        connected = []
        for name, entries in addresses.items():
            for entry in entries:
                if entry.family == socket.AF_INET and not entry.address.startswith('127.'):
                    connected.append((name, entry.address))
        if connected:
            lines = [f'●  {name}: {ip}' for name, ip in connected[:3]]
            self.network_info.setText('\n\n'.join(lines))
        else:
            self.network_info.setText('●  No active IPv4 network detected')
        self.top_status.setText(f'NETWORK {"ONLINE" if connected else "OFFLINE"}    •    BATTERY {f"{battery.percent:.0f}%" if battery else "N/A"}')
        self.clock.setText(datetime.now().strftime('%H:%M'))

    def uptime(self):
        seconds = max(0, int(datetime.now().timestamp()-psutil.boot_time()))
        return f'{seconds//3600}h {(seconds%3600)//60}m'

    def show_all(self):
        for panel in self.widgets.values(): panel.show()
        self.save_layout()

    def choose_widgets(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('AOS Widget Manager')
        dialog.setStyleSheet(STYLE + 'QDialog {background-color:#111c1e;color:#f1f5f4;}')
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('DESKTOP WIDGETS', 16, TEXT, True))
        hint = label('Enable EDIT, drag a widget title to move it and use its red bottom-right corner to resize. Right-click a widget for size presets.', 10, MUTED)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        for name, panel in self.widgets.items():
            btn = QPushButton(('✓  ' if panel.isVisible() else '+  ') + name)
            def toggle(checked=False, p=panel):
                p.setVisible(not p.isVisible())
                p.raise_()
                self.save_layout()
                dialog.accept()
            btn.clicked.connect(toggle)
            layout.addWidget(btn)
        reset = QPushButton('RESET WIDGET POSITIONS')
        reset.clicked.connect(lambda: (self.reset_layout(), dialog.accept()))
        layout.addWidget(reset)
        dialog.exec()

    def reset_layout(self):
        positions = [(90,112,284,310),(704,112,290,240),(90,445,284,202),(704,382,290,265),(394,382,290,265),(394,112,290,240),(90,112,284,240),(394,382,290,265),(704,382,290,265)]
        for panel, pos in zip(self.widgets.values(), positions):
            panel.setGeometry(*pos)
            panel.setVisible(panel.title not in ('Schedule','Roster','Planning Map'))
        self.save_layout()

    def save_layout(self):
        data = {'_layout_version': 39, **{name: {'x':p.x(),'y':p.y(),'w':p.width(),'h':p.height(),'visible':p.isVisible()}
                for name,p in self.widgets.items()}}
        try: CONFIG.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except OSError: pass

    def restore_layout(self):
        if not CONFIG.exists(): return
        try:
            data = json.loads(CONFIG.read_text(encoding='utf-8'))
            # One-time visual migration: back up the old geometry, then use the
            # new six-panel desktop. Never delete user custom layouts.
            if not (isinstance(data, dict) and data.get('_layout_version') in (35, 39)):
                backup = CONFIG.with_name('layout-before-3.9.json')
                if not backup.exists():
                    shutil.copy2(CONFIG, backup)
                self.reset_layout()
                return
            for name, p in self.widgets.items():
                d = data.get(name)
                if not d: continue
                x = max(80, min(int(d['x']), self.width()-p.minimumWidth()-8))
                y = max(82, min(int(d['y']), self.height()-p.minimumHeight()-8))
                w = min(max(p.minimumWidth(), int(d['w'])), self.width()-x-8)
                h = min(max(p.minimumHeight(), int(d['h'])), self.height()-y-8)
                p.setGeometry(x, y, max(p.minimumWidth(), w), max(p.minimumHeight(), h))
                p.setVisible(bool(d.get('visible', True)))
        except (ValueError, KeyError, TypeError, OSError): pass

    def info_dialog(self, title, text, buttons=None):
        dialog = QDialog(self)
        dialog.setWindowTitle('AOS // '+title)
        dialog.setMinimumSize(440, 270)
        dialog.setStyleSheet(STYLE + 'QDialog {background-color:#111c1e;color:#f1f5f4;}')
        l = QVBoxLayout(dialog)
        l.addWidget(label(title.upper(), 18, RED, True))
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setPlainText(text)
        l.addWidget(text_area)
        for caption, action in (buttons or []):
            b = QPushButton(caption)
            b.clicked.connect(action)
            l.addWidget(b)
        close = QPushButton('CLOSE')
        close.clicked.connect(dialog.accept)
        l.addWidget(close)
        dialog.exec()

    def operations_window(self):
        OperationsManager(self).exec()

    def updates_window(self):
        UpdateChecker(self).exec()

    def game_window(self):
        self.info_dialog('Game Control', 'AOJ GAME CONTROL\n\nAlpha 0.5 demonstration.\n\nUse the Game Status desktop widget to start and stop a local demo session.\n\nFull game-control integration is planned for a later version.')

    def hack_window(self):
        CyberOperations(self).exec()

    def device_window(self):
        self.info_dialog('Device Manager', 'AOJ DEVICE MANAGER\n\nESP32 discovery and communications are not implemented in Alpha 0.6.\n\nNo hardware connections are simulated or reported as real.')

    def display_window(self):
        self.info_dialog('Display Manager', f'CURRENT DESKTOP: {self.width()} × {self.height()}\n\nThe external scoreboard/display controller is reserved for a later build.')

    def network_window(self):
        details = []
        for name, entries in psutil.net_if_addrs().items():
            details.append(name)
            for entry in entries:
                if entry.family in (socket.AF_INET, socket.AF_INET6):
                    details.append(f'  {entry.address}')
        self.info_dialog('Network Details', '\n'.join(details) or 'No interfaces detected')

    def files_window(self):
        # Launch a real file manager directly; never use a folder chooser as a substitute.
        for program in ('thunar', 'pcmanfm', 'konqueror', 'dolphin'):
            binary = shutil.which(program)
            if binary:
                try:
                    subprocess.Popen([binary, str(Path.home())], start_new_session=True)
                    self.log('File manager launched: ' + program)
                    return
                except OSError:
                    continue
        QMessageBox.warning(self, 'AOJ Files', 'No file manager found. Install Thunar: sudo apt install thunar')

    def load_preferences(self):
        if not PREFS.exists():
            return
        try:
            d = json.loads(PREFS.read_text(encoding='utf-8'))
            self.grid_step = max(10, min(80, int(d.get('grid_step', 20))))
            self.grid_enabled = bool(d.get('grid_enabled', True))
            self.snap_enabled = bool(d.get('snap_enabled', True))
            self.widgets_locked = bool(d.get('widgets_locked', False))
            self.accent = str(d.get('accent', '#db3c35'))
            self.wallpaper = str(d.get('wallpaper', ''))
            self.interface_scale = max(10, min(18, int(d.get('interface_scale', 12))))
            self.titlebar_size = max(26, min(54, int(d.get('titlebar_size', 36))))
            if self.wallpaper and Path(self.wallpaper).is_file():
                self.wallpaper_pixmap = QPixmap(self.wallpaper)
        except (OSError, ValueError, TypeError):
            pass

    def save_preferences(self):
        d = dict(grid_step=self.grid_step, grid_enabled=self.grid_enabled,
                 snap_enabled=self.snap_enabled, widgets_locked=self.widgets_locked,
                 accent=self.accent, wallpaper=self.wallpaper,
                 interface_scale=self.interface_scale, titlebar_size=self.titlebar_size, team=self.team)
        PREFS.write_text(json.dumps(d, indent=2), encoding='utf-8')

    def apply_accent(self):
        self.setStyleSheet(STYLE + f"""
        QWidget {{ font-size: {self.interface_scale}px; }}
        QPushButton#primary {{ background-color: {self.accent}; border-color: {self.accent}; }}
        QFrame#panel {{ border-top: 2px solid {self.accent}; }}
        """)
        self.update()
        self.save_preferences()

    def choose_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose wallpaper', str(Path.home()),
                                              'Images (*.png *.jpg *.jpeg *.webp)')
        if path:
            self.wallpaper = path
            self.wallpaper_pixmap = QPixmap(path)
            self.update()
            self.save_preferences()

    def settings_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('AOS CONTROL CENTRE // 3.9.0')
        dialog.resize(660, 610)
        dialog.setStyleSheet(STYLE + 'QDialog {background-color:#111c1e;color:#f1f5f4;}')
        outer = QVBoxLayout(dialog)
        outer.addWidget(label('AOS CONTROL CENTRE  /  APPEARANCE & WORKSPACE', 18, RED, True))
        tabs = QTabWidget()
        outer.addWidget(tabs)
        tabs.setMinimumHeight(360)

        appearance = QWidget()
        a = QVBoxLayout(appearance)
        grid = QCheckBox('Show tactical grid')
        grid.setChecked(self.grid_enabled)
        grid.toggled.connect(lambda v: (setattr(self, 'grid_enabled', v), self.update(), self.save_preferences()))
        a.addWidget(grid)
        step_line = QHBoxLayout()
        step_line.addWidget(label('Grid spacing'))
        step = QSpinBox()
        step.setRange(10, 80)
        step.setSingleStep(5)
        step.setValue(self.grid_step)
        step.valueChanged.connect(lambda v: (setattr(self, 'grid_step', v), self.update(), self.save_preferences()))
        step_line.addWidget(step)
        a.addLayout(step_line)
        a.addWidget(label('Interface font size'))
        font_size = QSpinBox()
        font_size.setRange(10, 18)
        font_size.setValue(self.interface_scale)
        font_size.valueChanged.connect(lambda v: (setattr(self, 'interface_scale', v), self.apply_accent()))
        a.addWidget(font_size)
        a.addWidget(label('Window title bar height (applies after logout/login)'))
        bar_height = QSpinBox()
        bar_height.setRange(26, 54)
        bar_height.setValue(self.titlebar_size)
        bar_height.valueChanged.connect(lambda v: (setattr(self, 'titlebar_size', v), self.save_preferences()))
        a.addWidget(bar_height)
        apply_wm = QPushButton('Apply AOS window theme / title bar size')
        apply_wm.clicked.connect(self.apply_window_theme)
        a.addWidget(apply_wm)
        a.addWidget(label('Accent colour'))
        for name, colour in [('AOJ Red', '#db3c35'), ('Stealth Green', '#5eac82'),
                             ('Amber', '#e3b75d'), ('Ice Blue', '#65a8d6')]:
            b = QPushButton(name)
            b.clicked.connect(lambda checked=False, c=colour: (setattr(self, 'accent', c), self.apply_accent()))
            a.addWidget(b)
        wallpaper = QPushButton('Choose custom wallpaper...')
        wallpaper.clicked.connect(self.choose_wallpaper)
        a.addWidget(wallpaper)
        clear_wallpaper = QPushButton('Remove custom wallpaper')
        clear_wallpaper.clicked.connect(lambda: (setattr(self, 'wallpaper', ''),
            setattr(self, 'wallpaper_pixmap', QPixmap()), self.update(), self.save_preferences()))
        a.addWidget(clear_wallpaper)
        a.addStretch()
        # Keep controls accessible on the Toughbook's 1024x768 screen.
        appearance_scroll = QScrollArea()
        appearance_scroll.setWidgetResizable(True)
        appearance_scroll.setWidget(appearance)
        tabs.addTab(appearance_scroll, 'Appearance')

        desktop = QWidget()
        d = QVBoxLayout(desktop)
        snap = QCheckBox('Snap widgets to grid')
        snap.setChecked(self.snap_enabled)
        snap.toggled.connect(lambda v: (setattr(self, 'snap_enabled', v), self.save_preferences()))
        d.addWidget(snap)
        lock = QCheckBox('Lock widget positions')
        lock.setChecked(self.widgets_locked)
        lock.toggled.connect(lambda v: (setattr(self, 'widgets_locked', v), [p.grip.setEnabled(not v) for p in self.widgets.values()], self.save_preferences()))
        d.addWidget(lock)
        for caption, fn in [('Manage widgets', self.choose_widgets),
                            ('Manage layout profiles', self.profiles_window),
                            ('Reset widget positions', self.reset_layout)]:
            b = QPushButton(caption)
            b.clicked.connect(fn)
            d.addWidget(b)
        d.addStretch()
        tabs.addTab(desktop, 'Desktop')

        system_tools = QWidget()
        tools = QVBoxLayout(system_tools)
        tools.addWidget(label('OPEN DEBIAN SYSTEM SETTINGS', 13, GREEN, True))
        tools.addWidget(label('These open installed native system utilities. Missing tools show an explanation.'))
        for caption, candidates in [
            ('Network Connections', ['nm-connection-editor']),
            ('Bluetooth Settings', ['blueman-manager']),
            ('Display Settings', ['arandr']),
            ('Audio Mixer', ['pavucontrol']),
            ('Power Manager', ['xfce4-power-manager-settings']),
            ('File Manager', ['thunar', 'pcmanfm', 'konqueror']),
            ('Terminal', ['xfce4-terminal', 'x-terminal-emulator', 'xterm'])]:
            b = QPushButton(caption)
            b.clicked.connect(lambda checked=False, names=candidates: self.open_system_tool(names))
            tools.addWidget(b)
        tools.addStretch()
        usb = QPushButton('Open removable USB devices')
        usb.clicked.connect(self.open_usb_devices)
        tools.addWidget(usb)
        tools.addWidget(label('USB volumes are mounted through udisks2/GVfs; never format a device automatically.'))
        system_scroll = QScrollArea()
        system_scroll.setWidgetResizable(True)
        system_scroll.setWidget(system_tools)
        tabs.addTab(system_scroll, 'Linux Settings')

        about = QWidget()
        info = QVBoxLayout(about)
        info.addWidget(label(f'Host: {platform.node()}'))
        info.addWidget(label(f'OS: {platform.platform()}'))
        info.addWidget(label(f'CPU threads: {psutil.cpu_count()}'))
        info.addWidget(label(f'RAM: {psutil.virtual_memory().total / 1024**3:.1f} GB'))
        info.addWidget(label(f'Config: {CONFIG.parent}', 10, MUTED))
        info.addStretch()
        tabs.addTab(about, 'System')
        # System-wide GTK appearance is controlled by a user-local settings file.
        native = QWidget()
        nlayout = QVBoxLayout(native)
        nlayout.addWidget(label('NATIVE APPLICATION APPEARANCE', 14, GREEN, True))
        nlayout.addWidget(label('Fix light text on white windows in GTK applications.'))
        gtk = QPushButton('Apply dark GTK theme to native applications')
        gtk.clicked.connect(self.apply_gtk_theme)
        nlayout.addWidget(gtk)
        nlayout.addWidget(label('Existing applications may need to be restarted.'))
        nlayout.addStretch()
        tabs.addTab(native, 'Native Apps')
        close = QPushButton('CLOSE')
        close.clicked.connect(dialog.accept)
        outer.addWidget(close)
        dialog.exec()

    def apply_gtk_theme(self):
        for version in ('3.0', '4.0'):
            path = Path.home() / '.config' / ('gtk-' + version) / 'settings.ini'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('[Settings]\ngtk-theme-name=Adwaita-dark\ngtk-icon-theme-name=Adwaita\ngtk-application-prefer-dark-theme=1\n', encoding='utf-8')
        QMessageBox.information(self, 'AOJ Native Theme', 'Dark GTK theme configured. Restart Konqueror/Thunar or log in again to apply where supported. KDE/Qt apps may use their own theme settings.')

    def apply_window_theme(self):
        config = Path.home() / '.config' / 'aoj-os' / 'window.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({'titlebar_size': self.titlebar_size}, indent=2))
        tool = BASE / 'linux' / 'configure-window-theme.py'
        if tool.is_file():
            subprocess.run([sys.executable, str(tool)], check=False)
            subprocess.run(['openbox', '--reconfigure'], check=False)
        QMessageBox.information(self, 'AOJ Window Theme', 'AOJ window settings saved. Some title bar changes require logging out and back in.')

    def open_usb_devices(self):
        """Discover actual block devices and mount selected removable partitions."""
        dialog = QDialog(self)
        dialog.setWindowTitle('AOJ // Removable Media')
        dialog.resize(520, 370)
        dialog.setStyleSheet(STYLE)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('USB / REMOVABLE STORAGE', 16, GREEN, True))
        layout.addWidget(label('Select a detected removable partition. No formatting or deletion is performed.'))
        options = QComboBox()
        layout.addWidget(options)
        status = QLabel('')
        status.setWordWrap(True)
        layout.addWidget(status)
        devices = []
        def refresh():
            nonlocal devices
            devices = []
            options.clear()
            try:
                output = subprocess.check_output(['lsblk', '-J', '-o', 'NAME,PATH,SIZE,TYPE,RM,TRAN,FSTYPE,LABEL,MOUNTPOINTS'], text=True, timeout=8)
                tree = json.loads(output)
                def walk(item, removable=False):
                    removable = removable or bool(item.get('rm')) or item.get('tran') == 'usb'
                    for child in item.get('children') or []:
                        walk(child, removable)
                    if removable and item.get('type') == 'part' and item.get('fstype'):
                        devices.append(item)
                for root in tree.get('blockdevices', []):
                    walk(root)
                for item in devices:
                    mount = ', '.join(x for x in (item.get('mountpoints') or []) if x)
                    options.addItem(f"{item.get('label') or item['name']} — {item.get('size')} — {mount or 'Not mounted'}")
                status.setText(f'{len(devices)} removable partition(s) detected.' if devices else 'No removable partitions found. Reinsert the USB drive and refresh.')
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                status.setText('Cannot inspect drives: ' + str(exc))
        def open_selected():
            index = options.currentIndex()
            if index < 0 or index >= len(devices):
                return
            device = devices[index]
            path = device.get('path')
            mounts = [x for x in device.get('mountpoints') or [] if x]
            if not mounts:
                try:
                    result = subprocess.run(['udisksctl', 'mount', '-b', path], capture_output=True, text=True, timeout=20)
                    if result.returncode:
                        status.setText('Mount failed: ' + (result.stderr.strip() or result.stdout.strip()))
                        return
                    refresh()
                    # Resolve the newly mounted path without parsing translated command output.
                    output = subprocess.check_output(['lsblk', '-J', '-o', 'PATH,MOUNTPOINTS'], text=True, timeout=8)
                    def locate(nodes):
                        for node in nodes:
                            if node.get('path') == path:
                                return next((x for x in node.get('mountpoints') or [] if x), None)
                            found = locate(node.get('children') or [])
                            if found: return found
                        return None
                    mount = locate(json.loads(output).get('blockdevices', []))
                    mounts = [mount] if mount else []
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    status.setText('Mount failed: ' + str(exc))
                    return
            if mounts:
                for program in ('thunar', 'konqueror', 'pcmanfm', 'dolphin'):
                    executable = shutil.which(program)
                    if executable:
                        subprocess.Popen([executable, mounts[0]], start_new_session=True)
                        status.setText('Opened ' + mounts[0])
                        return
                status.setText('Mounted at ' + mounts[0] + ' (no file manager found)')
            else:
                status.setText('Mounted, but could not determine the location. Refresh and retry.')
        actions = QHBoxLayout()
        for caption, fn in [('Refresh', refresh), ('Mount / Open', open_selected), ('Close', dialog.accept)]:
            button = QPushButton(caption)
            button.clicked.connect(fn)
            actions.addWidget(button)
        layout.addLayout(actions)
        layout.addStretch()
        refresh()
        dialog.exec()

    def open_system_tool(self, candidates):
        for name in candidates:
            executable = shutil.which(name)
            if executable:
                try:
                    subprocess.Popen([executable], start_new_session=True)
                    self.log('Opened system utility: ' + name)
                    return
                except OSError as exc:
                    QMessageBox.warning(self, 'AOJ System Settings', str(exc))
                    return
        QMessageBox.information(self, 'AOJ System Settings',
            'No compatible utility is installed. Try: sudo apt install ' + candidates[0])

    def profiles_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('AOJ // Layout Profiles')
        dialog.resize(430, 330)
        dialog.setStyleSheet(STYLE + 'QDialog {background-color:#111c1e;color:#f1f5f4;}')
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('SAVE / RESTORE WORKSPACES', 16, RED, True))
        name = QLineEdit()
        name.setPlaceholderText('Profile name, e.g. Field Operations')
        layout.addWidget(name)
        options = QComboBox()
        def refresh_options():
            options.clear()
            options.addItems(sorted(p.stem for p in PROFILES.glob('*.json')))
        refresh_options()
        layout.addWidget(options)
        def save():
            raw = name.text().strip()
            safe = ''.join(c for c in raw if c.isalnum() or c in '-_ ').strip()[:50]
            if not safe:
                QMessageBox.warning(dialog, 'Profile', 'Enter a profile name.')
                return
            self.save_layout()
            target = PROFILES / (safe + '.json')
            shutil.copyfile(CONFIG, target)
            refresh_options()
            options.setCurrentText(safe)
        def load():
            target = PROFILES / (options.currentText() + '.json')
            if target.is_file():
                shutil.copyfile(target, CONFIG)
                self.restore_layout()
                self.log('Layout profile loaded: ' + options.currentText())
        def delete():
            target = PROFILES / (options.currentText() + '.json')
            if target.is_file():
                target.unlink()
                refresh_options()
        for title, fn in [('SAVE CURRENT LAYOUT', save), ('LOAD SELECTED LAYOUT', load),
                          ('DELETE SELECTED LAYOUT', delete)]:
            button = QPushButton(title)
            button.clicked.connect(fn)
            layout.addWidget(button)
        layout.addStretch()
        close = QPushButton('CLOSE')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def closeEvent(self, event):
        self.save_layout()
        self.save_preferences()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor('#10191b'))
    pal.setColor(QPalette.WindowText, QColor('#f1f5f4'))
    pal.setColor(QPalette.Base, QColor('#101b1d'))
    pal.setColor(QPalette.AlternateBase, QColor('#1b2a2d'))
    pal.setColor(QPalette.Text, QColor('#f1f5f4'))
    pal.setColor(QPalette.Button, QColor('#203135'))
    pal.setColor(QPalette.ButtonText, QColor('#f1f5f4'))
    pal.setColor(QPalette.Highlight, QColor('#9e3934'))
    pal.setColor(QPalette.HighlightedText, QColor('#ffffff'))
    pal.setColor(QPalette.PlaceholderText, QColor('#aab9b6'))
    app.setPalette(pal)
    app.setStyleSheet(STYLE)
    app.setApplicationName('Airsoft OS 3.9.0')
    desktop = AOJDesktop()
    if '--fullscreen' in sys.argv:
        desktop.showFullScreen()
    elif '--desktop' in sys.argv:
        screen = app.primaryScreen()
        desktop.setWindowFlag(Qt.FramelessWindowHint, True)
        desktop.setGeometry(screen.geometry())
        desktop.show()
    else:
        desktop.show()
    # Ensure chrome is not hidden by background or panels restored from old layouts.
    desktop.top.raise_()
    desktop.sidebar.raise_()
    sys.exit(app.exec())
