import ui
import sys
from PyQt4 import QtCore, QtGui
from recorder import *
from time import perf_counter
from pythonosc import udp_client

class AudioAnalyzer:
    min_bpm = 60
    max_bpm = 180
    input_recorder: InputRecorder

    # Timing
    current_time: float
    prev_beat_time: float

    # BPM
    current_bpm: int
    bpm_history: list

    # Intensity over time
    y_avg_history: list
    low_freq_avg_history: list

    def __init__(self, input_recorder):
        self.input_recorder = input_recorder
        self.reset_tracking()
        self.callback_beat_detected = lambda: None
        self.callback_bpm_changed = lambda: None
        self.callback_new_song = lambda: None

    def reset_tracking(self):
        self.current_bpm = 0
        self.prev_beat_time = perf_counter()
        self.bpm_history = []
        self.y_avg_history = []
        self.low_freq_avg_history = []

    def analyze_audio(self):
        if not self.input_recorder.has_new_audio:
            return

        # Get x and y values from FFT
        xs, ys = self.input_recorder.fft()

        # Calculate average for all frequency ranges
        y_avg = numpy.mean(ys)
        self.y_avg_history.append(y_avg)

        # Calculate low frequency average
        low_freq = [ys[i] for i in range(len(xs)) if xs[i] < 500]
        low_freq_avg = numpy.mean(low_freq)

        # Calculate recent low frequency average
        self.low_freq_avg_history.append(low_freq_avg)
        recent_low_freq_avg = numpy.mean(self.low_freq_avg_history)

        # Calculate bass frequency average
        bass = low_freq[:int(len(low_freq) / 2)]
        bass_avg = numpy.mean(bass)
        # print("bass: {:.2f} vs cumulative: {:.2f}".format(bass_avg, cumulative_avg))

        # Check if there is a beat
        if (y_avg > 1000  # Minimum intensity
            and (
                bass_avg > recent_low_freq_avg * 1.5 # Significantly more bass than before
                or (
                    low_freq_avg < y_avg * 1.2 #
                    and bass_avg > recent_low_freq_avg
                )
            )
        ):
            self.current_time = perf_counter()
            # print(self.curr_time - self.prev_beat)
            time_since_last_beat = self.current_time - self.prev_beat_time
            if (time_since_last_beat > 60 / self.max_bpm):
                self.detect_beat()
                self.detect_bpm(time_since_last_beat)
                self.prev_beat_time = self.current_time

        # Reset tracking if the song has stopped
        y_avg_mean = numpy.mean(self.y_avg_history)
        # print(y_avg, y_avg_mean)
        if y_avg < 100 or y_avg < y_avg_mean / 50:
            self.detect_new_song()

        self.housekeeping()

    def housekeeping(self):
        # Shorten the cumulative list to account for changes in dynamics
        if len(self.low_freq_avg_history) > 50:
            self.low_freq_avg_history = self.low_freq_avg_history[25:]

        # Shorten avg list
        if len(self.y_avg_history) > 24:
            self.y_avg_history = self.y_avg_history[24:]

        # Keep two 8-counts of BPMs so we can maybe catch tempo changes
        if len(self.bpm_history) > 24:
            self.bpm_history = self.bpm_history[8:]

    def detect_beat(self):
        # print("detect beat")
        self.callback_beat_detected()

    def detect_new_song(self):
        # print("detect new song")
        self.reset_tracking()
        self.callback_new_song()

    def detect_bpm(self, time_since_last_beat):
        # print("detect bpm")
        bpm_detected = int(60 / time_since_last_beat)
        if len(self.bpm_history) < 4:
            if bpm_detected > self.min_bpm:
                self.bpm_history.append(bpm_detected)
        else:
            # bpm_avg = int(numpy.mean(self.bpm_history))
            if (self.current_bpm == 0 or abs(self.current_bpm - bpm_detected) < 35):
                self.bpm_history.append(bpm_detected)
                # Recalculate with the new BPM value included
                self.current_bpm = int(numpy.mean(self.bpm_history))
                self.callback_bpm_changed(self.current_bpm)

    def on_beat_detected(self, callback):
        self.callback_beat_detected = callback

    def on_new_song_detected(self, callback):
        self.callback_new_song = callback

    def on_bpm_changed(self, callback):
        self.callback_bpm_changed = callback


class SignalGenerator:
    bar_modulo: int
    beat_index: int
    bpm: int

    def __init__(self, audio_analyzer, bar_modulo) -> None:
        self.bar_modulo = bar_modulo
        self.reset_tracking()

        self.callback_beat = lambda : None
        self.callback_bar = lambda : None
        self.callback_new_song = lambda : None
        self.callback_bpm_change = lambda : None

        # Wire up detection events
        audio_analyzer.on_beat_detected(self.track_beat)
        audio_analyzer.on_new_song_detected(self.track_new_song)
        audio_analyzer.on_bpm_changed(self.track_bpm_changed)

    def reset_tracking(self):
        self.beat_index = self.bar_modulo - 1
        self.bpm = 0

    def track_beat(self):
        self.beat_index += 1
        beat_index_mod = self.beat_index % self.bar_modulo
        self.callback_beat(beat_index_mod)
        if (beat_index_mod == 0):
            self.callback_bar()

    def track_new_song(self):
        self.callback_new_song()
        self.reset_tracking()

    def track_bpm_changed(self, bpm):
        self.bpm = bpm
        self.callback_bpm_change(bpm)

    def on_beat(self, callback):
        self.callback_beat = callback

    def on_bar(self, callback):
        self.callback_bar = callback

    def on_new_song(self, callback):
        self.callback_new_song = callback

    def on_bpm_change(self, callback):
        self.callback_bpm_change = callback
