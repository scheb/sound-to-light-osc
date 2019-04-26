from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QPushButton

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


class UserInterface(object):
    beat_button: QPushButton
    colorsList = ["red", "yellow", "green", "orange", "white", "cyan"]
    beat_color_index = 0
    bar_color_index = 0

    def setup_ui(self, win_plot):
        win_plot.setObjectName(_fromUtf8("win_plot"))
        win_plot.resize(300, 80)
        central_widget = QtGui.QWidget(win_plot)
        vertical_layout = QtGui.QVBoxLayout(central_widget)

        self.beat_button = QtGui.QPushButton(central_widget)
        self.beat_button.setObjectName(_fromUtf8("btn_beat"))
        self.beat_button.setStyleSheet("background-color: red; font-size: 18pt")
        vertical_layout.addWidget(self.beat_button)

        self.bar_button = QtGui.QPushButton(central_widget)
        self.bar_button.setObjectName(_fromUtf8("btn_bar"))
        self.bar_button.setStyleSheet("background-color: red; font-size: 18pt")
        vertical_layout.addWidget(self.bar_button)

        win_plot.setCentralWidget(central_widget)
        self.translate_ui(win_plot)
        QtCore.QMetaObject.connectSlotsByName(win_plot)

    def translate_ui(self, win_plot):
        win_plot.setWindowTitle(QtGui.QApplication.translate("win_plot", "Beat Detector", None, QtGui.QApplication.UnicodeUTF8))
        self.beat_button.setText(QtGui.QApplication.translate("win_plot", "Beat", None, QtGui.QApplication.UnicodeUTF8))
        self.bar_button.setText(QtGui.QApplication.translate("win_plot", "BPM", None, QtGui.QApplication.UnicodeUTF8))

    def change_beat_button_color(self):
        self.beat_color_index += 1
        color = self.colorsList[self.beat_color_index % len(self.colorsList)]
        self.beat_button.setStyleSheet("background-color: {:s}; font-size: 18pt".format(color))

    def change_bar_button_color(self):
        self.bar_color_index += 1
        color = self.colorsList[self.bar_color_index % len(self.colorsList)]
        self.bar_button.setStyleSheet("background-color: {:s}; font-size: 18pt".format(color))

    def display_beat_index(self, beat_index):
        self.beat_button.setText(_fromUtf8("Beat: {:d}".format(beat_index)))

    def display_bpm(self, bpm):
        self.bar_button.setText(_fromUtf8("BPM: {:d}".format(int(bpm))))

    def display_new_song(self):
        self.beat_button.setText(_fromUtf8("Beat"))
        self.bar_button.setText(_fromUtf8("BPM: New song"))
