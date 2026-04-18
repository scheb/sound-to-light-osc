import math

import numpy
import pyaudio
import threading


class InputRecorder:
    """Simple, cross-platform class to record from the default input device."""

    def __init__(self, beat_detector, sec_to_record):
        self.RATE = 44100
        self.kill_threads = False
        self.has_new_audio = False
        self.beat_detector = beat_detector
        self.actual_index = 1

        # This value has to be aligned with consumption rate on the other end
        # It has to be reasonable fast enough to detect desired BPM
        self.sec_per_buffer = sec_to_record
        self.sample_buffer_size = math.floor(self.RATE * self.sec_per_buffer)
        self.buffers_to_record = 4 # Sliding window of 4 buffers
        print("Recorder config:")
        print(f"  sec_per_buffer {self.sec_per_buffer}")
        print(f"  sample_buffer_size {self.sample_buffer_size}")
        print(f"  buffers_to_record {self.buffers_to_record}")

        self.thread = None
        self.pyaudio = pyaudio.PyAudio()

        # get all input devices
        info = self.pyaudio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        for i in range(0, num_devices):
            if (self.pyaudio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                self.beat_detector.ui.add_audio_source(
                    self.pyaudio.get_device_info_by_host_api_device_index(0, i).get('name'))

        # make sure the default input device is broadcasting the speaker output
        # there are a few ways to do this
        # e.g., stereo mix, VB audio cable for windows, soundflower for mac
        default_input_device_info = self.pyaudio.get_default_input_device_info()
        print("Using default input device: {:s}".format(default_input_device_info['name']))
        self.in_stream = self.pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.RATE,
            input_device_index=default_input_device_info["index"],
            input=True,
            frames_per_buffer=self.sample_buffer_size)
        self.beat_detector.ui.select_audio_source(default_input_device_info["index"])
        self.actual_index = default_input_device_info["index"]
        self.audio = numpy.empty((self.buffers_to_record * self.sample_buffer_size), dtype=numpy.int16)

    def close(self):
        self.kill_threads = True
        self.pyaudio.close(self.in_stream)

    def change_input(self, index):
        if index != self.actual_index:
            print("Using input device: {:s}".format(
                self.pyaudio.get_device_info_by_host_api_device_index(0, index).get('name')))
            self.in_stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                input_device_index=index,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.sample_buffer_size)
            self.actual_index = index

    ### RECORDING AUDIO ###

    def get_audio(self):
        """get a single buffer size worth of audio."""
        audio_string = self.in_stream.read(self.sample_buffer_size)
        return numpy.frombuffer(audio_string, dtype=numpy.int16)

    def record(self):
        while not self.kill_threads:
            for i in range(self.buffers_to_record):
                self.audio[:-self.sample_buffer_size] = self.audio[self.sample_buffer_size:]
                self.audio[-self.sample_buffer_size:] = self.get_audio()
                self.has_new_audio = True

    def start(self):
        self.thread = threading.Thread(target=self.record)
        self.thread.start()

    def fft(self, data=None):
        if not data:
            data = self.audio.flatten()
        left, right = numpy.split(numpy.abs(numpy.fft.fft(data, self.sample_buffer_size)), 2)
        # The second half of the FFT of a real signal is a mirror image of the first.
        # We only need the first half (left) for the frequency spectrum.
        ys = left
        xs = numpy.arange(self.sample_buffer_size / 2, dtype=float)
        xs = xs * self.RATE / self.sample_buffer_size
        return xs, ys
