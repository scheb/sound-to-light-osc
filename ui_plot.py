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


class UserInterface(object):
    def setupUi(self, win_plot, on_beat_button_click, on_bar_button_click):
        win_plot.setObjectName(_fromUtf8("win_plot"))
        win_plot.resize(300, 80)
        self.centralwidget = QtGui.QWidget(win_plot)
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)

        self.beatButton = QtGui.QPushButton(self.centralwidget)
        self.beatButton.setObjectName(_fromUtf8("btnBeat"))
        self.beatButton.setStyleSheet("background-color: red; font-size: 18pt")
        self.beatButton.clicked.connect(on_beat_button_click)
        self.verticalLayout.addWidget(self.beatButton)

        self.barButton = QtGui.QPushButton(self.centralwidget)
        self.barButton.setObjectName(_fromUtf8("btnBar"))
        self.barButton.setStyleSheet("background-color: red; font-size: 18pt")
        self.barButton.clicked.connect(on_bar_button_click)
        self.verticalLayout.addWidget(self.barButton)

        win_plot.setCentralWidget(self.centralwidget)
        self.retranslateUi(win_plot)
        QtCore.QMetaObject.connectSlotsByName(win_plot)

    def retranslateUi(self, win_plot):
        win_plot.setWindowTitle(QtGui.QApplication.translate("win_plot", "Beat Detector", None, QtGui.QApplication.UnicodeUTF8))
        self.beatButton.setText(QtGui.QApplication.translate("win_plot", "Beat", None, QtGui.QApplication.UnicodeUTF8))
        self.barButton.setText(QtGui.QApplication.translate("win_plot", "BPM", None, QtGui.QApplication.UnicodeUTF8))
