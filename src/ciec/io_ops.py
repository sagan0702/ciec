# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def write_log_line(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def write_lista_txt(out_base: Path, paths: list[Path]) -> Path:
    lista_path = out_base / "lista.txt"
    paths_sorted = sorted(paths, key=lambda p: str(p).casefold())

    out_base.mkdir(parents=True, exist_ok=True)
    with lista_path.open("w", encoding="utf-8", newline="\n") as f:
        for p in paths_sorted:
            f.write(str(p) + "\n")
    return lista_path