from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel


class UserInterface(object):
    auto_prog_button: QPushButton
    intensity_label: QLabel
    beat_label: QLabel
    bar_label: QLabel
    colorsList = ["#a9a9a9", "#f58231", "#ffe119", "#bfef45", "#3cb44b", "#42d4f4", "#4363d8", "#f032e6"]
    beat_color_index = 0
    bar_color_index = 0

    def __init__(self, auto_prog_callback, callback_input_changed):
        self.callback_auto_prog_clicked = auto_prog_callback
        self.callback_input_changed = callback_input_changed

    def setup_ui(self, win_plot):
        win_plot.setObjectName("win_plot")
        win_plot.resize(300, 80)
        central_widget = QtWidgets.QWidget(win_plot)
        vertical_layout = QtWidgets.QVBoxLayout(central_widget)

        input_widget = QtWidgets.QWidget(win_plot)
        input_widget.setFixedHeight(95)
        vertical_layout_input = QtWidgets.QVBoxLayout(input_widget)

        self.input_label = QtWidgets.QLabel(central_widget)

        self.input_combobox = QtWidgets.QComboBox(central_widget)
        self.input_combobox.setStyleSheet("background-color: #a9a9a9; font-size: 15pt; selection-background-color: transparent; selection-color: black")
        self.input_combobox.setObjectName("auto_prog_button")
        self.input_combobox.activated.connect(self.callback_input_changed)

        self.input_intensity = QtWidgets.QProgressBar(central_widget)
        self.input_intensity.setStyleSheet("QProgressBar { border: 2px solid grey; border-radius: 0px; text-align: center; } QProgressBar::chunk {background-color: #3add36; width: 1px;}")
        self.input_intensity.setTextVisible(False)
        self.input_intensity.setFixedHeight(15)
        self.input_intensity.setValue(0)

        vertical_layout_input.addWidget(self.input_label)
        vertical_layout_input.addWidget(self.input_combobox)
        vertical_layout_input.addWidget(self.input_intensity)
        vertical_layout.addWidget(input_widget)

        self.auto_prog_button = QtWidgets.QPushButton(central_widget)
        self.auto_prog_button.setObjectName("auto_prog_button")
        self.auto_prog_button.setStyleSheet("background-color: red; font-size: 18pt")
        self.auto_prog_button.clicked.connect(self.callback_auto_prog_clicked)
        vertical_layout.addWidget(self.auto_prog_button)

        self.intensity_label = QtWidgets.QLabel(central_widget)
        self.intensity_label.setObjectName("lbl_intensity")
        self.intensity_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: #a9a9a9; font-size: 18pt")
        vertical_layout.addWidget(self.intensity_label)

        self.beat_label = QtWidgets.QLabel(central_widget)
        self.beat_label.setObjectName("lbl_beat")
        self.beat_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: #a9a9a9; font-size: 18pt")
        vertical_layout.addWidget(self.beat_label)

        self.bar_label = QtWidgets.QLabel(central_widget)
        self.bar_label.setObjectName("lbl_bar")
        self.bar_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: #a9a9a9; font-size: 18pt")
        vertical_layout.addWidget(self.bar_label)

        win_plot.setCentralWidget(central_widget)
        self.translate_ui(win_plot)
        QtCore.QMetaObject.connectSlotsByName(win_plot)

    def translate_ui(self, win_plot):
        win_plot.setWindowTitle(QtWidgets.QApplication.translate("win_plot", "Beat Detector", None))
        self.auto_prog_button.setText(QtWidgets.QApplication.translate("win_plot", "Auto Prog OFF", None))
        self.intensity_label.setText(QtWidgets.QApplication.translate("win_plot", "Intensity", None))
        self.beat_label.setText(QtWidgets.QApplication.translate("win_plot", "Beat", None))
        self.bar_label.setText(QtWidgets.QApplication.translate("win_plot", "BPM", None))
        self.input_label.setText(QtWidgets.QApplication.translate("win_plot", "Audio Source", None))

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
        self.beat_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: {:s}; font-size: 18pt".format(color))

    def change_bar_button_color(self):
        self.bar_color_index += 1
        color = self.colorsList[self.bar_color_index % len(self.colorsList)]
        self.bar_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: {:s}; font-size: 18pt".format(color))

    def display_intensity(self, intensity):
        if intensity == 1:
            intensity_label = "Intense"
        elif intensity == 0:
            intensity_label = "Normal"
        else:
            intensity_label = "Calm"
        self.intensity_label.setText(intensity_label)

    def display_beat_index(self, beat_index):
        self.beat_label.setText("Beat: {:d}".format(beat_index))

    def display_bpm(self, bpm):
        self.bar_label.setText("BPM: {:d}".format(int(bpm)))

    def display_new_song(self):
        self.beat_label.setText("Beat")
        self.bar_label.setText("BPM: New song")

    def add_audio_source(self, text):
        self.input_combobox.addItem(text)

    def select_audio_source(self, index):
        self.input_combobox.setCurrentIndex(index)

    def display_input_intensity(self, level):
        self.input_intensity.setValue(level)
