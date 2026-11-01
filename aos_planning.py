"""Offline image-based planning board with coloured markers and routes."""
import json
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QFont
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QComboBox, QLabel, QInputDialog, QMessageBox, QScrollArea)

DATA = Path.home()/'.config'/'aoj-os'/'planning'
COLORS = {'Red':'#ed5c54','Blue':'#55aaff','Green':'#69d99a','Yellow':'#f5c65d','Purple':'#c79aff','White':'#ffffff'}

class MapCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.image = QPixmap()
        self.image_path = ''
        self.items = []
        self.tool = 'Marker'
        self.colour = COLORS['Red']
        self.pending = []
        self.on_changed = lambda: None

    def set_image(self, path):
        img = QPixmap(path)
        if img.isNull(): raise ValueError('Unsupported or damaged image')
        self.image = img
        self.image_path = str(path)
        self.setMinimumSize(600, 400)
        self.update()

    def rect_for_image(self):
        if self.image.isNull(): return QRectF(0,0,self.width(),self.height())
        w,h = self.image.width(), self.image.height()
        scale = min(self.width()/w,self.height()/h)
        width,height=w*scale,h*scale
        return QRectF((self.width()-width)/2,(self.height()-height)/2,width,height)

    def point_from_event(self, pos):
        r=self.rect_for_image()
        if not r.contains(pos): return None
        return [max(0,min(1,(pos.x()-r.x())/r.width())),max(0,min(1,(pos.y()-r.y())/r.height()))]

    def screen_point(self, point):
        r=self.rect_for_image()
        return QPointF(r.x()+point[0]*r.width(),r.y()+point[1]*r.height())

    def mousePressEvent(self,event):
        if event.button()!=Qt.LeftButton or self.image.isNull(): return
        pt=self.point_from_event(event.position())
        if pt is None: return
        if self.tool=='Marker':
            title,ok=QInputDialog.getText(self,'Marker label','Name / objective:')
            if ok:
                self.items.append({'kind':'marker','points':[pt],'label':title[:100],'colour':self.colour})
                self.on_changed()
        elif self.tool in ('Route','Waypoint'):
            self.pending.append(pt)
            self.update()

    def finish_path(self):
        if self.pending:
            title,ok=QInputDialog.getText(self,'Route name','Route / waypoint name:')
            if ok:
                self.items.append({'kind':self.tool.lower(),'points':self.pending[:],
                                   'label':title[:100],'colour':self.colour})
                self.on_changed()
            self.pending=[]
            self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),QColor('#0d171a'))
        r=self.rect_for_image()
        if not self.image.isNull(): p.drawPixmap(r.toRect(),self.image)
        else:
            p.setPen(QColor('#d0dedc'))
            p.drawText(self.rect(),Qt.AlignCenter,'OPEN AN IMAGE TO START PLANNING')
        for item in self.items + ([{'kind':'route','points':self.pending,'colour':self.colour,'label':''}] if self.pending else []):
            points=[self.screen_point(q) for q in item.get('points',[])]
            if not points: continue
            color=QColor(item.get('colour','#ffffff'))
            p.setPen(QPen(QColor('#081215'),5))
            if item['kind']!='marker':
                for a,b in zip(points,points[1:]): p.drawLine(a,b)
            p.setPen(QPen(color,3))
            if item['kind']!='marker':
                for a,b in zip(points,points[1:]): p.drawLine(a,b)
            for index,pt in enumerate(points):
                p.setBrush(color)
                p.drawEllipse(pt,6 if item['kind']=='marker' else 4,6 if item['kind']=='marker' else 4)
                p.setPen(QColor('#ffffff'))
                if item['kind']=='marker' or index==0:
                    p.setFont(QFont('Sans',10,QFont.Bold))
                    p.drawText(pt+QPointF(10,-8),item.get('label','')[:45])
                p.setPen(QPen(color,3))
        p.end()

class PlanningDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('AOS // TACTICAL PLANNING MAP')
        self.resize(960,680)
        self.setStyleSheet('''QDialog,QWidget {background:#101b1e;color:#eaf2f0;} QPushButton,QComboBox {background:#213338;color:white;border:1px solid #527077;padding:8px;} QPushButton:hover {border-color:#e85d55;}''')
        self.canvas=MapCanvas()
        self.canvas.on_changed=self.autosave
        outer=QVBoxLayout(self)
        tools=QHBoxLayout()
        def button(name,fn):
            b=QPushButton(name); b.clicked.connect(fn); tools.addWidget(b)
        button('OPEN IMAGE',self.open_image)
        self.mode=QComboBox(); self.mode.addItems(['Marker','Route','Waypoint'])
        self.mode.currentTextChanged.connect(lambda value: setattr(self.canvas,'tool',value))
        tools.addWidget(self.mode)
        self.color=QComboBox(); self.color.addItems(COLORS)
        self.color.currentTextChanged.connect(lambda value: setattr(self.canvas,'colour',COLORS[value]))
        tools.addWidget(self.color)
        button('FINISH ROUTE',self.canvas.finish_path)
        button('UNDO',self.undo)
        button('SAVE PLAN',self.save_plan)
        button('LOAD PLAN',self.load_plan)
        button('EXPORT PNG',self.export_png)
        outer.addLayout(tools)
        outer.addWidget(self.canvas,1)
        hint=QLabel('Marker: click to label  •  Route/Waypoint: click successive points, then FINISH ROUTE  •  All plans work offline')
        outer.addWidget(hint)

    def open_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Select field map or aerial photograph','','Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if path:
            try: self.canvas.set_image(path)
            except ValueError as e: QMessageBox.warning(self,'Image error',str(e))

    def undo(self):
        if self.canvas.pending: self.canvas.pending.pop()
        elif self.canvas.items: self.canvas.items.pop()
        self.canvas.update(); self.autosave()

    def document(self):
        return {'format':'aos-map-v1','image':self.canvas.image_path,'items':self.canvas.items,
                'saved':datetime.now().isoformat(timespec='seconds')}

    def save_plan(self):
        DATA.mkdir(parents=True,exist_ok=True)
        path,_=QFileDialog.getSaveFileName(self,'Save planning board',str(DATA/'field-plan.json'),'AOS Plans (*.json)')
        if path: Path(path).write_text(json.dumps(self.document(),indent=2),encoding='utf-8')

    def load_plan(self):
        DATA.mkdir(parents=True,exist_ok=True)
        path,_=QFileDialog.getOpenFileName(self,'Load planning board',str(DATA),'AOS Plans (*.json)')
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            if data.get('format')!='aos-map-v1' or not isinstance(data.get('items'),list): raise ValueError('Invalid AOS map format')
            if len(data['items'])>5000: raise ValueError('Too many map objects')
            image=data.get('image','')
            if image and Path(image).exists(): self.canvas.set_image(image)
            else:
                QMessageBox.warning(self,'Missing image','The original image is unavailable. Open the image manually.')
                self.canvas.image=QPixmap()
            self.canvas.items=data['items']; self.canvas.pending=[]; self.canvas.update()
        except (OSError,ValueError,TypeError) as e: QMessageBox.warning(self,'Cannot load plan',str(e))

    def autosave(self):
        self.canvas.update()
        DATA.mkdir(parents=True,exist_ok=True)
        (DATA/'autosave.json').write_text(json.dumps(self.document(),indent=2),encoding='utf-8')

    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,'Export map image',str(DATA/'field-map.png'),'PNG image (*.png)')
        if path:
            image=self.canvas.grab()
            if not image.save(path,'PNG'): QMessageBox.warning(self,'Export error','Could not save PNG')
