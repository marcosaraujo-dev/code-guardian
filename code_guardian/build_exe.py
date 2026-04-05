"""
build_exe.py — Empacota o Code Guardian UI como executável standalone (.exe)

Uso:
    python build_exe.py

Pré-requisito:
    pip install pyinstaller

O .exe gerado fica em: dist/CodeGuardian.exe
Os scripts Python (.py) são embutidos no exe e extraídos para
%APPDATA%/CodeGuardian/scripts/ na primeira execução — ou lidos
diretamente de sys._MEIPASS enquanto o processo está ativo.

IMPORTANTE: O .exe requer Python instalado no sistema do usuário
para executar os scripts de análise (runner.py, vb6_rule_engine.py).
Instale Python 3.10+ em python.org e adicione ao PATH.
"""

import sys
import subprocess
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR   = SCRIPT_DIR.parent.parent.parent  # raiz do repo

# Scripts Python que serão embutidos no exe como dados
ANALYSIS_SCRIPTS = [
    "runner.py",
    "rule_engine.py",
    "vb6_rule_engine.py",
    "metrics.py",
    "diff_parser.py",
    "ai_client.py",
    "spelling_checker.py",
    "config.json",
]

# Ícone (opcional — coloque um .ico em SCRIPT_DIR/assets/icon.ico)
ICON_PATH = SCRIPT_DIR / "assets" / "icon.ico"


def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        print("✓ PyInstaller encontrado.")
    except ImportError:
        print("PyInstaller não instalado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller instalado.")


def build():
    check_pyinstaller()

    # Montar --add-data para cada script de análise
    # Formato PyInstaller Windows: "origem;destino_dentro_do_bundle"
    add_data_args = []
    for script in ANALYSIS_SCRIPTS:
        src = SCRIPT_DIR / script
        if src.exists():
            add_data_args += ["--add-data", f"{src};scripts"]
        else:
            print(f"  AVISO: {script} não encontrado, será ignorado.")

    # Embutir pasta assets/ (ícone e outros recursos)
    assets_dir = SCRIPT_DIR / "assets"
    if assets_dir.exists():
        add_data_args += ["--add-data", f"{assets_dir};assets"]
        print(f"✓ Assets embutidos: {assets_dir}")

    icon_args = []
    if ICON_PATH.exists():
        icon_args = ["--icon", str(ICON_PATH)]
        print(f"✓ Ícone: {ICON_PATH}")
    else:
        print(f"  INFO: Ícone não encontrado em {ICON_PATH} — sem ícone personalizado.")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Tudo em um único .exe
        "--windowed",                   # Sem janela de console
        "--name", "CodeGuardian",       # Nome do exe
        "--distpath", str(ROOT_DIR / "dist"),
        "--workpath", str(ROOT_DIR / "build"),
        "--specpath", str(SCRIPT_DIR),
        "--clean",                      # Limpar build anterior
        *icon_args,
        *add_data_args,
        # Ocultar imports que PyInstaller pode não detectar automaticamente
        "--hidden-import", "customtkinter",
        "--hidden-import", "darkdetect",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "packaging",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",
        # Coletar todos os dados do customtkinter (temas, imagens)
        "--collect-data", "customtkinter",
        str(SCRIPT_DIR / "code_guardian_ui.py"),
    ]

    print("\nExecutando PyInstaller...")
    print("Comando:", " ".join(cmd))
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = ROOT_DIR / "dist" / "CodeGuardian.exe"
        size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0
        print(f"\n{'='*60}")
        print(f"✓ Build concluído!")
        print(f"  Arquivo : {exe_path}")
        print(f"  Tamanho : {size_mb:.1f} MB")
        print(f"\nDistribuição:")
        print(f"  Copie apenas: dist/CodeGuardian.exe")
        print(f"\nRequisito no sistema do usuário:")
        print(f"  Python 3.10+ instalado e no PATH (para rodar os scripts de análise)")
        print(f"{'='*60}")
    else:
        print(f"\n✗ Build falhou (exit {result.returncode})")
        print("Verifique os erros acima.")
        sys.exit(1)


if __name__ == "__main__":
    build()
