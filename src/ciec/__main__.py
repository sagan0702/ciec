# -*- coding: utf-8 -*-
from __future__ import annotations

def _main():
    # Executando como pacote: python -m src.ciec  (imports relativos funcionam)
    try:
        from .ciec_gui import main  # type: ignore
        main()
        return
    except Exception:
        pass

    # Fallbacks (para outros modos de empacotamento/execução)
    try:
        from src.ciec.ciec_gui import main  # type: ignore
        main()
        return
    except Exception:
        pass

    from ciec.ciec_gui import main  # type: ignore
    main()


if __name__ == "__main__":
    _main()
