# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk

from .config_io import read_version
from .ui_splash import Splash
from .ui_app import App
from .constants import SPLASH_MIN_MS

def main():
    root = tk.Tk()

    version = read_version()
    splash_frame = Splash(root, version)

    start_time = int(root.tk.call("clock", "milliseconds"))

    def show_app():
        now = int(root.tk.call("clock", "milliseconds"))
        elapsed = now - start_time
        wait_more = max(0, SPLASH_MIN_MS - elapsed)

        def _switch():
            splash_frame.destroy()
            app = App(root, version)
            app.grid(row=0, column=0, sticky="nsew")

            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            root.geometry(f"{w}x{h}+{x}+{y}")

        root.after(wait_more, _switch)

    root.after(3000, show_app)
    root.mainloop()


if __name__ == "__main__":
    main()
