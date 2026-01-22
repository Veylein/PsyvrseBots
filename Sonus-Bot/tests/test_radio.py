import pytest
from types import SimpleNamespace

from src.commands.music import radio


def test_load_radios_minimal():
    radios = radio._load_radios()
    assert isinstance(radios, dict)
    # repo ships with at least one sample radio
    assert "lofi" in radios


def test_find_radio_by_id_and_name():
    radios = {
        "lofi": {"id": "lofi", "name": "LoFi", "source": "http://example.com"},
        "cafe": {"id": "cafe", "name": "Cafe", "source": "http://example.com"},
    }
    radio._RADIO_CACHE = radios
    assert radio._find_radio("lofi")["id"] == "lofi"
    assert radio._find_radio("LoFi")["id"] == "lofi"
    assert radio._find_radio("Cafe")["id"] == "cafe"
    assert radio._find_radio("unknown") is None

