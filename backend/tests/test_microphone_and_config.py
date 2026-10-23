import io
import wave

import numpy as np
import pytest

from aristote.config import Config, load_config, mock_config
from aristote.hardware import build_hardware
from aristote.hardware.microphone import MockMicrophone, to_wav


def test_wav_encoding():
    wav = to_wav(np.arange(1600, dtype=np.int16), 16000)
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 1600)


def test_mock_microphone_cycle():
    mic = MockMicrophone()
    mic.start()
    assert mic.recording
    assert mic.stop()[:4] == b"RIFF" and not mic.recording


def test_example_config_is_valid():
    from pathlib import Path

    config = load_config(Path(__file__).parents[1] / "config.example.toml")
    assert config.kiosk.students == ["E01", "E02", "E03", "E04"]
    assert config.kiosk_vault_dir.name == "K01"


@pytest.mark.parametrize("data", [
    {"kiosk": {"id": "../evil"}},
    {"kiosk": {"students": ["E01", "E01"]}},
    {"kiosk": {"students": ["Jean Dupont"]}},
    {"kiosk": {"students": ["E1", "E2", "E3", "E4", "E5"]}},
    {"hardware": {"buttons": {"student_pins": [5, 6]}}},
])
def test_invalid_configs_are_rejected(data):
    with pytest.raises(ValueError):
        Config.model_validate(data)


def test_mock_hardware_builds_without_pi_libraries():
    hw = build_hardware(mock_config())
    assert hw.camera.capture().page_found
    hw.printer.print_ticket(__import__("aristote.hardware.printer_csn_a2", fromlist=["Ticket"]).Ticket())
    hw.close()
