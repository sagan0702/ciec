# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import unicodedata
import subprocess
from pathlib import Path

from .constants import IMAGE_EXTS
import sys

_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.strip().replace(" ", "_")
    s = _SAFE_CHARS_RE.sub("", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("._-")
    return s or "arquivo"


def safe_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    i = 1
    while True:
        cand = parent / f"{stem}_{i:02d}{suffix}"
        if not cand.exists():
            return cand
        i += 1


def count_images_in_folder(folder: Path) -> int:
    n = 0
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            n += 1
    return n


# ==============================
# Abrir pasta no Explorer
# ==============================
def open_in_explorer(path: Path) -> None:
    """
    Abre o Explorer do Windows.
    Se for pasta abre a pasta.
    Se for arquivo abre a pasta onde ele está.
    """
    try:
        p = Path(path)
        if p.is_dir():
            os.startfile(str(p))
        else:
            os.startfile(str(p.parent))
    except Exception:
        pass


# ==============================
# Abrir arquivo (ex: log.txt)
# ==============================
def open_file(path: Path) -> None:
    """
    Abre um arquivo no programa padrão do Windows.
    TXT normalmente abre no Notepad.
    """
    try:
        if path.exists():
            os.startfile(str(path))
    except Exception:
        try:
            subprocess.Popen(["notepad.exe", str(path)])
        except Exception:
            pass


def beep_finish() -> None:
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        try:
            import tkinter as tk
            tk._default_root.bell()
        except Exception:
            pass


def resource_path(rel_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]

    return base / rel_path