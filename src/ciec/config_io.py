# -*- coding: utf-8 -*-
from __future__ import annotations

import configparser
from pathlib import Path


from .constants import DEFAULTS, VERSION_FALLBACK, config_path, version_path, default_config_path

def ensure_config_exists() -> None:
    target = config_path()
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)

    src = default_config_path()
    if src.exists():
        target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        escrever_config_padrao(target)



def read_version() -> str:
    p = version_path()
    try:
        v = p.read_text(encoding="utf-8").strip()
        if v:
            return v
    except Exception:
        pass
    return VERSION_FALLBACK


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
