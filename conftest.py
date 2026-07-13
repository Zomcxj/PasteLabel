"""
pytest conftest - 在收集测试前 mock PyQt5
使用真实类继承，避免 metaclass 冲突
"""
import sys
import types

# ponytail: 子进程测试用 sys.executable 在本地无 PyQt5，转至 llm 环境
import os as _os
for _p in (
    r"D:\Softwaredata\miniforge3\envs\llm\python.exe",
    r"D:\Softwaredata\miniforge3\envs\llm\Scripts\python.exe",
):
    if _os.path.exists(_p):
        sys.executable = _p
        break
del _os, _p


def _make_mock_module(name):
    """创建一个支持 from X import Y 的 mock 模块"""
    mod = types.ModuleType(name)
    mod.__path__ = []  # 标记为包
    mod.__file__ = f"<mock {name}>"
    # 预注册常用 Qt 名称，确保 from X import Y 可用
    for attr in [
        'QPoint', 'Qt', 'QUrl', 'QSize', 'QTimer', 'QRectF', 'QRect',
        'QPropertyAnimation', 'QEasingCurve',
        'pyqtSignal', 'QObject', 'QPixmap', 'QPainter', 'QColor', 'QIcon',
        'QFont', 'QFontDatabase', 'QEvent', 'QKeySequence', 'QImage',
        'QStandardItem', 'QStandardItemModel', 'QSortFilterProxyModel',
        'QValidator', 'QRegExp', 'QDesktopWidget', 'QApplication',
        'QMainWindow', 'QDialog', 'QWidget', 'QVBoxLayout', 'QHBoxLayout',
        'QLabel', 'QPushButton', 'QListWidget', 'QListWidgetItem',
        'QLineEdit', 'QCheckBox', 'QSpinBox', 'QGroupBox', 'QFrame',
        'QSplitter', 'QScrollArea', 'QFileDialog', 'QMessageBox',
        'QInputDialog', 'QMenu', 'QAction', 'QWidgetAction', 'QShortcut', 'QKeySequence',
        'QProgressDialog', 'QSvgRenderer', 'QCursor',
        'QStackedWidget', 'QComboBox', 'QDoubleSpinBox', 'QTextBrowser',
        'QTabWidget', 'QToolButton', 'QSlider', 'QRadioButton', 'QColorDialog', 'QDialogButtonBox',
    ]:
        setattr(mod, attr, type(f'Mock{attr}', (), {
            '__init__': lambda self, *a, **kw: None,
        }))
    return mod


class _MockQWidget:
    """最小化的 QWidget mock，支持继承"""
    def __init__(self, *a, **kw):
        pass
    def setMinimumSize(self, *a): pass
    def setMouseTracking(self, *a): pass
    def setFocusPolicy(self, *a): pass
    def setFocus(self): pass
    def update(self): pass
    def width(self): return 800
    def height(self): return 600
    def rect(self):
        r = type('R', (), {'left': lambda: 0, 'top': lambda: 0,
                           'width': lambda: 800, 'height': lambda: 600,
                           'x': lambda: 0, 'y': lambda: 0})()
        return r
    def setCursor(self, *a): pass
    def mapToGlobal(self, p): return p
    def installEventFilter(self, *a): pass
    def children(self): return []
    def parent(self): return None
    def repaint(self): pass
    def updateGeometry(self): pass
    def show(self): pass
    def raise_(self): pass
    def setAttribute(self, *a): pass
    def adjustSize(self): pass
    def move(self, *a): pass
    def setWordWrap(self, *a): pass


class _MockQMainWindow(_MockQWidget):
    """最小化的 QMainWindow mock"""
    def statusBar(self):
        sb = type('StatusBar', (), {'addWidget': lambda self, w: None})()
        return sb
    def setCentralWidget(self, *a): pass
    def setWindowTitle(self, *a): pass
    def resize(self, *a): pass
    def setWindowIcon(self, *a): pass


class _MockQDialog(_MockQWidget):
    Accepted = 1
    Rejected = 0
    def setWindowTitle(self, *a): pass
    def setMinimumWidth(self, *a): pass
    def setLayout(self, *a): pass
    def exec_(self): return False
    def accept(self): pass
    def reject(self): pass


class _MockQListWidget(_MockQWidget):
    IconMode = 0
    ListMode = 1
    LeftToRight = 0
    TopToBottom = 1
    Adjust = 1
    ScrollPerPixel = 0
    ScrollPerItem = 1
    CustomContextMenu = 1

    def addItem(self, *a): pass
    def clear(self): pass
    def count(self): return 0
    def item(self, *a): return None
    def selectedItems(self): return []
    def setCurrentRow(self, *a): pass
    def setContextMenuPolicy(self, *a): pass
    def setViewMode(self, *a): pass
    def setIconSize(self, *a): pass
    def setGridSize(self, *a): pass
    def setSpacing(self, *a): pass
    def setWrapping(self, *a): pass
    def setFlow(self, *a): pass
    def setResizeMode(self, *a): pass
    def setVerticalScrollMode(self, *a): pass
    def setHorizontalScrollMode(self, *a): pass
    def scrollToTop(self): pass
    def mapToGlobal(self, p): return p


class _MockQSplitter(_MockQWidget):
    def setStretchFactor(self, *a): pass
    def setSizes(self, *a): pass
    def addWidget(self, *a): pass


class _MockQScrollArea(_MockQWidget):
    def setWidget(self, *a): pass
    def setWidgetResizable(self, *a): pass


class _MockQBoxLayout:
    def __init__(self, *a): pass
    def addWidget(self, *a): pass
    def addLayout(self, *a): pass
    def addSpacing(self, *a): pass
    def addStretch(self): pass
    def setStretch(self, *a): pass
    def setContentsMargins(self, *a): pass


class _MockQLabel(_MockQWidget):
    def __init__(self, *a, **kw):
        super().__init__()
    def setText(self, *a): pass
    def text(self): return ''
    def hide(self): pass
    def show(self): pass
    def setStyleSheet(self, *a): pass
    def setMaximumWidth(self, *a): pass
    def setToolTip(self, *a): pass


class _MockQPushButton(_MockQWidget):
    def __init__(self, *a, **kw):
        super().__init__()
    def setIcon(self, *a): pass
    def setMaximumWidth(self, *a): pass
    def setToolTip(self, *a): pass
    def setStyleSheet(self, *a): pass
    def setText(self, *a): pass
    def setMinimumWidth(self, *a): pass
    clicked = type('Signal', (), {'connect': lambda self, f: None})()


class _MockQCheckBox(_MockQWidget):
    def __init__(self, *a, **kw):
        super().__init__()
    def isChecked(self): return False
    def setChecked(self, *a): pass
    def setStyleSheet(self, *a): pass
    stateChanged = type('Signal', (), {'connect': lambda self, f: None})()


class _MockQSpinBox(_MockQWidget):
    def __init__(self, *a, **kw):
        super().__init__()
    def minimum(self): return 0
    def maximum(self): return 100
    def value(self): return 0
    def setValue(self, *a): pass
    def setMinimum(self, *a): pass
    def setMaximum(self, *a): pass
    def setMinimumWidth(self, *a): pass
    def setStyleSheet(self, *a): pass
    valueChanged = type('Signal', (), {'connect': lambda self, f: None})()
    editingFinished = type('Signal', (), {'connect': lambda self, f: None})()


class _MockQLineEdit(_MockQWidget):
    def __init__(self, *a, **kw):
        super().__init__()
    def text(self): return ''
    def setText(self, *a): pass
    def setStyleSheet(self, *a): pass
    def setMaximumWidth(self, *a): pass
    def focusInEvent(self, *a): pass
    def focusOutEvent(self, *a): pass
    returnPressed = type('Signal', (), {'connect': lambda self, f: None})()


class _MockQListWidgetItem:
    def __init__(self, *a, **kw):
        pass
    def setData(self, *a): pass
    def data(self, *a): return None
    def setIcon(self, *a): pass
    def setSizeHint(self, *a): pass
    def text(self): return ''


class _MockQProgressDialog(_MockQWidget):
    last_args = None
    def __init__(self, *a, **kw):
        super().__init__()
        self.args = a
        _MockQProgressDialog.last_args = a
    def setWindowTitle(self, *a): pass
    def setMinimumWidth(self, *a): pass
    def setModal(self, *a): pass
    def setStyleSheet(self, *a): pass
    def show(self): pass
    def setValue(self, *a): pass
    def setLabelText(self, *a): pass
    def wasCanceled(self): return False
    def close(self): pass
    def geometry(self):
        return type('G', (), {'width': lambda self: 400, 'height': lambda self: 200})()


class _MockQInputDialog:
    def __init__(self, *a, **kw): pass
    def setWindowTitle(self, *a): pass
    def setLabelText(self, *a): pass
    def setTextValue(self, *a): pass
    def setOkButtonText(self, *a): pass
    def setCancelButtonText(self, *a): pass
    def textValue(self): return ''
    def exec_(self): return _MockQDialog.Rejected
    def showEvent(self, *a): pass
    @staticmethod
    def getText(*a, **kw): return ('', False)


class _MockQMessageBox:
    Critical = 2
    Warning = 2
    Question = 4
    Ok = 0x00000400
    Yes = 0x00000400
    No = 0x00000200
    Cancel = 0x00400000
    def __init__(self, *a, **kw): pass
    def setIcon(self, *a): pass
    def setWindowTitle(self, *a): pass
    def setText(self, *a): pass
    def setStandardButtons(self, *a): pass
    def setDefaultButton(self, *a): pass
    def button(self, *a): return type('Button', (), {'setText': lambda self, text: None})()
    def exec_(self): return _MockQMessageBox.No
    def showEvent(self, *a): pass
    @staticmethod
    def warning(*a, **kw): pass
    @staticmethod
    def critical(*a, **kw): pass
    @staticmethod
    def information(*a, **kw): pass
    @staticmethod
    def question(*a, **kw): return _MockQMessageBox.No


class _MockQFileDialog:
    @staticmethod
    def getOpenFileNames(*a, **kw): return ([], '')
    @staticmethod
    def getExistingDirectory(*a, **kw): return ''
    @staticmethod
    def getOpenFileName(*a, **kw): return ('', '')


class _MockQApplication:
    @staticmethod
    def primaryScreen():
        return type('S', (), {'availableGeometry': lambda self: type('R', (), {
            'width': lambda self: 1920, 'height': lambda self: 1080})()})()
    @staticmethod
    def desktop():
        return type('D', (), {'screenGeometry': lambda: type('R', (), {
            'width': lambda: 1920, 'height': lambda: 1080})()})()
    @staticmethod
    def processEvents(): pass
    @staticmethod
    def instance(): return None
    def __init__(self, *a): pass
    def exec_(self): return 0


# ========== 构建 mock 模块 ==========

qtcore = types.ModuleType('PyQt5.QtCore')
qtcore.Qt = type('Qt', (), {
    'Key_A': 0x41, 'Key_D': 0x44, 'Key_R': 0x52, 'Key_T': 0x54,
    'Key_W': 0x57, 'Key_Q': 0x51, 'Key_E': 0x45, 'Key_G': 0x47,
    'Key_Delete': 0x01000007,
    'Horizontal': 1, 'CustomContextMenu': 1, 'StrongFocus': 2,
    'LeftButton': 1, 'RightButton': 2,
    'ControlModifier': 0x04000000, 'KeepAspectRatio': 1,
    'SmoothTransformation': 1, 'transparent': 0,
    'PointingHandCursor': 18,
    'OpenHandCursor': 17,
    'ClosedHandCursor': 18,
    'ArrowCursor': 0,
})()
qtcore.QPoint = type('QPoint', (), {'__init__': lambda self, x=0, y=0: None})
qtcore.QPointF = type('QPointF', (), {'__init__': lambda self, x=0, y=0: None})
qtcore.QRectF = type('QRectF', (), {
    '__init__': lambda self, *a: None,
    'contains': lambda self, p: True,
    'x': lambda self: 0,
    'y': lambda self: 0,
    'width': lambda self: 10,
    'height': lambda self: 10,
    'left': lambda self: 0,
    'top': lambda self: 0,
})
qtcore.QRect = type('QRect', (), {'__init__': lambda self, *a: None})
qtcore.QSize = type('QSize', (), {'__init__': lambda self, w=0, h=0: None})
qtcore.QSizeF = type('QSizeF', (), {'__init__': lambda self, w=0, h=0: None})
qtcore.QTimer = type('QTimer', (), {'singleShot': staticmethod(lambda *a: None)})
qtcore.QPropertyAnimation = type('QPropertyAnimation', (), {'__init__': lambda self, *a: None})
qtcore.QEasingCurve = type('QEasingCurve', (), {'OutCubic': 0})
qtcore.QEvent = type('QEvent', (), {'KeyPress': 6})
qtcore.QUrl = type('QUrl', (), {'fromLocalFile': staticmethod(lambda f: f)})
qtcore.QMimeData = type('QMimeData', (), {
    '__init__': lambda self, *a, **kw: None,
    'hasUrls': lambda self: False,
    'setUrls': lambda self, *a: None,
})
qtcore.qInstallMessageHandler = lambda *a: None
qtcore.pyqtSignal = lambda *a, **kw: type('Signal', (), {'connect': lambda self, f: None})()

class _MockQObject:
    """QObject mock - 支持继承和 pyqtSignal 作为类属性"""
    def __init__(self, *a, **kw):
        pass
    def connect(self, *a): pass
    def emit(self, *a): pass

qtcore.QObject = _MockQObject

qtgui = types.ModuleType('PyQt5.QtGui')
qtgui.QPixmap = type('QPixmap', (), {
    '__init__': lambda self, *a: None,
    'isNull': lambda self: False,
    'width': lambda self: 100,
    'height': lambda self: 100,
    'scaled': lambda self, *a: self,
    'save': lambda self, *a: True,
    'fill': lambda self, *a: None,
})
qtgui.QIcon = type('QIcon', (), {'__init__': lambda self, *a: None})
qtgui.QColor = type('QColor', (), {
    '__init__': lambda self, *a: None,
    'setAlpha': lambda self, *a: None,
    'isValid': lambda self: True,
    'name': lambda self: '#00FF80',
})
qtgui.QPainter = type('QPainter', (), {
    '__init__': lambda self, *a: None,
    'setRenderHint': lambda self, *a: None,
    'setPen': lambda self, *a: None,
    'setBrush': lambda self, *a: None,
    'setFont': lambda self, *a: None,
    'drawPixmap': lambda self, *a: None,
    'drawRect': lambda self, *a: None,
    'drawLine': lambda self, *a: None,
    'drawText': lambda self, *a: None,
    'fillRect': lambda self, *a: None,
    'end': lambda self: None,
    'font': lambda self: type('F', (), {'pointSize': lambda: 12})(),
})
qtgui.QPen = type('QPen', (), {'__init__': lambda self, *a: None})
qtgui.QFontMetrics = type('QFontMetrics', (), {
    '__init__': lambda self, *a: None,
    'width': lambda self, *a: 50,
    'height': lambda self: 20,
})
qtgui.QKeySequence = type('QKeySequence', (), {
    '__init__': lambda self, *a: None,
})
qtgui.QDragEnterEvent = type('QDragEnterEvent', (), {'__init__': lambda self, *a: None})
qtgui.QDropEvent = type('QDropEvent', (), {'__init__': lambda self, *a: None})
qtgui.QDrag = type('QDrag', (), {'__init__': lambda self, *a: None, 'exec_': lambda self, *a: 0})
qtgui.QFontDatabase = type('QFontDatabase', (), {'addApplicationFont': staticmethod(lambda *a: 0)})

qtwidgets = types.ModuleType('PyQt5.QtWidgets')
qtwidgets.QWidget = _MockQWidget
qtwidgets.QMainWindow = _MockQMainWindow
qtwidgets.QDialog = _MockQDialog
qtwidgets.QListWidget = _MockQListWidget
qtwidgets.QListWidgetItem = _MockQListWidgetItem
qtwidgets.QSplitter = _MockQSplitter
qtwidgets.QStackedWidget = type('QStackedWidget', (_MockQWidget,), {
    'addWidget': lambda self, *a: None,
    'setCurrentIndex': lambda self, *a: None,
    'currentIndex': lambda self: 0,
    'count': lambda self: 1,
    'widget': lambda self, i: None,
})
qtwidgets.QScrollArea = _MockQScrollArea
qtwidgets.QVBoxLayout = type('QVBoxLayout', (_MockQBoxLayout,), {})
qtwidgets.QHBoxLayout = type('QHBoxLayout', (_MockQBoxLayout,), {})
qtwidgets.QLabel = _MockQLabel
qtwidgets.QPushButton = _MockQPushButton
qtwidgets.QCheckBox = _MockQCheckBox
qtwidgets.QSpinBox = _MockQSpinBox
qtwidgets.QDoubleSpinBox = type('QDoubleSpinBox', (_MockQWidget,), {
    'minimum': lambda self: 0.0,
    'maximum': lambda self: 100.0,
    'value': lambda self: 0.0,
    'setValue': lambda self, *a: None,
    'setMinimum': lambda self, *a: None,
    'setMaximum': lambda self, *a: None,
    'setSingleStep': lambda self, *a: None,
    'setDecimals': lambda self, *a: None,
    'setMinimumWidth': lambda self, *a: None,
    'setStyleSheet': lambda self, *a: None,
    'valueChanged': type('Signal', (), {'connect': lambda self, f: None})(),
    'editingFinished': type('Signal', (), {'connect': lambda self, f: None})(),
})
qtwidgets.QLineEdit = _MockQLineEdit
qtwidgets.QProgressDialog = _MockQProgressDialog
qtwidgets.QInputDialog = _MockQInputDialog
qtwidgets.QMessageBox = _MockQMessageBox
qtwidgets.QFileDialog = _MockQFileDialog
qtwidgets.QColorDialog = type('QColorDialog', (), {
    'DontUseNativeDialog': 1,
    '__init__': lambda self, *a, **kw: None,
    'getColor': staticmethod(lambda *a, **kw: qtgui.QColor()),
    'setOption': lambda self, *a: None,
    'setWindowTitle': lambda self, *a: None,
    'setCurrentColor': lambda self, *a: None,
    'setStyleSheet': lambda self, *a: None,
    'showEvent': lambda self, *a: None,
    'findChild': lambda self, *a: None,
    'findChildren': lambda self, *a: [],
    'exec_': lambda self: _MockQDialog.Rejected,
    'currentColor': lambda self: qtgui.QColor(),
})
qtwidgets.QDialogButtonBox = type('QDialogButtonBox', (), {'Ok': 1, 'Cancel': 2})
qtwidgets.QApplication = _MockQApplication
qtwidgets.QMenu = type('QMenu', (_MockQWidget,), {
    'addAction': lambda self, *a: None,
    'addSeparator': lambda self: None,
    'exec_': lambda self, *a: None,
})
qtwidgets.QAction = type('QAction', (), {'__init__': lambda self, *a: None})
qtwidgets.QWidgetAction = type('QWidgetAction', (), {
    '__init__': lambda self, *a: None,
    'setDefaultWidget': lambda self, *a: None,
})
qtwidgets.QGroupBox = type('QGroupBox', (_MockQWidget,), {
    'setStyleSheet': lambda self, *a: None,
})
qtwidgets.QFrame = type('QFrame', (_MockQWidget,), {
    'VLine': 1,
    'Sunken': 3,
    'setFrameShape': lambda self, *a: None,
    'setFrameShadow': lambda self, *a: None,
    'setFixedHeight': lambda self, *a: None,
})
qtwidgets.QComboBox = type('QComboBox', (_MockQWidget,), {
    'addItems': lambda self, *a: None,
    'setCurrentIndex': lambda self, *a: None,
    'currentIndex': lambda self: 0,
    'setMaximumWidth': lambda self, *a: None,
})
qtwidgets.QShortcut = type('QShortcut', (_MockQWidget,), {
    '__init__': lambda self, *a, **kw: None,
    'setContext': lambda self, *a: None,
    'activated': type('Signal', (), {'connect': lambda self, f: None})(),
})

# 注册模块
sys.modules['PyQt5'] = types.ModuleType('PyQt5')
sys.modules['PyQt5.QtCore'] = qtcore
sys.modules['PyQt5.QtGui'] = qtgui
sys.modules['PyQt5.QtWidgets'] = qtwidgets
