# Code Guardian UI — Tarefas de Implementação

Referência: `docs/code-guardian/21-GUI-Code-Guardian-UI.md`
Arquivo alvo: `code_guardian/code_guardian_ui.py`

---

## Fase 1 — Estrutura Base

### ✅ Task 1 — Bootstrap e guard de dependência
**Arquivo:** `code_guardian_ui.py`

- Tentar `import customtkinter as ctk`; se falhar, usar shim de compatibilidade com `tkinter`
- Importar todos os módulos necessários: `threading`, `queue`, `subprocess`, `sys`, `os`, `json`, `webbrowser`, `time`, `datetime`, `pathlib.Path`, `dataclasses`, `tkinter.filedialog`, `tkinter.messagebox`
- Definir constantes:
  ```python
  VERSION = "1.0.0"
  SCRIPT_DIR = Path(__file__).parent
  CONFIG_PATH = SCRIPT_DIR / "config.json"
  RUNNER_SCRIPT = SCRIPT_DIR / "runner.py"
  VB6_SCRIPT = SCRIPT_DIR / "vb6_rule_engine.py"
  ```

---

### ✅ Task 2 — AppState dataclass
**Dependência:** Task 1

```python
@dataclass
class AppState:
    is_running: bool = False
    last_report_path: Path | None = None
    current_runner: Any = None
    output_queue: queue.Queue = field(default_factory=queue.Queue)
    repo_root: Path = field(default_factory=Path.cwd)
```

---

### ✅ Task 3 — Constantes de cores e fontes
**Dependência:** Task 1

```python
TERMINAL_BG     = "#1E1E1E"
TERMINAL_FG     = "#D4D4D4"
COLOR_SUCCESS   = "#4EC9B0"
COLOR_WARNING   = "#CE9178"
COLOR_ERROR     = "#F44747"
COLOR_INFO      = "#9CDCFE"
COLOR_DIM       = "#858585"
MONOSPACE_FONT  = ("Consolas", 11)
```

---

## Fase 2 — Componentes Core

### ✅ Task 4 — TerminalOutput widget
**Dependência:** Tasks 1, 3

Classe `TerminalOutput(ctk.CTkFrame)`:
- `__init__`: cria `ctk.CTkTextbox` com `state="disabled"`, `font=MONOSPACE_FONT`, `fg_color=TERMINAL_BG`, `wrap="word"`
- Configura tags de cor no widget interno `_textbox`: `success`, `warning`, `error`, `info`, `dim`, `timestamp`
- Método `append_line(text, tag="info")`: habilita temporariamente, insere `[HH:MM:SS] text\n` com tags, re-desabilita, chama `see("end")`
- Método `clear()`: apaga todo o conteúdo

---

### ✅ Task 5 — SubprocessRunner (thread)
**Dependência:** Tasks 1, 2

Classe `SubprocessRunner(threading.Thread)`:
- Constructor: recebe `cmd: list[str]`, `output_queue: queue.Queue`, `cwd: str`, `env: dict`
- `run()`: lança `subprocess.Popen` com `stdout=PIPE`, `stderr=STDOUT`, `encoding="utf-8"`, `errors="replace"`. Lê linha por linha, classifica a tag via `_classify_line()`, enfileira `(tag, linha)`. Ao terminar, enfileira `("_done_", str(returncode))`
- `cancel()`: chama `proc.terminate()` → `proc.kill()` após 2s via `threading.Timer`
- `_classify_line(line) -> str`: retorna tag baseado em palavras-chave (`critical`, `error`, `warning`, `✅`, etc.)

---

## Fase 3 — Construtores de Comandos

### ✅ Task 6 — build_csharp_cmd()
**Dependência:** Tasks 1, 2

Função pura `build_csharp_cmd(panel) -> list[str]`:
- Inicia com `[sys.executable, str(RUNNER_SCRIPT)]`
- Adiciona flags conforme o modo selecionado (diff/staged/file/scan)
- Adiciona `--rules-only`, `--severity`, `--fail-on`, `--timeout`, `--output` quando aplicável
- Lança `ValueError` com mensagem em português se campo obrigatório estiver vazio

---

### ✅ Task 7 — build_vb6_cmd()
**Dependência:** Tasks 1, 2

Função pura `build_vb6_cmd(panel) -> list[str]`:
- Inicia com `[sys.executable, str(VB6_SCRIPT)]`
- Adiciona args conforme modo (file/scan/compare)
- Adiciona `--severity` e `--format` quando necessário
- Para saída HTML, gera nome automático: `.codeguardian/code-review-YYYY-MM-DD-HHMM - VB6.html`
- Lança `ValueError` com mensagem em português se campo obrigatório estiver vazio

---

### ✅ Task 8 — _find_guardian_dir() helper
**Dependência:** Task 1

- Executa `git rev-parse --show-toplevel` via `subprocess.run`
- Se bem-sucedido, retorna `Path(stdout.strip()) / ".codeguardian"`
- Fallback: `Path.cwd() / ".codeguardian"`
- Cria o diretório se não existir

---

## Fase 4 — Painel C#

### ✅ Task 9 — RadioGroup modo de análise (C#)
**Dependência:** Task 1

- 4 `ctk.CTkRadioButton` dentro de `ctk.CTkFrame` com label "Modo de Análise"
- `tk.StringVar(value="diff")`
- Callback `_on_mode_change()` que mostra/oculta widgets de input abaixo
- Criar todos os widgets de input upfront, usar `.grid_remove()` / `.grid()` para mostrar/ocultar

---

### ✅ Task 10 — Widgets de input por modo (C#)
**Dependência:** Task 9

Para cada modo, criar widgets (ocultos por padrão exceto diff):
- **Diff:** label "Branch base" + `ctk.CTkEntry(placeholder_text="origin/main")`
- **Staged:** `ctk.CTkLabel("Analisa apenas arquivos no staging area")`
- **Arquivo:** `ctk.CTkEntry` (readonly) + `ctk.CTkButton("Escolher...")` abrindo `filedialog.askopenfilename` para `.cs`
- **Scan:** `ctk.CTkEntry` (readonly) + `ctk.CTkButton("Escolher pasta...")` abrindo `filedialog.askdirectory`

---

### ✅ Task 11 — Seção de opções (C#)
**Dependência:** Task 9

- `ctk.CTkCheckBox("Apenas regras (sem IA)", ...)` — oculta/exibe linha de provedor IA quando toggled
- `ctk.CTkOptionMenu` para Severidade: `["info", "warning", "error", "critical"]`
- `ctk.CTkOptionMenu` para Falhar em: `["none", "warning", "error", "critical"]`
- `ctk.CTkEntry` para Timeout (width=70, default "60")
- `ctk.CTkEntry` para Saída + botão `...` para seletor de arquivo
- `ctk.CTkOptionMenu` para Provedor IA: `["Auto (config.json)", "gemini", "claude", "openai", "ollama"]`

---

## Fase 5 — Painel VB6

### ✅ Task 12 — RadioGroup modo de análise (VB6)
**Dependência:** Task 1

- 3 `ctk.CTkRadioButton` dentro de `ctk.CTkFrame` com label "Modo de Análise"
- `tk.StringVar(value="file")`
- Callback `_on_mode_change()` que mostra/oculta widgets

---

### ✅ Task 13 — Widgets de input por modo (VB6)
**Dependência:** Task 12

- **Arquivo:** seletor de arquivo para `.bas .cls .frm .ctl`
- **Scan:** seletor de pasta
- **Comparação:** `ctk.CTkFrame` com label "Comparação de Pastas" contendo:
  - Label + Entry + Botão para "Pasta base (original)"
  - Label + Entry + Botão para "Pasta revisão (modificada)"

---

### ✅ Task 14 — Opções (VB6)
**Dependência:** Task 12

- `ctk.CTkOptionMenu` para Severidade
- `ctk.CTkOptionMenu` para Formato: `["text + html", "json", "html"]`

---

## Fase 6 — Janela Principal

### ✅ Task 15 — CodeGuardianApp — estrutura e layout
**Dependência:** Tasks 2, 3, 4

```python
class CodeGuardianApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Code Guardian")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.state = AppState()
        self._setup_layout()
        self.after(50, self._poll_queue)
```

- Grid 2 colunas: painel esquerdo (fixo ~420px) + terminal (expande)
- Painel esquerdo: `ctk.CTkTabview` com abas "C#" e "VB6"
- Painel direito: `TerminalOutput`

---

### ✅ Task 16 — Barra de botões e status bar
**Dependência:** Task 15

- Frame na parte inferior (full width)
- `btn_run`, `btn_report` (disabled), `btn_clear`, `btn_settings`
- `ctk.CTkLabel` para status bar com texto inicial "Pronto"
- Mostrar o repo_root detectado na status bar ao iniciar

---

### ✅ Task 17 — _on_run() e _on_cancel()
**Dependência:** Tasks 5, 6, 7, 15, 16

- `_on_run()`: detecta aba ativa, chama `build_csharp_cmd` ou `build_vb6_cmd`, valida (mostra messagebox em erro), inicia `SubprocessRunner`, muda UI para estado "executando"
- `_on_cancel()`: chama `runner.cancel()`, atualiza terminal e status

---

### ✅ Task 18 — _poll_queue()
**Dependência:** Tasks 4, 5, 17

```python
def _poll_queue(self):
    try:
        while True:
            tag, text = self.state.output_queue.get_nowait()
            if tag == "_done_":
                self._on_run_complete(int(text))
            else:
                self.terminal.append_line(text, tag)
    except queue.Empty:
        pass
    self.after(50, self._poll_queue)
```

---

### ✅ Task 19 — _on_run_complete() e _set_running_ui()
**Dependência:** Tasks 16, 17, 18

- `_on_run_complete(returncode)`: finaliza estado, detecta último relatório, atualiza botões e status
- `_set_running_ui(running)`: alterna texto/comando do btn_run, habilita/desabilita outros botões
- `_detect_last_report()`: varre `.codeguardian/` por `.html` mais recente, salva em `state.last_report_path`
- `_on_open_report()`: `webbrowser.open(state.last_report_path.as_uri())`

---

## Fase 7 — Configurações

### ✅ Task 20 — SettingsDialog
**Dependência:** Tasks 1, 16

Classe `SettingsDialog(ctk.CTkToplevel)`:
- `grab_set()` para comportamento modal
- `_load_config()`: lê `config.json`; fallback para dict padrão se arquivo não existir
- `_build_ui()`: seções para Provedores, Gemini, Claude, OpenAI, Ollama
- Campos de API key com `show="*"` (mascarados)
- `_save()`: escreve `config.json`, aplica API keys como `os.environ[key]`, exibe confirmação

---

## Fase 8 — Finalização

### ✅ Task 21 — Detecção do repo root
**Dependência:** Tasks 2, 15

- Ao iniciar `CodeGuardianApp`, executar `git rev-parse --show-toplevel`
- Armazenar em `state.repo_root`
- Exibir na status bar: `"Repositório: <path>"`
- Se não for repo git, usar `Path.cwd()` com aviso visual

---

### ✅ Task 22 — Bloco __main__ e verificação de dependências
**Dependência:** Todas

```python
if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
        print("Execute: pip install customtkinter")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = CodeGuardianApp()
    app.mainloop()
```

- Verificar se `customtkinter` está instalado; oferecer instalação automática via messagebox se não estiver

---

## Ordem de Implementação Recomendada

```
1 → 2 → 3 → 4 → 5 → 8 → 6 → 7 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22
```

---

## Estimativa de Linhas

| Seção | Linhas estimadas |
|-------|-----------------|
| Imports e constantes | ~40 |
| AppState + helpers | ~30 |
| TerminalOutput | ~60 |
| SubprocessRunner | ~65 |
| build_csharp_cmd + build_vb6_cmd | ~70 |
| CsharpPanel | ~130 |
| Vb6Panel | ~120 |
| SettingsDialog | ~110 |
| CodeGuardianApp | ~170 |
| __main__ | ~15 |
| **Total estimado** | **~810 linhas** |
