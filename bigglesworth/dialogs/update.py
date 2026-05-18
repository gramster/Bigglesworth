# *-* coding: utf-8 *-*

from PyQt5 import QtCore, QtGui, QtWidgets
from bigglesworth.utils import load_ui

class LoaderWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        size = 24
        self.setFixedSize(size, size)
        self.pen_width = 5
        top = left = self.pen_width / 2.
        bottom = right = size - 1 - self.pen_width
        self.area = QtCore.QRectF(top, left, right, bottom)
        self.brush = QtGui.QConicalGradient(.5, .5, 0)
        self.brush.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
        self.brush.setColorAt(0, QtCore.Qt.darkGray)
        self.brush.setColorAt(1, QtCore.Qt.lightGray)
        self.pen = QtGui.QPen(self.brush, self.pen_width)

        self.loading_timer = QtCore.QTimer()
        self.loading_timer.setInterval(20)
        self.loading_timer.timeout.connect(self.rotate)

    def rotate(self):
        angle = self.brush.angle() - 10
        if angle < 0:
            angle += 360
        self.brush.setAngle(angle)
        self.pen.setBrush(self.brush)
        self.update()

    def showEvent(self, event):
        self.loading_timer.start()

    def hideEvent(self, event):
        self.loading_timer.stop()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.pen)
        qp.drawEllipse(self.area)
        qp.end()


class VersionRequestDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loader = LoaderWidget()
        layout = QtWidgets.QGridLayout()
        layout.setSpacing(10)
        self.setLayout(layout)
        label = QtWidgets.QLabel('Checking for updates, please wait...')
        label.setAlignment(QtCore.Qt.AlignHCenter)
        layout.addWidget(label)
        layout.addWidget(loader, 1, 0, alignment=QtCore.Qt.AlignHCenter)
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        buttonBox.setCenterButtons(True)
        layout.addWidget(buttonBox)


class UpdatedDialog(QtWidgets.QDialog):
    def __init__(self, main, parent):
        QtWidgets.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/update_info.ui')
        self.main = main
        self.info_text.document().setIndentWidth(20)
        self.css_base = '''
                        .version {
                                font-size: xx-large; margin-left: .5em; font-weight: bold;
                            } 
                        .release {
                                margin-left: 1.5em; margin-top: .5em;
                            } 
                        .content {
                                margin-left: .3em; margin-top: .8em; margin-bottom: .8em;
                            }
                   '''

    def exec_(self, content):
        self.info_text.document().setDefaultStyleSheet(self.css_base)
        self.info_text.clear()
        self.info_text.append('<a name="top"></a>')
        self.info_text.moveCursor(self.info_text.textCursor().End)
        self.info_text.insertHtml(content)
        self.info_text.scrollToAnchor('top')
        QtWidgets.QDialog.exec_(self)


