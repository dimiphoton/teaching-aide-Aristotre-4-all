"""Chargement de la configuration du kiosque (TOML validé par pydantic)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_CONFIG_PATH = Path("/etc/aristote/config.toml")


class KioskConfig(BaseModel):
    id: str = "K01"
    students: list[str] = Field(default_factory=lambda: ["E01", "E02", "E03", "E04"])

    @field_validator("id")
    @classmethod
    def _id_is_path_safe(cls, value: str) -> str:
        if not value or not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("kiosk.id ne doit contenir que des lettres, chiffres, - et _")
        return value

    @field_validator("students")
    @classmethod
    def _students_are_pseudonyms(cls, value: list[str]) -> list[str]:
        if not 1 <= len(value) <= 4:
            raise ValueError("un kiosque accueille de 1 à 4 élèves")
        if len(set(value)) != len(value):
            raise ValueError("pseudonymes en double")
        for pseudo in value:
            if not pseudo.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"pseudonyme invalide : {pseudo!r}")
        return value


class ButtonsConfig(BaseModel):
    backend: Literal["gpio", "keyboard"] = "gpio"
    student_pins: list[int] = Field(default_factory=lambda: [5, 6, 13, 19])
    scan_pin: int = 26
    long_press_s: float = 3.0
    bounce_s: float = 0.05


class LedsConfig(BaseModel):
    enabled: bool = True
    student_pins: list[int] = Field(default_factory=lambda: [12, 16, 20, 21])
    scan_pin: int = 25


class CameraConfig(BaseModel):
    backend: Literal["picamera2", "opencv", "mock"] = "picamera2"
    width: int = 4608
    height: int = 2592
    opencv_device: int = 0
    deskew: bool = True


class PrinterConfig(BaseModel):
    enabled: bool = True
    port: str = "/dev/aristote-printer"
    baudrate: int = 19200
    heat_dots: int = Field(11, ge=0, le=255)
    heat_time: int = Field(120, ge=3, le=255)
    heat_interval: int = Field(40, ge=0, le=255)
    density: int = Field(10, ge=0, le=31)
    break_time: int = Field(2, ge=0, le=7)
    dot_print_time_s: float = 0.0033
    dot_feed_time_s: float = 0.0021


class MicrophoneConfig(BaseModel):
    backend: Literal["sounddevice", "mock"] = "sounddevice"
    device: str = ""
    samplerate: int = 16000
    max_seconds: int = 60


class HardwareConfig(BaseModel):
    mode: Literal["real", "mock"] = "real"
    buttons: ButtonsConfig = Field(default_factory=ButtonsConfig)
    leds: LedsConfig = Field(default_factory=LedsConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    printer: PrinterConfig = Field(default_factory=PrinterConfig)
    microphone: MicrophoneConfig = Field(default_factory=MicrophoneConfig)


class StorageConfig(BaseModel):
    vault_dir: Path = Path("/var/lib/aristote/vault")
    eval_corpus_dir: Path = Path("/var/lib/aristote/eval_corpus")
    keep_scans: bool = False
    eval_capture: bool = False
    eval_retention_days: int = 90


class SessionConfig(BaseModel):
    idle_timeout_s: int = 600


class Config(BaseModel):
    kiosk: KioskConfig = Field(default_factory=KioskConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)

    @model_validator(mode="after")
    def _one_button_per_student(self) -> "Config":
        n = len(self.kiosk.students)
        if len(self.hardware.buttons.student_pins) < n:
            raise ValueError("il faut au moins une broche de bouton par élève")
        if self.hardware.leds.enabled and len(self.hardware.leds.student_pins) < n:
            raise ValueError("il faut au moins une broche de LED par élève")
        return self

    @property
    def kiosk_vault_dir(self) -> Path:
        """Dossier propre à ce kiosque dans le coffre synchronisé."""
        return self.storage.vault_dir / self.kiosk.id


def load_config(path: Path | str | None = None) -> Config:
    """Charge la configuration depuis `path`, $ARISTOTE_CONFIG ou /etc/aristote/config.toml.

    Si aucun fichier n'existe, renvoie la configuration par défaut.
    `ARISTOTE_MOCK=1` force le mode simulation (développement sur PC).
    """
    candidate = Path(path or os.environ.get("ARISTOTE_CONFIG") or DEFAULT_CONFIG_PATH)
    data: dict = {}
    if candidate.exists():
        with candidate.open("rb") as fh:
            data = tomllib.load(fh)
    config = Config.model_validate(data)
    if os.environ.get("ARISTOTE_MOCK") == "1":
        config = mock_config(config)
    return config


def mock_config(base: Config | None = None) -> Config:
    """Copie de la configuration avec tous les périphériques simulés."""
    config = (base or Config()).model_copy(deep=True)
    config.hardware.mode = "mock"
    config.hardware.camera.backend = "mock"
    config.hardware.microphone.backend = "mock"
    return config
