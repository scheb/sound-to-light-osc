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
beat_idx = 3;
beat_color_idx = 0;
bar_color_idx = 0;

bpm_list = []
prev_beat = perf_counter()
low_freq_avg_list = []
bass_avg_list = []

osc_client = udp_client.SimpleUDPClient("127.0.0.1", 7701)

def plot_audio_and_detect_beats():
    if not input_recorder.has_new_audio:
        return

    # Get x and y values from FFT
    xs, ys = input_recorder.fft()

    # Calculate average for all frequency ranges
    y_avg = numpy.mean(ys)

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
        global prev_beat
        curr_time = perf_counter()
        # print(curr_time - prev_beat)
        if curr_time - prev_beat > 60 / 180:  # 180 BPM max
            # print("bar")
            global beat_idx
            beat_idx += 1;
            if (beat_idx % 4 == 0):
                # print("beat")
                global bass_avg_list
                bass_avg_list.append(bass_avg)
                change_bar_button_text(curr_time, prev_beat)
                change_bar_button_color()
                send_bar_signal()
                # if (bass_idx % 4 == 0):
                #     strongest_beat = bass_avg_list.index(max(bass_avg_list))
                #     print("strongest beat:" + str(strongest_beat));
                #     print(bass_avg_list, bass_avg)
                #     if (numpy.max(bass_avg_list) == bass_avg):

            change_beat_button_text(beat_idx)
            change_beat_button_color()
            send_beat_signal()

            # Reset the timer
            prev_beat = curr_time

            # Remove oldest bass avg value
            if len(bass_avg_list) > 3:
                bass_avg_list = bass_avg_list[1:]

    # Shorten the cumulative list to account for changes in dynamics
    if len(low_freq_avg_list) > 50:
        low_freq_avg_list = low_freq_avg_list[25:]
        # print("REFRESH!!")

    # Keep two 8-counts of BPMs so we can maybe catch tempo changes
    global bpm_list
    if len(bpm_list) > 24:
        bpm_list = bpm_list[8:]

    # Reset song data if the song has stopped
    if y_avg < 100:
        bpm_list = []
        low_freq_avg_list = []
        reset_beat_idx()
        ui.beatButton.setText(_fromUtf8("BPM"))
        ui.barButton.setText(_fromUtf8("Bar: New Song"))


def change_beat_button_text(bar_idx):
    ui.beatButton.setText(_fromUtf8("Beat: {:d}".format(bar_idx % 4 + 1)))


def change_bar_button_text(curr_time, prev_beat):
    global bpm_list
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


def inc_bass_idx():
    global beat_idx
    beat_idx = 3


def reset_beat_idx():
    global beat_idx
    beat_idx = 3


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    window = ui_plot.QtGui.QMainWindow()
    ui = ui_plot.UserInterface()
    ui.setupUi(window, reset_beat_idx, inc_bass_idx)

    ui.timer = QtCore.QTimer()
    ui.timer.start(1.0)
    window.connect(ui.timer, QtCore.SIGNAL('timeout()'), plot_audio_and_detect_beats)

    input_recorder = InputRecorder()
    input_recorder.start()

    ### DISPLAY WINDOWS
    window.show()
    code = app.exec_()

    # clean up
    input_recorder.close()
    sys.exit(code)
