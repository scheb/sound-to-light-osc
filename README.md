sound-to-light-osc
==================

Real-time detection of beats with Python from an audio input device (typically "Stereo Mix"). Outputs OSC signals,
to be used for sound-to-light control.

It keeps track of the music "intensity" (calm, normal, intense) to switch lighting programs.

I use [QLC+](https://github.com/mcallegari/qlcplus) for DMX control.

![Video](video.gif)

Required modules
----------------

- PyAudio
- PyQt5
- PyQwt
- matplotlib
- scipy
- python-osc

Usage
-----

`python beatDetector.py`

OSC Signals
-----------

OSC signals are sent to `localhost:7701`, can be changed in `beatDetector.py`.

- `/beat` is sent for every beat detected.
- `/bar` is sent every to change the lighting scene.
- `/prog1` - `/prog8` is sent to change lighting programs (available have to be configured in `beatDetector.py`)

Contributing
------------

Thanks for your interest in contributing to this project! Glad you like it 😊

I typically do not accept contributions to this project, as I've built this for myself and it just works fine for
me the way it is. The project isn't intended to work for anyone but myself. I've put it onto GitHub in case
someone finds this useful. So if you need changes, feel free to fork the repository and modify it for your own
needs.

If you have an idea that you believe is worth integrating, please reach out first. I don't want you to work on 
things that I wouldn't merge.

Acknowledgments
---------------

Based on [shunfu/python-beat-detector](https://github.com/shunfu/python-beat-detector).

Version History
---------------

### 1.0

- Beat detection
- Automatic beat generation based on BPM
- Pause and new song detection

### 1.1

- Improved max volume calibration
- Improved pause detection
- Intensity detection
- Automatic lighting program switch

License
-------
This software is available under the [MIT license](LICENSE).

Support Me
----------
I love to hear from people using my work, it's giving me the motivation to keep working on it.

If you want to let me know you're finding it useful, please consider giving it a star ⭐ on GitHub.

If you love my work and want to say thank you, you can help me out for a beer 🍻️
[via PayPal](https://paypal.me/ChristianScheb).
