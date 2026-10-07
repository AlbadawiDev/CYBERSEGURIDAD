"""Persistencia de resultados sin perder un historial inválido."""
import json
import os
from pathlib import Path
import tempfile


def append_history(path, results):
    path = Path(path)
    if not results:
        return
    history = []
    if path.exists():
        # Un JSON corrupto nunca debe sustituirse silenciosamente.
        history = json.loads(path.read_text(encoding="utf8"))
        if not isinstance(history, list):
            raise ValueError("El historial debe ser una lista JSON.")
    history.extend(results)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(history, temporary, indent=4, ensure_ascii=False)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
