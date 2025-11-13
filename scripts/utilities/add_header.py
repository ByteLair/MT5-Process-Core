#!/usr/bin/env python3
"""
Pre-commit hook: Adiciona header de copyright/licença privada bilingue em todos os arquivos .py do projeto.
"""

import pathlib
import sys

HEADER_TEXT = """Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
All rights reserved. | Todos os direitos reservados.
Private License: This code is the exclusive property of Felipe Petracco Carmo.
Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
"""

FILE_HEADERS = {
    ".py": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".sh": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".sql": f"-- =============================================================\n-- {HEADER_TEXT}-- =============================================================\n\n",
    ".md": f"<!-- =============================================================\n{HEADER_TEXT}============================================================= -->\n\n",
    ".yml": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".yaml": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".ini": f"; =============================================================\n; {HEADER_TEXT}; =============================================================\n\n",
    ".toml": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".env": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".conf": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    "Dockerfile": f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n\n",
    ".ipynb": None,  # handled separately
}


def has_header(text: str) -> bool:
    return "Copyright (c) 2025 Felipe Petracco Carmo" in text


def add_header_to_file(path: pathlib.Path) -> None:
    ext = path.suffix
    name = path.name
    if ext == ".ipynb":
        try:
            import nbformat

            nb = nbformat.read(path.open("r", encoding="utf-8"), as_version=4)
            if nb.cells and has_header(nb.cells[0].get("source", "")):
                return
            header = f"# =============================================================\n# {HEADER_TEXT}# =============================================================\n"
            nb.cells.insert(0, nbformat.v4.new_markdown_cell(header))
            nbformat.write(nb, path.open("w", encoding="utf-8"))
        except Exception:
            pass
        return
    header = FILE_HEADERS.get(ext) or (FILE_HEADERS["Dockerfile"] if name == "Dockerfile" else None)
    if not header:
        return
    content = path.read_text(encoding="utf-8")
    if has_header(content):
        return
    path.write_text(header + content, encoding="utf-8")


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        path = pathlib.Path(filename)
        if path.is_file():
            add_header_to_file(path)
