#!/usr/bin/env python3
"""
Diff Parser - Extrai arquivos e linhas alterados do repositório git.

Uso:
    python diff_parser.py                        # diff vs origin/main
    python diff_parser.py --staged               # apenas staged files
    python diff_parser.py --base origin/develop  # branch base diferente
    python diff_parser.py --files-only           # apenas lista de arquivos
    python diff_parser.py --format text          # saída legível
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import re
import subprocess
from dataclasses import dataclass, asdict

EXCLUDE_PATTERNS = [
    "/Migrations/",
    ".Designer.cs",
    "/obj/",
    "/bin/",
    "/packages/",
    "AssemblyInfo.cs",
    ".g.cs",           # arquivos gerados
    ".g.i.cs",         # arquivos gerados
    "TemporaryGeneratedFile",
]

INCLUDE_EXTENSIONS = [".cs"]


@dataclass
class LineChange:
    file: str
    line: int
    content: str
    change_type: str   # "added" | "context"


@dataclass
class FileSummary:
    file: str
    lines_added: int
    lines_changed: list[LineChange]


def _run_git(cmd: list[str]) -> str:
    """Executa comando git e retorna stdout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if result.returncode != 0 and result.stderr:
            # Não fatal - pode ser que não haja diff
            pass
        return result.stdout
    except FileNotFoundError:
        print("❌ git não encontrado. Certifique-se de que git está instalado.", file=sys.stderr)
        sys.exit(1)


def _should_include(file_path: str) -> bool:
    """Verifica se o arquivo deve ser incluído na análise."""
    if not any(file_path.endswith(ext) for ext in INCLUDE_EXTENSIONS):
        return False
    if any(pattern in file_path.replace("\\", "/") for pattern in EXCLUDE_PATTERNS):
        return False
    return True


def get_changed_files(mode: str = "branch", base: str = "origin/main") -> list[str]:
    """Retorna lista de arquivos alterados filtrados."""
    if mode == "staged":
        output = _run_git(["git", "diff", "--cached", "--name-only"])
    else:
        _run_git(["git", "fetch", "origin", "main"])
        output = _run_git(["git", "diff", f"{base}...HEAD", "--name-only"])

    files = [f.strip() for f in output.splitlines() if f.strip()]
    return [f for f in files if _should_include(f)]


def parse_diff(mode: str = "branch", base: str = "origin/main") -> list[FileSummary]:
    """
    Parseia o diff do git e retorna mudanças por arquivo com número de linha.
    Inclui contexto (linhas ao redor) para melhor análise de IA.
    """
    if mode == "staged":
        diff_output = _run_git(["git", "diff", "--cached", "--unified=3"])
    else:
        _run_git(["git", "fetch", "origin", "main"])
        diff_output = _run_git(["git", "diff", f"{base}...HEAD", "--unified=3"])

    summaries: dict[str, FileSummary] = {}
    current_file: str | None = None
    current_line = 0

    for line in diff_output.splitlines():
        # Detectar arquivo
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            if current_file not in summaries and _should_include(current_file):
                summaries[current_file] = FileSummary(
                    file=current_file,
                    lines_added=0,
                    lines_changed=[]
                )
            continue

        if line.startswith("--- ") or line.startswith("diff --git"):
            continue

        # Detectar hunk header (@@ -X,Y +A,B @@)
        hunk_match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        if current_file is None or current_file not in summaries:
            # Arquivo excluído pelos filtros
            if not line.startswith(("-", "+")):
                current_line += 1
            elif line.startswith("+") and not line.startswith("+++"):
                current_line += 1
            continue

        summary = summaries[current_file]

        if line.startswith("+") and not line.startswith("+++"):
            # Linha adicionada
            summary.lines_changed.append(LineChange(
                file=current_file,
                line=current_line,
                content=line[1:],
                change_type="added"
            ))
            summary.lines_added += 1
            current_line += 1

        elif line.startswith("-") and not line.startswith("---"):
            # Linha removida - não incrementa line number do arquivo destino
            pass

        else:
            # Linha de contexto (sem + ou -)
            summary.lines_changed.append(LineChange(
                file=current_file,
                line=current_line,
                content=line[1:] if line.startswith(" ") else line,
                change_type="context"
            ))
            current_line += 1

    return list(summaries.values())


def format_diff_for_ai(summaries: list[FileSummary]) -> str:
    """
    Formata o diff de forma legível para análise de IA.
    Inclui apenas linhas adicionadas com contexto.
    """
    output = []
    for summary in summaries:
        output.append(f"\n=== {summary.file} ({summary.lines_added} linhas adicionadas) ===\n")
        for change in summary.lines_changed:
            prefix = "+" if change.change_type == "added" else " "
            output.append(f"{prefix} L{change.line:4d}: {change.content}")
    return "\n".join(output)


def main() -> None:
    args = sys.argv[1:]

    mode = "branch"
    base = "origin/main"
    files_only = "--files-only" in args
    output_format = "json"
    for_ai = "--for-ai" in args

    if "--staged" in args:
        mode = "staged"
    if "--base" in args:
        idx = args.index("--base")
        if idx + 1 < len(args):
            base = args[idx + 1]
    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            output_format = args[idx + 1]

    if files_only:
        files = get_changed_files(mode, base)
        if output_format == "json":
            print(json.dumps(files, ensure_ascii=False, indent=2))
        else:
            for f in files:
                print(f)
        sys.exit(0 if files else 1)

    summaries = parse_diff(mode, base)

    if not summaries:
        if output_format == "json":
            print("[]")
        else:
            print("ℹ️  Nenhum arquivo .cs alterado encontrado.")
        sys.exit(0)

    if for_ai:
        print(format_diff_for_ai(summaries))
    elif output_format == "json":
        result = []
        for s in summaries:
            result.append({
                "file": s.file,
                "lines_added": s.lines_added,
                "changes": [asdict(c) for c in s.lines_changed]
            })
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for s in summaries:
            added = [c for c in s.lines_changed if c.change_type == "added"]
            print(f"\n📁 {s.file} (+{s.lines_added} linhas)")
            for c in added[:10]:  # mostrar apenas 10 primeiras
                print(f"   L{c.line}: {c.content[:80]}")
            if len(added) > 10:
                print(f"   ... e mais {len(added) - 10} linhas")

    total_added = sum(s.lines_added for s in summaries)
    if output_format == "text":
        print(f"\n📊 Total: {len(summaries)} arquivo(s) | {total_added} linha(s) adicionada(s)")


if __name__ == "__main__":
    main()
