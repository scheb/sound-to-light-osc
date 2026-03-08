from PyQt5.QtCore import QTimer
from PyQt5 import QtCore

from recorder import *
from time import perf_counter

class AudioAnalyzer:
    input_recorder: InputRecorder

    # Timing
    current_time: float

    def __init__(self, input_recorder):
        self.input_recorder = input_recorder
        self.current_intensity = 0
        self.callback_beat_detected = lambda: None
        self.callback_new_song = lambda: None
        self.callback_pause = lambda: None
        self.callback_intensity_changed = lambda: None
        self.prev_volume_track_time = 0
        self.volume_long_history = []

    def analyze_audio(self):
        if not self.input_recorder.has_new_audio:
            return

        self.current_time = perf_counter()

        # Get x and y values from FFT
        xs, ys = self.input_recorder.fft()
        self.input_recorder.has_new_audio = False

        # TODO: Implement beat detection

    def on_beat_detected(self, callback):
        self.callback_beat_detected = callback

    def on_new_song_detected(self, callback):
        self.callback_new_song = callback

    def on_pause(self, callback):
        self.callback_pause = callback

    def on_intensity_changed(self, callback):
        self.callback_intensity_changed = callback


class SignalGenerator:
    bar_modulo: int
    beat_index: int
    bpm: int
    auto_generating = False
    timer: QTimer
    last_beats: list
    last_beat_time: float
    intensity: int

    def __init__(self, audio_analyzer) -> None:
        self.reset_tracking()

        self.callback_beat = lambda: None
        self.callback_bar = lambda: None
        self.callback_new_song = lambda: None
        self.callback_bpm_change = lambda: None
        self.callback_intensity_change = lambda: None

        # Wire up detection events
        audio_analyzer.on_beat_detected(self.track_beat)
        audio_analyzer.on_new_song_detected(self.track_new_song)
        audio_analyzer.on_pause(self.track_pause)
        audio_analyzer.on_intensity_changed(self.track_intensity_change)

    def reset_tracking(self):
        self.bar_modulo = 2
        self.beat_index = -1
        self.auto_generating = False
        self.bpm = 0
        self.intensity = 0
        self.last_beat_time = 0
        self.last_beats = []  # Sliding window of the last 4 beats

    def reset_beat_index(self):
        self.beat_index = -1

    def recalculate_bar_modulo(self):
        # Bar modulo based on intensity
        modulo = 2
        if self.intensity == 1:
            modulo = 1
        if self.intensity == -1:
            modulo = 4

        # Additional modifier based in BPM
        if self.bpm > 0:
            if self.bpm < 100:
                modulo /= 2
            # if self.bpm > 155:
            #     modulo *= 2

        self.bar_modulo = numpy.max([1, modulo])  # Must be at least 1
        print("Bar modulo: {:.0f}".format(self.bar_modulo))

    def track_beat(self, beat_time, bpm):
        bpm_changed = False

        if abs(bpm - self.bpm) > 1:
            print("BPM changed {:d} -> {:d}".format(int(self.bpm), int(bpm)))
            self.bpm = bpm
            self.recalculate_bar_modulo()
            self.callback_bpm_change(bpm)
            bpm_changed = True

        if self.auto_generating:
            if bpm_changed:
                print("Sync auto generated beat")
                self.timer.stop()
                self.generate_beat_signal(beat_time=beat_time)
        else:
            if bpm_changed and self.can_auto_generate():
                print("Start auto generating beat with {:d} BPM".format(int(self.bpm)))
                self.auto_generating = True
            self.generate_beat_signal(beat_time=beat_time)

    def can_auto_generate(self):
        # return False  # Disabled auto beat generation
        if self.bpm > 0 and len(self.last_beats) >= 8:
            oldest_beat = numpy.min(self.last_beats)
            newest_beat = numpy.min(self.last_beats)
            max_difference = 60 / self.bpm * 16  # 8 beats max

            # We have to see at least half of the expected beats to start auto generating
            return newest_beat - oldest_beat < max_difference
        return False

    def generate_beat_signal(self, beat_time=None):
        if beat_time is None:
            beat_time = perf_counter()

        # Protect against too many beat signals at once
        if beat_time - self.last_beat_time > 0.333:
            self.last_beats.append(beat_time)
            if len(self.last_beats) > 8:  # Keep the last 8 beats
                self.last_beats = self.last_beats[1:]
            self.last_beat_time = beat_time
            self.beat_index += 1

            beat_index_mod = self.beat_index % (self.bar_modulo * 2)
            if self.beat_index % 2 == 0:
                self.callback_beat(int(beat_index_mod / 2))
            if beat_index_mod == 0:
                self.callback_bar()

        if self.auto_generating:
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.generate_beat_signal)
            time_passed = int((perf_counter() - beat_time) * 1000)  # Take code execution time into account
            timeout = int(60000 / self.bpm) - time_passed
            self.timer.start(timeout)

    def track_new_song(self):
        self.callback_new_song()
        self.callback_intensity_change(0)
        self.reset_tracking()

    def track_pause(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.auto_generating = False
        self.reset_beat_index()

    def track_intensity_change(self, intensity):
        self.intensity = intensity
        self.recalculate_bar_modulo()
        self.callback_intensity_change(intensity)

    def on_beat(self, callback):
        self.callback_beat = callback

    def on_bar(self, callback):
        self.callback_bar = callback

    def on_new_song(self, callback):
        self.callback_new_song = callback

    def on_bpm_change(self, callback):
        self.callback_bpm_change = callback

    def on_intensity_change(self, callback):
        self.callback_intensity_change = callback
