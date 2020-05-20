from PyQt5.QtCore import QTimer
from PyQt5 import QtCore
from recorder import *
from time import perf_counter

class AudioAnalyzer:
    min_bpm = 80
    max_bpm = 160
    bpm_history_length = 16  # beats
    freq_history_length = 24  # samples
    intensity_history_length = 128  # samples
    volume_history_length = 3*60  # seconds
    input_recorder: InputRecorder

    # Timing
    current_time: float
    prev_beat_time: float
    prev_volume_track_time: float

    # BPM
    current_bpm: int
    bpm_history: list

    # Intensity over time
    pause_count = 0
    max_volume = 1000  # Recent max volume
    current_intensity: int
    intensity_history: list
    y_max_history: list
    volume_long_history: list
    low_history: list
    bass_history: list
    low_midrange_history: list
    low_avg_time: -1

    def __init__(self, input_recorder):
        self.input_recorder = input_recorder
        self.current_intensity = 0
        self.reset_tracking()
        self.callback_beat_detected = lambda: None
        self.callback_new_song = lambda: None
        self.callback_pause = lambda: None
        self.callback_intensity_changed = lambda: None
        self.prev_volume_track_time = 0
        self.volume_long_history = []

    def reset_tracking(self):
        self.current_bpm = 0
        self.prev_beat_time = perf_counter()
        self.bpm_history = []
        self.y_max_history = []
        self.low_history = []
        self.bass_history = []
        self.low_midrange_history = []
        self.low_avg_time = -1
        self.change_intensity(0)
        self.intensity_history = []

    def analyze_audio(self):
        if not self.input_recorder.has_new_audio:
            return

        self.current_time = perf_counter()

        # Get x and y values from FFT
        xs, ys = self.input_recorder.fft()
        # print("max hz", numpy.max(xs))

        intensity_samples = ys # [ys[i] for i in range(len(xs)) if 60 <= xs[i] <= 1000]

        # Keep track of volume
        # y_max = numpy.percentile(ys, 90)
        y_max = numpy.percentile(intensity_samples, 55)
        self.track_max_volume(y_max)

        # Evaluate the intensity
        # intensity_samples = [ys[i] for i in range(len(xs)) if 60 <= xs[i] <= 4000]
        # intensity_level = numpy.mean(intensity_samples)

        # print(y_max, intensity_level)

        # intensity_samples = [ys[i] for i in range(len(xs)) if 60 <= xs[i] <= 4000]

        y_avg = numpy.percentile(intensity_samples, 50)
        self.track_intensity(y_avg)

        if not self.track_low_volume(y_avg):
            # Calculate frequency average
            low_samples = [ys[i] for i in range(len(xs)) if xs[i] <= 1000]  # Overall low frequencies
            low = numpy.mean(low_samples)

            bass_samples = [ys[i] for i in range(len(xs)) if 60 <= xs[i] <= 130]  # Bass frequencies
            bass = numpy.mean(bass_samples)

            low_midrange_samples = [ys[i] for i in range(len(xs)) if 301 <= xs[i] <= 750]  # Low mid-range frequencies
            low_midrange = numpy.mean(low_midrange_samples)

            # Calculate recent low frequency average
            self.low_history.append(low)
            self.bass_history.append(bass)
            self.low_midrange_history.append(low_midrange)
            
            # recent_low_avg = numpy.mean(self.low_history)
            recent_bass_avg = numpy.mean(self.bass_history)
            recent_low_midrange_avg = numpy.mean(self.low_midrange_history)

            # print("bass: {:.2f} vs recent: {:.2f}".format(bass, recent_bass_avg))
            # print("low_midrange: {:.2f} vs recent: {:.2f}".format(low_midrange, recent_low_midrange_avg))

            # threshold = self.calculate_threshold(self.bass_history)
            # print("threshold {:.2f}".format(threshold))

            # Check if there is a beat
            if (y_avg > 1000  # Minimum intensity
                    and (
                            bass > recent_bass_avg * self.calculate_threshold(self.bass_history)
                            or low_midrange > recent_low_midrange_avg * self.calculate_threshold(self.low_midrange_history)
                    )
            ):
                # print(self.curr_time - self.prev_beat)
                time_since_last_beat = self.current_time - self.prev_beat_time
                if time_since_last_beat > 60 / self.max_bpm:
                    self.detect_beat(time_since_last_beat)
                    self.prev_beat_time = self.current_time

        # Detect pause in song when missing out more than 3 expected beats
        if self.current_bpm > 0 and self.current_time - self.prev_beat_time > 60 / self.current_bpm * 3.5:
            self.detect_pause()

        self.housekeeping()

    def track_max_volume(self, level):
        self.y_max_history.append(level)
        if self.current_time > self.prev_volume_track_time + 1:
            self.prev_volume_track_time = self.current_time
            self.volume_long_history.append(numpy.percentile(self.y_max_history, 95))
            if len(self.volume_long_history) > self.volume_history_length:
                self.volume_long_history = self.volume_long_history[1:]
            self.max_volume = numpy.percentile(self.volume_long_history, 95)

    def track_intensity(self, level):
        self.intensity_history.append(level / self.max_volume)
        if len(self.intensity_history) < self.intensity_history_length / 2:
            return

        avg = numpy.average(self.intensity_history)
        # print(self.intensity_history)
        # print(avg, self.max_volume)

        # Make it harder to switch intensity
        resistance_to_intense = +0.07
        resistance_to_calm = -0.07
        if self.current_intensity == 1:
            resistance_to_intense = -0.07
            resistance_to_calm = -0.07
        if self.current_intensity == -1:
            resistance_to_intense = +0.07
            resistance_to_calm = +0.07

        if avg > 0.60 + resistance_to_intense:  # Intense
            intensity = 1
        elif avg > 0.45 + resistance_to_calm:  # Normal
            intensity = 0
        else:  # Calm
            intensity = -1

        self.change_intensity(intensity)

    def change_intensity(self, intensity):
        if intensity != self.current_intensity:
            self.current_intensity = intensity
            self.detect_intensity_changed(self.current_intensity)

    def track_low_volume(self, y_avg):
        # Detect very low volume (to detect new track)
        if y_avg < self.max_volume * 0.05:
            if self.low_avg_time == -1:
                self.low_avg_time = self.current_time
        else:
            self.low_avg_time = -1

        # Reset tracking if intensity dropped significantly for multiple iterations
        if y_avg < 100:
            print("low avg {:.2f} -> new song".format(y_avg))
            self.detect_new_song()
            return True

        if self.low_avg_time > 0 and (self.current_time - self.low_avg_time) * 1000 > 1000:
            print("low avg (timeout) -> new song".format(y_avg))
            self.detect_new_song()
            return True

        return False

    def housekeeping(self):
        # Shorten the cumulative list to account for changes in dynamics
        if len(self.low_history) > self.freq_history_length:
            self.low_history = self.low_history[1:]
        if len(self.bass_history) > self.freq_history_length:
            self.bass_history = self.bass_history[1:]
        if len(self.low_midrange_history) > self.freq_history_length:
            self.low_midrange_history = self.low_midrange_history[1:]
        if len(self.y_max_history) > self.freq_history_length:
            self.y_max_history = self.y_max_history[1:]
        if len(self.intensity_history) > self.intensity_history_length:
            self.intensity_history = self.intensity_history[1:]

        # Keep two 8-counts of BPMs so we can maybe catch tempo changes
        if len(self.bpm_history) > self.bpm_history_length:
            self.bpm_history = self.bpm_history[1:]

    # https://www.parallelcube.com/2018/03/30/beat-detection-algorithm/
    def calculate_threshold(self, history):
        history_max = numpy.max(history)
        history_average = numpy.average(history)
        variance = numpy.average([numpy.power((i - history_average) / history_max, 2) for i in history])
        # print(variance)
        return numpy.max([-15 * variance + 1.55, 1.2])

    def detect_beat(self, time_since_last_beat):
        print("Detected: Beat")
        bpm_detected = 60 / time_since_last_beat
        if len(self.bpm_history) < 8:
            if bpm_detected > self.min_bpm:
                self.bpm_history.append(bpm_detected)
        else:
            # bpm_avg = int(numpy.mean(self.bpm_history))
            if self.current_bpm == 0 or abs(self.current_bpm - bpm_detected) < 35:
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
        print("Detected: New song")
        self.reset_tracking()
        self.callback_new_song()

    def detect_pause(self):
        print("Detected: Pause")
        self.callback_pause()

    def detect_intensity_changed(self, intensity):
        print("New intensity: {:d}".format(intensity))
        self.callback_intensity_changed(intensity)

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
