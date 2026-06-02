import sys
import math
import array
import wave
import tempfile
import threading
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from app.core.translator import tr
from app.ui.base.widgets import AppCard, AppHeading, AppPrimaryButton, AppButton, AppStatusBadge


def _play_tone(freq: float = 440.0, duration: float = 1.0, volume: float = 0.5):
    """Play a pure sine tone. Uses sounddevice if available, falls back to system player."""
    # Prefer sounddevice (cross-platform, no subprocess)
    try:
        import sounddevice as sd
        import numpy as np
        sr = 44100
        t  = np.linspace(0, duration, int(sr * duration), endpoint=False)
        samples = (np.sin(2 * np.pi * freq * t) * volume * 32767).astype(np.int16)
        sd.play(samples, sr)
        sd.wait()
        return
    except Exception:
        pass

    # Fallback: write a WAV file and open with the system player
    try:
        sr = 44100
        raw = array.array("h", (
            int(32767 * volume * math.sin(2 * math.pi * freq * i / sr))
            for i in range(int(sr * duration))
        ))
        tmp = tempfile.mktemp(suffix=".wav")
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(raw.tobytes())
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(tmp, winsound.SND_FILENAME)
            except Exception:
                os.startfile(tmp)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["afplay", tmp])
        else:
            import subprocess
            subprocess.Popen(["aplay", tmp])
    except Exception:
        pass


def _wav_write(path: str, sr: int, data):
    """Write numpy int16 array to a WAV file."""
    import numpy as np
    arr = np.asarray(data)
    if arr.ndim == 2:
        ch = arr.shape[1]
        flat = arr.flatten()
    else:
        ch   = 1
        flat = arr
    with wave.open(path, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(flat.astype(np.int16).tobytes())


def _wav_read(path: str):
    """Read a WAV file, return (sample_rate, numpy_array)."""
    import numpy as np
    with wave.open(path, "rb") as wf:
        sr  = wf.getframerate()
        ch  = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    data = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        data = data.reshape(-1, ch)
    return sr, data


class AudioTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("category_audio"))
        self.resize(560, 360)
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
        for freq, label in [(440, "▶ 440 Hz"), (1000, "▶ 1 kHz"), (300, "▶ Low"), (2000, "▶ High")]:
            btn = AppButton(text=label)
            btn.clicked.connect(
                lambda _, f=freq: threading.Thread(target=_play_tone, args=(f,), daemon=True).start()
            )
            spk_row.addWidget(btn)
        spk_row.addStretch()
        spk.inner_layout().addLayout(spk_row)
        layout.addWidget(spk)

        # Microphone
        mic = AppCard()
        mic.inner_layout().addWidget(AppHeading("audio_microphone", level=3))

        if sys.platform == "darwin":
            note = QLabel("macOS: grant Microphone permission in System Settings → Privacy & Security → Microphone")
            note.setWordWrap(True)
            note.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.5);")
            mic.inner_layout().addWidget(note)

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
            try:
                data = sd.rec(3 * sr, samplerate=sr, channels=1, dtype="int16")
                sd.wait()
                tmp = tempfile.mktemp(suffix=".wav")
                _wav_write(tmp, sr, data)
                self._recorded_file = tmp
                self._mic_status.set_status("pass")
                self._mic_status.setText("Recorded ✓")
                self._play_btn.setEnabled(True)
            except Exception as e:
                self._mic_status.set_status("fail")
                self._mic_status.setText(f"Error: {e}")
            finally:
                self._rec_btn.setEnabled(True)

        threading.Thread(target=do, daemon=True).start()

    def _playback(self):
        if not self._recorded_file:
            return
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            return
        try:
            sr, data = _wav_read(self._recorded_file)
        except Exception:
            return
        self._mic_status.set_status("info")
        self._mic_status.setText(tr("audio_playing"))

        def do():
            try:
                sd.play(data, sr)
                sd.wait()
                self._mic_status.set_status("pass")
                self._mic_status.setText("Done ✓")
            except Exception as e:
                self._mic_status.set_status("fail")
                self._mic_status.setText(f"Error: {e}")

        threading.Thread(target=do, daemon=True).start()
