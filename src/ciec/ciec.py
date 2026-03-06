# -*- coding: utf-8 -*-
"""
ciec_gui.py — CIEC - Conversor de Imagens de Eleições Comunitárias

Mudanças solicitadas:
- Saída padrão (quando "Saída" estiver vazia):
    -> cria/usa a pasta: <PASTA_PAI_DA_ENTRADA>\convertidos\
    -> NÃO cria mais PROCESSADAS_161x225
- Saída escolhida pelo usuário (campo "Saída"):
    -> cria/usa: <PASTA_ESCOLHIDA>\convertidos\
- Mantém geração de:
    - log_processamento_YYYYMMDD_HHMMSS.txt (na pasta BASE, não dentro de convertidos)
    - lista.txt (na pasta BASE, não dentro de convertidos), com 1 caminho completo por linha
- Pop-up final (resumo) mostra apenas:
    OK, Falhas, Ignorados, Total processado, Tempo
"""

from __future__ import annotations

import configparser
import os
import re
import threading
import queue
import unicodedata
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError, ImageTk


# =========================================================
# CONTROLE DE VERSÃO (FIXO - você edita VERSION.txt)
# =========================================================
VERSION_FALLBACK = "1.0.0"


def version_path() -> Path:
    return Path(__file__).parent / "VERSION.txt"


def read_version() -> str:
    p = version_path()
    try:
        v = p.read_text(encoding="utf-8").strip()
        if v:
            return v
    except Exception:
        pass
    return VERSION_FALLBACK


__version__ = read_version()


# =========================================================
# CONSTANTES / APP
# =========================================================
APP_TITLE = "CIEC — Conversor de Imagens de Eleições Comunitárias"
SPLASH_TITLE = "CIEC - Conversor de Imagens de Eleições Comunitárias"
SPLASH_IMAGE_PATH = Path(__file__).parent / "assets" / "splash.png"  # opcional
SPLASH_MIN_MS = 800

FIXED_W = 161
FIXED_H = 225
FIXED_TARGET = (FIXED_W, FIXED_H)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}

DEFAULTS = {
    "QUALIDADE": 90,
    "AUTO_BRIGHT": 1,
    "IGNORAR_SAIDA": 1,
    "MODO_TESTE": 0,
}


@dataclass
class Counters:
    total_files: int = 0
    tried: int = 0
    ok: int = 0
    not_image: int = 0
    failed: int = 0


def config_path() -> Path:
    return Path(__file__).parent / "config.ini"


def assets_dir() -> Path:
    return Path(__file__).parent / "assets"


def manual_path() -> Path:
    return assets_dir() / "manual.txt"


def escrever_config_padrao(path: Path) -> None:
    cfg = configparser.ConfigParser()
    cfg["GERAL"] = {
        "QUALIDADE": str(DEFAULTS["QUALIDADE"]),
        "AUTO_BRIGHT": str(DEFAULTS["AUTO_BRIGHT"]),
        "IGNORAR_SAIDA": str(DEFAULTS["IGNORAR_SAIDA"]),
        "MODO_TESTE": str(DEFAULTS["MODO_TESTE"]),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        cfg.write(f)


def carregar_config_ou_criar() -> dict:
    p = config_path()
    if not p.exists():
        escrever_config_padrao(p)

    cfg = configparser.ConfigParser()
    cfg.read(p, encoding="utf-8")
    g = cfg["GERAL"] if "GERAL" in cfg else {}

    def geti(k: str, default: int) -> int:
        try:
            return int(str(g.get(k, default)).strip())
        except Exception:
            return default

    return {
        "QUALIDADE": max(1, min(geti("QUALIDADE", DEFAULTS["QUALIDADE"]), 95)),
        "AUTO_BRIGHT": 1 if geti("AUTO_BRIGHT", DEFAULTS["AUTO_BRIGHT"]) else 0,
        "IGNORAR_SAIDA": 1 if geti("IGNORAR_SAIDA", DEFAULTS["IGNORAR_SAIDA"]) else 0,
        "MODO_TESTE": 1 if geti("MODO_TESTE", DEFAULTS["MODO_TESTE"]) else 0,
    }


def salvar_config(conf: dict) -> None:
    p = config_path()
    cfg = configparser.ConfigParser()
    cfg["GERAL"] = {
        "QUALIDADE": str(conf["QUALIDADE"]),
        "AUTO_BRIGHT": "1" if conf["AUTO_BRIGHT"] else "0",
        "IGNORAR_SAIDA": "1" if conf["IGNORAR_SAIDA"] else "0",
        "MODO_TESTE": "1" if conf["MODO_TESTE"] else "0",
    }
    with p.open("w", encoding="utf-8") as f:
        cfg.write(f)


def write_log_line(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


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


_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.strip().replace(" ", "_")
    s = _SAFE_CHARS_RE.sub("", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("._-")
    return s or "arquivo"


# =========================================================
# SAÍDA: BASE + CONVERTIDOS
# =========================================================

def get_out_base(src_root: Path, out_str: str) -> Path:
    """
    Se o usuário escolher uma pasta em 'Saída', usamos ela como BASE.
    Se 'Saída' estiver vazia, BASE = pasta pai da entrada.

    Ex.: src_root = D:\Projetos\CIEC
         BASE = D:\Projetos
         convertidos = D:\Projetos\convertidos
    """
    if out_str.strip():
        return Path(out_str).resolve()
    return src_root.parent.resolve()


def get_convertidos_dir(out_base: Path) -> Path:
    return out_base / "convertidos"


def build_output_path_flat(src_file: Path, convertidos_dir: Path) -> Path:
    """
    Saída achatada dentro de convertidos_dir (sem subpastas).
    """
    nome = normalize_name(src_file.stem)
    return convertidos_dir / f"{nome}.jpg"


# =========================================================
# AUTO BRILHO
# =========================================================

def mean_luminance_rgb(im_rgb: Image.Image) -> float:
    g = im_rgb.convert("L")
    hist = g.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    s = 0
    for i, c in enumerate(hist):
        s += i * c
    return s / total


def auto_brightness(im_rgb: Image.Image) -> tuple[Image.Image, str]:
    im2 = ImageOps.autocontrast(im_rgb, cutoff=1)
    m = mean_luminance_rgb(im2)

    if m < 80:
        b, c = 1.35, 1.10
    elif m < 110:
        b, c = 1.18, 1.06
    elif m > 185:
        b, c = 0.92, 1.02
    else:
        b, c = 1.00, 1.03

    tag = f"auto_bright:mean={m:.1f},B={b:.2f},C={c:.2f}"
    im3 = ImageEnhance.Brightness(im2).enhance(b)
    im4 = ImageEnhance.Contrast(im3).enhance(c)
    return im4, tag


def convert_cover(
    src: Path,
    dst: Path,
    quality: int,
    do_autobright: bool,
    dry_run: bool,
) -> tuple[bool, str, str, Path]:
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                im = im.convert("RGB")

            adjust_info = "auto_bright:off"
            if do_autobright:
                im, adjust_info = auto_brightness(im)

            out = ImageOps.fit(
                im,
                FIXED_TARGET,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

            dst.parent.mkdir(parents=True, exist_ok=True)
            dst_final = safe_unique_path(dst)

            if dry_run:
                return True, "TESTE (não gerou arquivo)", adjust_info, dst_final

            out.save(dst_final, format="JPEG", quality=quality, optimize=True)
            return True, "OK", adjust_info, dst_final

    except UnidentifiedImageError:
        return False, "SKIP: não é imagem", "n/a", dst
    except Exception as e:
        return False, f"ERRO: {e}", "n/a", dst


def open_in_explorer(path: Path) -> None:
    try:
        if path.is_dir():
            os.startfile(str(path))
        else:
            os.startfile(str(path.parent))
    except Exception:
        pass


def beep_finish() -> None:
    try:
        import winsound  # type: ignore
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        try:
            tk._default_root.bell()  # type: ignore
        except Exception:
            pass


def count_images_in_folder(folder: Path) -> int:
    n = 0
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            n += 1
    return n


# =========================================================
# LISTA.TXT (caminho completo por linha)
# =========================================================

def write_lista_txt(out_base: Path, paths: list[Path]) -> Path:
    """
    Gera lista.txt na BASE:
    cada linha contém o caminho completo do arquivo final (em convertidos).
    Em ordem alfabética.
    """
    lista_path = out_base / "lista.txt"
    paths_sorted = sorted(paths, key=lambda p: str(p).casefold())

    out_base.mkdir(parents=True, exist_ok=True)
    with lista_path.open("w", encoding="utf-8", newline="\n") as f:
        for p in paths_sorted:
            f.write(str(p) + "\n")
    return lista_path


class HelpWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.title(f"Ajuda — CIEC v{__version__}")
        self.minsize(760, 540)

        p = manual_path()

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        txt = tk.Text(frm, wrap="word")
        txt.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)

        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
            except Exception:
                content = "Erro ao ler o manual (assets/manual.txt)."
        else:
            content = "Manual não encontrado.\n\nCrie: assets/manual.txt"

        txt.insert("1.0", content)
        txt.configure(state="disabled")

        ttk.Button(self, text="Fechar", command=self.destroy).pack(pady=(0, 10))
        self._center()

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


class Splash(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=12)
        self.master = master
        self._imgtk = None

        self.master.title(f"{SPLASH_TITLE} v{__version__}")
        self.master.resizable(False, False)

        ttk.Label(self, text=f"{SPLASH_TITLE} v{__version__}", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        if SPLASH_IMAGE_PATH.exists():
            try:
                im = Image.open(SPLASH_IMAGE_PATH)
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


class App(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master

        self.conf = carregar_config_ou_criar()

        self.worker_thread: threading.Thread | None = None
        self.stop_flag = threading.Event()
        self.ui_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()

        self.last_log_path: Path | None = None
        self.last_out_base: Path | None = None
        self.last_convertidos_dir: Path | None = None
        self.last_lista_path: Path | None = None

        self.var_in = tk.StringVar(value="")
        self.var_out = tk.StringVar(value="")
        self.var_q = tk.IntVar(value=self.conf["QUALIDADE"])
        self.var_auto = tk.BooleanVar(value=bool(self.conf["AUTO_BRIGHT"]))
        self.var_ignore_out = tk.BooleanVar(value=bool(self.conf["IGNORAR_SAIDA"]))
        self.var_test = tk.BooleanVar(value=bool(self.conf["MODO_TESTE"]))

        self.var_status = tk.StringVar(value="Pronto.")
        self.var_counts = tk.StringVar(value="—")
        self.var_imgcount = tk.StringVar(value="Imagens na pasta: —")

        self._build_ui()
        self._poll_queue()

        self.master.after(200, self.pick_input_initial)

    def _build_ui(self):
        self.master.title(APP_TITLE)
        self.master.minsize(980, 630)

        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass

        pad = {"padx": 10, "pady": 6}

        top = ttk.LabelFrame(self, text="Pastas")
        top.grid(row=0, column=0, sticky="ew", **pad)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Entrada (fotos):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_in).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(top, text="Selecionar…", command=self.pick_input).grid(row=0, column=2, padx=8, pady=6)

        ttk.Label(top, textvariable=self.var_imgcount).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(top, text="Saída (opcional):").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_out).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(top, text="Selecionar…", command=self.pick_output).grid(row=2, column=2, padx=8, pady=6)

        ttk.Label(
            top,
            text="(Se vazio: salvará em <pasta pai da entrada>\\convertidos)",
        ).grid(row=3, column=1, sticky="w", padx=8, pady=(0, 6))

        mid = ttk.LabelFrame(self, text="Configurações")
        mid.grid(row=1, column=0, sticky="ew", **pad)
        for c in range(6):
            mid.columnconfigure(c, weight=1)

        ttk.Label(mid, text=f"Tamanho fixo (L×A): {FIXED_W} × {FIXED_H}").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=6
        )

        ttk.Label(mid, text="Qualidade JPEG:").grid(row=0, column=3, sticky="e", padx=8, pady=6)
        ttk.Spinbox(mid, from_=1, to=95, textvariable=self.var_q, width=6).grid(
            row=0, column=4, sticky="w", padx=8, pady=6
        )

        ttk.Separator(mid).grid(row=1, column=0, columnspan=6, sticky="ew", padx=8, pady=8)

        ttk.Checkbutton(mid, text="Ajuste automático de brilho (recomendado)", variable=self.var_auto).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(mid, text="Ignorar pasta de saída na varredura", variable=self.var_ignore_out).grid(
            row=2, column=3, columnspan=3, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(mid, text="Modo teste (não salva arquivos)", variable=self.var_test).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=8, pady=4
        )

        bot = ttk.Frame(self)
        bot.grid(row=2, column=0, sticky="ew", **pad)
        bot.columnconfigure(0, weight=1)

        self.btn_start = ttk.Button(bot, text="▶ Iniciar processamento", command=self.start)
        self.btn_start.grid(row=0, column=0, sticky="w", padx=4)

        self.btn_stop = ttk.Button(bot, text="■ Parar", command=self.stop, state="disabled")
        self.btn_stop.grid(row=0, column=1, sticky="w", padx=4)

        self.btn_help = ttk.Button(bot, text="❓ Ajuda", command=self.show_help)
        self.btn_help.grid(row=0, column=2, sticky="w", padx=4)

        self.btn_exit = ttk.Button(bot, text="⎋ Sair", command=self.on_exit)
        self.btn_exit.grid(row=0, column=3, sticky="w", padx=4)

        self.btn_open_out = ttk.Button(bot, text="📁 Abrir saída", command=self.open_out, state="disabled")
        self.btn_open_out.grid(row=0, column=4, sticky="w", padx=4)

        self.btn_open_log = ttk.Button(bot, text="📄 Abrir log", command=self.open_log, state="disabled")
        self.btn_open_log.grid(row=0, column=5, sticky="w", padx=4)

        self.progress = ttk.Progressbar(bot, orient="horizontal", mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=6, sticky="ew", padx=4, pady=10)

        status = ttk.LabelFrame(self, text="Status")
        status.grid(row=3, column=0, sticky="nsew", **pad)
        status.columnconfigure(0, weight=1)

        ttk.Label(status, textvariable=self.var_status).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(status, textvariable=self.var_counts).grid(row=1, column=0, sticky="w", padx=8, pady=6)

        self.grid(row=0, column=0, sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.master.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _update_image_count_async(self, folder: Path):
        def worker():
            try:
                n = count_images_in_folder(folder)
                self.ui_queue.put(("imgcount", n))
            except Exception:
                self.ui_queue.put(("imgcount", None))
        threading.Thread(target=worker, daemon=True).start()

    def show_help(self):
        HelpWindow(self.master)

    def on_exit(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if not messagebox.askyesno("CIEC", "Há um processamento em andamento. Deseja sair mesmo assim?"):
                return
        try:
            self.stop_flag.set()
        except Exception:
            pass
        self.master.destroy()

    def pick_input_initial(self):
        if not self.var_in.get().strip():
            self.pick_input()

    def pick_input(self):
        path = filedialog.askdirectory(title="Selecione a pasta onde estão as fotos", mustexist=True)
        if path:
            self.var_in.set(path)
            self.var_imgcount.set("Imagens na pasta: contando…")
            self._update_image_count_async(Path(path))

    def pick_output(self):
        path = filedialog.askdirectory(title="Selecione a pasta BASE de saída (opcional)", mustexist=True)
        if path:
            self.var_out.set(path)

    def _validate(self) -> tuple[Path, Path, Path, dict]:
        in_str = self.var_in.get().strip()
        if not in_str:
            raise ValueError("Selecione a pasta de entrada (fotos).")

        src_root = Path(in_str).resolve()
        if not src_root.is_dir():
            raise ValueError("Pasta de entrada inválida.")

        q = int(self.var_q.get())
        if q < 1 or q > 95:
            raise ValueError("Qualidade deve ser 1..95.")

        out_base = get_out_base(src_root, self.var_out.get())
        out_base.mkdir(parents=True, exist_ok=True)

        convertidos_dir = get_convertidos_dir(out_base)
        convertidos_dir.mkdir(parents=True, exist_ok=True)

        conf = {
            "QUALIDADE": q,
            "AUTO_BRIGHT": 1 if self.var_auto.get() else 0,
            "IGNORAR_SAIDA": 1 if self.var_ignore_out.get() else 0,
            "MODO_TESTE": 1 if self.var_test.get() else 0,
        }
        return src_root, out_base, convertidos_dir, conf

    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        try:
            src_root, out_base, convertidos_dir, conf = self._validate()
        except Exception as e:
            messagebox.showerror("CIEC", str(e))
            return

        salvar_config(conf)

        self.last_out_base = out_base
        self.last_convertidos_dir = convertidos_dir
        self.last_lista_path = None
        self.btn_open_out.configure(state="disabled")
        self.btn_open_log.configure(state="disabled")

        self.stop_flag.clear()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        self.var_status.set("Coletando arquivos…")
        self.var_counts.set("—")
        self.progress.configure(value=0, maximum=1)

        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(src_root, out_base, convertidos_dir, conf),
            daemon=True,
        )
        self.worker_thread.start()

    def stop(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_flag.set()
            self.var_status.set("Solicitada parada… aguardando finalizar o arquivo atual.")

    def open_out(self):
        if self.last_convertidos_dir:
            open_in_explorer(self.last_convertidos_dir)

    def open_log(self):
        if self.last_log_path and self.last_log_path.exists():
            try:
                os.startfile(str(self.last_log_path))
            except Exception:
                open_in_explorer(self.last_log_path)

    def _worker(self, src_root: Path, out_base: Path, convertidos_dir: Path, conf: dict):
        t0 = time.perf_counter()

        quality = conf["QUALIDADE"]
        do_autobright = bool(conf["AUTO_BRIGHT"])
        ignorar_saida = bool(conf["IGNORAR_SAIDA"])
        modo_teste = bool(conf["MODO_TESTE"])

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = out_base / f"log_processamento_{now}.txt"
        self.last_log_path = log_path

        write_log_line(log_path, "==== INICIO ====")
        write_log_line(log_path, f"Versao...........: {__version__}")
        write_log_line(log_path, f"Data/Hora........: {datetime.now().isoformat(sep=' ', timespec='seconds')}")
        write_log_line(log_path, f"Entrada..........: {src_root}")
        write_log_line(log_path, f"Base Saida........: {out_base}")
        write_log_line(log_path, f"Convertidos......: {convertidos_dir}")
        write_log_line(log_path, f"Tamanho..........: {FIXED_W}x{FIXED_H} (fixo)")
        write_log_line(log_path, f"Quality..........: {quality}")
        write_log_line(log_path, f"AutoBrightness...: {'ON' if do_autobright else 'OFF'}")
        write_log_line(log_path, f"Ignorar Saida....: {'ON' if ignorar_saida else 'OFF'}")
        write_log_line(log_path, f"Modo teste.......: {'ON' if modo_teste else 'OFF'}")
        write_log_line(log_path, "Saida achatada...: convertidos (sem subpastas)")
        write_log_line(log_path, "Nomes............: normalizados (sem acentos/especiais/espaços)")
        write_log_line(log_path, "")

        all_files: list[Path] = []
        for p in src_root.rglob("*"):
            if self.stop_flag.is_set():
                break
            if not p.is_file():
                continue
            if ignorar_saida:
                # Se por acaso o usuário apontar a BASE dentro da árvore de entrada,
                # evitamos reprocessar arquivos já gerados
                try:
                    p.relative_to(out_base)
                    continue
                except ValueError:
                    pass
            all_files.append(p)

        counters = Counters(total_files=len(all_files))
        self.ui_queue.put(("set_max", counters.total_files))
        self.ui_queue.put(("status", f"Processando {counters.total_files} arquivos…"))

        produced: list[Path] = []

        for idx, p in enumerate(all_files, start=1):
            if self.stop_flag.is_set():
                break

            counters.tried += 1

            # >>> saída achatada em convertidos
            dst = build_output_path_flat(p, convertidos_dir)

            success, msg, adj, dst_final = convert_cover(
                p, dst, quality, do_autobright, modo_teste
            )

            if success:
                counters.ok += 1
                produced.append(dst_final)
                tag = "[TESTE]" if modo_teste else "[OK]"
                write_log_line(log_path, f"{tag} SRC={p}  DST={dst_final}  AJUSTE={adj}")
            else:
                if msg.startswith("SKIP"):
                    counters.not_image += 1
                    write_log_line(log_path, f"[SKIP] SRC={p}  MOTIVO={msg}")
                else:
                    counters.failed += 1
                    write_log_line(log_path, f"[ERRO] SRC={p}  MOTIVO={msg}")

            self.ui_queue.put(("progress", idx))
            self.ui_queue.put(("counts", counters))

        # lista.txt (mantém geração e gravação, mas não cita no pop-up)
        lista_path = write_lista_txt(out_base, produced)
        self.last_lista_path = lista_path
        write_log_line(log_path, f"Lista............: {lista_path}")

        # som ao final
        self.ui_queue.put(("beep", None))

        write_log_line(log_path, "")
        write_log_line(log_path, "==== RESUMO ====")
        write_log_line(log_path, f"Arquivos encontrados (geral) : {counters.total_files}")
        write_log_line(log_path, f"Arquivos tentados (abrir)    : {counters.tried}")
        write_log_line(log_path, f"Imagens processadas (OK)     : {counters.ok}")
        write_log_line(log_path, f"Não-imagem (ignorados)       : {counters.not_image}")
        write_log_line(log_path, f"Falhas reais                 : {counters.failed}")
        write_log_line(log_path, f"Log                          : {log_path}")
        write_log_line(log_path, "==== FIM ====")

        elapsed = time.perf_counter() - t0

        if self.stop_flag.is_set():
            self.ui_queue.put(("done", ("Parado pelo usuário.", counters, elapsed)))
        else:
            self.ui_queue.put(("done", ("Concluído.", counters, elapsed)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()

                if kind == "set_max":
                    maxv = int(payload) if payload else 1
                    self.progress.configure(maximum=maxv if maxv > 0 else 1, value=0)

                elif kind == "progress":
                    self.progress.configure(value=int(payload))

                elif kind == "status":
                    self.var_status.set(str(payload))

                elif kind == "counts":
                    c: Counters = payload  # type: ignore
                    self.var_counts.set(
                        f"OK: {c.ok} | Falhas: {c.failed} | Ignorados: {c.not_image} | Total: {c.total_files}"
                    )

                elif kind == "imgcount":
                    if payload is None:
                        self.var_imgcount.set("Imagens na pasta: (erro ao contar)")
                    else:
                        self.var_imgcount.set(f"Imagens na pasta: {int(payload)}")

                elif kind == "beep":
                    beep_finish()

                elif kind == "done":
                    msg, c, elapsed = payload  # type: ignore

                    self.btn_start.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                    self.btn_open_out.configure(state="normal")
                    self.btn_open_log.configure(state="normal")

                    self.var_status.set(msg)
                    self.var_counts.set(
                        f"OK: {c.ok} | Falhas: {c.failed} | Ignorados: {c.not_image} | Total: {c.total_files}"
                    )

                    total_processado = c.total_files
                    tempo_txt = f"{elapsed:.1f}s"

                    # POP-UP FINAL: SOMENTE os campos solicitados
                    messagebox.showinfo(
                        "CIEC",
                        f"{msg}\n\n"
                        f"OK: {c.ok}\n"
                        f"Falhas: {c.failed}\n"
                        f"Ignorados: {c.not_image}\n"
                        f"Total processado: {total_processado}\n"
                        f"Tempo: {tempo_txt}"
                    )

        except queue.Empty:
            pass

        self.after(120, self._poll_queue)


def main():
    root = tk.Tk()
    splash_frame = Splash(root)

    start_time = int(root.tk.call("clock", "milliseconds"))

    def show_app():
        now = int(root.tk.call("clock", "milliseconds"))
        elapsed = now - start_time
        wait_more = max(0, SPLASH_MIN_MS - elapsed)

        def _switch():
            splash_frame.destroy()
            app = App(root)
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

    root.after(50, show_app)
    root.mainloop()


if __name__ == "__main__":
    main()