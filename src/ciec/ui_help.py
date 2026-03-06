# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .constants import manual_pdf_path
from .utils import open_file


class HelpWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, version: str):
        super().__init__(master)

        self.title(f"Ajuda — CIEC v{version}")
        self.resizable(False, False)

        # Conteúdo
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttl = ttk.Label(frm, text="Ajuda do CIEC", font=("Segoe UI", 14, "bold"))
        ttl.pack(anchor="center", pady=(0, 10))

        texto = (
            "• O CIEC converte imagens para o padrão 161×225.\n"
            "• Selecione a pasta das fotos.\n"
            "• Clique em 'Iniciar processamento'.\n\n"
            "O manual completo pode ser aberto pelo botão abaixo."
        )
        lbl = ttk.Label(frm, text=texto, justify="left")
        lbl.pack(anchor="w", pady=(0, 12))

        btn = ttk.Button(frm, text="Abrir manual (PDF)", command=self._abrir_manual)
        btn.pack(anchor="center")

        # Centraliza a janela (depois de montar)
        self.after(10, self._centralizar)

    def _abrir_manual(self):
        p = manual_pdf_path()
        if p and Path(p).exists():
            open_file(Path(p))
        else:
            tk.messagebox.showwarning("CIEC", "Manual não encontrado.")

    def _centralizar(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()

        # centraliza em cima da janela principal quando possível
        try:
            mw = self.master.winfo_width()
            mh = self.master.winfo_height()
            mx = self.master.winfo_rootx()
            my = self.master.winfo_rooty()
            x = mx + (mw // 2) - (w // 2)
            y = my + (mh // 2) - (h // 2)
        except Exception:
            x = (self.winfo_screenwidth() // 2) - (w // 2)
            y = (self.winfo_screenheight() // 2) - (h // 2)

        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
