import math
import array
import wave
import tempfile
import threading
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from app.core.translator import tr
from app.ui.base.widgets import AppCard, AppHeading, AppPrimaryButton, AppButton, AppStatusBadge


def _play_tone(freq: float = 440.0, duration: float = 1.0, volume: float = 0.5):
    try:
        import winsound
        winsound.Beep(int(freq), int(duration * 1000))
        return
    except Exception:
        pass
    try:
        sample_rate = 44100
        samples = array.array("h", (
            int(32767 * volume * math.sin(2 * math.pi * freq * i / sample_rate))
            for i in range(int(sample_rate * duration))
        ))
        tmp = tempfile.mktemp(suffix=".wav")
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        if os.name == "nt":
            os.startfile(tmp)
        else:
            import subprocess
            subprocess.Popen(["aplay", tmp])
    except Exception:
        pass


def _wav_write(path, sr, data):
    import numpy as np
    with wave.open(path, "wb") as wf:
        ch = 1 if data.ndim == 1 else data.shape[1]
        wf.setnchannels(ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.astype("int16").tobytes())


def _wav_read(path):
    import numpy as np
    with wave.open(path, "rb") as wf:
        sr, ch = wf.getframerate(), wf.getnchannels()
        frames = wf.readframes(wf.getnframes())
    data = np.frombuffer(frames, dtype="int16")
    return sr, (data.reshape(-1, ch) if ch > 1 else data)


class AudioTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("category_audio"))
        self.resize(540, 320)
        self._recorded_file = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        layout.addWidget(AppHeading("category_audio", level=2))

        # Speakers
        spk = AppCard()
        spk.inner_layout().addWidget(AppHeading("audio_speakers", level=3))
        spk_row = QHBoxLayout()
        for freq, label in [(440, "▶ 440 Hz"), (1000, "▶ 1 kHz"), (300, "◀ Low"), (2000, "▶ High")]:
            btn = AppButton(text=label)
            btn.clicked.connect(lambda _, f=freq: threading.Thread(target=_play_tone, args=(f,), daemon=True).start())
            spk_row.addWidget(btn)
        spk_row.addStretch()
        spk.inner_layout().addLayout(spk_row)
        layout.addWidget(spk)

        # Microphone
        mic = AppCard()
        mic.inner_layout().addWidget(AppHeading("audio_microphone", level=3))
        mic_row = QHBoxLayout()
        self._rec_btn  = AppPrimaryButton(text="⏺  Record 3 s")
        self._play_btn = AppButton(text="▶  Play Back")
        self._play_btn.setEnabled(False)
        self._mic_status = AppStatusBadge("info", "Ready")
        mic_row.addWidget(self._rec_btn)
        mic_row.addWidget(self._play_btn)
        mic_row.addStretch()
        mic_row.addWidget(self._mic_status)
        mic.inner_layout().addLayout(mic_row)
        layout.addWidget(mic)

        self._rec_btn.clicked.connect(self._record)
        self._play_btn.clicked.connect(self._playback)

    def _record(self):
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self._mic_status.set_status("warn")
            self._mic_status.setText("sounddevice not installed")
            return
        self._mic_status.set_status("running")
        self._mic_status.setText(tr("audio_recording"))
        self._rec_btn.setEnabled(False)
        sr = 44100

        def do():
            data = sd.rec(3 * sr, samplerate=sr, channels=1, dtype="int16")
            sd.wait()
            tmp = tempfile.mktemp(suffix=".wav")
            _wav_write(tmp, sr, data)
            self._recorded_file = tmp
            self._mic_status.set_status("pass")
            self._mic_status.setText("Recorded ✓")
            self._rec_btn.setEnabled(True)
            self._play_btn.setEnabled(True)

        threading.Thread(target=do, daemon=True).start()

    def _playback(self):
        if not self._recorded_file:
            return
        try:
            import sounddevice as sd
        except ImportError:
            return
        sr, data = _wav_read(self._recorded_file)
        self._mic_status.set_status("info")
        self._mic_status.setText(tr("audio_playing"))

        def do():
            sd.play(data, sr)
            sd.wait()
            self._mic_status.set_status("pass")
            self._mic_status.setText("Done ✓")

        threading.Thread(target=do, daemon=True).start()
