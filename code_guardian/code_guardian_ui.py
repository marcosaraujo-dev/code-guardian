"""
Code Guardian UI — Interface gráfica para execução dos scripts de code review.
Suporta análise de projetos C# e VB6 com terminal integrado.

Uso: python code_guardian_ui.py

Dependências (instaladas automaticamente na primeira execução):
  - customtkinter  — UI moderna dark/light
  - darkdetect     — detecção de tema do sistema (dep. do customtkinter)
  - packaging      — utilitários de versão (dep. do customtkinter)
  - Pillow         — suporte a imagens e ícones
"""

import sys
import os
import json
import queue
import threading
import subprocess
import webbrowser
import time
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ── Tela de instalação de dependências ───────────────────────────────────────

REQUIRED_PACKAGES = [
    ("customtkinter", "customtkinter"),
    ("darkdetect",    "darkdetect"),
    ("Pillow",        "PIL"),
    ("packaging",     "packaging"),
]


def _check_missing() -> list[tuple[str, str]]:
    """Retorna lista de (pip_name, import_name) dos pacotes não instalados."""
    missing = []
    for pip_name, import_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append((pip_name, import_name))
    return missing


class InstallerWindow:
    """Janela de loading/instalação de dependências em tkinter puro."""

    BG      = "#1E1E1E"
    FG      = "#D4D4D4"
    GREEN   = "#4EC9B0"
    YELLOW  = "#CE9178"
    BLUE    = "#4FC3F7"
    FONT    = ("Segoe UI", 10)
    FONT_B  = ("Segoe UI", 11, "bold")
    FONT_SM = ("Segoe UI", 9)

    def __init__(self, packages: list[tuple[str, str]]):
        self.packages = packages
        self.success = False
        self._root = tk.Tk()
        self._root.title("Code Guardian — Instalando dependências")
        self._root.geometry("480x380")
        self._root.resizable(False, False)
        self._root.configure(bg=self.BG)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center()
        self._build_ui()

    def _center(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - 480) // 2
        y = (sh - 380) // 2
        self._root.geometry(f"480x380+{x}+{y}")

    def _build_ui(self):
        # Título
        tk.Label(self._root, text="Code Guardian", bg=self.BG, fg=self.GREEN,
                 font=("Segoe UI", 16, "bold")).pack(pady=(20, 2))
        tk.Label(self._root, text="Instalando dependências necessárias...",
                 bg=self.BG, fg=self.FG, font=self.FONT).pack(pady=(0, 16))

        # Lista de pacotes
        pkg_frame = tk.Frame(self._root, bg="#2A2A2A", bd=0)
        pkg_frame.pack(fill="x", padx=24, pady=(0, 12))
        self._pkg_labels: dict[str, tk.Label] = {}
        for pip_name, _ in self.packages:
            row = tk.Frame(pkg_frame, bg="#2A2A2A")
            row.pack(fill="x", padx=12, pady=4)
            tk.Label(row, text=f"  {pip_name}", bg="#2A2A2A", fg=self.FG,
                     font=self.FONT, anchor="w", width=22).pack(side="left")
            lbl = tk.Label(row, text="Aguardando...", bg="#2A2A2A",
                           fg=self.YELLOW, font=self.FONT_SM)
            lbl.pack(side="left")
            self._pkg_labels[pip_name] = lbl

        # Barra de progresso
        tk.Label(self._root, text="Progresso:", bg=self.BG, fg=self.FG,
                 font=self.FONT).pack(anchor="w", padx=24, pady=(4, 2))
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Guardian.Horizontal.TProgressbar",
                        troughcolor="#2A2A2A", background=self.BLUE,
                        bordercolor="#2A2A2A", lightcolor=self.BLUE,
                        darkcolor=self.BLUE)
        self._progress = ttk.Progressbar(
            self._root, style="Guardian.Horizontal.TProgressbar",
            orient="horizontal", length=430, mode="determinate",
            maximum=len(self.packages),
        )
        self._progress.pack(padx=24, pady=(0, 8))

        # Log de saída
        self._log = tk.Text(self._root, height=5, bg="#111111", fg="#858585",
                            font=("Consolas", 8), state="disabled", bd=0,
                            wrap="word")
        self._log.pack(fill="x", padx=24, pady=(0, 12))

        # Status
        self._status = tk.Label(self._root, text="Iniciando...",
                                bg=self.BG, fg=self.YELLOW, font=self.FONT)
        self._status.pack(pady=(0, 8))

    def _log_line(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")
        self._root.update()

    def _set_status(self, text: str, color: str = None):
        self._status.configure(text=text, fg=color or self.YELLOW)
        self._root.update()

    def _set_pkg_status(self, pip_name: str, text: str, color: str):
        if pip_name in self._pkg_labels:
            self._pkg_labels[pip_name].configure(text=text, fg=color)
        self._root.update()

    def _install_all(self):
        total = len(self.packages)
        failed = []

        for i, (pip_name, _) in enumerate(self.packages):
            self._set_pkg_status(pip_name, "Instalando...", self.BLUE)
            self._set_status(f"Instalando {pip_name} ({i+1}/{total})...")
            self._log_line(f">> pip install {pip_name}")

            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", pip_name,
                     "--quiet", "--no-warn-script-location"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                for line in iter(proc.stdout.readline, ""):
                    stripped = line.strip()
                    if stripped:
                        self._log_line(f"   {stripped}")
                proc.wait()

                if proc.returncode == 0:
                    self._set_pkg_status(pip_name, "✓ Instalado", self.GREEN)
                    self._log_line(f"   OK: {pip_name}")
                else:
                    self._set_pkg_status(pip_name, "✗ Falhou", "#F44747")
                    failed.append(pip_name)
                    self._log_line(f"   ERRO: {pip_name} (exit {proc.returncode})")
            except Exception as e:
                self._set_pkg_status(pip_name, "✗ Erro", "#F44747")
                failed.append(pip_name)
                self._log_line(f"   EXCECAO: {e}")

            self._progress["value"] = i + 1
            self._root.update()
            time.sleep(0.1)

        if failed:
            self._set_status(
                f"Falhou: {', '.join(failed)}. Tente: pip install {' '.join(failed)}",
                color="#F44747",
            )
            self._root.after(4000, self._root.destroy)
        else:
            self._set_status("Todas as dependências instaladas! Iniciando...", self.GREEN)
            self.success = True
            self._root.after(1200, self._root.destroy)

    def _on_close(self):
        self._root.destroy()

    def run(self) -> bool:
        """Executa a janela de instalação. Retorna True se tudo foi instalado."""
        threading.Thread(target=self._install_all, daemon=True).start()
        self._root.mainloop()
        return self.success


def _ensure_dependencies() -> bool:
    """
    Verifica e instala dependências ausentes.
    Retorna True se todas estão disponíveis (já instaladas ou instaladas agora).
    """
    missing = _check_missing()
    if not missing:
        return True

    installer = InstallerWindow(missing)
    ok = installer.run()

    if not ok:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erro de instalação",
            "Não foi possível instalar todas as dependências.\n\n"
            "Execute manualmente:\n"
            "  pip install customtkinter Pillow\n\n"
            "Em seguida reinicie o programa.",
        )
        root.destroy()
        return False

    # Verificar novamente após instalação
    still_missing = _check_missing()
    if still_missing:
        names = ", ".join(p[0] for p in still_missing)
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Reinício necessário",
            f"Pacotes instalados mas não carregados: {names}\n\n"
            "Feche e abra o programa novamente.",
        )
        root.destroy()
        return False

    return True


# ── Task 1: Importar customtkinter após garantir instalação ──────────────────
# (importação real acontece no __main__ após _ensure_dependencies())

CTK_AVAILABLE = False
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    # Shim mínimo para que o módulo carregue sem CTK
    class _Shim:
        def __getattr__(self, name):
            mapping = {
                "CTk": tk.Tk,
                "CTkFrame": tk.Frame,
                "CTkLabel": tk.Label,
                "CTkButton": tk.Button,
                "CTkEntry": tk.Entry,
                "CTkCheckBox": tk.Checkbutton,
                "CTkRadioButton": tk.Radiobutton,
                "CTkTextbox": tk.Text,
                "CTkTabview": None,
                "CTkOptionMenu": tk.OptionMenu,
                "CTkToplevel": tk.Toplevel,
                "CTkScrollableFrame": tk.Frame,
            }
            if name in mapping and mapping[name]:
                return mapping[name]
            raise AttributeError(f"Shim não implementa: {name}")
        def set_appearance_mode(self, *a): pass
        def set_default_color_theme(self, *a): pass
    ctk = _Shim()

VERSION = "1.0.0"

# Quando empacotado como .exe (PyInstaller), os scripts ficam em sys._MEIPASS/scripts/
if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys._MEIPASS) / "scripts"  # type: ignore[attr-defined]
else:
    SCRIPT_DIR = Path(__file__).parent

RUNNER_SCRIPT = SCRIPT_DIR / "runner.py"
VB6_SCRIPT    = SCRIPT_DIR / "vb6_rule_engine.py"

# config.json fica em %APPDATA%/CodeGuardian/ para que o usuário possa
# alterar chaves de API sem precisar recompilar o exe.
# Quando rodando como script Python puro (dev), usa o arquivo local.
_APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "CodeGuardian"
_DEFAULT_CONFIG_TEMPLATE = SCRIPT_DIR / "config.json"   # template embutido no exe

if getattr(sys, "frozen", False):
    # Frozen (.exe): sempre usar AppData
    CONFIG_PATH = _APPDATA_DIR / "config.json"
else:
    # Desenvolvimento: usar arquivo local (comportamento original)
    CONFIG_PATH = _DEFAULT_CONFIG_TEMPLATE


def _ensure_config_dir():
    """
    Garante que o diretório de configuração do usuário existe e tem o config.json.
    Na primeira execução do exe, copia o template embutido para AppData.
    """
    if not getattr(sys, "frozen", False):
        return  # Dev: nada a fazer

    _APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists() and _DEFAULT_CONFIG_TEMPLATE.exists():
        shutil.copy2(_DEFAULT_CONFIG_TEMPLATE, CONFIG_PATH)


def _get_python_executable() -> str:
    """
    Retorna o caminho do interpretador Python.
    Quando rodando como .exe empacotado (frozen), procura Python no PATH do sistema,
    pois sys.executable aponta para o .exe, não para python.exe.
    """
    if not getattr(sys, "frozen", False):
        return sys.executable

    # Frozen: tentar encontrar Python instalado no sistema
    for candidate in ["python", "python3", "py"]:
        found = shutil.which(candidate)
        if found:
            return found

    # Fallback para tentativas comuns no Windows
    for path in [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Python/Python311/python.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Python/Python312/python.exe",
        Path("C:/Python311/python.exe"),
        Path("C:/Python312/python.exe"),
    ]:
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "Python não encontrado no sistema.\n"
        "Instale Python 3.10+ em python.org e adicione ao PATH."
    )

# ── Task 3: Constantes de cores e fontes ─────────────────────────────────────
TERMINAL_BG    = "#1E1E1E"
TERMINAL_FG    = "#D4D4D4"
COLOR_SUCCESS  = "#4EC9B0"
COLOR_WARNING  = "#CE9178"
COLOR_ERROR    = "#F44747"
COLOR_INFO     = "#9CDCFE"
COLOR_DIM      = "#858585"
MONOSPACE_FONT = ("Consolas", 11)


# ── Task 2: AppState dataclass ────────────────────────────────────────────────
@dataclass
class AppState:
    is_running: bool = False
    last_report_path: Optional[Path] = None
    current_runner: Any = None
    output_queue: queue.Queue = field(default_factory=queue.Queue)
    repo_root: Path = field(default_factory=Path.cwd)


# ── Task 8: Helper _find_guardian_dir ────────────────────────────────────────
def _find_guardian_dir(cwd: Optional[Path] = None) -> Path:
    """Detecta a pasta .guardian/ via git rev-parse; fallback para cwd."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
            cwd=str(cwd or Path.cwd()),
            timeout=5,
        )
        if result.returncode == 0:
            guardian = Path(result.stdout.strip()) / ".guardian"
            guardian.mkdir(exist_ok=True)
            return guardian
    except Exception:
        pass
    fallback = (cwd or Path.cwd()) / ".guardian"
    fallback.mkdir(exist_ok=True)
    return fallback


def _detect_repo_root() -> Path:
    """Retorna o root do repositório git, ou o diretório atual."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
            cwd=str(SCRIPT_DIR),
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


# ── Task 4: TerminalOutput widget ────────────────────────────────────────────
class TerminalOutput(ctk.CTkFrame):
    """Widget de terminal com cores e auto-scroll."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._textbox = ctk.CTkTextbox(
            self,
            state="disabled",
            font=MONOSPACE_FONT,
            fg_color=TERMINAL_BG,
            text_color=TERMINAL_FG,
            wrap="word",
        )
        self._textbox.grid(row=0, column=0, sticky="nsew")

        # Configurar tags de cor no widget interno
        inner = self._textbox._textbox if hasattr(self._textbox, "_textbox") else self._textbox
        inner.tag_config("success",   foreground=COLOR_SUCCESS)
        inner.tag_config("warning",   foreground=COLOR_WARNING)
        inner.tag_config("error",     foreground=COLOR_ERROR)
        inner.tag_config("info",      foreground=COLOR_INFO)
        inner.tag_config("dim",       foreground=COLOR_DIM)
        inner.tag_config("timestamp", foreground=COLOR_DIM)
        self._inner = inner

    def append_line(self, text: str, tag: str = "info"):
        """Insere linha com timestamp e cor no terminal."""
        ts = datetime.now().strftime("[%H:%M:%S] ")
        self._inner.configure(state="normal")
        self._inner.insert("end", ts, "timestamp")
        self._inner.insert("end", text + "\n", tag)
        self._inner.configure(state="disabled")
        self._inner.see("end")

    def clear(self):
        """Limpa todo o conteúdo."""
        self._inner.configure(state="normal")
        self._inner.delete("1.0", "end")
        self._inner.configure(state="disabled")


# ── Task 5: SubprocessRunner ──────────────────────────────────────────────────
class SubprocessRunner(threading.Thread):
    """Executa um subprocess em background e alimenta a queue com output."""

    def __init__(self, cmd: list, output_queue: queue.Queue,
                 cwd: Optional[str] = None, env: Optional[dict] = None):
        super().__init__(daemon=True)
        self.cmd = cmd
        self.output_queue = output_queue
        self.cwd = cwd
        self.env = env
        self._proc: Optional[subprocess.Popen] = None
        self._cancelled = False

    def run(self):
        try:
            self._proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                cwd=self.cwd,
                env=self.env,
            )
            for line in iter(self._proc.stdout.readline, ""):
                if self._cancelled:
                    break
                stripped = line.rstrip()
                if stripped:
                    tag = self._classify_line(stripped)
                    self.output_queue.put((tag, stripped))
            self._proc.wait()
            returncode = -1 if self._cancelled else (self._proc.returncode or 0)
        except Exception as e:
            self.output_queue.put(("error", f"Erro ao executar: {e}"))
            returncode = 1
        self.output_queue.put(("_done_", str(returncode)))

    def cancel(self):
        self._cancelled = True
        if self._proc:
            self._proc.terminate()
            def _force_kill():
                try:
                    if self._proc and self._proc.poll() is None:
                        self._proc.kill()
                except Exception:
                    pass
            threading.Timer(2.0, _force_kill).start()

    def _classify_line(self, line: str) -> str:
        low = line.lower()
        if any(x in low for x in ["critical", "🔴", "sql injection", "hardcoded"]):
            return "error"
        if any(x in low for x in ["error", "erro", "falha", "🟠", "exception", "bloqueado"]):
            return "error"
        if any(x in low for x in ["warning", "aviso", "🟡", "atenção"]):
            return "warning"
        if any(x in low for x in ["✅", "concluída", "concluido", "sucesso", "nenhum problema",
                                   "nenhum bloqueador", "liberado"]):
            return "success"
        if any(x in low for x in ["executando", "analisando", "processando", "[guardian]"]):
            return "dim"
        return "info"


# ── Task 6: build_csharp_cmd ──────────────────────────────────────────────────
def build_csharp_cmd(panel) -> list:
    """Constrói a lista de args para runner.py baseado nas seleções do painel C#."""
    cmd = [_get_python_executable(), str(RUNNER_SCRIPT)]
    mode = panel.mode_var.get()

    if mode == "diff":
        base = panel.base_branch_var.get().strip() or "origin/main"
        cmd += ["--base", base]
    elif mode == "staged":
        cmd += ["--staged"]
    elif mode == "file":
        path = panel.file_var.get().strip()
        if not path:
            raise ValueError("Selecione um arquivo .cs para analisar.")
        cmd += ["--file", path]
    elif mode == "scan":
        d = panel.scan_dir_var.get().strip()
        if not d:
            raise ValueError("Selecione uma pasta para o scan.")
        cmd += ["--scan", "--dir", d]

    if panel.rules_only_var.get():
        cmd += ["--rules-only"]

    severity = panel.severity_var.get()
    if severity and severity != "info":
        cmd += ["--severity", severity]

    fail_on = panel.fail_on_var.get()
    if fail_on and fail_on != "none":
        cmd += ["--fail-on", fail_on]

    timeout = panel.timeout_var.get().strip()
    if timeout and timeout != "60":
        cmd += ["--timeout", timeout]

    output = panel.output_var.get().strip()
    if output:
        cmd += ["--output", output]

    return cmd


# ── Task 7: build_vb6_cmd ─────────────────────────────────────────────────────
def build_vb6_cmd(panel) -> list:
    """Constrói a lista de args para vb6_rule_engine.py baseado nas seleções do painel VB6."""
    cmd = [_get_python_executable(), str(VB6_SCRIPT)]
    mode = panel.mode_var.get()

    if mode == "file":
        path = panel.file_var.get().strip()
        if not path:
            raise ValueError("Selecione um arquivo VB6 (.bas, .cls, .frm, .ctl).")
        cmd += [path]
    elif mode == "scan":
        d = panel.scan_dir_var.get().strip()
        if not d:
            raise ValueError("Selecione uma pasta para o scan.")
        cmd += ["--scan", "--dir", d]
    elif mode == "compare":
        base = panel.compare_base_var.get().strip()
        review = panel.compare_review_var.get().strip()
        if not base:
            raise ValueError("Selecione a pasta base (código original).")
        if not review:
            raise ValueError("Selecione a pasta de revisão (código modificado).")
        cmd += ["--compare", "--base", base, "--review", review]
        if getattr(panel, "diff_only_var", None) and panel.diff_only_var.get():
            cmd += ["--diff-only"]
    elif mode == "file_compare":
        base = panel.compare_file_base_var.get().strip()
        review = panel.compare_file_review_var.get().strip()
        if not base:
            raise ValueError("Selecione o arquivo original (base).")
        if not review:
            raise ValueError("Selecione o arquivo modificado (revisão).")
        cmd += ["--compare-files", "--base", base, "--review", review]
        if getattr(panel, "diff_only_var", None) and panel.diff_only_var.get():
            cmd += ["--diff-only"]

    severity = panel.severity_var.get()
    if severity and severity != "info":
        cmd += ["--severity", severity]

    fmt = panel.format_var.get()
    if fmt == "json":
        cmd += ["--format", "json"]
    elif fmt == "html":
        cmd += ["--format", "html"]
    # "text + html" é o padrão, sem flag

    # Gerar nome de saída automático para HTML e forçar --format html
    if fmt != "json" and mode != "file":
        ts = datetime.now().strftime("%Y-%m-%d-%H%M")
        guardian = _find_guardian_dir()
        out_name = f"code-review-{ts} - VB6.html"
        cmd += ["--format", "html", "--output", str(guardian / out_name)]

    return cmd


# ── Task 9-11: CsharpPanel ────────────────────────────────────────────────────
class CsharpPanel(ctk.CTkFrame):
    """Painel de configurações para análise C#."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.mode_var = tk.StringVar(value="diff")
        self.base_branch_var = tk.StringVar(value="origin/main")
        self.file_var = tk.StringVar()
        self.scan_dir_var = tk.StringVar()
        self.rules_only_var = tk.BooleanVar(value=False)
        self.severity_var = tk.StringVar(value="info")
        self.fail_on_var = tk.StringVar(value="none")
        self.timeout_var = tk.StringVar(value="60")
        self.output_var = tk.StringVar()
        self.ai_provider_var = tk.StringVar(value="Auto (config.json)")
        self.project_root_var = tk.StringVar()   # raiz do projeto (CWD do subprocess)
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        row = 0

        # ── Seção: Modo de Análise
        mode_frame = ctk.CTkFrame(self)
        mode_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 4))
        mode_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mode_frame, text="Modo de Análise", font=("Segoe UI", 12, "bold")
                     ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        modes = [
            ("Diff vs branch (padrão)", "diff"),
            ("Staged (arquivos em staging)", "staged"),
            ("Arquivo único (.cs)", "file"),
            ("Scan de diretório", "scan"),
        ]
        for i, (label, value) in enumerate(modes):
            ctk.CTkRadioButton(
                mode_frame, text=label,
                variable=self.mode_var, value=value,
                command=self._on_mode_change,
            ).grid(row=i + 1, column=0, sticky="w", padx=20, pady=2)

        row += 1

        # ── Seção: Input específico por modo
        self._input_frame = ctk.CTkFrame(self)
        self._input_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        self._input_frame.grid_columnconfigure(1, weight=1)
        self._build_mode_inputs()
        row += 1

        # ── Seção: Opções
        opt_frame = ctk.CTkFrame(self)
        opt_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        opt_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(opt_frame, text="Opções", font=("Segoe UI", 12, "bold")
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))

        # Checkbox "Apenas regras"
        ctk.CTkCheckBox(
            opt_frame, text="Apenas regras (sem IA)",
            variable=self.rules_only_var,
            command=self._on_rules_only_change,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=2)

        # Severidade
        ctk.CTkLabel(opt_frame, text="Severidade mínima:").grid(
            row=2, column=0, sticky="w", padx=20, pady=2)
        ctk.CTkOptionMenu(opt_frame, values=["info", "warning", "error", "critical"],
                          variable=self.severity_var, width=140,
                          ).grid(row=2, column=1, sticky="w", padx=4, pady=2)

        # Falhar em
        ctk.CTkLabel(opt_frame, text="Falhar em:").grid(
            row=3, column=0, sticky="w", padx=20, pady=2)
        ctk.CTkOptionMenu(opt_frame, values=["none", "warning", "error", "critical"],
                          variable=self.fail_on_var, width=140,
                          ).grid(row=3, column=1, sticky="w", padx=4, pady=2)

        # Timeout
        ctk.CTkLabel(opt_frame, text="Timeout (s):").grid(
            row=4, column=0, sticky="w", padx=20, pady=2)
        ctk.CTkEntry(opt_frame, textvariable=self.timeout_var, width=70,
                     ).grid(row=4, column=1, sticky="w", padx=4, pady=2)

        # Saída HTML
        ctk.CTkLabel(opt_frame, text="Saída HTML (opcional):").grid(
            row=5, column=0, sticky="w", padx=20, pady=2)
        out_entry = ctk.CTkEntry(opt_frame, textvariable=self.output_var,
                                 placeholder_text="relatorio.html")
        out_entry.grid(row=5, column=1, sticky="ew", padx=4, pady=2)
        ctk.CTkButton(opt_frame, text="...", width=32,
                      command=self._pick_output).grid(row=5, column=2, padx=4, pady=2)

        # Provedor IA
        self._ai_label = ctk.CTkLabel(opt_frame, text="Provedor IA:")
        self._ai_label.grid(row=6, column=0, sticky="w", padx=20, pady=2)
        self._ai_menu = ctk.CTkOptionMenu(
            opt_frame,
            values=["Auto (config.json)", "gemini", "claude", "openai", "ollama"],
            variable=self.ai_provider_var, width=180,
        )
        self._ai_menu.grid(row=6, column=1, sticky="w", padx=4, pady=(2, 10))

    def _build_mode_inputs(self):
        f = self._input_frame

        # Diff: branch base
        self._diff_label = ctk.CTkLabel(f, text="Branch base:")
        self._diff_entry = ctk.CTkEntry(f, textvariable=self.base_branch_var,
                                        placeholder_text="origin/main")

        # Staged: aviso informativo
        self._staged_info = ctk.CTkLabel(
            f, text="Analisa apenas arquivos no staging area (git add).",
            text_color=COLOR_DIM,
        )

        # Raiz do projeto (diff + staged): seletor de pasta do repo
        self._proj_label = ctk.CTkLabel(f, text="Raiz do projeto:")
        self._proj_entry = ctk.CTkEntry(
            f, textvariable=self.project_root_var, state="readonly",
            placeholder_text="(auto-detectado via git)",
        )
        self._proj_btn = ctk.CTkButton(f, text="Escolher...", width=90,
                                       command=self._pick_project_root)

        # Arquivo único
        self._file_label = ctk.CTkLabel(f, text="Arquivo .cs:")
        self._file_entry = ctk.CTkEntry(f, textvariable=self.file_var, state="readonly")
        self._file_btn = ctk.CTkButton(f, text="Escolher...", width=90,
                                       command=self._pick_file)

        # Scan
        self._scan_label = ctk.CTkLabel(f, text="Pasta:")
        self._scan_entry = ctk.CTkEntry(f, textvariable=self.scan_dir_var, state="readonly")
        self._scan_btn = ctk.CTkButton(f, text="Escolher pasta...", width=120,
                                       command=self._pick_scan_dir)

        self._on_mode_change()

    def _on_mode_change(self):
        mode = self.mode_var.get()
        f = self._input_frame
        f.grid_columnconfigure(1, weight=1)

        # Ocultar tudo
        for w in [self._diff_label, self._diff_entry,
                  self._staged_info,
                  self._proj_label, self._proj_entry, self._proj_btn,
                  self._file_label, self._file_entry, self._file_btn,
                  self._scan_label, self._scan_entry, self._scan_btn]:
            w.grid_remove()

        if mode == "diff":
            self._diff_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
            self._diff_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=(8, 2))
            # Raiz do projeto para diff
            self._proj_label.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))
            self._proj_entry.grid(row=1, column=1, sticky="ew", padx=4, pady=(2, 8))
            self._proj_btn.grid(row=1, column=2, padx=4, pady=(2, 8))

        elif mode == "staged":
            self._staged_info.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
            # Raiz do projeto para staged (essencial — define qual repo usar)
            self._proj_label.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))
            self._proj_entry.grid(row=1, column=1, sticky="ew", padx=4, pady=(2, 8))
            self._proj_btn.grid(row=1, column=2, padx=4, pady=(2, 8))

        elif mode == "file":
            self._file_label.grid(row=0, column=0, sticky="w", padx=10, pady=6)
            self._file_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
            self._file_btn.grid(row=0, column=2, padx=4, pady=6)

        elif mode == "scan":
            self._scan_label.grid(row=0, column=0, sticky="w", padx=10, pady=6)
            self._scan_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
            self._scan_btn.grid(row=0, column=2, padx=4, pady=6)

    def _on_rules_only_change(self):
        state = "disabled" if self.rules_only_var.get() else "normal"
        self._ai_label.configure(text_color=COLOR_DIM if self.rules_only_var.get() else TERMINAL_FG)
        self._ai_menu.configure(state=state)

    def _pick_project_root(self):
        path = filedialog.askdirectory(title="Selecionar raiz do projeto (pasta com .git)")
        if path:
            self.project_root_var.set(path)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo C#",
            filetypes=[("C# files", "*.cs"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def _pick_scan_dir(self):
        path = filedialog.askdirectory(title="Selecionar pasta para scan")
        if path:
            self.scan_dir_var.set(path)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Salvar relatório HTML",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)


# ── Task 12-14: Vb6Panel ──────────────────────────────────────────────────────
class Vb6Panel(ctk.CTkFrame):
    """Painel de configurações para análise VB6."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.mode_var = tk.StringVar(value="file")
        self.file_var = tk.StringVar()
        self.scan_dir_var = tk.StringVar()
        self.compare_base_var = tk.StringVar()
        self.compare_review_var = tk.StringVar()
        self.compare_file_base_var = tk.StringVar()
        self.compare_file_review_var = tk.StringVar()
        self.severity_var = tk.StringVar(value="info")
        self.format_var = tk.StringVar(value="text + html")
        self.diff_only_var = tk.BooleanVar(value=False)
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        row = 0

        # ── Seção: Modo de Análise
        mode_frame = ctk.CTkFrame(self)
        mode_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 4))
        mode_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mode_frame, text="Modo de Análise", font=("Segoe UI", 12, "bold")
                     ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        modes = [
            ("Arquivo único (.bas, .cls, .frm, .ctl)", "file"),
            ("Scan de diretório", "scan"),
            ("Comparação de pastas", "compare"),
            ("Comparação de arquivos", "file_compare"),
        ]
        for i, (label, value) in enumerate(modes):
            ctk.CTkRadioButton(
                mode_frame, text=label,
                variable=self.mode_var, value=value,
                command=self._on_mode_change,
            ).grid(row=i + 1, column=0, sticky="w", padx=20, pady=2)

        row += 1

        # ── Seção: Input específico por modo
        self._input_frame = ctk.CTkFrame(self)
        self._input_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        self._input_frame.grid_columnconfigure(1, weight=1)
        self._build_mode_inputs()
        row += 1

        # ── Seção: Opções
        opt_frame = ctk.CTkFrame(self)
        opt_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        opt_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(opt_frame, text="Opções", font=("Segoe UI", 12, "bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))

        ctk.CTkLabel(opt_frame, text="Severidade mínima:").grid(
            row=1, column=0, sticky="w", padx=20, pady=2)
        ctk.CTkOptionMenu(opt_frame, values=["info", "warning", "error", "critical"],
                          variable=self.severity_var, width=140,
                          ).grid(row=1, column=1, sticky="w", padx=4, pady=2)

        ctk.CTkLabel(opt_frame, text="Formato de saída:").grid(
            row=2, column=0, sticky="w", padx=20, pady=(2, 4))
        ctk.CTkOptionMenu(opt_frame, values=["text + html", "json", "html"],
                          variable=self.format_var, width=140,
                          ).grid(row=2, column=1, sticky="w", padx=4, pady=(2, 4))

        self._diff_only_chk = ctk.CTkCheckBox(
            opt_frame,
            text="Apenas linhas alteradas (diff-only)",
            variable=self.diff_only_var,
        )
        self._diff_only_chk.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(2, 10))
        self.mode_var.trace_add("write", lambda *_: self._update_diff_only_state())
        self._update_diff_only_state()

    def _update_diff_only_state(self):
        """Habilita diff-only nos modos de comparação."""
        compare_modes = ("compare", "file_compare")
        state = "normal" if self.mode_var.get() in compare_modes else "disabled"
        self._diff_only_chk.configure(state=state)
        if self.mode_var.get() not in compare_modes:
            self.diff_only_var.set(False)

    def _build_mode_inputs(self):
        f = self._input_frame

        # Arquivo único
        self._file_label = ctk.CTkLabel(f, text="Arquivo VB6:")
        self._file_entry = ctk.CTkEntry(f, textvariable=self.file_var, state="readonly")
        self._file_btn = ctk.CTkButton(f, text="Escolher...", width=90,
                                       command=self._pick_file)

        # Scan
        self._scan_label = ctk.CTkLabel(f, text="Pasta:")
        self._scan_entry = ctk.CTkEntry(f, textvariable=self.scan_dir_var, state="readonly")
        self._scan_btn = ctk.CTkButton(f, text="Escolher pasta...", width=120,
                                       command=self._pick_scan_dir)

        # Comparação
        self._cmp_frame = ctk.CTkFrame(f, fg_color="transparent")
        ctk.CTkLabel(self._cmp_frame, text="Pasta base (original):"
                     ).grid(row=0, column=0, sticky="w", padx=0, pady=2)
        ctk.CTkEntry(self._cmp_frame, textvariable=self.compare_base_var, state="readonly"
                     ).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        ctk.CTkButton(self._cmp_frame, text="Escolher...", width=90,
                      command=self._pick_base_dir
                      ).grid(row=0, column=2, padx=4, pady=2)
        ctk.CTkLabel(self._cmp_frame, text="Pasta revisão (modificada):"
                     ).grid(row=1, column=0, sticky="w", padx=0, pady=2)
        ctk.CTkEntry(self._cmp_frame, textvariable=self.compare_review_var, state="readonly"
                     ).grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        ctk.CTkButton(self._cmp_frame, text="Escolher...", width=90,
                      command=self._pick_review_dir
                      ).grid(row=1, column=2, padx=4, pady=2)
        self._cmp_frame.grid_columnconfigure(1, weight=1)

        # Comparação de arquivos individuais
        self._file_cmp_frame = ctk.CTkFrame(f, fg_color="transparent")
        ctk.CTkLabel(self._file_cmp_frame, text="Arquivo original (base):"
                     ).grid(row=0, column=0, sticky="w", padx=0, pady=2)
        ctk.CTkEntry(self._file_cmp_frame, textvariable=self.compare_file_base_var, state="readonly"
                     ).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        ctk.CTkButton(self._file_cmp_frame, text="Escolher...", width=90,
                      command=self._pick_base_file
                      ).grid(row=0, column=2, padx=4, pady=2)
        ctk.CTkLabel(self._file_cmp_frame, text="Arquivo modificado (revisão):"
                     ).grid(row=1, column=0, sticky="w", padx=0, pady=2)
        ctk.CTkEntry(self._file_cmp_frame, textvariable=self.compare_file_review_var, state="readonly"
                     ).grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        ctk.CTkButton(self._file_cmp_frame, text="Escolher...", width=90,
                      command=self._pick_review_file
                      ).grid(row=1, column=2, padx=4, pady=2)
        self._file_cmp_frame.grid_columnconfigure(1, weight=1)

        self._on_mode_change()

    def _on_mode_change(self):
        mode = self.mode_var.get()
        f = self._input_frame
        f.grid_columnconfigure(1, weight=1)

        for w in [self._file_label, self._file_entry, self._file_btn,
                  self._scan_label, self._scan_entry, self._scan_btn,
                  self._cmp_frame, self._file_cmp_frame]:
            w.grid_remove()

        if mode == "file":
            self._file_label.grid(row=0, column=0, sticky="w", padx=10, pady=6)
            self._file_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
            self._file_btn.grid(row=0, column=2, padx=4, pady=6)
        elif mode == "scan":
            self._scan_label.grid(row=0, column=0, sticky="w", padx=10, pady=6)
            self._scan_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
            self._scan_btn.grid(row=0, column=2, padx=4, pady=6)
        elif mode == "compare":
            self._cmp_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=8)
        elif mode == "file_compare":
            self._file_cmp_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=8)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo VB6",
            filetypes=[("VB6 files", "*.bas *.cls *.frm *.ctl"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def _pick_scan_dir(self):
        path = filedialog.askdirectory(title="Selecionar pasta para scan VB6")
        if path:
            self.scan_dir_var.set(path)

    def _pick_base_dir(self):
        path = filedialog.askdirectory(title="Selecionar pasta base (original)")
        if path:
            self.compare_base_var.set(path)

    def _pick_review_dir(self):
        path = filedialog.askdirectory(title="Selecionar pasta de revisão (modificada)")
        if path:
            self.compare_review_var.set(path)

    def _pick_base_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo VB6 original (base)",
            filetypes=[("VB6 files", "*.bas *.cls *.frm *.ctl"), ("All files", "*.*")],
        )
        if path:
            self.compare_file_base_var.set(path)

    def _pick_review_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo VB6 modificado (revisão)",
            filetypes=[("VB6 files", "*.bas *.cls *.frm *.ctl"), ("All files", "*.*")],
        )
        if path:
            self.compare_file_review_var.set(path)


# ── Task 20: SettingsDialog ───────────────────────────────────────────────────
class SettingsDialog(ctk.CTkToplevel):
    """Diálogo modal para configuração de provedores de IA e API keys."""

    _DEFAULT_CONFIG = {
        "ai": {
            "primary": "gemini",
            "fallback": "ollama",
            "gemini":  {"model": "gemini-1.5-pro",      "api_key_env": "GEMINI_API_KEY"},
            "claude":  {"model": "claude-sonnet-4-6",   "api_key_env": "ANTHROPIC_API_KEY", "max_tokens": 4096},
            "openai":  {"model": "gpt-4o",              "api_key_env": "OPENAI_API_KEY",    "max_tokens": 4096},
            "ollama":  {"base_url": "http://localhost:11434", "model": "qwen2.5-coder:32b", "timeout_seconds": 120},
        }
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configurações — Code Guardian")
        self.geometry("520x580")
        self.resizable(False, False)
        self.grab_set()
        self._config = self._load_config()
        self._vars: dict = {}
        self._build_ui()

    def _load_config(self) -> dict:
        try:
            if CONFIG_PATH.exists():
                return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return json.loads(json.dumps(self._DEFAULT_CONFIG))

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        row = 0
        ai = self._config.get("ai", {})

        def section(title, r):
            f = ctk.CTkFrame(self)
            f.grid(row=r, column=0, sticky="ew", padx=12, pady=(8, 2))
            f.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(f, text=title, font=("Segoe UI", 11, "bold")
                         ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 2))
            return f

        def row_entry(frame, label, var_key, default="", masked=False, row_n=1):
            ctk.CTkLabel(frame, text=label).grid(
                row=row_n, column=0, sticky="w", padx=14, pady=2)
            v = tk.StringVar(value=default)
            self._vars[var_key] = v
            kw = {"show": "*"} if masked else {}
            ctk.CTkEntry(frame, textvariable=v, **kw).grid(
                row=row_n, column=1, sticky="ew", padx=8, pady=2)

        def row_option(frame, label, var_key, values, default, row_n=1):
            ctk.CTkLabel(frame, text=label).grid(
                row=row_n, column=0, sticky="w", padx=14, pady=2)
            v = tk.StringVar(value=default)
            self._vars[var_key] = v
            ctk.CTkOptionMenu(frame, values=values, variable=v, width=160
                              ).grid(row=row_n, column=1, sticky="w", padx=8, pady=2)

        providers = ["gemini", "claude", "openai", "ollama"]
        fallback_vals = providers + ["none"]

        # Provedores
        f1 = section("Provedores de IA", row); row += 1
        row_option(f1, "Primário:", "primary", providers, ai.get("primary", "gemini"), 1)
        row_option(f1, "Fallback:", "fallback", fallback_vals, ai.get("fallback", "ollama"), 2)

        # Gemini
        g = ai.get("gemini", {})
        f2 = section("Gemini", row); row += 1
        row_entry(f2, "Modelo:", "gemini_model", g.get("model", "gemini-1.5-pro"), row_n=1)
        row_entry(f2, "GEMINI_API_KEY:", "gemini_key",
                  os.environ.get("GEMINI_API_KEY", ""), masked=True, row_n=2)

        # Claude
        c = ai.get("claude", {})
        f3 = section("Claude (Anthropic)", row); row += 1
        row_entry(f3, "Modelo:", "claude_model", c.get("model", "claude-sonnet-4-6"), row_n=1)
        row_entry(f3, "ANTHROPIC_API_KEY:", "claude_key",
                  os.environ.get("ANTHROPIC_API_KEY", ""), masked=True, row_n=2)

        # OpenAI
        o = ai.get("openai", {})
        f4 = section("OpenAI", row); row += 1
        row_entry(f4, "Modelo:", "openai_model", o.get("model", "gpt-4o"), row_n=1)
        row_entry(f4, "OPENAI_API_KEY:", "openai_key",
                  os.environ.get("OPENAI_API_KEY", ""), masked=True, row_n=2)

        # Ollama
        ol = ai.get("ollama", {})
        f5 = section("Ollama (local)", row); row += 1
        row_entry(f5, "URL base:", "ollama_url",
                  ol.get("base_url", "http://localhost:11434"), row_n=1)
        row_entry(f5, "Modelo:", "ollama_model",
                  ol.get("model", "qwen2.5-coder:32b"), row_n=2)

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="e", padx=12, pady=12)
        ctk.CTkButton(btn_frame, text="Salvar", command=self._save, width=90
                      ).grid(row=0, column=0, padx=4)
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy,
                      fg_color="gray40", width=90).grid(row=0, column=1, padx=4)

    def _save(self):
        v = self._vars
        cfg = {
            "ai": {
                "primary": v["primary"].get(),
                "fallback": v["fallback"].get(),
                "gemini": {
                    "model": v["gemini_model"].get(),
                    "api_key_env": "GEMINI_API_KEY",
                },
                "claude": {
                    "model": v["claude_model"].get(),
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "max_tokens": 4096,
                },
                "openai": {
                    "model": v["openai_model"].get(),
                    "api_key_env": "OPENAI_API_KEY",
                    "max_tokens": 4096,
                },
                "ollama": {
                    "base_url": v["ollama_url"].get(),
                    "model": v["ollama_model"].get(),
                    "timeout_seconds": 120,
                },
            }
        }
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

        # Aplicar API keys como variáveis de ambiente na sessão
        for env_var, key in [("GEMINI_API_KEY", "gemini_key"),
                              ("ANTHROPIC_API_KEY", "claude_key"),
                              ("OPENAI_API_KEY", "openai_key")]:
            val = v[key].get().strip()
            if val:
                os.environ[env_var] = val

        messagebox.showinfo("Configurações", "Configurações salvas com sucesso!", parent=self)
        self.destroy()


# ── Tasks 15-19, 21: CodeGuardianApp ─────────────────────────────────────────
class CodeGuardianApp(ctk.CTk):
    """Janela principal do Code Guardian UI."""

    def __init__(self):
        super().__init__()
        _ensure_config_dir()   # Garante config.json em AppData (exe) na 1ª execução
        self.title(f"Code Guardian  v{VERSION}")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self._set_window_icon()
        self.app_state = AppState()

        # Task 21: Detectar repo root
        self.app_state.repo_root = _detect_repo_root()

        self._setup_layout()
        self.after(50, self._poll_queue)

    def _set_window_icon(self):
        """Define o ícone da janela usando assets/icon.ico (CygnusForge)."""
        # Quando frozen (PyInstaller), o ícone está em sys._MEIPASS/assets/
        if getattr(sys, "frozen", False):
            ico = Path(sys._MEIPASS) / "assets" / "icon.ico"  # type: ignore[attr-defined]
        else:
            ico = SCRIPT_DIR / "assets" / "icon.ico"

        if ico.exists():
            try:
                self.iconbitmap(str(ico))
            except Exception:
                pass  # Silencioso — ícone é cosmético

    def _setup_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # ── Painel esquerdo: TabView
        left = ctk.CTkFrame(self, width=430)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Code Guardian",
                     font=("Segoe UI", 16, "bold")
                     ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.tab_view = ctk.CTkTabview(left)
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.tab_view.add("C#")
        self.tab_view.add("VB6")

        self.csharp_panel = CsharpPanel(self.tab_view.tab("C#"))
        self.csharp_panel.pack(fill="both", expand=True)

        self.vb6_panel = Vb6Panel(self.tab_view.tab("VB6"))
        self.vb6_panel.pack(fill="both", expand=True)

        # ── Painel direito: Terminal
        self.terminal = TerminalOutput(self)
        self.terminal.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)

        # ── Task 16: Barra de botões
        btn_bar = ctk.CTkFrame(self)
        btn_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 4))

        self.btn_run = ctk.CTkButton(
            btn_bar, text="Executar", width=110,
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self._on_run,
        )
        self.btn_run.grid(row=0, column=0, padx=8, pady=8)

        self.btn_report = ctk.CTkButton(
            btn_bar, text="Abrir Relatorio", width=130,
            state="disabled", command=self._on_open_report,
        )
        self.btn_report.grid(row=0, column=1, padx=4, pady=8)

        ctk.CTkButton(
            btn_bar, text="Limpar Terminal", width=130,
            fg_color="gray40", hover_color="gray30",
            command=self._on_clear,
        ).grid(row=0, column=2, padx=4, pady=8)

        self.btn_settings = ctk.CTkButton(
            btn_bar, text="Configuracoes", width=120,
            fg_color="gray40", hover_color="gray30",
            command=self._on_settings,
        )
        self.btn_settings.grid(row=0, column=3, padx=4, pady=8)

        ctk.CTkButton(
            btn_bar, text="?", width=36,
            fg_color="gray35", hover_color="gray25",
            command=lambda: webbrowser.open((Path(__file__).parent / "assets" / "help.html").as_uri()),
        ).grid(row=0, column=4, padx=(4, 8), pady=8)

        # ── Status bar
        status_bar = ctk.CTkFrame(self, height=28)
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))
        status_bar.grid_propagate(False)
        status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_bar,
            text=f"Repositorio: {self.app_state.repo_root}   |   Pronto",
            anchor="w", font=("Segoe UI", 10), text_color=COLOR_DIM,
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=8)

        # Mensagem de boas-vindas no terminal
        self.terminal.append_line("Code Guardian UI pronto.", "success")
        self.terminal.append_line(f"Repositorio: {self.app_state.repo_root}", "dim")
        if not CTK_AVAILABLE:
            self.terminal.append_line(
                "AVISO: customtkinter nao instalado. Execute: pip install customtkinter",
                "warning",
            )

    # ── Task 17: _on_run e _on_cancel
    def _on_run(self):
        if self.app_state.is_running:
            return

        active_tab = self.tab_view.get()
        try:
            python_exe = _get_python_executable()
        except FileNotFoundError as e:
            messagebox.showerror("Python não encontrado", str(e))
            return

        try:
            if active_tab == "C#":
                cmd = build_csharp_cmd(self.csharp_panel)
                # Usar raiz do projeto selecionada, ou auto-detectada
                proj = self.csharp_panel.project_root_var.get().strip()
                cwd = proj if proj else str(self.app_state.repo_root)
            else:
                cmd = build_vb6_cmd(self.vb6_panel)
                cwd = str(self.app_state.repo_root)
        except ValueError as e:
            messagebox.showerror("Erro de validacao", str(e))
            return

        self.terminal.append_line("─" * 60, "dim")
        self.terminal.append_line(f"Diretorio: {cwd}", "dim")
        self.terminal.append_line(f"Executando: {' '.join(cmd)}", "dim")
        self.terminal.append_line("─" * 60, "dim")

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8:replace"

        runner = SubprocessRunner(
            cmd=cmd,
            output_queue=self.app_state.output_queue,
            cwd=cwd,
            env=env,
        )
        self.app_state.current_runner = runner
        self.app_state.is_running = True
        self._set_running_ui(True)
        runner.start()

    def _on_cancel(self):
        if self.app_state.current_runner:
            self.app_state.current_runner.cancel()
            # Descarta mensagens acumuladas na fila para que o sinal _done_
            # seja processado imediatamente, sem esperar drenar milhares de linhas.
            try:
                while True:
                    self.app_state.output_queue.get_nowait()
            except queue.Empty:
                pass
            self.terminal.append_line("Cancelando analise...", "warning")
            self._update_status("Cancelando...")

    # ── Task 18: _poll_queue
    def _poll_queue(self):
        # Processa no máximo 20 mensagens por ciclo para não travar a UI.
        # Se a fila tiver mais mensagens (ex: scan com milhares de issues),
        # elas serão processadas nos próximos ciclos de 50ms.
        processed = 0
        try:
            while processed < 20:
                tag, text = self.app_state.output_queue.get_nowait()
                processed += 1
                if tag == "_done_":
                    self._on_run_complete(int(text))
                    break
                else:
                    self.terminal.append_line(text, tag)
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)

    # ── Task 19: _on_run_complete, _set_running_ui, _detect_last_report
    def _on_run_complete(self, returncode: int):
        self.app_state.is_running = False
        self.app_state.current_runner = None
        self.terminal.append_line("─" * 60, "dim")

        if returncode == -1:
            self.terminal.append_line("Analise cancelada.", "dim")
            self._update_status("Cancelado")
        elif returncode == 0:
            self.terminal.append_line("Analise concluida com sucesso.", "success")
            self._update_status("Concluido com sucesso")
        else:
            self.terminal.append_line(
                f"Analise concluida com avisos/erros (exit {returncode}).", "warning")
            self._update_status(f"Concluido com codigo {returncode}")

        self._detect_last_report()
        self._set_running_ui(False)

    def _set_running_ui(self, running: bool):
        if running:
            self.btn_run.configure(text="Cancelar", fg_color="#B71C1C",
                                   hover_color="#7F0000", command=self._on_cancel)
            self.btn_report.configure(state="disabled")
            self.btn_settings.configure(state="disabled")
        else:
            self.btn_run.configure(text="Executar", fg_color="#1565C0",
                                   hover_color="#0D47A1", command=self._on_run)
            has_report = self.app_state.last_report_path is not None
            self.btn_report.configure(state="normal" if has_report else "disabled")
            self.btn_settings.configure(state="normal")

    def _detect_last_report(self):
        guardian = _find_guardian_dir(self.app_state.repo_root)
        html_files = sorted(
            guardian.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if html_files:
            self.app_state.last_report_path = html_files[0]
            self.terminal.append_line(
                f"Relatorio: {self.app_state.last_report_path}", "dim")

    def _on_open_report(self):
        if self.app_state.last_report_path:
            webbrowser.open(self.app_state.last_report_path.as_uri())

    def _on_clear(self):
        self.terminal.clear()

    def _on_settings(self):
        SettingsDialog(self)

    def _update_status(self, msg: str):
        self.status_label.configure(
            text=f"Repositorio: {self.app_state.repo_root}   |   {msg}"
        )


# ── Task 22: Ponto de entrada ─────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Garantir dependências (mostra tela de loading se necessário)
    if not _ensure_dependencies():
        sys.exit(1)

    # 2. Re-importar customtkinter se acabou de ser instalado
    if not CTK_AVAILABLE:
        try:
            import importlib
            import customtkinter as ctk  # noqa: F811
            CTK_AVAILABLE = True
        except ImportError:
            pass  # Continua com shim tkinter puro

    # 3. Aplicar tema
    if CTK_AVAILABLE:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    # 4. Abrir aplicação principal
    app = CodeGuardianApp()
    app.mainloop()
