# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Any

from .constants import IMAGE_EXTS, FIXED_W, FIXED_H
from .utils import normalize_name
from .image_ops import convert_cover
from .io_ops import write_log_line


def get_exec_log_path() -> Path:
    """Gera o caminho do log de execução em logs/ciec_YYYYMMDD_HHMM.log"""
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return log_dir / f"ciec_{stamp}.log"



@dataclass
class Counters:
    total_files: int = 0
    tried: int = 0
    ok: int = 0
    not_image: int = 0
    failed: int = 0


def get_out_base(src_root: Path, out_value: str | Path | None, conf: dict | None = None) -> Path:
    """
    Decide a base de saída.
    - Se conf["IGNORAR_SAIDA"] for True, ignora out_value e usa src_root.
    - Se out_value vier vazio/None, usa src_root.
    - Caso contrário, usa out_value.
    """
    if conf is not None and bool(conf.get("IGNORAR_SAIDA", False)):
        return Path(src_root).resolve()

    if out_value is None:
        return Path(src_root).resolve()

    out_str = str(out_value).strip()
    if out_str:
        return Path(out_str).resolve()

    return Path(src_root).resolve()


def get_convertidos_dir(out_base: Path) -> Path:
    """Pasta final onde ficam os JPGs, log.txt e lista.txt."""
    return Path(out_base) / "convertidos"


def build_output_path_flat(src_file: Path, convertidos_dir: Path) -> Path:
    nome = normalize_name(src_file.stem)
    return Path(convertidos_dir) / f"{nome}.jpg"


def write_lista_txt_in_convertidos(lista_path: Path, produced: list[Path]) -> Path:
    """
    Gera lista.txt com caminho completo, 1 por linha, em ordem alfabética.
    Sempre dentro de convertidos.
    """
    lista_path.parent.mkdir(parents=True, exist_ok=True)
    linhas = sorted({str(p.resolve()) for p in produced})
    with open(lista_path, "w", encoding="utf-8") as f:
        for line in linhas:
            f.write(line + "\n")
    return lista_path


def _make_ui_callbacks(ui_queue, progress_cb, status_cb, counts_cb):
    """
    Constrói callbacks seguros:
    - Se ui_queue existir: publica eventos ("status", ...), ("progress", (cur,total)), ("counts", "..."), etc.
    - Se callbacks antigos forem passados: também chama.
    """
    def safe_status(msg: str):
        if ui_queue is not None:
            ui_queue.put(("status", msg))
        if callable(status_cb):
            status_cb(msg)

    def safe_progress(cur: int, total: int):
        if ui_queue is not None:
            ui_queue.put(("progress", (cur, total)))
        if callable(progress_cb):
            progress_cb(cur, total)

    def safe_counts(c: Counters):
        # UI atual mostra var_counts como texto; vamos mandar um resumo já formatado
        if ui_queue is not None:
            ui_queue.put((
                "counts",
                f"OK: {c.ok}  |  Falha: {c.failed}  |  Ignorados: {c.not_image}  |  Total processado: {c.tried}/{c.total_files}"
            ))
        if callable(counts_cb):
            counts_cb(c)

    return safe_progress, safe_status, safe_counts


def process_folder(
    *,
    src_root: Path,
    out_value: str | Path | None = None,
    conf: dict,
    version: str,
    stop_flag,
    ui_queue=None,
    # compat: callbacks antigos (opcionais)
    progress_cb: Callable[[int, int], Any] | None = None,
    status_cb: Callable[[str], Any] | None = None,
    counts_cb: Callable[[Counters], Any] | None = None,
) -> tuple[str, Counters, float, Path, Path]:
    """
    Executa o processamento.

    Retorna: (msg_final, counters, elapsed, log_path, lista_path)

    Eventos via ui_queue (se fornecido):
    - ("status", str)
    - ("progress", (cur,total))
    - ("counts", str)  # já formatado para a UI
    - ("out_dir", str)
    - ("log_path", str)
    - ("done", Counters)  # no final
    - ("error", str)      # se exception escapar (idealmente não escapa)
    """
    t0 = time.perf_counter()

    src_root = Path(src_root)
    out_base = get_out_base(src_root, out_value, conf)
    convertidos_dir = get_convertidos_dir(out_base)

    quality = int(conf.get("QUALIDADE", 90))
    do_autobright = bool(conf.get("AUTO_BRIGHT", True))
    ignorar_saida = bool(conf.get("IGNORAR_SAIDA", False))
    modo_teste = bool(conf.get("MODO_TESTE", False))

    convertidos_dir.mkdir(parents=True, exist_ok=True)

    # ✅ log e lista sempre dentro de convertidos
    log_path = convertidos_dir / "log.txt"
    lista_path = convertidos_dir / "lista.txt"


    # ✅ log de execução global em logs/ (útil para suporte)
    exec_log_path = get_exec_log_path()
    # callbacks (queue + compat)
    safe_progress, safe_status, safe_counts = _make_ui_callbacks(
        ui_queue, progress_cb, status_cb, counts_cb
    )

    if ui_queue is not None:
        ui_queue.put(("out_dir", str(convertidos_dir)))
        ui_queue.put(("log_path", str(log_path)))

    def wlog(line: str):
        """Escreve no log.txt (convertidos) e no log global (logs/)."""
        write_log_line(log_path, line)
        write_log_line(exec_log_path, line)


    wlog("==== INICIO ====")
    wlog(f"Versao...........: {version}")
    wlog(f"Data/Hora........: {datetime.now().isoformat(sep=' ', timespec='seconds')}")
    wlog(f"Entrada..........: {src_root}")
    wlog(f"Base Saida.......: {out_base}")
    wlog(f"Convertidos......: {convertidos_dir}")
    wlog(f"Tamanho..........: {FIXED_W}x{FIXED_H} (fixo)")
    wlog(f"Quality..........: {quality}")
    wlog(f"AutoBrightness...: {'ON' if do_autobright else 'OFF'}")
    wlog(f"Ignorar Saida....: {'ON' if ignorar_saida else 'OFF'}")
    wlog(f"Modo teste.......: {'ON' if modo_teste else 'OFF'}")
    wlog("Saida achatada...: convertidos (sem subpastas)")
    wlog("Nomes............: normalizados (sem acentos/especiais/espaços)")
    wlog("")

    # coleta imagens
    all_files: list[Path] = []
    for p in src_root.rglob("*"):
        if stop_flag.is_set():
            break
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        if ignorar_saida:
            # ignora tudo que estiver dentro de convertidos_dir
            try:
                p.relative_to(convertidos_dir)
                continue
            except ValueError:
                pass
        all_files.append(p)

    counters = Counters(total_files=len(all_files))
    safe_status(f"Processando {counters.total_files} imagem(ns)…")
    safe_counts(counters)
    safe_progress(0, counters.total_files)

    produced: list[Path] = []

    for idx, p in enumerate(all_files, start=1):
        if stop_flag.is_set():
            break

        counters.tried += 1
        dst = build_output_path_flat(p, convertidos_dir)

        success, msg, adj, dst_final = convert_cover(
            p, dst, quality, do_autobright, modo_teste
        )

        if success:
            counters.ok += 1
            produced.append(dst_final)
            tag = "[TESTE]" if modo_teste else "[OK]"
            wlog(f"{tag} SRC={p}  DST={dst_final}  AJUSTE={adj}")
        else:
            if str(msg).startswith("SKIP"):
                counters.not_image += 1
                wlog(f"[SKIP] SRC={p}  MOTIVO={msg}")
            else:
                counters.failed += 1
                wlog(f"[ERRO] SRC={p}  MOTIVO={msg}")

        safe_progress(idx, counters.total_files)
        safe_counts(counters)

    # ✅ gera lista.txt dentro de convertidos
    lista_path = write_lista_txt_in_convertidos(lista_path, produced)
    wlog(f"Lista............: {lista_path}")

    wlog("")
    wlog("==== RESUMO ====")
    wlog(f"Arquivos (imagens) encontrados: {counters.total_files}")
    wlog(f"Imagens processadas (OK)      : {counters.ok}")
    wlog(f"Ignorados (não-imagem/skip)   : {counters.not_image}")
    wlog(f"Falhas reais                  : {counters.failed}")
    wlog(f"Log (convertidos)             : {log_path}")
    wlog(f"Log de execução (logs/)       : {exec_log_path}")
    wlog("==== FIM ====")

    elapsed = time.perf_counter() - t0

    final_msg = "Parado pelo usuário." if stop_flag.is_set() else "Concluído."

    return final_msg, counters, elapsed, log_path, lista_path
