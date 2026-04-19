import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel

from analyzer import SpectralFluxIntensityDetector


class UserInterface(object):
    auto_prog_button: QPushButton
    intensity_label: QLabel
    beat_label: QLabel
    bar_label: QLabel
    colorsList = [("#ffffff", "#000000"), ("#000000", "#ffffff")]
    beat_color_index = 0
    bar_color_index = 0
    chart_x_size = 200
    beat_chart_y_size = 2000
    intensity_chart_y_size = 1500

    def __init__(self, auto_prog_callback, callback_input_changed):
        self.callback_auto_prog_clicked = auto_prog_callback
        self.callback_input_changed = callback_input_changed
        self.beat_flux_data = np.zeros(self.chart_x_size)
        self.beat_threshold_data = np.zeros(self.chart_x_size)
        self.beat_data = np.zeros(self.chart_x_size)
        self.intensity_flux_data = np.zeros(self.chart_x_size)
        self.intensity_threshold_data = np.zeros(self.chart_x_size)
        self.intensity_change_data = np.zeros(self.chart_x_size)

    def setup_ui(self, win_plot):
        win_plot.setObjectName("win_plot")
        win_plot.resize(400, 400)
        central_widget = QtWidgets.QWidget(win_plot)
        vertical_layout = QtWidgets.QVBoxLayout(central_widget)

        # Plot Widget for Beat Detection Visualization
        self.beat_plot = pg.PlotWidget(central_widget)
        self.beat_plot.setBackground('k')
        self.beat_plot.setYRange(0, self.beat_chart_y_size)
        self.beat_plot.setXRange(0, self.chart_x_size)
        self.beat_plot.hideAxis('bottom')
        self.beat_plot.setFixedHeight(150)
        self.beat_curve = self.beat_plot.plot(pen=pg.mkPen('r', width=1))
        self.beat_flux_curve = self.beat_plot.plot(pen=pg.mkPen('c', width=1))
        self.beat_threshold_curve = self.beat_plot.plot(pen=pg.mkPen('y', width=1))
        vertical_layout.addWidget(self.beat_plot)

        self.beat_label = QtWidgets.QLabel(central_widget)
        self.beat_label.setObjectName("lbl_beat")
        self.beat_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: #a9a9a9; font-size: 18pt")
        vertical_layout.addWidget(self.beat_label)

        # Plot Widget for Intensity Visualization
        self.intensity_plot = pg.PlotWidget(central_widget)
        self.intensity_plot.setBackground('k')
        self.intensity_plot.setYRange(0, self.intensity_chart_y_size)
        self.intensity_plot.setXRange(0, self.chart_x_size)
        self.intensity_plot.hideAxis('bottom')
        self.intensity_plot.setFixedHeight(150)
        self.intensity_change_curve = self.intensity_plot.plot(pen=pg.mkPen('r', width=1))
        self.intensity_flux_curve = self.intensity_plot.plot(pen=pg.mkPen('c', width=1))
        self.intensity_threshold_curve = self.intensity_plot.plot(pen=pg.mkPen('y', width=1))
        self.intensity_threshold_high_curve = self.intensity_plot.plot(pen=pg.mkPen('#ffff0070', width=1))
        self.intensity_threshold_low_curve = self.intensity_plot.plot(pen=pg.mkPen('#ffff0070', width=1))
        vertical_layout.addWidget(self.intensity_plot)

        input_widget = QtWidgets.QWidget(win_plot)
        vertical_layout_input = QtWidgets.QVBoxLayout(input_widget)

        self.input_label = QtWidgets.QLabel(central_widget)

        self.input_combobox = QtWidgets.QComboBox(central_widget)
        self.input_combobox.setStyleSheet("background-color: #a9a9a9; font-size: 15pt; selection-background-color: transparent; selection-color: black")
        self.input_combobox.setObjectName("auto_prog_button")
        self.input_combobox.activated.connect(self.callback_input_changed)

        vertical_layout_input.addWidget(self.input_label)
        vertical_layout_input.addWidget(self.input_combobox)
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
        (bgColor, fontColor) = self.colorsList[self.beat_color_index % len(self.colorsList)]
        self.beat_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: {:s}; font-size: 18pt; color: {:s}".format(bgColor, fontColor))

    def change_bar_button_color(self):
        self.bar_color_index += 1
        (bgColor, fontColor) = self.colorsList[self.bar_color_index % len(self.colorsList)]
        self.bar_label.setStyleSheet("padding: 5px; qproperty-alignment: AlignCenter; background-color: {:s}; font-size: 18pt; color: {:s}".format(bgColor, fontColor))

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
        self.beat_label.setText("Beat: New song")

    def display_pause(self):
        self.beat_label.setText("Beat: Pause")

    def add_audio_source(self, text):
        self.input_combobox.addItem(text)

    def select_audio_source(self, index):
        self.input_combobox.setCurrentIndex(index)

    def update_beat_plot(self, flux, threshold, is_beat):
        self.beat_flux_data = np.roll(self.beat_flux_data, -1)
        self.beat_flux_data[-1] = flux
        self.beat_threshold_data = np.roll(self.beat_threshold_data, -1)
        self.beat_threshold_data[-1] = threshold
        self.beat_data = np.roll(self.beat_data, -1)
        self.beat_data[-1] = self.beat_chart_y_size*2 if is_beat else 0

        self.beat_flux_curve.setData(self.beat_flux_data)
        self.beat_threshold_curve.setData(self.beat_threshold_data)
        self.beat_curve.setData(self.beat_data)

    def update_intensity_plot(self, flux, threshold, is_change):
        self.intensity_flux_data = np.roll(self.intensity_flux_data, -1)
        self.intensity_flux_data[-1] = flux
        self.intensity_threshold_data = np.roll(self.intensity_threshold_data, -1)
        self.intensity_threshold_data[-1] = threshold
        self.intensity_change_data = np.roll(self.intensity_change_data, -1)
        self.intensity_change_data[-1] = self.intensity_chart_y_size*2 if is_change else 0

        self.intensity_flux_curve.setData(self.intensity_flux_data)
        self.intensity_threshold_curve.setData(self.intensity_threshold_data)
        self.intensity_threshold_high_curve.setData(self.intensity_threshold_data * SpectralFluxIntensityDetector.UPPER_THRESHOLD_MULTIPLIER)
        self.intensity_threshold_low_curve.setData(self.intensity_threshold_data * SpectralFluxIntensityDetector.LOWER_THRESHOLD_MULTIPLIER)
        self.intensity_change_curve.setData(self.intensity_change_data)
