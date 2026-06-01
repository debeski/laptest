from PyQt6.QtCore import QThread, pyqtSignal
from typing import Callable, Any


class Worker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            out = self._fn(*self._args, **self._kwargs)
            self.result.emit(out)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class MultiWorker(QThread):
    """Runs a list of (key, callable) pairs sequentially, emitting per-step."""
    step_done = pyqtSignal(str, object)
    all_done = pyqtSignal()
    progress = pyqtSignal(int, int, str)

    def __init__(self, tasks: list[tuple[str, Callable]]):
        super().__init__()
        self._tasks = tasks
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total = len(self._tasks)
        for i, (key, fn) in enumerate(self._tasks):
            if self._stop:
                break
            self.progress.emit(i, total, key)
            try:
                result = fn()
            except Exception as e:
                result = []
            self.step_done.emit(key, result)
        self.all_done.emit()
