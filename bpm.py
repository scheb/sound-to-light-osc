from collections import deque

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from recorder import *
from time import perf_counter

class VolumeNormalizer(QObject):
    def __init__(self):
        super().__init__()
        self.raw_max_values = []
        self.historic_max_values = deque(maxlen=300)
        self.target_max = 1000.0
        self.scale_factor = 1.0

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_scale_factor)
        self.timer.start(1000)  # Update every second

    def update_scale_factor(self):
        if not self.raw_max_values:
            return

        # Find the maximum value in the last second and add it to the history
        max_in_second = numpy.percentile(self.raw_max_values, 95)
        self.raw_max_values = []
        self.historic_max_values.append(max_in_second)

        # The new scaling factor is based on the max value in the history
        if self.historic_max_values:
            max_overall = numpy.percentile(self.historic_max_values, 95)
            # print(f"New max_overall {max_overall}")
            if max_overall > 0:
                self.scale_factor = self.target_max / max_overall

    def normalize_volume(self, ys):
        # Keep track of the max value in the raw signal
        self.raw_max_values.append(numpy.percentile(ys, 95))
        return ys * self.scale_factor

class VuMeter(QObject):
    vu_level_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.volume_max = 1.0

    def update(self, audio_data):
        # Calculate the volume (RMS of the raw signal)
        volume = numpy.sqrt(numpy.mean(audio_data**2))
        if numpy.isnan(volume):
            volume = 0

        self.volume_max = max(self.volume_max, volume)

        # Normalize the current volume against the dynamic maximum
        vu_level = (volume / self.volume_max) * 100
        vu_level = min(100, vu_level)  # Ensure it's capped at 100

        self.vu_level_changed.emit(vu_level)
        return volume

class IntensityDetector(QObject):
    pause_detected = pyqtSignal()
    new_song_detected = pyqtSignal()
    intensity_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.current_intensity = 0
        self.volume_long_history = []
        self.pause_counter = 0
        self.is_paused = False
        
        # Intensity stability
        self.pending_intensity = 0
        self.intensity_hold_counter = 0

    def update(self, volume):
        self.volume_long_history.append(volume)
        if len(self.volume_long_history) > 1500:  # ~30 seconds history for a very stable baseline
            self.volume_long_history.pop(0)

        if len(self.volume_long_history) > 50:
            avg_vol = numpy.mean(self.volume_long_history)

            # Detect Pause/Silence
            if volume < 500:
                self.pause_counter += 1
                if self.pause_counter > 100:  # ~2 seconds of silence
                    if not self.is_paused:
                        self.pause_detected.emit()
                        self.is_paused = True
            else:
                self.pause_counter = 0
                if self.is_paused:
                    self.is_paused = False
                    self.new_song_detected.emit()

            # Detect Intensity
            current_avg_vol = numpy.mean(self.volume_long_history[-50:])
            
            detected_intensity = 0
            if current_avg_vol > avg_vol * 1.1 and current_avg_vol > 1000:
                detected_intensity = 1  # Intense
            elif current_avg_vol < avg_vol * 0.9:
                detected_intensity = -1  # Calm
            
            if detected_intensity != self.current_intensity:
                if detected_intensity == self.pending_intensity:
                    self.intensity_hold_counter += 1
                else:
                    self.pending_intensity = detected_intensity
                    self.intensity_hold_counter = 0
                
                if self.intensity_hold_counter > 50: # ~1 second at 50Hz
                    self.current_intensity = detected_intensity
                    self.intensity_changed.emit(detected_intensity)
                    self.intensity_hold_counter = 0
            else:
                self.intensity_hold_counter = 0
                self.pending_intensity = None

class BeatDetector(QObject):
    beat_detected = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.beat_time = 0
        self.beat_timestamps = []
        self.beat_refractory_period = 0.2
        self.prev_spectrum = None
        self.odf_history = []
        self.odf_history_size = 50
        self.dynamic_threshold_multiplier = 1.4
        self.dynamic_threshold_offset = 0.05

    def update(self, xs, ys, current_time):
        freq_mask = (xs <= 1000)
        ys_band = ys[freq_mask]

        if self.prev_spectrum is None or len(ys_band) != len(self.prev_spectrum):
            self.prev_spectrum = ys_band
            return

        spectral_flux = numpy.sum(numpy.maximum(0, ys_band - self.prev_spectrum))
        self.prev_spectrum = ys_band

        self.odf_history.append(spectral_flux)
        if len(self.odf_history) > self.odf_history_size: self.odf_history.pop(0)
        if not self.odf_history: return

        median_odf = numpy.median(self.odf_history)
        dynamic_threshold = (median_odf * self.dynamic_threshold_multiplier) + self.dynamic_threshold_offset

        is_peak = spectral_flux >= numpy.max(self.odf_history[-3:]) if len(self.odf_history) >= 3 else True
        is_beat = spectral_flux > dynamic_threshold and is_peak

        if is_beat and (current_time - self.beat_time) > self.beat_refractory_period:
            self.beat_time = current_time
            self.beat_timestamps.append(self.beat_time)

            if len(self.beat_timestamps) > 32: self.beat_timestamps.pop(0)

            if len(self.beat_timestamps) > 4:
                intervals = numpy.diff(self.beat_timestamps)
                valid_intervals = intervals[(intervals > 0.3) & (intervals < 1.5)]
                
                if len(valid_intervals) > 2:
                    median_ibi = numpy.median(valid_intervals)
                    consistent_intervals = valid_intervals[numpy.abs(valid_intervals - median_ibi) < 0.15 * median_ibi]
                    
                    if len(consistent_intervals) > 0:
                        avg_ibi = numpy.mean(consistent_intervals)
                        bpm = 60 / avg_ibi
                        self.beat_detected.emit(self.beat_time, bpm)

class AudioAnalyzer(QObject):
    def __init__(self, input_recorder):
        super().__init__()
        self.input_recorder = input_recorder
        
        self.vu_meter = VuMeter()
        self.intensity_detector = IntensityDetector()
        self.beat_detector = BeatDetector()
        self.volume_normalizer = VolumeNormalizer()

    def analyze_audio(self):
        if not self.input_recorder.has_new_audio: return

        current_time = perf_counter()
        xs, ys = self.input_recorder.fft()
        ys = self.volume_normalizer.normalize_volume(ys)
        # print(f"Max ys: {numpy.percentile(ys, 95)}")

        audio_data = self.input_recorder.audio.astype(numpy.float64)
        self.input_recorder.has_new_audio = False

        volume = self.vu_meter.update(audio_data)
        self.intensity_detector.update(volume)
        self.beat_detector.update(xs, ys, current_time)

class SignalGenerator(QObject):
    bpm_changed = pyqtSignal(int)
    beat_signal = pyqtSignal(int)
    bar_detected = pyqtSignal()
    new_song_detected = pyqtSignal()
    
    def __init__(self) -> None:
        super().__init__()
        self.reset_tracking()

    def reset_tracking(self):
        self.bar_modulo = 2
        self.beat_index = -1
        self.auto_generating = False
        self.bpm = 0
        self.intensity = 0
        self.last_beat_time = 0
        self.last_beats = []

    def reset_beat_index(self):
        self.beat_index = -1

    def recalculate_bar_modulo(self):
        modulo = 2
        if self.intensity == 1: modulo = 1
        if self.intensity == -1: modulo = 4
        if self.bpm > 0 and self.bpm < 100: modulo /= 2
        self.bar_modulo = numpy.max([1, modulo])
        # print("Bar modulo: {:.0f}".format(self.bar_modulo))

    @pyqtSlot(float, float)
    def track_beat(self, beat_time, bpm):
        bpm_changed = False
        if abs(bpm - self.bpm) > 1:
            # print("BPM changed {:d} -> {:d}".format(int(self.bpm), int(bpm)))
            self.bpm = bpm
            self.recalculate_bar_modulo()
            self.bpm_changed.emit(int(bpm))
            bpm_changed = True

        if self.auto_generating:
            if bpm_changed:
                # print("Sync auto generated beat")
                # self.timer.stop()
                self.generate_beat_signal(beat_time=beat_time)
        else:
            if bpm_changed and self.can_auto_generate():
                # print("Start auto generating beat with {:d} BPM".format(int(self.bpm)))
                self.auto_generating = True
            self.generate_beat_signal(beat_time=beat_time)

    def can_auto_generate(self):
        if self.bpm > 0 and len(self.last_beats) >= 8:
            oldest_beat = numpy.min(self.last_beats)
            newest_beat = numpy.max(self.last_beats)
            max_difference = 60 / self.bpm * 16
            return newest_beat - oldest_beat < max_difference
        return False

    def generate_beat_signal(self, beat_time=None):
        if beat_time is None: beat_time = perf_counter()

        if beat_time - self.last_beat_time > 0.333:
            self.last_beats.append(beat_time)
            if len(self.last_beats) > 8: self.last_beats.pop(0)
            self.last_beat_time = beat_time
            self.beat_index += 1

            beat_index_mod = self.beat_index % (self.bar_modulo * 2)
            if self.beat_index % 2 == 0:
                self.beat_signal.emit(int(beat_index_mod / 2))
            if beat_index_mod == 0:
                self.bar_detected.emit()

        if self.auto_generating:
            return False
            # self.timer = QtCore.QTimer()
            # self.timer.setSingleShot(True)
            # self.timer.timeout.connect(self.generate_beat_signal)
            # time_passed = int((perf_counter() - beat_time) * 1000)
            # timeout = int(60000 / self.bpm) - time_passed
            # self.timer.start(timeout)

    @pyqtSlot()
    def track_new_song(self):
        self.new_song_detected.emit()
        self.reset_tracking()

    @pyqtSlot()
    def track_pause(self):
        if hasattr(self, 'timer'): self.timer.stop()
        self.auto_generating = False
        self.reset_beat_index()

    @pyqtSlot(int)
    def track_intensity_change(self, intensity):
        self.intensity = intensity
        self.recalculate_bar_modulo()
