from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QPushButton

class UserInterface(object):
    auto_prog_button: QPushButton
    beat_button: QPushButton
    bar_button: QPushButton
    colorsList = ["#a9a9a9", "#f58231", "#ffe119", "#bfef45", "#3cb44b", "#42d4f4", "#4363d8", "#f032e6"]
    beat_color_index = 0
    bar_color_index = 0

    def __init__(self, auto_prog_callback):
        self.callback_auto_prog_clicked = auto_prog_callback

    def setup_ui(self, win_plot):
        win_plot.setObjectName("win_plot")
        win_plot.resize(300, 80)
        central_widget = QtGui.QWidget(win_plot)
        vertical_layout = QtGui.QVBoxLayout(central_widget)

        self.auto_prog_button = QtGui.QPushButton(central_widget)
        self.auto_prog_button.setObjectName("auto_prog_button")
        self.auto_prog_button.setStyleSheet("background-color: red; font-size: 18pt")
        self.auto_prog_button.clicked.connect(self.callback_auto_prog_clicked)
        vertical_layout.addWidget(self.auto_prog_button)

        self.beat_button = QtGui.QPushButton(central_widget)
        self.beat_button.setObjectName("btn_beat")
        self.beat_button.setStyleSheet("background-color: red; font-size: 18pt")
        vertical_layout.addWidget(self.beat_button)

        self.bar_button = QtGui.QPushButton(central_widget)
        self.bar_button.setObjectName("btn_bar")
        self.bar_button.setStyleSheet("background-color: red; font-size: 18pt")
        vertical_layout.addWidget(self.bar_button)

        win_plot.setCentralWidget(central_widget)
        self.translate_ui(win_plot)
        QtCore.QMetaObject.connectSlotsByName(win_plot)

    def translate_ui(self, win_plot):
        win_plot.setWindowTitle(QtGui.QApplication.translate("win_plot", "Beat Detector", None, QtGui.QApplication.UnicodeUTF8))
        self.auto_prog_button.setText(QtGui.QApplication.translate("win_plot", "Auto Prog OFF", None, QtGui.QApplication.UnicodeUTF8))
        self.beat_button.setText(QtGui.QApplication.translate("win_plot", "Beat", None, QtGui.QApplication.UnicodeUTF8))
        self.bar_button.setText(QtGui.QApplication.translate("win_plot", "BPM", None, QtGui.QApplication.UnicodeUTF8))

    def change_auto_prog_state(self, enabled):
        if enabled:
            self.auto_prog_button.setText("Auto Prog ON")
            self.auto_prog_button.setStyleSheet("background-color: green; font-size: 18pt")
        else:
            self.auto_prog_button.setText("Auto Prog OFF")
            self.auto_prog_button.setStyleSheet("background-color: red; font-size: 18pt")

    def change_beat_button_color(self):
        self.beat_color_index += 1
        color = self.colorsList[self.beat_color_index % len(self.colorsList)]
        self.beat_button.setStyleSheet("background-color: {:s}; font-size: 18pt".format(color))

    def change_bar_button_color(self):
        self.bar_color_index += 1
        color = self.colorsList[self.bar_color_index % len(self.colorsList)]
        self.bar_button.setStyleSheet("background-color: {:s}; font-size: 18pt".format(color))

    def display_beat_index(self, beat_index):
        self.beat_button.setText("Beat: {:d}".format(beat_index))

    def display_bpm(self, bpm):
        self.bar_button.setText("BPM: {:d}".format(int(bpm)))

    def display_new_song(self):
        self.beat_button.setText("Beat")
        self.bar_button.setText("BPM: New song")
