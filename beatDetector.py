import random

import ui_plot
import sys
from PyQt4 import QtCore, QtGui
from recorder import *
from time import perf_counter
from pythonosc import udp_client

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

colors_list = ["red", "yellow", "green", "orange", "white", "cyan"]
bar_modulo = 8

beat_idx = bar_modulo-1;
beat_color_idx = 0;
bar_color_idx = 0;
curr_time = 0

bpm_list = []
prev_beat = perf_counter()
low_freq_avg_list = []
y_avg_list = []

osc_client = udp_client.SimpleUDPClient("127.0.0.1", 7701)

def plot_audio_and_detect_beats():
    if not input_recorder.has_new_audio:
        return

    # Get x and y values from FFT
    xs, ys = input_recorder.fft()

    # Calculate average for all frequency ranges
    global y_avg_list
    y_avg = numpy.mean(ys)
    y_avg_list.append(y_avg)

    # Calculate low frequency average
    low_freq = [ys[i] for i in range(len(xs)) if xs[i] < 500]
    low_freq_avg = numpy.mean(low_freq)

    # Calculate recent low frequency average
    global low_freq_avg_list
    low_freq_avg_list.append(low_freq_avg)
    cumulative_avg = numpy.mean(low_freq_avg_list)

    bass = low_freq[:int(len(low_freq) / 2)]
    bass_avg = numpy.mean(bass)
    # print("bass: {:.2f} vs cumulative: {:.2f}".format(bass_avg, cumulative_avg))

    # Check if there is a beat
    # Song is pretty uniform across all frequencies
    if (y_avg > 1000 and (bass_avg > cumulative_avg * 1.5 or (low_freq_avg < y_avg * 1.2 and bass_avg > cumulative_avg))):
        global prev_beat, curr_time
        curr_time = perf_counter()
        # print(curr_time - prev_beat)
        if curr_time - prev_beat > 60 / 180:  # 180 BPM max
            track_beat()

            # Reset the timer
            prev_beat = curr_time

    # Shorten the cumulative list to account for changes in dynamics
    if len(low_freq_avg_list) > 50:
        low_freq_avg_list = low_freq_avg_list[25:]
        # print("REFRESH!!")
    
    # Shorten avg list
    if len(y_avg_list) > 24:
        y_avg_list = y_avg_list[24:]

    # Keep two 8-counts of BPMs so we can maybe catch tempo changes
    global bpm_list
    if len(bpm_list) > 24:
        bpm_list = bpm_list[8:]

    # Reset song data if the song has stopped
    y_avg_mean = numpy.mean(y_avg_list)
    # print(y_avg, y_avg_mean)
    if y_avg < 100 or y_avg < y_avg_mean / 50:
        reset_new_song()


def reset_new_song():
    global bpm_list, low_freq_avg_list, y_avg_mean, beat_idx, bar_modulo
    bpm_list = []
    low_freq_avg_list = []
    y_avg_mean = []
    beat_idx = bar_modulo-1
    ui.beatButton.setText(_fromUtf8("BPM"))
    ui.barButton.setText(_fromUtf8("Bar: New Song"))

def track_beat():
    print("beat")
    global beat_idx, bar_modulo
    beat_idx += 1;
    if (beat_idx % bar_modulo == 0):
        track_bar()

    change_beat_button_text()
    change_beat_button_color()
    send_beat_signal()

def track_bar():
    print("bar")
    change_bar_button_text()
    change_bar_button_color()
    send_bar_signal()

def change_beat_button_text():
    global beat_idx, bar_modulo
    ui.beatButton.setText(_fromUtf8("Beat: {:d}".format(beat_idx % bar_modulo + 1)))


def change_bar_button_text():
    global bpm_list, curr_time, prev_beat
    bpm = int(60 / (curr_time - prev_beat))
    if len(bpm_list) < 4:
        if bpm > 60:
            bpm_list.append(bpm)
    else:
        bpm_avg = int(numpy.mean(bpm_list))
        if abs(bpm_avg - bpm) < 35:
            bpm_list.append(bpm)
        ui.barButton.setText(_fromUtf8("BPM: {:d}".format(bpm_avg)))


def change_beat_button_color():
    global beat_color_idx
    beat_color_idx += 1;
    ui.beatButton.setStyleSheet("background-color: {:s}; font-size: 18pt".format(colors_list[beat_color_idx % len(colors_list)]))


def change_bar_button_color():
    global bar_color_idx
    bar_color_idx += 1;
    ui.barButton.setStyleSheet("background-color: {:s}; font-size: 18pt".format(colors_list[bar_color_idx % len(colors_list)]))


def send_beat_signal():
    global osc_client
    # print("send beat signal")
    osc_client.send_message("/beat", 1.0);
    osc_client.send_message("/beat", 0.0);


def send_bar_signal():
    global osc_client
    # print("send bar signal")
    osc_client.send_message("/bar", 1.0);
    osc_client.send_message("/bar", 0.0);


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    window = ui_plot.QtGui.QMainWindow()
    ui = ui_plot.UserInterface()
    ui.setupUi(window)

    ui.timer = QtCore.QTimer()
    ui.timer.start(50.0)
    window.connect(ui.timer, QtCore.SIGNAL('timeout()'), plot_audio_and_detect_beats)

    input_recorder = InputRecorder()
    input_recorder.start()

    ### DISPLAY WINDOWS
    window.show()
    code = app.exec_()

    # clean up
    input_recorder.close()
    sys.exit(code)
