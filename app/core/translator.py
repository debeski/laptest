import json
from pathlib import Path
from functools import lru_cache

_LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"
_RTL_LANGS = {"ar", "he", "fa", "ur"}

_cache: dict[str, dict] = {}
_current_lang: str = "en"


def set_language(lang: str) -> None:
    global _current_lang
    _current_lang = lang
    _load(lang)


def _load(lang: str) -> dict:
    if lang not in _cache:
        path = _LOCALES_DIR / f"{lang}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _cache[lang] = json.load(f)
        else:
            _cache[lang] = {}
    return _cache[lang]


def tr(key: str, **kwargs) -> str:
    data = _load(_current_lang)
    text = data.get(key)
    if text is None:
        fallback = _load("en")
        text = fallback.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def is_rtl(lang: str | None = None) -> bool:
    return (lang or _current_lang) in _RTL_LANGS


def current_lang() -> str:
    return _current_lang
