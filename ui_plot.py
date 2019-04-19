# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_plot.ui'
#
# Created: Wed May 08 10:02:53 2013
#      by: PyQt4 UI code generator 4.9.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_win_plot(object):
    def setupUi(self, win_plot):
        win_plot.setObjectName(_fromUtf8("win_plot"))
        win_plot.resize(300, 80)
        self.centralwidget = QtGui.QWidget(win_plot)
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.bpmButton = QtGui.QPushButton(self.centralwidget)
        self.bpmButton.setObjectName(_fromUtf8("btnD"))
        self.bpmButton.setStyleSheet("background-color: red")
        self.verticalLayout.addWidget(self.bpmButton)
        win_plot.setCentralWidget(self.centralwidget)
        self.retranslateUi(win_plot)
        QtCore.QMetaObject.connectSlotsByName(win_plot)

    def retranslateUi(self, win_plot):
        win_plot.setWindowTitle(QtGui.QApplication.translate("win_plot", "Beat Detector", None, QtGui.QApplication.UnicodeUTF8))
        self.bpmButton.setText(QtGui.QApplication.translate("win_plot", "BPM", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import Qwt5

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    win_plot = QtGui.QMainWindow()
    ui = Ui_win_plot()
    ui.setupUi(win_plot)
    win_plot.show()
    sys.exit(app.exec_())

