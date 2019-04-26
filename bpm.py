from PyQt4.QtCore import QTimer
from PyQt4 import QtCore
from recorder import *
from time import perf_counter

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
    pause_count = 0
    y_avg_history: list
    low_freq_avg_history: list
    low_avg_counter: 0

    def __init__(self, input_recorder):
        self.input_recorder = input_recorder
        self.reset_tracking()
        self.callback_beat_detected = lambda: None
        self.callback_new_song = lambda: None
        self.callback_pause = lambda: None

    def reset_tracking(self):
        self.current_bpm = 0
        self.prev_beat_time = perf_counter()
        self.bpm_history = []
        self.y_avg_history = []
        self.low_freq_avg_history = []
        self.low_avg_counter = 0

    def analyze_audio(self):
        if not self.input_recorder.has_new_audio:
            return

        self.current_time = perf_counter()

        # Get x and y values from FFT
        xs, ys = self.input_recorder.fft()

        # Calculate average for all frequency ranges
        y_avg = numpy.mean(ys)
        self.y_avg_history.append(y_avg)

        # Track intensity
        y_avg_mean = numpy.mean(self.y_avg_history)
        if y_avg < y_avg_mean / 50:
            self.low_avg_counter += 1
        else:
            self.low_avg_counter = 0

        # Reset tracking if intensity dropped significantly for multiple iterations
        if y_avg < 100 or self.low_avg_counter > 8:
            print("low avg -> new song")
            self.detect_new_song()

        # Otherwise do normal beat detection
        else:
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
                            bass_avg > recent_low_freq_avg * 1.5  # Significantly more bass than before
                            or (
                                    low_freq_avg < y_avg * 1.2  #
                                    and bass_avg > recent_low_freq_avg
                            )
                    )
            ):
                # print(self.curr_time - self.prev_beat)
                time_since_last_beat = self.current_time - self.prev_beat_time
                if time_since_last_beat > 60 / self.max_bpm:
                    self.detect_beat(time_since_last_beat)
                    self.prev_beat_time = self.current_time

        # Detect pause in song when missing out more than 4 expected beats
        if self.current_bpm > 0 and self.current_time - self.prev_beat_time > 60 / self.current_bpm * 4.5:
            self.detect_pause()

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

    def detect_beat(self, time_since_last_beat):
        # print("beat detected")
        bpm_detected = 60 / time_since_last_beat
        if len(self.bpm_history) < 8:
            if bpm_detected > self.min_bpm:
                self.bpm_history.append(bpm_detected)
        else:
            # bpm_avg = int(numpy.mean(self.bpm_history))
            if (self.current_bpm == 0 or abs(self.current_bpm - bpm_detected) < 35):
                self.bpm_history.append(bpm_detected)
                # Recalculate with the new BPM value included
                self.current_bpm = self.calculate_bpm()

        self.callback_beat_detected(self.current_time, self.current_bpm)

    def calculate_bpm(self):
        self.reject_outliers(self.bpm_history)
        return numpy.mean(self.bpm_history)

    def reject_outliers(self, data, m=2.):
        data = numpy.array(data)
        return data[abs(data - numpy.mean(data)) < m * numpy.std(data)]

    def detect_new_song(self):
        # print("detect new song")
        self.reset_tracking()
        self.callback_new_song()

    def detect_pause(self):
        # print("detect pause")
        self.callback_pause()

    def on_beat_detected(self, callback):
        self.callback_beat_detected = callback

    def on_new_song_detected(self, callback):
        self.callback_new_song = callback

    def on_pause(self, callback):
        self.callback_pause = callback


class SignalGenerator:
    bar_modulo: int
    beat_index: int
    bpm: int
    auto_generating = False
    timer: QTimer
    last_beats: list
    last_beat_time: float

    def __init__(self, audio_analyzer, bar_modulo) -> None:
        self.bar_modulo = bar_modulo
        self.reset_tracking()

        self.callback_beat = lambda: None
        self.callback_bar = lambda: None
        self.callback_new_song = lambda: None
        self.callback_bpm_change = lambda: None

        # Wire up detection events
        audio_analyzer.on_beat_detected(self.track_beat)
        audio_analyzer.on_new_song_detected(self.track_new_song)
        audio_analyzer.on_pause(self.track_pause)

    def reset_tracking(self):
        self.beat_index = -1
        self.auto_generating = False
        self.bpm = 0
        self.last_beat_time = 0
        self.last_beats = []  # Sliding window of the last 4 beats

    def reset_beat_index(self):
        self.beat_index = -1

    def track_beat(self, beat_time, bpm):
        bpm_changed = False

        if abs(bpm - self.bpm) > 1:
            print("BPM changed {:d} -> {:d}".format(int(self.bpm), int(bpm)))
            self.bpm = bpm
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
        print("New song")
        self.callback_new_song()
        self.reset_tracking()

    def track_pause(self):
        print("Pause")
        self.timer.stop()
        self.auto_generating = False
        self.reset_beat_index()

    def on_beat(self, callback):
        self.callback_beat = callback

    def on_bar(self, callback):
        self.callback_bar = callback

    def on_new_song(self, callback):
        self.callback_new_song = callback

    def on_bpm_change(self, callback):
        self.callback_bpm_change = callback
