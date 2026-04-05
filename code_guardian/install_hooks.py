#!/usr/bin/env python3
"""
Code Guardian - Instalador de Git Hooks.

Suporta dois hooks:
  pre-commit  -> roda antes de cada 'git commit' (arquivos staged)
  pre-push    -> roda antes de cada 'git push'   (ultima barreira)

Uso:
    python install_hooks.py install                # instala pre-commit + pre-push
    python install_hooks.py install --pre-commit   # so pre-commit
    python install_hooks.py install --pre-push     # so pre-push
    python install_hooks.py uninstall              # remove ambos
    python install_hooks.py status                 # exibe status dos dois hooks
"""

import sys
import os
import subprocess
from pathlib import Path

# Garantir UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_MARKER_COMMIT = "Code Guardian Hook pre-commit"

# Cabeçalho comum aos dois hooks: resolve a raiz do repositório via git para
# garantir que o caminho do runner.py seja absoluto, independente do CWD com
# que o Visual Studio (ou outro cliente git) invocar o hook.
_HOOK_RESOLVE_ROOT = (
    "GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)\n"
    "if [ -z \"$GIT_ROOT\" ]; then\n"
    "    echo \"[guardian] Nao foi possivel encontrar a raiz do repositorio -- hook pulado.\"\n"
    "    exit 0\n"
    "fi\n"
    'GUARDIAN="$GIT_ROOT/code_guardian/runner.py"\n'
)

_HOOK_PRE_COMMIT = (
    "#!/bin/sh\n"
    "# Code Guardian Hook pre-commit\n"
    "# Executa analise estatica nos arquivos staged antes de commitar.\n"
    "# Para pular: git commit --no-verify\n"
    "\n"
    # Resolve a raiz do repositório e monta o caminho absoluto do runner
    + _HOOK_RESOLVE_ROOT +
    "\n"
    "if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then\n"
    "    echo \"[guardian] Python nao encontrado -- hook pulado.\"\n"
    "    exit 0\n"
    "fi\n"
    "PYTHON=python3\n"
    "command -v python3 > /dev/null 2>&1 || PYTHON=python\n"
    "\n"
    "if [ ! -f \"$GUARDIAN\" ]; then\n"
    "    echo \"[guardian] runner.py nao encontrado em: $GUARDIAN -- hook pulado.\"\n"
    "    exit 0\n"
    "fi\n"
    "\n"
    "STAGED=$(git diff --cached --name-only | grep -i \"\\.cs$\" | grep -v \"/Migrations/\" | grep -v \"\\.Designer\\.cs\" | grep -v \"/obj/\" | grep -v \"/bin/\")\n"
    "\n"
    "if [ -z \"$STAGED\" ]; then\n"
    "    exit 0\n"
    "fi\n"
    "\n"
    # Diretório e caminhos do relatório HTML e summary file
    "REPORT_DIR=\"$GIT_ROOT/.guardian\"\n"
    "REPORT_HTML=\"$REPORT_DIR/last-commit-report.html\"\n"
    "SUMMARY_FILE=\"$REPORT_DIR/last-commit-summary.txt\"\n"
    "mkdir -p \"$REPORT_DIR\"\n"
    # Limpar summary anterior para evitar reutilização se --no-verify for usado depois
    "rm -f \"$SUMMARY_FILE\"\n"
    "\n"
    "echo \"\"\n"
    "echo \"[guardian] Verificando arquivos antes do commit...\"\n"
    "echo \"\"\n"
    "\n"
    # --severity warning: HTML mostra tudo; --fail-on error: bloqueia só em critical/error
    # --summary-file: grava trailer para o hook prepare-commit-msg injetar na mensagem
    "$PYTHON \"$GUARDIAN\" --staged --rules-only --severity warning --fail-on error --timeout 60 --output \"$REPORT_HTML\" --summary-file \"$SUMMARY_FILE\"\n"
    "\n"
    "EXIT_CODE=$?\n"
    "\n"
    "if [ $EXIT_CODE -ne 0 ]; then\n"
    "    rm -f \"$SUMMARY_FILE\"\n"
    "    echo \"\"\n"
    "    echo \"[guardian] BLOQUEADO: issues criticas encontradas.\"\n"
    "    echo \"   Relatorio detalhado: $REPORT_HTML\"\n"
    "    echo \"   Para pular a verificacao: git commit --no-verify\"\n"
    "    echo \"\"\n"
    "    exit 1\n"
    "fi\n"
    "\n"
    "echo \"\"\n"
    "echo \"[guardian] Nenhum bloqueador. Commit liberado.\"\n"
    "echo \"   Relatorio: $REPORT_HTML\"\n"
    "echo \"\"\n"
    "exit 0\n"
)

_MARKER_PREPARE = "Code Guardian Hook prepare-commit-msg"

_HOOK_PREPARE_COMMIT_MSG = (
    "#!/bin/sh\n"
    "# Code Guardian Hook prepare-commit-msg\n"
    "# Injeta trailer Guardian-Review na mensagem do commit apos analise bem-sucedida.\n"
    "\n"
    + _HOOK_RESOLVE_ROOT +
    "\n"
    "if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then\n"
    "    exit 0\n"
    "fi\n"
    "PYTHON=python3\n"
    "command -v python3 > /dev/null 2>&1 || PYTHON=python\n"
    "\n"
    'TRAILER_SCRIPT="$GIT_ROOT/code_guardian/_append_guardian_trailer.py"\n'
    'if [ ! -f "$TRAILER_SCRIPT" ]; then exit 0; fi\n'
    "\n"
    '$PYTHON "$TRAILER_SCRIPT" "$1" "${2:-}"\n'
    "exit 0\n"
)

_MARKER_PUSH = "Code Guardian Hook pre-push"

_HOOK_PRE_PUSH = (
    "#!/bin/sh\n"
    "# Code Guardian Hook pre-push\n"
    "# Executa analise estatica antes de cada push (ultima barreira).\n"
    "# Para pular: git push --no-verify\n"
    "\n"
    # Resolve a raiz do repositório e monta o caminho absoluto do runner
    + _HOOK_RESOLVE_ROOT +
    "\n"
    "if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then\n"
    "    echo \"[guardian] Python nao encontrado -- hook pulado.\"\n"
    "    exit 0\n"
    "fi\n"
    "PYTHON=python3\n"
    "command -v python3 > /dev/null 2>&1 || PYTHON=python\n"
    "\n"
    "if [ ! -f \"$GUARDIAN\" ]; then\n"
    "    echo \"[guardian] runner.py nao encontrado em: $GUARDIAN -- hook pulado.\"\n"
    "    exit 0\n"
    "fi\n"
    "\n"
    # Diretório e caminho do relatório HTML — sempre gerado para cada push
    "REPORT_DIR=\"$GIT_ROOT/.guardian\"\n"
    "REPORT_HTML=\"$REPORT_DIR/last-push-report.html\"\n"
    "mkdir -p \"$REPORT_DIR\"\n"
    "\n"
    "echo \"\"\n"
    "echo \"[guardian] Verificando branch antes do push...\"\n"
    "echo \"\"\n"
    "\n"
    # --severity warning: HTML mostra tudo; --fail-on error: bloqueia só em critical/error
    "$PYTHON \"$GUARDIAN\" --rules-only --severity warning --fail-on error --timeout 60 --output \"$REPORT_HTML\"\n"
    "\n"
    "EXIT_CODE=$?\n"
    "\n"
    "if [ $EXIT_CODE -ne 0 ]; then\n"
    "    echo \"\"\n"
    "    echo \"[guardian] BLOQUEADO: issues criticas encontradas.\"\n"
    "    echo \"   Relatorio detalhado: $REPORT_HTML\"\n"
    "    echo \"   Para pular a verificacao: git push --no-verify\"\n"
    "    echo \"\"\n"
    "    exit 1\n"
    "fi\n"
    "\n"
    "echo \"\"\n"
    "echo \"[guardian] Nenhum bloqueador. Push liberado.\"\n"
    "echo \"   Relatorio: $REPORT_HTML\"\n"
    "echo \"\"\n"
    "exit 0\n"
)


def _find_git_root():
    """Localiza a raiz do repositorio git."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(r.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _get_hooks_dir(git_root):
    """Retorna o diretorio de hooks do git."""
    try:
        r = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True, text=True, check=True, cwd=git_root,
        )
        custom = r.stdout.strip()
        if custom:
            p = Path(custom)
            return p if p.is_absolute() else git_root / custom
    except subprocess.CalledProcessError:
        pass
    return git_root / ".git" / "hooks"


def _install_one(hooks_dir, hook_name, marker, script_content):
    """Instala um hook individual. Retorna True se bem-sucedido."""
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / hook_name

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8", errors="ignore")
        if marker not in existing:
            print(f"Aviso: ja existe um hook {hook_name} em {hook_path}")
            print("  Ele NAO foi criado pelo Code Guardian.")
            print("  Para nao sobrescrever, adicione ao final do hook existente:")
            print("  python code_guardian/runner.py \\")
            print("    --staged --rules-only --severity error --fail-on error || exit 1")
            print()
            resposta = input(f"  Sobrescrever o hook {hook_name} existente? [s/N] ").strip().lower()
            if resposta != "s":
                print(f"  Instalacao de {hook_name} cancelada.")
                return False
        else:
            print(f"Info: Hook {hook_name} do Code Guardian ja existe. Atualizando...")

    hook_path.write_text(script_content, encoding="utf-8")
    if os.name != "nt":
        hook_path.chmod(0o755)

    print(f"OK: Hook {hook_name} instalado em: {hook_path}")
    return True


def _uninstall_one(hooks_dir, hook_name, marker):
    """Remove um hook se foi criado pelo Code Guardian."""
    hook_path = hooks_dir / hook_name

    if not hook_path.exists():
        print(f"Info: Hook {hook_name}: nao encontrado (nao instalado).")
        return True

    existing = hook_path.read_text(encoding="utf-8", errors="ignore")
    if marker not in existing:
        print(f"Aviso: Hook {hook_name}: existe mas NAO foi criado pelo Code Guardian.")
        print("  Remocao cancelada para nao apagar hook de terceiro.")
        return False

    hook_path.unlink()
    print(f"OK: Hook {hook_name} removido.")
    return True


def _status_one(hooks_dir, hook_name, marker):
    """Exibe o status de um hook."""
    hook_path = hooks_dir / hook_name

    if not hook_path.exists():
        print(f"  {hook_name:12} NAO instalado")
        return False

    existing   = hook_path.read_text(encoding="utf-8", errors="ignore")
    is_guardian = marker in existing
    is_exec     = os.access(hook_path, os.X_OK) if os.name != "nt" else True

    if is_guardian and is_exec:
        print(f"  {hook_name:12} OK (Code Guardian)")
    elif is_guardian and not is_exec:
        print(f"  {hook_name:12} Aviso: sem permissao de execucao")
        print(f"               Corrigir: chmod +x {hook_path}")
    else:
        print(f"  {hook_name:12} Aviso: instalado (NAO e do Code Guardian)")

    return True


def cmd_install(git_root, which):
    """Instala um ou ambos os hooks."""
    hooks_dir = _get_hooks_dir(git_root)
    ok = True

    if which in ("pre-commit", "all"):
        if not _install_one(hooks_dir, "pre-commit", _MARKER_COMMIT, _HOOK_PRE_COMMIT):
            ok = False
        else:
            # prepare-commit-msg é instalado junto com o pre-commit (injeta trailer na mensagem)
            _install_one(hooks_dir, "prepare-commit-msg", _MARKER_PREPARE, _HOOK_PREPARE_COMMIT_MSG)

    if which in ("pre-push", "all"):
        if not _install_one(hooks_dir, "pre-push", _MARKER_PUSH, _HOOK_PRE_PUSH):
            ok = False

    if ok:
        print()
        print("Para pular qualquer hook:")
        print("  git commit --no-verify   (pula pre-commit)")
        print("  git push   --no-verify   (pula pre-push)")
        print()
        print("Para remover:")
        print("  python install_hooks.py uninstall")

    return 0 if ok else 1


def cmd_uninstall(git_root, which):
    """Remove um ou ambos os hooks."""
    hooks_dir = _get_hooks_dir(git_root)
    ok = True

    if which in ("pre-commit", "all"):
        if not _uninstall_one(hooks_dir, "pre-commit", _MARKER_COMMIT):
            ok = False
        _uninstall_one(hooks_dir, "prepare-commit-msg", _MARKER_PREPARE)

    if which in ("pre-push", "all"):
        if not _uninstall_one(hooks_dir, "pre-push", _MARKER_PUSH):
            ok = False

    return 0 if ok else 1


def cmd_status(git_root):
    """Exibe o status dos hooks instalados."""
    hooks_dir = _get_hooks_dir(git_root)

    print(f"Repositorio : {git_root}")
    print(f"Hooks dir   : {hooks_dir}")
    print()
    print("Hooks instalados:")

    _status_one(hooks_dir, "pre-commit",         _MARKER_COMMIT)
    _status_one(hooks_dir, "prepare-commit-msg",  _MARKER_PREPARE)
    _status_one(hooks_dir, "pre-push",            _MARKER_PUSH)
    return 0


def main():
    valid_cmds = ("install", "uninstall", "status")

    if len(sys.argv) < 2 or sys.argv[1] not in valid_cmds:
        print("Uso: python install_hooks.py <comando> [--pre-commit | --pre-push]")
        print()
        print("Comandos:")
        print("  install     Instala os hooks (padrao: pre-commit + pre-push)")
        print("  uninstall   Remove os hooks instalados pelo Code Guardian")
        print("  status      Exibe status dos hooks")
        print()
        print("Flags:")
        print("  --pre-commit   Apenas o hook pre-commit (antes do commit)")
        print("  --pre-push     Apenas o hook pre-push   (antes do push)")
        print("  (sem flag)     Ambos os hooks")
        sys.exit(1)

    git_root = _find_git_root()
    if git_root is None:
        print("Erro: Nenhum repositorio git encontrado no diretorio atual.")
        sys.exit(1)

    cmd   = sys.argv[1]
    flags = sys.argv[2:]

    if "--pre-commit" in flags:
        which = "pre-commit"
    elif "--pre-push" in flags:
        which = "pre-push"
    else:
        which = "all"

    if cmd == "install":
        sys.exit(cmd_install(git_root, which))
    elif cmd == "uninstall":
        sys.exit(cmd_uninstall(git_root, which))
    elif cmd == "status":
        sys.exit(cmd_status(git_root))


if __name__ == "__main__":
    main()
