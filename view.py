# view.py: image viewer
#
# author: Antony Ducommun dit Boudry (nitro.tm@gmail.com)
# license: GPL
#

from pathlib import Path

from PySide2.QtCore import Qt, Signal, Slot, QEvent, QLine, QLineF, QPoint, QPointF, QRect, QRectF, QSize, QTimer, QThreadPool, QRunnable
from PySide2.QtGui import QBitmap, QBrush, QColor, QCursor, QImage, QPainter, QPainterPath, QPen, QPixmap, QTabletEvent
from PySide2.QtWidgets import QWidget


def normalizeCoords(ap, rc):
  return QPointF(
    (ap.x() - rc.x()) / max(1.0, rc.width()),
    (ap.y() - rc.y()) / max(1.0, rc.height())
  )

def realCoords(np, rc):
  return QPointF(
    np.x() * rc.width()  + rc.x(),
    np.y() * rc.height() + rc.y()
  )

def makeCursor(filename, color=Qt.black):
  pixmap = QPixmap(filename)
  mask = QBitmap(pixmap)
  pixmap.fill(color)
  pixmap.setMask(mask)
  return QCursor(pixmap)

class View(QWidget):
  previous = Signal()
  next = Signal()

  def __init__(self, window):
    super(View, self).__init__(window)

    self.setFocusPolicy(Qt.StrongFocus)
    self.shiftKey = False
    self.ctrlKey = False
    self.lastMousePos = QPoint()
    self.lastTabletPos = QPoint()
    self.mode = 'add'
    self.maskOnly = False

    self.refresh = QTimer(self)
    self.refresh.setSingleShot(True)
    self.refresh.timeout.connect(self.repaint)

    self.addCursor = makeCursor('images/cursor-add.png', QColor.fromRgbF(0.5, 0.5, 1.0))
    self.delCursor = makeCursor('images/cursor-del.png', QColor.fromRgbF(1.0, 0.5, 0.5))
    self.setCursor(self.addCursor)

    self.imagefile = None
    self.maskfile = None
    self.image = QImage()
    self.mask = QImage(self.image.size(), QImage.Format_RGB32)
    self.mask.fill(Qt.black)
    self.changed = False
    self.update()

    self.path = list()

    self.load_threads = QThreadPool()
    self.load_threads.setMaxThreadCount(4)


  def load(self, filename):
    self.load_threads.start(LoadTask(self, filename))

  def save(self):
    if self.maskfile and self.changed:
      self.load_threads.waitForDone()
    if self.maskfile and self.changed:
      bitmap = self.mask.createMaskFromColor(QColor.fromRgbF(1.0, 0.0, 1.0).rgb())
      bitmap.save(str(self.maskfile), "PNG")
      self.changed = False


  def update(self):
    widgetRatio = self.width() / self.height()
    aspectRatio = self.image.width() / max(1, self.image.height())
    if aspectRatio >= widgetRatio:
      width = self.width()
      height = self.width() / aspectRatio
    else:
      width = self.height() * aspectRatio
      height = self.height()
    self.rc = QRectF(
      (self.width()  - width ) / 2.0,
      (self.height() - height) / 2.0,
      width,
      height
    )
    self.repaint()


  def resizeEvent(self, event):
    self.update()

  def paintEvent(self, event):
    p = QPainter(self.mask)
    for (mode, p1, p2, weight) in self.path:
      if mode == 'add':
        p.setPen(QPen(QColor.fromRgbF(1.0, 0.0, 1.0), (weight * 10.0) ** 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
      else:
        p.setPen(QPen(QColor.fromRgbF(0.0, 0.0, 0.0), (weight * 10.0) ** 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
      p.drawLine(realCoords(p1, self.mask.rect()), realCoords(p2, self.mask.rect()))
      self.changed = True
    self.path = list()
    p.end()

    p = QPainter(self)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    if not self.maskOnly:
      p.drawImage(self.rc, self.image)
      p.setCompositionMode(QPainter.CompositionMode_Plus)
    p.drawImage(self.rc, self.mask)
    p.end()

  def closeEvent(self, event):
    self.refresh.stop()
    event.accept()


  def enterEvent(self, event):
    self.setFocus(Qt.OtherFocusReason)


  def keyPressEvent(self, event):
    k = event.key()
    if k == Qt.Key_Shift:
      self.shiftKey = True
    if k == Qt.Key_Control:
      self.ctrlKey = True

    if k == Qt.Key_Space:
      self.maskOnly = not self.maskOnly
      self.repaint()

  def keyReleaseEvent(self, event):
    k = event.key()
    mod = event.modifiers()
    if k == Qt.Key_Shift:
      self.shiftKey = False
    if k == Qt.Key_Control:
      self.ctrlKey = False

  def mousePressEvent(self, event):
    x = event.x()
    y = event.y()
    self.lastMousePos = event.pos()

    if event.button() == Qt.ExtraButton1:
      if self.mode == 'add':
        self.mode = 'del'
        self.setCursor(self.delCursor)
      else:
        self.mode = 'add'
        self.setCursor(self.addCursor)
    elif event.button() == Qt.ExtraButton2:
      self.maskOnly = not self.maskOnly
      self.repaint()
    elif event.button() == Qt.ExtraButton3:
      self.previous.emit()
    elif event.button() == Qt.ExtraButton4:
      self.next.emit()

  def mouseMoveEvent(self, event):
    x = event.x()
    y = event.y()
    dx = x - self.lastMousePos.x()
    dy = y - self.lastMousePos.y()
    self.lastMousePos = event.pos()

    # if event.buttons() & Qt.LeftButton:
    # elif event.buttons() & Qt.MiddleButton:
    # elif event.buttons() & Qt.RightButton:

  def wheelEvent(self, event):
    dx = event.angleDelta().x() / 8
    dy = event.angleDelta().y() / 8
    # self.cameraZoom.emit(dy / 15)

  def tabletEvent(self, event):
    if event.device() == QTabletEvent.Stylus and event.pointerType() == QTabletEvent.Pen:
      if event.type() == QEvent.TabletPress:
        self.tabletPressEvent(event)
      elif event.type() == QEvent.TabletRelease:
        self.tabletReleaseEvent(event)
      elif event.type() == QEvent.TabletMove:
        if event.pressure() > 0.0:
          self.tabletMoveEvent(event)
      else:
        print('tabletEvent', event.device(), event.type(), event.pointerType())
    else:
      print('tabletEvent', event.device(), event.type(), event.pointerType())

  def tabletPressEvent(self, event):
    if event.buttons() & Qt.LeftButton:
      self.lastTabletPos = normalizeCoords(event.posF(), self.rc)
    if event.buttons() & Qt.MiddleButton:
      if self.mode == 'add':
        self.mode = 'del'
        self.setCursor(self.delCursor)
      else:
        self.mode = 'add'
        self.setCursor(self.addCursor)
    if event.buttons() & Qt.RightButton:
      self.next.emit()

  def tabletReleaseEvent(self, event):
    self.lastTabletPos = normalizeCoords(event.posF(), self.rc)

  def tabletMoveEvent(self, event):
    self.path.append((self.mode, self.lastTabletPos, normalizeCoords(event.posF(), self.rc), event.pressure()))
    self.lastTabletPos = normalizeCoords(event.posF(), self.rc)
    if not self.refresh.isActive():
      self.refresh.start(50)


class LoadTask(QRunnable):
  def __init__(self, view, filename):
    super(LoadTask, self).__init__()
    self.view = view
    self.filename = filename

  def run(self):
    image = QImage()
    image.load(str(self.filename))

    mask = QImage(image.size(), QImage.Format_RGB32)
    mask.fill(Qt.black)

    maskfile = self.filename.parent / (self.filename.stem + ".mask")
    if maskfile.exists():
      bitmap = QImage(str(maskfile))
      if bitmap.size() != image.size():
        raise Exception("Mask %s doesn't match image size" % maskfile)
      mask.fill(QColor.fromRgbF(1.0, 0.0, 1.0))
      p = QPainter(mask)
      p.setCompositionMode(QPainter.CompositionMode_Multiply)
      p.drawImage(mask.rect(), bitmap)
      p.end()

    self.view.imagefile = self.filename
    self.view.image = image
    self.view.mask = mask
    self.view.maskfile = maskfile

    self.view.path = list()
    self.view.changed = False
    self.view.update()
