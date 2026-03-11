import random
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot

import osc
import ui
from analyzer import SignalGenerator, AudioAnalyzer
from recorder import *


class BeatDetector(QtCore.QObject):
    def __init__(self, window) -> None:
        super().__init__()
        self.ui = ui.UserInterface(self.on_auto_prog_button_clicked, self.on_input_changed)
        self.ui.setup_ui(window)
        self.osc_client = osc.OscClient("localhost", 7701)
        self.auto_prog = False

        self.input_recorder = InputRecorder(self)
        self.audio_analyzer = AudioAnalyzer(self.input_recorder)
        self.signal_generator = SignalGenerator()

        self.setup_signal_connections()

        self.timer = QtCore.QTimer()
        self.timer.start(int(round(20)))  # 20ms
        self.timer.timeout.connect(self.audio_analyzer.analyze_audio)
        self.input_recorder.start()

        self.min_program_beats = 8
        self.max_program_beats = 8 * 4
        self.current_intensity = 0
        self.current_program = 0
        self.current_program_beats = 0
        self.change_program = False
        self.calm_programs = [2, 5, 8]
        self.normal_programs = [1, 3, 6]
        self.intense_programs = [4, 7]

    def setup_signal_connections(self):
        # Connect analysis components to signal generator
        self.audio_analyzer.beat_detector.beat_detected.connect(self.signal_generator.track_beat)
        self.audio_analyzer.intensity_detector.pause_detected.connect(self.signal_generator.track_pause)
        self.audio_analyzer.intensity_detector.intensity_changed.connect(self.signal_generator.track_intensity_change)

        # Connect signal generator to UI and OSC
        self.signal_generator.beat_signal.connect(self.on_beat)
        self.signal_generator.bar_detected.connect(self.on_bar)
        self.signal_generator.bpm_changed.connect(self.on_bpm_change)

        # Connect new song detector to UI
        self.audio_analyzer.new_song_detector.new_song_detected.connect(self.on_new_song)

        # Connect intensity directly to the UI
        self.audio_analyzer.intensity_detector.intensity_changed.connect(self.on_intensity_change)

        # Connect VU meter to UI
        self.audio_analyzer.vu_meter.vu_level_changed.connect(self.ui.display_input_intensity)

    def change_program_if_needed(self):
        if self.change_program and self.current_program_beats >= self.min_program_beats:
            new_program = self.choose_program_by_intensity()
            if new_program != self.current_program:
                # print("Change program to {:d} for intensity {:d}".format(new_program, self.current_intensity))
                self.current_program = new_program
                self.osc_client.send_prog_signal(new_program)
            self.current_program_beats = 1
            self.change_program = False

    def choose_program_by_intensity(self):
        if self.current_intensity == 1:
            program_list = self.intense_programs
        elif self.current_intensity == -1:
            program_list = self.calm_programs
        else:
            program_list = self.normal_programs
        return random.choice(program_list)

    def on_auto_prog_button_clicked(self):
        self.auto_prog = not self.auto_prog
        self.current_program = 0
        self.current_program_beats = 0
        if self.auto_prog:
            self.change_program = True
        self.ui.change_auto_prog_state(self.auto_prog)

    def on_input_changed(self, index):
        self.input_recorder.change_input(index)

    @pyqtSlot(int)
    def on_beat(self, beat_index):
        self.osc_client.send_beat_signal()
        self.ui.change_beat_button_color()
        self.ui.display_beat_index(beat_index + 1)

        if self.auto_prog:
            self.current_program_beats += 1
            if self.current_program_beats > self.max_program_beats:
                self.change_program = True

    @pyqtSlot()
    def on_bar(self):
        self.change_program_if_needed()
        self.osc_client.send_bar_signal()
        self.ui.change_bar_button_color()

    @pyqtSlot()
    def on_new_song(self):
        self.change_program = True
        self.ui.display_new_song()

    @pyqtSlot(int)
    def on_bpm_change(self, bpm):
        self.ui.display_bpm(bpm)

    @pyqtSlot(int)
    def on_intensity_change(self, intensity):
        self.current_intensity = intensity
        if self.auto_prog:
            self.change_program = True
        self.ui.display_intensity(intensity)

    def close(self):
        self.input_recorder.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    beat_detector = BeatDetector(window)
    window.show()
    code = app.exec_()
    beat_detector.close()
    sys.exit(code)
