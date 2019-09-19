import random

import osc
import ui
import sys
from PyQt4 import QtCore, QtGui
from bpm import SignalGenerator, AudioAnalyzer
from recorder import *


class BeatDetector:
    ui: ui.UserInterface
    osc_client: osc.OscClient
    input_recorder: InputRecorder
    timer_period = 1000 / (180 / 60) / 16  # 180bpm / 16

    max_program_beats = 8 * 4
    current_intensity = 0
    current_program = 0
    current_program_beats = 0
    change_program = False
    calm_programs = [
        2,  # Full Color Slow
        5,  # Retro
        8,  # Wipe Noise
    ]
    normal_programs = [
        1,  # Full Color Moving
        3,  # Fill Up Once
        6,  # Kitt
    ]
    intense_programs = [
        4,  # Fill Up Repeat
        7,  # Flash Noise
    ]

    def __init__(self, window) -> None:
        self.ui = ui.UserInterface(self.on_auto_prog_button_clicked)
        self.ui.setup_ui(window)
        self.osc_client = osc.OscClient("localhost", 7701)
        self.auto_prog = False

        # Wire up beat detector and signal generation
        self.input_recorder = InputRecorder()
        self.audio_analyzer = AudioAnalyzer(self.input_recorder)
        signal_generator = SignalGenerator(self.audio_analyzer)

        # Wire up callbacks
        signal_generator.on_beat(self.on_beat)
        signal_generator.on_bar(self.on_bar)
        signal_generator.on_new_song(self.on_new_song)
        signal_generator.on_bpm_change(self.on_bpm_change)
        signal_generator.on_intensity_change(self.on_intensity_change)

        # Start beat detection
        self.timer = QtCore.QTimer()
        self.timer.start(self.timer_period)

        window.connect(self.timer, QtCore.SIGNAL('timeout()'), self.audio_analyzer.analyze_audio)
        self.input_recorder.start()

    def change_program_if_needed(self):
        if self.change_program:
            new_program = self.choose_program_by_intensity()
            if new_program != self.current_program:
                print("Change program to {:d} for intensity {:d}".format(new_program, self.current_intensity))
                self.current_program = new_program
                self.osc_client.send_prog_signal(new_program)
            self.current_program_beats = 0
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

    def on_beat(self, beat_index):
        # print("beat")
        self.osc_client.send_beat_signal()
        self.ui.change_beat_button_color()
        self.ui.display_beat_index(beat_index + 1)  # Starts with 0

        # Keep track how long current program is running
        if self.auto_prog:
            self.current_program_beats += 1
            if self.current_program_beats > self.max_program_beats:
                self.change_program = True

    def on_bar(self):
        # print("bar")
        self.change_program_if_needed()
        self.osc_client.send_bar_signal()
        self.ui.change_bar_button_color()

    def on_new_song(self):
        # print("next song")
        self.change_program = True
        self.ui.display_new_song()

    def on_bpm_change(self, bpm):
        # print("bpm changed")
        self.ui.display_bpm(bpm)

    def on_intensity_change(self, intensity):
        self.current_intensity = intensity
        if self.auto_prog:
            self.change_program = True
        self.ui.display_intensity(intensity)

    def close(self):
        self.input_recorder.close()


if __name__ == "__main__":
    # Setup UI
    app = QtGui.QApplication(sys.argv)
    window = ui.QtGui.QMainWindow()

    # Start beat tracking
    beat_detector = BeatDetector(window)

    # Display window
    window.show()
    code = app.exec_()

    # Clean up
    beat_detector.close()
    sys.exit(code)
