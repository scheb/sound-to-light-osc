import ui_plot
import sys
import numpy
from PyQt4 import QtCore, QtGui
import PyQt4.Qwt5 as Qwt
from recorder import *
from time import perf_counter

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

colors_list = ["red", "yellow", "green"]
beat_idx = 0;
colors_idx = 0;

bpm_list = []
prev_beat = perf_counter()
low_freq_avg_list = []

def plot_audio_and_detect_beats():
    if not input_recorder.has_new_audio: 
        return

    # Get x and y values from FFT
    xs, ys = input_recorder.fft()

    # Calculate average for all frequency ranges
    y_avg = numpy.mean(ys)

    # Calculate low frequency average
    low_freq = [ys[i] for i in range(len(xs)) if xs[i] < 1000]
    low_freq_avg = numpy.mean(low_freq)
    
    global low_freq_avg_list
    low_freq_avg_list.append(low_freq_avg)
    cumulative_avg = numpy.mean(low_freq_avg_list)
    
    bass = low_freq[:int(len(low_freq)/2)]
    bass_avg = numpy.mean(bass)
    # print("bass: {:.2f} vs cumulative: {:.2f}".format(bass_avg, cumulative_avg))

    # Check if there is a beat
    # Song is pretty uniform across all frequencies
    if (y_avg > 10 and (bass_avg > cumulative_avg * 1.5 or (low_freq_avg < y_avg * 1.2 and bass_avg > cumulative_avg))):
        global prev_beat
        curr_time = perf_counter()
        # print(curr_time - prev_beat)
        if curr_time - prev_beat > 60/180: # 180 BPM max
            # print("beat")
            # change the button color
            global beat_idx
            beat_idx += 1;
            # if beat_idx % 4 == 0:
            global colors_idx
            colors_idx += 1;
            uiplot.bpmButton.setStyleSheet("background-color: {:s}".format(colors_list[colors_idx % len(colors_list)]))
            
            # Change the button text
            global bpm_list
            bpm = int(60 / (curr_time - prev_beat))
            if len(bpm_list) < 4:
                if bpm > 60:
                    bpm_list.append(bpm)
            else:
                bpm_avg = int(numpy.mean(bpm_list))
                if abs(bpm_avg - bpm) < 35:
                    bpm_list.append(bpm)
                uiplot.bpmButton.setText(_fromUtf8("BPM: {:d}".format(bpm_avg)))
            
            # Reset the timer
            prev_beat = curr_time
    
    # Shorten the cumulative list to account for changes in dynamics
    if len(low_freq_avg_list) > 50:
        low_freq_avg_list = low_freq_avg_list[25:]
        # print("REFRESH!!")

    # Keep two 8-counts of BPMs so we can maybe catch tempo changes
    if len(bpm_list) > 24:
        bpm_list = bpm_list[8:]

    # Reset song data if the song has stopped
    if y_avg < 10:
        bpm_list = []
        low_freq_avg_list = []
        uiplot.bpmButton.setText(_fromUtf8("BPM"))
        # print("new song")

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    
    win_plot = ui_plot.QtGui.QMainWindow()
    uiplot = ui_plot.Ui_win_plot()
    uiplot.setupUi(win_plot)

    uiplot.timer = QtCore.QTimer()
    uiplot.timer.start(1.0)
    win_plot.connect(uiplot.timer, QtCore.SIGNAL('timeout()'), plot_audio_and_detect_beats) 

    input_recorder = InputRecorder()
    input_recorder.start()

    ### DISPLAY WINDOWS
    win_plot.show()
    code = app.exec_()

    # clean up
    input_recorder.close()
    sys.exit(code)
