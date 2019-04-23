# python-beat-detector

Real-time detection of beats for audio from an input device (typically "Stereo Mix"). Outputs OSC signals, which can be
used for sound-to-light control.

I use [QLC+](https://github.com/mcallegari/qlcplus) for DMX control.

## Required modules

- PyAudio
- PyQt4
- PyQwt
- matplotlib
- scipy
- python-osc

## Usage

`python beatDetector.py`

Automatically listens to default audio input device.

## OSC Signals

OSC signals are sent to `localhost:7701`, can be changed in `beatDetector.py`.

- `/beat` is sent each time a beat is detected. Ideal for fast light change.
- `/bar` is sent every 8 beats. Ideal for less frequent light change.

## Acknowledgments

Based on [shunfu/python-beat-detector](https://github.com/shunfu/python-beat-detector).