# -*- coding: utf-8 -*-
from __future__ import annotations

import threading
import queue
import logging
from .logger import setup_logger
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk, ImageDraw

from .constants import APP_TITLE, FIXED_W, FIXED_H
from .config_io import carregar_config_ou_criar, salvar_config
from .utils import count_images_in_folder, open_in_explorer, open_file, beep_finish
from .ui_help import HelpWindow
from .worker import process_folder, get_out_base, get_convertidos_dir
from .photo_validator import validar_fotos

AVG_SEC_PER_IMAGE = 0.12  # ajuste depois (0.08 ~ 0.25 é comum)


class App(ttk.Frame):
    def __init__(self, master: tk.Tk, version: str):
        super().__init__(master)

        self.master = master
        self.version = version

        self.conf = carregar_config_ou_criar()

        self.worker_thread: threading.Thread | None = None
        self.stop_flag = threading.Event()
        self.ui_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()

        self.last_log_path: Path | None = None
        self.last_convertidos_dir: Path | None = None

        self.var_in = tk.StringVar(value="")
        self.var_out = tk.StringVar(value="")
        self.var_q = tk.IntVar(value=int(self.conf.get("QUALIDADE", 90)))

        self.var_auto = tk.BooleanVar(value=bool(self.conf.get("AUTO_BRIGHT", True)))
        self.var_ignore_out = tk.BooleanVar(value=bool(self.conf.get("IGNORAR_SAIDA", False)))
        self.var_test = tk.BooleanVar(value=bool(self.conf.get("MODO_TESTE", False)))

        self.var_status = tk.StringVar(value="PRONTO")
        self.var_counts = tk.StringVar(value="—")
        self.var_imgcount = tk.StringVar(value="Imagens na pasta: —")

        self._init_icons()
        self._build_ui()
        self._poll_queue()

        # Ajusta automaticamente o tamanho da janela para não "cortar" controles
        self.master.update_idletasks()
        w = self.master.winfo_reqwidth()
        h = self.master.winfo_reqheight()
        self.master.geometry(f"{w}x{h}")
        self.master.minsize(w, h)
        self.master.resizable(True, True)

    # -----------------------------------------------------

    def _init_icons(self) -> None:
        """
        Cria ícones PNG em memória (sem arquivos externos) para uso nos botões.
        Isso evita problemas com Base64 corrompido e funciona no PyInstaller.
        """
        def mk(size=(20, 20)):
            return Image.new("RGBA", size, (0, 0, 0, 0))

        def to_tk(img: Image.Image):
            return ImageTk.PhotoImage(img)

        icons: dict[str, ImageTk.PhotoImage] = {}

        # Play (triângulo)
        img = mk()
        d = ImageDraw.Draw(img)
        d.polygon([(6, 4), (6, 16), (16, 10)], fill=(40, 40, 40, 255))
        icons["processar"] = to_tk(img)

        # Stop (quadrado)
        img = mk()
        d = ImageDraw.Draw(img)
        d.rectangle([6, 6, 14, 14], fill=(40, 40, 40, 255))
        icons["parar"] = to_tk(img)

        # Validar (check)
        img = mk()
        d = ImageDraw.Draw(img)
        d.line([(5, 11), (9, 15), (16, 6)], fill=(40, 40, 40, 255), width=3)
        icons["validar"] = to_tk(img)

        # Pasta (folder)
        img = mk()
        d = ImageDraw.Draw(img)
        d.rectangle([4, 8, 16, 15], outline=(40, 40, 40, 255), width=2)
        d.rectangle([4, 6, 10, 9], fill=(40, 40, 40, 255))
        icons["saida"] = to_tk(img)

        # Log (documento)
        img = mk()
        d = ImageDraw.Draw(img)
        d.rectangle([5, 4, 15, 16], outline=(40, 40, 40, 255), width=2)
        d.line([(7, 8), (13, 8)], fill=(40, 40, 40, 255), width=2)
        d.line([(7, 11), (13, 11)], fill=(40, 40, 40, 255), width=2)
        icons["log"] = to_tk(img)

        # Ajuda (?)
        img = mk()
        d = ImageDraw.Draw(img)
        d.ellipse([4, 4, 16, 16], outline=(40, 40, 40, 255), width=2)
        d.text((8, 5), "?", fill=(40, 40, 40, 255))
        icons["ajuda"] = to_tk(img)

        # Sair (porta)
        img = mk()
        d = ImageDraw.Draw(img)
        d.rectangle([6, 4, 14, 16], outline=(40, 40, 40, 255), width=2)
        d.ellipse([12, 10, 13, 11], fill=(40, 40, 40, 255))
        d.polygon([(3, 10), (7, 7), (7, 9), (11, 9), (11, 11), (7, 11), (7, 13)], fill=(40, 40, 40, 255))
        icons["sair"] = to_tk(img)

        self._icons = icons  # manter referência

    def _make_toolbar_button(self, parent, text: str, icon_key: str, command, state: str | None = None):
        kwargs = dict(
            text=text,
            image=self._icons[icon_key],
            compound="left",
            command=command,
            takefocus=False,
        )
        if state is not None:
            kwargs["state"] = state
        return ttk.Button(parent, **kwargs)


    # -----------------------------------------------------
    # Filtro de arquivos: ignora LISTA.* e logs dentro de convertidos
    # -----------------------------------------------------
    def _is_ignored_in_convertidos(self, p: Path) -> bool:
        name = p.name.upper()
        if name.startswith("LISTA."):
            return True
        if name.endswith(".LOG"):
            return True
        # compatível com padrão ciec_YYYYMMDD_HHMM.log
        if name.startswith("CIEC_") and name.endswith(".LOG"):
            return True
        return False

    def _is_image_candidate(self, p: Path) -> bool:
        if not p.is_file():
            return False
        if self._is_ignored_in_convertidos(p):
            return False
        return p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

    def _count_images_filtered(self, folder: Path) -> int:
        try:
            return sum(1 for fp in folder.iterdir() if self._is_image_candidate(fp))
        except Exception:
            return 0

    def _validate_images_filtered(self, folder: Path) -> dict:
        """Valida imagens pulando LISTA.* e *.log. Critério: JPG 161x225."""
        ok = ext_errada = resolucao_errada = corrompida = 0
        erros = []
        for fp in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
            if not self._is_image_candidate(fp):
                continue
            if fp.suffix.lower() not in {".jpg", ".jpeg"}:
                ext_errada += 1
                erros.append(f"{fp.name} (extensão inválida)")
                continue
            try:
                with Image.open(fp) as im:
                    im.load()
                    w, h = im.size
                    if (w, h) != (161, 225):
                        resolucao_errada += 1
                        erros.append(f"{fp.name} (resolução {w}x{h})")
                    else:
                        ok += 1
            except Exception:
                corrompida += 1
                erros.append(f"{fp.name} (corrompida/ilegível)")

        total = ok + ext_errada + resolucao_errada + corrompida
        return {"ok": ok, "ext_errada": ext_errada, "resolucao_errada": resolucao_errada, "corrompida": corrompida, "total": total, "erros": erros}
    def _build_ui(self):
        self.master.title(APP_TITLE)

        # Layout responsivo
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # Status cresce

        pad = {"padx": 10, "pady": 6}

        # -------------------------
        # PASTAS
        # -------------------------
        top = ttk.LabelFrame(self, text="Pastas")
        top.grid(row=0, column=0, sticky="ew", **pad)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Entrada (fotos):").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.var_in).grid(row=0, column=1, sticky="ew")
        ttk.Button(top, text="Selecionar…", command=self.pick_input).grid(row=0, column=2)

        ttk.Label(top, textvariable=self.var_imgcount).grid(row=1, column=1, sticky="w")

        ttk.Label(top, text="Saída (opcional):").grid(row=2, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.var_out).grid(row=2, column=1, sticky="ew")
        ttk.Button(top, text="Selecionar…", command=self.pick_output).grid(row=2, column=2)

        # -------------------------
        # CONFIG
        # -------------------------
        mid = ttk.LabelFrame(self, text="Configurações")
        mid.grid(row=1, column=0, sticky="ew", **pad)

        ttk.Label(mid, text=f"Tamanho fixo: {FIXED_W} x {FIXED_H}").grid(row=0, column=0)

        ttk.Label(mid, text="Qualidade JPEG").grid(row=0, column=1)
        ttk.Spinbox(mid, from_=1, to=95, textvariable=self.var_q, width=6).grid(row=0, column=2)

        ttk.Checkbutton(mid, text="Ajuste automático de brilho", variable=self.var_auto).grid(row=1, column=0)
        ttk.Checkbutton(mid, text="Ignorar pasta saída", variable=self.var_ignore_out).grid(row=1, column=1)
        ttk.Checkbutton(mid, text="Modo teste", variable=self.var_test).grid(row=1, column=2)
        # -------------------------
        # BOTÕES
        # -------------------------
        bot = ttk.Frame(self)
        bot.grid(row=2, column=0, sticky="ew", **pad)
        bot.columnconfigure(0, weight=1)

        # Barra horizontal (ordem igual ao mockup):
        # Processar | Parar | Validar imagens | Abrir saída | Ver Log | Ajuda | Sair
        btnbar = ttk.Frame(bot)
        btnbar.grid(row=0, column=0, sticky="w")

        self.btn_start = self._make_toolbar_button(btnbar, "Processar", "processar", self.start)
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = self._make_toolbar_button(btnbar, "Parar", "parar", self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(0, 10))

        self.btn_validar = self._make_toolbar_button(btnbar, "Validar imagens", "validar", self.validar_fotos_interface)
        self.btn_validar.pack(side="left", padx=(0, 10))

        self.btn_open_out = self._make_toolbar_button(btnbar, "Abrir saída", "saida", self.open_out, state="disabled")
        self.btn_open_out.pack(side="left", padx=(0, 10))

        self.btn_open_log = self._make_toolbar_button(btnbar, "Ver Log", "log", self.open_log, state="disabled")
        self.btn_open_log.pack(side="left", padx=(0, 10))

        self.btn_help = self._make_toolbar_button(btnbar, "Ajuda", "ajuda", self.show_help)
        self.btn_help.pack(side="left", padx=(0, 10))

        self.btn_exit = self._make_toolbar_button(btnbar, "Sair", "sair", self.on_exit)
        self.btn_exit.pack(side="left", padx=(0, 0))

        self.progress = ttk.Progressbar(bot, orient="horizontal", mode="determinate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=10)

        # -------------------------
        # STATUS
        # -------------------------
        status = ttk.LabelFrame(self, text="Status")
        status.grid(row=3, column=0, sticky="nsew", **pad)
        status.columnconfigure(0, weight=1)

        ttk.Label(status, textvariable=self.var_status).grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.var_counts).grid(row=1, column=0, sticky="w")
        # versão no rodapé (direita)
        ttk.Label(status, text=f"CIEC v{self.version}", foreground="#666").grid(row=2, column=0, sticky="e")
        self.grid(row=0, column=0, sticky="nsew")
        
        

    # -----------------------------------------------------

    def validar_fotos_interface(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta com as fotos")
        if not pasta:
            return

        r = self._validate_images_filtered(Path(pasta))

        ok = int(r.get("ok", 0))
        ext_errada = int(r.get("ext_errada", 0))
        resolucao_errada = int(r.get("resolucao_errada", 0))
        corrompida = int(r.get("corrompida", 0))
        total = int(r.get("total", ok + ext_errada + resolucao_errada + corrompida))
        erros = r.get("erros", [])

        invalidas = total - ok

        msg = (
            f"Total analisado: {total}\n\n"
            f"Fotos OK (161x225 .jpg): {ok}\n"
            f"Fotos inválidas: {invalidas}\n\n"
            f"Extensão inválida: {ext_errada}\n"
            f"Resolução incorreta: {resolucao_errada}\n"
            f"Corrompidas/ilegíveis: {corrompida}\n"
        )

        if erros:
            msg += "\nArquivos com problemas:\n\n"
            limite = 200
            for i, e in enumerate(erros[:limite], start=1):
                msg += f"{i}. {e}\n"
            if len(erros) > limite:
                msg += f"\n... e mais {len(erros) - limite} arquivo(s).\n"

        messagebox.showinfo("Validação de Fotos", msg)

    # -----------------------------------------------------

    def show_help(self):
        HelpWindow(self.master, self.version)

    # -----------------------------------------------------

    def pick_input(self):
        path = filedialog.askdirectory(title="Selecione a pasta com as fotos")
        if path:
            self.var_in.set(path)
            try:
                n = self._count_images_filtered(Path(path))

                eta = n * AVG_SEC_PER_IMAGE
                if eta < 60:
                    eta_txt = f"{eta:.0f}s"
                else:
                    m = int(eta // 60)
                    s = int(eta % 60)
                    eta_txt = f"{m}m{s:02d}s"

                self.var_imgcount.set(f"Imagens na pasta: {n}  |  Estimativa: {eta_txt}")
                               
                
            except Exception:
                self.var_imgcount.set("Erro ao contar imagens")

    def pick_output(self):
        path = filedialog.askdirectory(title="Selecione a pasta de saída")
        if path:
            self.var_out.set(path)

    # -----------------------------------------------------

    def start(self):
        
        log_path = setup_logger()
        self.last_log_path = log_path

        logging.info("Processamento iniciado")

        src = Path(self.var_in.get())
        logging.info(f"Pasta origem: {src}")
        pasta_in = self.var_in.get().strip()
        out_value = self.var_out.get().strip() or None

        if not pasta_in:
            messagebox.showwarning("CIEC", "Selecione a pasta de entrada (fotos).")
            return

        src_root = Path(pasta_in)
        if not src_root.exists():
            messagebox.showerror("CIEC", "A pasta de entrada não existe.")
            return

        # Atualiza config em memória e salva
        self.conf["QUALIDADE"] = int(self.var_q.get())
        self.conf["AUTO_BRIGHT"] = bool(self.var_auto.get())
        self.conf["IGNORAR_SAIDA"] = bool(self.var_ignore_out.get())
        self.conf["MODO_TESTE"] = bool(self.var_test.get())
        salvar_config(self.conf)

        # Reset UI
        self.stop_flag.clear()
        self.progress["value"] = 0
        self.var_status.set("PROCESSANDO…")
        self.var_counts.set("—")

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_open_out.config(state="disabled")
        self.btn_open_log.config(state="disabled")

        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(src_root, out_value),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_worker(self, src_root: Path, out_value: str | None):
        try:
            # ❗ NÃO passe out_base aqui. O worker atual calcula out_base internamente.
            msg, counters, elapsed, log_path, lista_path = process_folder(
                src_root=src_root,
                out_value=out_value,
                conf=self.conf,
                version=self.version,
                stop_flag=self.stop_flag,
                ui_queue=self.ui_queue,
            )

            # Atualiza caminhos para botões
            try:
                self.last_log_path = Path(log_path) if log_path else None
            except Exception:
                self.last_log_path = None

            out_base = get_out_base(src_root, out_value, self.conf)
            self.last_convertidos_dir = get_convertidos_dir(out_base)

            # sinaliza conclusão
            self.ui_queue.put(("done_msg", msg))
            self.ui_queue.put(("done", counters))

        except Exception as e:
            self.ui_queue.put(("error", str(e)))

    def stop(self):
        self.stop_flag.set()
        self.var_status.set("PARANDO…")

    # -----------------------------------------------------

    def open_out(self):
        if self.last_convertidos_dir:
            open_in_explorer(self.last_convertidos_dir)

    def open_log(self):
        if self.last_log_path:
            open_file(self.last_log_path)

    def on_exit(self):
        try:
            self.stop_flag.set()
        except Exception:
            pass
        self.master.destroy()

    # -----------------------------------------------------

    def _poll_queue(self):
        try:
            while True:
                tipo, payload = self.ui_queue.get_nowait()

                if tipo == "status":
                    self.var_status.set(str(payload))

                elif tipo == "counts":
                    self.var_counts.set(str(payload))

                elif tipo == "progress":
                    # payload pode ser (cur,total)
                    if isinstance(payload, tuple) and len(payload) == 2:
                        cur, total = payload
                        self.progress["maximum"] = max(1, int(total))
                        self.progress["value"] = int(cur)
                    else:
                        self.progress["maximum"] = 100
                        self.progress["value"] = float(payload)

                elif tipo == "out_dir":
                    try:
                        self.last_convertidos_dir = Path(str(payload))
                        self.btn_open_out.config(state="normal")
                    except Exception:
                        pass

                elif tipo == "log_path":
                    try:
                        self.last_log_path = Path(str(payload))
                        self.btn_open_log.config(state="normal")
                    except Exception:
                        pass

                elif tipo == "done_msg":
                    # só guarda o texto final
                    self.var_status.set(str(payload))

                elif tipo == "done":
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    # habilita botões se já tiver caminhos
                    if self.last_convertidos_dir:
                        self.btn_open_out.config(state="normal")
                    if self.last_log_path:
                        self.btn_open_log.config(state="normal")
                    beep_finish()

                elif tipo == "error":
                    self.var_status.set("ERRO")
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    messagebox.showerror("CIEC", f"Erro no processamento:\n\n{payload}")

        except queue.Empty:
            pass

        self.after(150, self._poll_queue)