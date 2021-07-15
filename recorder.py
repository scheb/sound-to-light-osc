import matplotlib
matplotlib.use('TkAgg') # <-- THIS MAKES IT FAST!
import numpy
import pyaudio
import threading

class InputRecorder:
    """Simple, cross-platform class to record from the default input device."""

    def __init__(self, beatDetector):
        self.RATE = 44100
        self.BUFFERSIZE = 2**10
        self.secToRecord = .1
        self.kill_threads = False
        self.has_new_audio = False
        self.beatDetector = beatDetector
        self.actual_index = 1
        self.setup()

    def setup(self):
        self.buffers_to_record = int(self.RATE * self.secToRecord / self.BUFFERSIZE)
        if self.buffers_to_record == 0:
            self.buffers_to_record = 1
        self.samples_to_record = int(self.BUFFERSIZE * self.buffers_to_record)
        self.chunks_to_record = int(self.samples_to_record / self.BUFFERSIZE)
        self.sec_per_point = 1. / self.RATE

        self.p = pyaudio.PyAudio()

        # get all input devices
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                self.beatDetector.ui.add_audio_source(self.p.get_device_info_by_host_api_device_index(0, i).get('name'))

        # make sure the default input device is broadcasting the speaker output
        # there are a few ways to do this
        # e.g., stereo mix, VB audio cable for windows, soundflower for mac
        default_input_device_info = self.p.get_default_input_device_info()
        print("Using default input device: {:s}".format(default_input_device_info['name']))
        self.in_stream = self.p.open(format=pyaudio.paInt16,
                                     channels=1,
                                     rate=self.RATE,
                                     input_device_index=default_input_device_info["index"],
                                     input=True,
                                     frames_per_buffer=self.BUFFERSIZE)
        self.beatDetector.ui.select_audio_source(default_input_device_info["index"])
        self.actual_index = default_input_device_info["index"]

        self.audio = numpy.empty((self.chunks_to_record * self.BUFFERSIZE), dtype=numpy.int16)

    def close(self):
        self.kill_threads = True
        self.p.close(self.in_stream)

    def change_input(self, index):
        if index != self.actual_index:
            print("Using input device : {:s}".format(self.p.get_device_info_by_host_api_device_index(0, index).get('name')))
            self.in_stream = self.p.open(format=pyaudio.paInt16,
                                         channels=1,
                                         input_device_index=index,
                                         rate=self.RATE,
                                         input=True,
                                         frames_per_buffer=self.BUFFERSIZE)
            self.actual_index = index

    ### RECORDING AUDIO ###

    def get_audio(self):
        """get a single buffer size worth of audio."""
        audio_string = self.in_stream.read(self.BUFFERSIZE)
        return numpy.fromstring(audio_string, dtype=numpy.int16)

    def record(self):
        while not self.kill_threads:
            for i in range(self.chunks_to_record):
                self.audio[i*self.BUFFERSIZE:(i+1)*self.BUFFERSIZE] = self.get_audio()
            self.has_new_audio = True

    def start(self):
        self.t = threading.Thread(target=self.record)
        self.t.start()

    def fft(self, data=None, trim_by=2, log_scale=False, div_by=100):
        if not data:
            data = self.audio.flatten()
        left, right = numpy.split(numpy.abs(numpy.fft.fft(data)), 2)
        ys = numpy.add(left, right[::-1])
        if log_scale:
            ys = numpy.multiply(20, numpy.log10(ys))
        xs = numpy.arange(self.BUFFERSIZE/2, dtype=float)
        if trim_by:
            i = int((self.BUFFERSIZE/2) / trim_by)
            ys = ys[:i]
            xs = xs[:i] * self.RATE / self.BUFFERSIZE
        if div_by:
            ys = ys / float(div_by)
        return xs, ys
