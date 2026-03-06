# src/ciec/constants.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import sys

APP_TITLE = "CIEC — Conversor de Imagens de Eleições Comunitárias"
SPLASH_TITLE = "CIEC - Conversor de Imagens de Eleições Comunitárias"

FIXED_W = 161
FIXED_H = 225
FIXED_TARGET = (FIXED_W, FIXED_H)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}

DEFAULTS = {
    "QUALIDADE": 90,
    "AUTO_BRIGHT": 1,
    "IGNORAR_SAIDA": 1,
    "MODO_TESTE": 0,
    "LAST_INPUT": "",
    "LAST_OUTPUT": "",
}

VERSION_FALLBACK = "1.0.0"
SPLASH_MIN_MS = 800

def _bundle_root() -> Path:
    # Onde o PyInstaller extrai (onefile) ou raiz do projeto (dev)
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # constants.py = ...\src\ciec\constants.py -> raiz do projeto = parents[2]
    return Path(__file__).resolve().parents[2]

def exe_dir() -> Path:
    # Onde está o .exe (ou, em dev, a raiz do projeto)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _bundle_root()

def assets_dir() -> Path:
    return _bundle_root() / "assets"

def splash_image_path() -> Path:
    return assets_dir() / "images" / "splash.png"

def manual_pdf_path() -> Path:
    return assets_dir() / "docs" / "manual.pdf"

def default_config_path() -> Path:
    return assets_dir() / "config" / "config.ini"

def config_path() -> Path:
    # Config editável ao lado do EXE
    return exe_dir() / "config.ini"

def version_path() -> Path:
    # Version editável ao lado do EXE
    return exe_dir() / "VERSION.txt"

def manual_pdf_path() -> Path:
    # 1) Preferir manual “ao lado do EXE” (para distribuição)
    p1 = exe_dir() / "assets" / "docs" / "manual.pdf"
    if p1.exists():
        return p1
    # 2) Fallback: manual embutido no bundle (onefile/_MEIPASS)
    return assets_dir() / "docs" / "manual.pdf"