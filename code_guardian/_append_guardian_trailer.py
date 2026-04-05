#!/usr/bin/env python3
"""
Code Guardian — Injeta trailer Guardian-Review na mensagem do commit.

Chamado pelo hook prepare-commit-msg. Lê o arquivo de resumo gerado pelo
pre-commit (via runner.py --summary-file) e appenda o trailer na mensagem.

Uso (pelo hook):
    python _append_guardian_trailer.py <commit-msg-file> [<commit-source>]

Fontes válidas: vazio (commit normal), "message" (git commit -m), "template".
Ignoradas: "commit" (amend), "merge", "squash" — para não duplicar o trailer.
"""

import sys
import time
from pathlib import Path
import subprocess

# Tempo máximo (segundos) para considerar o summary file válido.
# Evita usar resultado de um commit anterior quando --no-verify é usado.
_MAX_AGE_SECONDS = 300  # 5 minutos


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(0)

    commit_msg_file = Path(sys.argv[1])
    commit_source = sys.argv[2] if len(sys.argv) > 2 else ""

    # Pular em amend, merge e squash para não duplicar o trailer
    if commit_source in ("commit", "merge", "squash"):
        sys.exit(0)

    # Localizar a raiz do repositório
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        sys.exit(0)

    if not root:
        sys.exit(0)

    summary_file = Path(root) / ".guardian" / "last-commit-summary.txt"

    if not summary_file.exists():
        sys.exit(0)

    # Verificar se o arquivo é recente (evita reutilizar resultado de commit anterior)
    age = time.time() - summary_file.stat().st_mtime
    if age > _MAX_AGE_SECONDS:
        sys.exit(0)

    trailer = summary_file.read_text(encoding="utf-8", errors="replace").strip()
    if not trailer:
        sys.exit(0)

    # Append do trailer na mensagem do commit (separado por linha em branco)
    current = commit_msg_file.read_text(encoding="utf-8", errors="replace")
    commit_msg_file.write_text(
        current.rstrip("\n") + "\n\n" + trailer + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
