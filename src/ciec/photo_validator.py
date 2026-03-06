from pathlib import Path
from PIL import Image

VALID_WIDTH = 161
VALID_HEIGHT = 225


def validar_fotos(pasta):

    pasta = Path(pasta)

    ok = 0
    ext_errada = 0
    resolucao_errada = 0
    corrompida = 0

    erros = []

    for arquivo in pasta.iterdir():

        if not arquivo.is_file():
            continue

        ext = arquivo.suffix.lower()

        if ext != ".jpg":
            ext_errada += 1
            erros.append(f"{arquivo.name} -> extensão inválida")
            continue

        try:
            with Image.open(arquivo) as img:

                w, h = img.size

                if w == VALID_WIDTH and h == VALID_HEIGHT:
                    ok += 1
                else:
                    resolucao_errada += 1
                    erros.append(
                        f"{arquivo.name} -> resolução {w}x{h}"
                    )

        except Exception:
            corrompida += 1
            erros.append(f"{arquivo.name} -> imagem inválida")

    total = ok + ext_errada + resolucao_errada + corrompida

    return {
        "ok": ok,
        "ext_errada": ext_errada,
        "resolucao_errada": resolucao_errada,
        "corrompida": corrompida,
        "total": total,
        "erros": erros
    }