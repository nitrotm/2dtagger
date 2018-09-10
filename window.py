# window.py: main app window
#
# author: Antony Ducommun dit Boudry (nitro.tm@gmail.com)
# license: GPL
#

import io, json

from pathlib import Path

from PySide2.QtCore import Signal, Slot, Qt, QFile, QFileInfo, QPoint, QRect, QSize
from PySide2.QtGui import QColor, QKeySequence, QIcon, QImage
from PySide2.QtWidgets import (
  QAbstractItemView, QAction, QActionGroup, QDockWidget, QFileDialog, QGridLayout, QHBoxLayout, QInputDialog,
  QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressDialog, QToolButton, QVBoxLayout, QWidget
)

from view import View


def find_images(rootpath, path=None):
  if not path:
    path = rootpath
  result = list()
  for child in path.iterdir():
    if child.is_dir():
      result = result + find_images(rootpath, child)
    if child.is_file():
      filename = child.name.lower()
      if filename.endswith(".png") or filename.endswith(".jpg"):
        result.append(str(child.relative_to(rootpath)))
  return sorted(result)


class Window(QMainWindow):
  def __init__(self):
    super(Window, self).__init__()

    self.lastProjectDirectory = None
    self.view = None
    self.items = dict()

    self.loadSettings()

    self.setWindowTitle("2D Tagger")
    self.createActions()
    self.createMenus()
    self.createFileList()
    self.createContainer()
    self.createStatusBar()


  def loadSettings(self):
    try:
      with io.open(Path(__file__).parent / 'app.json', 'r') as f:
        data = json.load(f)
        if 'lastProjectDirectory' in data:
          self.lastProjectDirectory = data['lastProjectDirectory']
    except:
      pass

  def saveSettings(self):
    data = dict()
    data['lastProjectDirectory'] = self.lastProjectDirectory
    with io.open(Path(__file__).parent / 'app.json', 'w') as f:
      json.dump(data, f, indent=' ')


  def createActions(self):
    # root = QFileInfo(__file__).absolutePath()
    self.openAct = QAction(
      # QIcon(root + '/icons/open.png'),
      "&Open",
      self,
      shortcut=QKeySequence.Open,
      statusTip="Open project",
      triggered=self.openProject
    )
    self.closeAct = QAction(
      # QIcon(root + '/icons/close.png'),
      "&Close",
      self,
      shortcut=QKeySequence.Close,
      statusTip="Close project",
      triggered=self.closeProject,
      enabled=False
    )
    self.exitAct = QAction(
      # QIcon(root + '/icons/quit.png'),
      "&Quit",
      self,
      shortcut=QKeySequence.Quit,
      statusTip="Close the application",
      triggered=self.close
    )
    self.aboutAct = QAction(
      "&About",
      self,
      statusTip="Show the application's About box",
      triggered=self.about
    )

  def createMenus(self):
    fileMenu = self.menuBar().addMenu("&File")
    fileMenu.addAction(self.openAct)
    fileMenu.addAction(self.closeAct)
    fileMenu.addSeparator()
    fileMenu.addAction(self.exitAct)

    self.menuBar().addSeparator()
    helpMenu = self.menuBar().addMenu("&Help")
    helpMenu.addAction(self.aboutAct)

  def createFileList(self):
    self.files = QListWidget()
    self.files.setSelectionMode(QAbstractItemView.SingleSelection)
    self.files.setSortingEnabled(False)
    self.files.itemSelectionChanged.connect(self.onSelect)
    self.files.itemDoubleClicked.connect(self.onToggle)
    self.files.setEnabled(False)

    dock = QDockWidget("Images", self)
    dock.setAllowedAreas(Qt.LeftDockWidgetArea)
    dock.setFixedWidth(320)
    dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
    dock.setWidget(self.files)
    self.addDockWidget(Qt.LeftDockWidgetArea, dock)

  def createContainer(self):
    self.container = QWidget(self)
    self.container.setStyleSheet("View { background: black; }")
    self.container.setLayout(QVBoxLayout())
    self.setCentralWidget(self.container)

  def createStatusBar(self):
    self.statusBar().showMessage("Initialized")


  def enableProjectActions(self, enabled):
    actions = [
      self.closeAct,
      self.files
    ]
    for action in actions:
      action.setEnabled(enabled)


  def closeEvent(self, event):
    event.accept()


  def openProject(self, path=None):
    if not path:
      path = QFileDialog.getExistingDirectory(
        self,
        "Choose image directory",
        dir=self.lastProjectDirectory
      )
    if path:
      self.closeProject()

      self.view = View(self)
      self.view.previous.connect(self.onPrevious)
      self.view.next.connect(self.onNext)
      self.container.layout().addWidget(self.view)

      filename = Path(path) / "items.json"
      if filename.exists():
        with io.open(filename, 'r') as f:
          self.items = json.load(f)
      else:
        self.items = dict()
      for filename in find_images(Path(path)):
        if filename in self.items:
          continue
        self.items[filename] = dict({
          "active": True
        })

      self.refreshItems()
      self.files.setItemSelected(self.files.item(0), True)

      self.enableProjectActions(True)

      self.lastProjectDirectory = path
      self.saveProject()
      self.saveSettings()

  def saveProject(self):
    if not self.view:
      return
    with io.open(Path(self.lastProjectDirectory) / "items.json", 'w') as f:
      json.dump(self.items, f, indent='  ')

  def closeProject(self):
    self.enableProjectActions(False)
    if self.view:
      self.container.layout().removeWidget(self.view)
      self.view.close()
      self.view = None
    self.items = dict()
    self.refreshItems()


  def selection(self):
    selection = self.files.selectedItems()
    if len(selection) > 0:
      return selection[0].text()
    return None


  def refreshItems(self):
    filenames = sorted(self.items.keys())
    for i in range(len(filenames)):
      filename = filenames[i]
      item = self.items[filename]
      file = self.files.item(i)
      if not file:
        file = QListWidgetItem(filenames[i])
        self.files.insertItem(i, file)
      if item['active']:
        file.setTextColor(QColor.fromRgbF(0.0, 0.5, 0.0))
      else:
        file.setTextColor(QColor.fromRgbF(0.5, 0.0, 0.0))
    while self.files.count() > len(filenames):
      self.files.takeItem(len(filenames))


  @Slot()
  def onToggle(self, item):
    self.items[item.text()]['active'] = not self.items[item.text()]['active']
    self.refreshItems()
    self.saveProject()

  @Slot()
  def onSelect(self):
    selection = self.selection()
    if self.view:
      self.view.save()
      if selection:
        self.view.load(Path(self.lastProjectDirectory) / selection)

  @Slot()
  def onPrevious(self):
    if self.files.count() == 0:
      return
    index = 0
    selection = self.selection()
    if selection:
      for i in range(self.files.count()):
        item = self.files.item(i)
        if item.text() == selection:
          index = i - 1
          break
    if index < 0:
      index = self.files.count() - 1
    self.files.setItemSelected(self.files.item(index), True)

  @Slot()
  def onNext(self):
    if self.files.count() == 0:
      return
    index = 0
    selection = self.selection()
    if selection:
      for i in range(self.files.count()):
        item = self.files.item(i)
        if item.text() == selection:
          index = i + 1
          break
    if index >= self.files.count():
      index = 0
    self.files.setItemSelected(self.files.item(index), True)


  @Slot(str)
  def showMessage(self, message):
    self.statusBar().showMessage(message)


  def about(self):
    QMessageBox.about(self, "About Application", "The <b>2D Tagger</b> can load images, manually tag/label images and export result.")

  # def contextMenuEvent(self, ev):
  #   print(ev)
