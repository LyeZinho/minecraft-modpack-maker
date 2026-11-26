"""Exportação do lockfile para artefato .mrpack.

Um .mrpack é, na prática, um ZIP contendo modrinth.index.json na raiz.
O launcher (Modrinth App, Prism, etc.) lê o index e baixa os JARs das URLs oficiais.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Union

from .lockfile import lockfile_to_index
from .models import Lockfile


def export_mrpack(lock: Union[Lockfile, str, Path], output: Path) -> Path:
    """Gera um .mrpack a partir de um Lockfile (objeto ou caminho para JSON)."""
    output.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(lock, Lockfile):
        index_data = lockfile_to_index(lock)
    else:  # é caminho (str ou Path) para JSON já salvo
        index_data = json.loads(Path(lock).read_text(encoding="utf-8"))

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "modrinth.index.json",
            json.dumps(index_data, indent=2, ensure_ascii=False),
        )
    return output
