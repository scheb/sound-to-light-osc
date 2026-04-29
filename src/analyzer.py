from collections import deque

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from recorder import *
from time import perf_counter

MAX_VOLUME = 1000.0


class VolumeNormalizer(QObject):
    def __init__(self, sample_length_secs):
        super().__init__()
        self.raw_max_values = []
        self.historic_max_values = deque(maxlen=int(30 / sample_length_secs)) # 30 seconds
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


class SpectralFluxIntensityDetector(QObject):
    intensity_changed = pyqtSignal(int)  # -1: Calm, 0: Normal, 1: Intense
    spectral_flux_updated = pyqtSignal(float, float, float, float, bool)
    INTENSITY_NORMAL = 0
    INTENSITY_INTENSE = 1
    INTENSITY_CALM = -1

    # Thresholds for entering states
    ENTER_INTENSE_FACTOR = 1.3
    ENTER_CALM_FACTOR = 0.7

    # Thresholds for leaving states (Resistance/Hysteresis)
    LEAVE_INTENSE_FACTOR = 1.1
    LEAVE_CALM_FACTOR = 0.9

    def __init__(self, sample_length_secs):
        super().__init__()
        self.prev_spectrum = None
        self.current_intensity = None
        self.flux_history = deque(maxlen=int(60 / sample_length_secs))  # 60 seconds
        self.flux_min_history = int(5 / sample_length_secs) # 5secs min history
        self.flux_evaluation_frame = int(1 / sample_length_secs) # 1sec
        self.is_paused = False

        # Stability logic
        self.pending_intensity = self.INTENSITY_NORMAL
        self.intensity_hold_counter = self.INTENSITY_NORMAL

    def reset_state(self):
        if self.current_intensity != self.INTENSITY_NORMAL:
            self.intensity_changed.emit(self.INTENSITY_NORMAL)
        self.prev_spectrum = None
        self.current_intensity = self.INTENSITY_NORMAL
        self.pending_intensity = self.INTENSITY_NORMAL
        self.intensity_hold_counter = 0

    @pyqtSlot()
    def on_pause_detected(self):
        self.is_paused = True

    @pyqtSlot()
    def on_new_song_detected(self):
        self.reset_state()
        self.is_paused = False

    def update(self, xs, ys, current_time: float):
        # Calculate spectral flux for the whole spectrum
        if self.prev_spectrum is None or len(ys) != len(self.prev_spectrum):
            self.prev_spectrum = ys
            return

        spectral_flux = numpy.sum(numpy.maximum(0, ys - self.prev_spectrum))
        self.prev_spectrum = ys

        if not self.is_paused:
            self.flux_history.append(spectral_flux)

        if len(self.flux_history) < self.flux_min_history:
            return

        avg_flux = numpy.median(self.flux_history)
        recent_flux = numpy.median(list(self.flux_history)[-self.flux_evaluation_frame:])

        # Determine target intensity based on hysteresis rules
        target_intensity = self.current_intensity

        if self.current_intensity == self.INTENSITY_INTENSE:
            # Resistance: Must drop below a lower threshold to return to normal
            upper_threshold = avg_flux * self.LEAVE_INTENSE_FACTOR
            lower_threshold = avg_flux * self.ENTER_CALM_FACTOR
            if recent_flux < lower_threshold:
                target_intensity = self.INTENSITY_CALM
            elif recent_flux < upper_threshold:
                target_intensity = self.INTENSITY_NORMAL
        
        elif self.current_intensity == self.INTENSITY_CALM:
            # Resistance: Must rise above a higher threshold to return to normal
            upper_threshold = avg_flux * self.ENTER_INTENSE_FACTOR
            lower_threshold = avg_flux * self.LEAVE_CALM_FACTOR
            if recent_flux > upper_threshold:
                target_intensity = self.INTENSITY_NORMAL
            elif recent_flux > lower_threshold:
                target_intensity = self.INTENSITY_NORMAL

        else:
            upper_threshold = avg_flux * self.ENTER_INTENSE_FACTOR
            lower_threshold = avg_flux * self.ENTER_CALM_FACTOR
            if recent_flux > upper_threshold:
                target_intensity = self.INTENSITY_INTENSE
            elif recent_flux < lower_threshold:
                target_intensity = self.INTENSITY_CALM

        # After startup choose normal, if nothing else is detected
        if target_intensity is None:
            target_intensity = self.INTENSITY_NORMAL

        # Require stability before switching (debounce)
        is_intensity_change = False
        if target_intensity != self.current_intensity:
            if target_intensity == self.pending_intensity:
                self.intensity_hold_counter += 1
            else:
                self.pending_intensity = target_intensity
                self.intensity_hold_counter = 0

            if self.intensity_hold_counter > 50:  # ~1 second stability
                self.current_intensity = target_intensity
                self.intensity_changed.emit(self.current_intensity)
                is_intensity_change = True
                self.intensity_hold_counter = 0
        else:
            self.intensity_hold_counter = 0
            self.pending_intensity = None

        self.spectral_flux_updated.emit(recent_flux, avg_flux, upper_threshold, lower_threshold, is_intensity_change)


class SpectralFluxBeatDetector(QObject):
    """
    Analyzes frequency spectrum data to detect beats.
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
        self.odf_history = deque(maxlen=int(30 / sample_length_secs))  # 30 seconds
        self.odf_min_history_size = int(5 / sample_length_secs) # 5secs min history
        # Sensitivity multiplier for the dynamic threshold. Higher values make beat detection more restrictive (requires a stronger peak relative to the median).
        self.dynamic_threshold_multiplier = 1.5
        # Constant floor added to the dynamic threshold. Prevents background noise from triggering beats during quiet sections.
        self.dynamic_threshold_offset = 200 # 1000max
        self.is_paused = False # Flag to control history tracking

    @pyqtSlot()
    def on_pause_detected(self):
        self.is_paused = True

    @pyqtSlot()
    def on_new_song_detected(self):
        self.is_paused = False

    def update(self, xs, ys, current_time: float):
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
        if not self.is_paused:
            # Maintain a history of flux values for thresholding
            self.odf_history.append(spectral_flux)

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
    pause_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.volume_threshold = MAX_VOLUME * 0.05 # 5% threshold
        self.is_silence = False
        self.silence_start_time = None
        self.silence_duration_threshold = 1.0 # seconds

    def update(self, xs, ys, current_time: float):
        peak_volume = numpy.max(ys)
        if peak_volume < self.volume_threshold:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            elif not self.is_silence and (current_time - self.silence_start_time) > self.silence_duration_threshold:
                self.is_silence = True
                self.pause_detected.emit()
        else:
            if self.is_silence:
                self.new_song_detected.emit()
                self.is_silence = False
            self.silence_start_time = None


class AudioAnalyzer(QObject):
    def __init__(self, input_recorder, sample_length_secs):
        super().__init__()
        self.input_recorder = input_recorder
        self.volume_normalizer = VolumeNormalizer(sample_length_secs)
        self.beat_detector = SpectralFluxBeatDetector(sample_length_secs)
        self.intensity_detector = SpectralFluxIntensityDetector(sample_length_secs)
        self.new_song_detector = NewSongDetector()

        # Connect signals for history management
        self.new_song_detector.pause_detected.connect(self.beat_detector.on_pause_detected)
        self.new_song_detector.new_song_detected.connect(self.beat_detector.on_new_song_detected)
        self.new_song_detector.pause_detected.connect(self.intensity_detector.on_pause_detected)
        self.new_song_detector.new_song_detected.connect(self.intensity_detector.on_new_song_detected)


    def analyze_audio(self):
        if not self.input_recorder.has_new_audio:
            print(f"WARNING: No new audio data available")
            return

        # Fetch raw data
        current_time = perf_counter()
        xs, ys = self.input_recorder.fft()
        self.input_recorder.has_new_audio = False

        # Normalize volume data
        ys = self.volume_normalizer.normalize_volume(ys)

        # 5 second training period for the volume normalizer until analyzing starts
        if current_time < 5.0:
            return

        # Update sub-components
        self.beat_detector.update(xs, ys, current_time)
        self.intensity_detector.update(xs, ys, current_time)
        self.new_song_detector.update(xs, ys, current_time)

        # Performance monitoring
        run_time = perf_counter() - current_time
        if run_time > self.input_recorder.sec_per_buffer:
            print(f"WARNING: Analyzer runtime exceeds sampling period: {run_time:.4f} > {self.input_recorder.sec_per_buffer:.4f}")


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
