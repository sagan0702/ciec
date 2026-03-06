# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageOps, ImageTk

from .constants import SPLASH_TITLE, splash_image_path


class Splash(ttk.Frame):
    def __init__(self, master: tk.Tk, version: str):
        super().__init__(master, padding=12)
        self.master = master
        self._imgtk = None

        self.master.title(f"{SPLASH_TITLE} v{version}")
        self.master.resizable(False, False)

        ttk.Label(self, text=f"{SPLASH_TITLE} v{version}", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        img_path = splash_image_path()
        if img_path.exists():
            try:
                im = Image.open(img_path)
                im = ImageOps.contain(im, (520, 300), method=Image.Resampling.LANCZOS)
                self._imgtk = ImageTk.PhotoImage(im)
                ttk.Label(self, image=self._imgtk).grid(row=1, column=0, pady=(10, 8))
            except Exception:
                ttk.Label(self, text="(Falha ao carregar imagem do splash)").grid(row=1, column=0, pady=(10, 8))
        else:
            ttk.Label(self, text="(Splash sem imagem)").grid(row=1, column=0, pady=(10, 8))

        ttk.Label(self, text="Carregando…", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=(0, 6))

        pb = ttk.Progressbar(self, mode="indeterminate", length=520)
        pb.grid(row=3, column=0, pady=(0, 2), sticky="ew")
        pb.start(18)

        self.grid(row=0, column=0)
        self._center()

    def _center(self):
        self.master.update_idletasks()
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        sw = self.master.winfo_screenwidth()
        sh = self.master.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.master.geometry(f"{w}x{h}+{x}+{y}")