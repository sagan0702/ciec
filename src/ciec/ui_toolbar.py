from __future__ import annotations

import base64
import io
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from PIL import Image, ImageTk


# ÍCONES PNG (24x24) EMBUTIDOS EM BASE64 (sem arquivos externos)
_ICON_B64 = {
    "PLAY": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAATUlEQVR4nO2VsQ2AMAxD/0JXyB0S8Ywqk3bZgQHcQnY4Jr2nYhLZg2QZVgqQ+f9nQq1y8iFJHkzq5A8pX9BvJm2c9mQAAAABJRU5ErkJggg==",
    "STOP": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAOElEQVR4nO2VsQ0AIAhD/0k3kY2QyQx4cYf0jQ2QnUu0Gm2mVqk6m5Qm2b1y8wQAAAABJRU5ErkJggg==",
    "VALIDATE": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAbElEQVR4nO2VsQ2AMAxD/0JXyB0S8Ywqk3bZgQHcQnY4Jr2nYhLZg2QZVgqQ+f9nQq1y8iFJHkzq5A8pX9BvJm2c9mQz5h8cYc1gq4m2t8ZqAAAAAElFTkSuQmCC",
    "FOLDER": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAU0lEQVR4nO2VsQ2AMAxD/0JXyB0S8Ywqk3bZgQHcQnY4Jr2nYhLZg2QZVgqQ+f9nQq1y8iFJHkzq5A8pX9BvJm2c9mQAAAABJRU5ErkJggg==",
    "LOG": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAVElEQVR4nO2VsQ0AIAhD/0k3kY2QyQx4cYf0jQ2QnUu0Gm2mVqk6m5Qm2b1y8wRkqQm2b1y8wQAAAABJRU5ErkJggg==",
    "HELP": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAaUlEQVR4nO2VsQ2AMAxD/0JXyB0S8Ywqk3bZgQHcQnY4Jr2nYhLZg2QZVgqQ+f9nQq1y8iFJHkzq5A8pX9BvJm2c9mQz9m2cYd0AAAAAElFTkSuQmCC",
    "EXIT": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAWUlEQVR4nO2VsQ2AMAxD/0JXyB0S8Ywqk3bZgQHcQnY4Jr2nYhLZg2QZVgqQ+f9nQq1y8iFJHkzq5A8pX9BvJm2c9mQAAAABJRU5ErkJggg==",
}


def _icon_from_b64(b64_png: str, size: int = 24) -> ImageTk.PhotoImage:
    raw = base64.b64decode(b64_png.encode("ascii"))
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    if img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


class CommandBar(ttk.Frame):
    """
    Barra de botões na ordem:
    Processar | Parar | Validar imagens | Abrir saída | Ver Log | Ajuda | Sair

    - Ícones PNG embutidos (Base64) => funciona no PyInstaller sem arquivos extras
    - Botões ttk com compound='left'
    """

    def __init__(
        self,
        master,
        on_processar: Callable[[], None],
        on_parar: Callable[[], None],
        on_validar: Callable[[], None],
        on_abrir_saida: Callable[[], None],
        on_ver_log: Callable[[], None],
        on_ajuda: Callable[[], None],
        on_sair: Callable[[], None],
    ):
        super().__init__(master)
        self._callbacks = {
            "processar": on_processar,
            "parar": on_parar,
            "validar": on_validar,
            "abrir_saida": on_abrir_saida,
            "ver_log": on_ver_log,
            "ajuda": on_ajuda,
            "sair": on_sair,
        }

        # manter referências dos ícones (senão some)
        self._icons: dict[str, ImageTk.PhotoImage] = {}
        self._buttons: dict[str, ttk.Button] = {}

        self._setup_style()
        self._build()

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.configure("CIEC.Toolbar.TButton", padding=(14, 10), font=("Segoe UI", 10))
        style.configure("CIEC.Toolbar.TFrame", padding=(8, 8))

    def _btn(self, key: str, text: str, icon_key: str, command: Callable[[], None]) -> ttk.Button:
        self._icons[icon_key] = _icon_from_b64(_ICON_B64[icon_key], size=24)
        b = ttk.Button(
            self,
            text=text,
            image=self._icons[icon_key],
            compound="left",
            command=command,
            style="CIEC.Toolbar.TButton",
            takefocus=False,
        )
        self._buttons[key] = b
        return b

    def _build(self) -> None:
        self.configure(style="CIEC.Toolbar.TFrame")

        # Ordem e disposição IGUAL à imagem
        items = [
            ("processar", "Processar", "PLAY", self._callbacks["processar"]),
            ("parar", "Parar", "STOP", self._callbacks["parar"]),
            ("validar", "Validar imagens", "VALIDATE", self._callbacks["validar"]),
            ("abrir_saida", "Abrir saída", "FOLDER", self._callbacks["abrir_saida"]),
            ("ver_log", "Ver Log", "LOG", self._callbacks["ver_log"]),
            ("ajuda", "Ajuda", "HELP", self._callbacks["ajuda"]),
            ("sair", "Sair", "EXIT", self._callbacks["sair"]),
        ]

        for i, (key, label, icon, cmd) in enumerate(items):
            b = self._btn(key, label, icon, cmd)
            b.pack(side="left", padx=(0 if i == 0 else 10, 0))

        # estado inicial recomendado
        self.set_running(False)

    def set_running(self, running: bool) -> None:
        """
        running=True:
          - Parar habilitado
          - Processar/Validar desabilitados (evita clicar de novo)
        running=False:
          - Parar desabilitado
          - Processar/Validar habilitados
        """
        if running:
            self._buttons["processar"].state(["disabled"])
            self._buttons["validar"].state(["disabled"])
            self._buttons["parar"].state(["!disabled"])
        else:
            self._buttons["processar"].state(["!disabled"])
            self._buttons["validar"].state(["!disabled"])
            self._buttons["parar"].state(["disabled"])