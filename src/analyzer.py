from collections import deque

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from recorder import *
from time import perf_counter

MAX_VOLUME = 1000.0


class VolumeNormalizer(QObject):
    def __init__(self):
        super().__init__()
        self.raw_max_values = []
        self.historic_max_values = deque(maxlen=300)
        self.target_max = MAX_VOLUME
        self.scale_factor = 1.0

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_scale_factor)
        self.timer.start(1000)  # Update every second

    def update_scale_factor(self):
        if not self.raw_max_values:
            return

        # Find the maximum value in the last second and add it to the history
        max_in_second = numpy.percentile(self.raw_max_values, 100)
        self.raw_max_values = []
        self.historic_max_values.append(max_in_second)

        # The new scaling factor is based on the max value in the history
        if self.historic_max_values:
            max_overall = numpy.percentile(self.historic_max_values, 100)
            # print(f"New max_overall {max_overall}")
            if max_overall > 0:
                self.scale_factor = self.target_max / max_overall

    def normalize_volume(self, ys):
        # Keep track of the max value in the raw signal
        self.raw_max_values.append(numpy.percentile(ys, 100))
        return ys * self.scale_factor


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

                if self.intensity_hold_counter > 50:  # ~1 second at 50Hz
                    self.current_intensity = detected_intensity
                    self.intensity_changed.emit(detected_intensity)
                    self.intensity_hold_counter = 0
            else:
                self.intensity_hold_counter = 0
                self.pending_intensity = None


class BeatDetector(QObject):
    """
    Analyzes frequency spectrum data to detect beats and estimate BPM.
    Uses spectral flux (Onset Detection Function) to identify rhythmic peaks.
    """
    beat_detected = pyqtSignal(float)
    spectral_flux_updated = pyqtSignal(float, float, bool)

    def __init__(self, sample_length_secs):
        super().__init__()
        self.sample_length_secs = sample_length_secs
        self.last_beat_time = 0.0
        self.beat_refractory_period = 0.333  # ~180bpm
        self.prev_spectrum = None
        self.odf_history = []
        self.odf_history_size = int(60 / sample_length_secs) # 60secs history
        self.odf_min_history_size = int(10 / sample_length_secs) # 10secs min history
        # Sensitivity multiplier for the dynamic threshold. Higher values make beat detection more restrictive (requires a stronger peak relative to the median).
        self.dynamic_threshold_multiplier = 1.5
        # Constant floor added to the dynamic threshold. Prevents background noise from triggering beats during quiet sections.
        self.dynamic_threshold_offset = 200 # 1000max

    def update(self, xs, ys, current_time):
        """
        Processes new FFT data.
        :param xs: Frequency bins
        :param ys: Magnitude values
        :param current_time: Timestamp of the audio frame
        """
        # Focus on frequencies below 1000Hz (where bass/kick drum usually reside)
        freq_mask = (xs <= 1000)
        bass_band = ys[freq_mask]

        if self.prev_spectrum is None or len(bass_band) != len(self.prev_spectrum):
            self.prev_spectrum = bass_band
            return

        # Spectral Flux: sum of positive changes in magnitude across frequency bins
        # This represents the "novelty" or onset energy in the signal
        spectral_flux = numpy.sum(numpy.maximum(0, bass_band - self.prev_spectrum))
        self.prev_spectrum = bass_band

        # Ignore silence for history to maintain threshold while no song is playing
        if spectral_flux > self.dynamic_threshold_offset:
            # Maintain a history of flux values for thresholding
            self.odf_history.append(spectral_flux)
            if len(self.odf_history) > self.odf_history_size:
                self.odf_history.pop(0)

        # Wait until we have enough history data before starting with beat detection
        if len(self.odf_history) < self.odf_min_history_size:
            return

        # Dynamic thresholding based on local median flux to adapt to different track volumes/densities
        median_odf = numpy.median(self.odf_history)
        dynamic_threshold = (median_odf * self.dynamic_threshold_multiplier) + self.dynamic_threshold_offset

        # A beat is detected if flux exceeds the threshold
        is_beat = spectral_flux > dynamic_threshold

        if is_beat:
            # Refractory period skips too many beats close to another
            if (current_time - self.last_beat_time) > self.beat_refractory_period:
                self.beat_detected.emit(current_time)
                self.last_beat_time = current_time
            else:
                is_beat = False

        self.spectral_flux_updated.emit(spectral_flux, dynamic_threshold, is_beat)


class NewSongDetector(QObject):
    new_song_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Volume threshold is static due to normalization
        self.volume_threshold = MAX_VOLUME * 0.005
        self.low_avg_time = None
        self.time_threshold_secs = 1.0

    def detect_low_volume(self, avg_volume: float, current_time: float):
        # Detect very low volume (to detect new track)
        if avg_volume < self.volume_threshold:
            if self.low_avg_time is None:
                self.low_avg_time = current_time
                return False
        else:
            self.low_avg_time = None
            return False

        # Reset tracking if intensity dropped significantly within time frame
        if self.low_avg_time is not None and (current_time - self.low_avg_time) > self.time_threshold_secs:
            # print("New song, reason: low avg timeout")
            self.new_song_detected.emit()
            return True

        return False


class AudioAnalyzer(QObject):
    def __init__(self, input_recorder, sample_length_secs):
        super().__init__()
        self.input_recorder = input_recorder
        self.max_volume = MAX_VOLUME * 0.05

        self.new_song_detector = NewSongDetector()
        self.intensity_detector = IntensityDetector()
        self.beat_detector = BeatDetector(sample_length_secs)
        self.volume_normalizer = VolumeNormalizer()

    def analyze_audio(self):
        if not self.input_recorder.has_new_audio:
            print(f"WARNING: No new audio data available")
            return

        # Fetch raw data
        current_time = perf_counter()
        xs, ys = self.input_recorder.fft()
        audio_data = self.input_recorder.audio.astype(numpy.float64)
        self.input_recorder.has_new_audio = False

        # Normalize volume data
        ys = self.volume_normalizer.normalize_volume(ys)
        # ys_median = numpy.percentile(ys, 50)
        # ys_max = numpy.percentile(ys, 100)
        # print(f"Median ys: {ys_median}")
        # print(f"Max ys: {ys_max}")

        # if self.new_song_detector.detect_low_volume(ys_median, current_time):
        #     # Don't do any analysis when low volume was detected
        #     print("low volume")
        #     return

        # self.intensity_detector.update(volume)
        self.beat_detector.update(xs, ys, current_time)

        run_time = perf_counter() - current_time
        if run_time > self.input_recorder.sec_per_buffer:
            print(f"WARNING: Analyzer runtime exceeds sampling period: {run_time} > {self.input_recorder.sec_per_buffer}")


class SignalGenerator(QObject):
    bpm_changed = pyqtSignal(int)
    beat_signal = pyqtSignal(int)
    bar_detected = pyqtSignal()
    new_song_detected = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

    @pyqtSlot(float)
    def track_beat(self, beat_time):
        self.beat_signal.emit(0)

    @pyqtSlot()
    def track_new_song(self):
        self.new_song_detected.emit()

    @pyqtSlot()
    def track_pause(self):
        pass

    @pyqtSlot(int)
    def track_intensity_change(self, intensity):
        self.intensity = intensity
