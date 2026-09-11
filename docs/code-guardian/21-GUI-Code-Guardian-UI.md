# Code Guardian UI — Especificação da Interface Gráfica

## Visão Geral

Interface gráfica Python para execução dos scripts de code review do Code Guardian, com suporte a C# e VB6, terminal integrado e geração de relatórios HTML.

**Arquivo:** `code_guardian/code_guardian_ui.py`
**Tecnologia:** Python + customtkinter (fallback para tkinter puro)
**Versão:** 1.0.0

---

## Layout da Janela Principal

```
┌─────────────────────────────────────────────────────────────────┐
│  Code Guardian  v1.0.0                                          │
├────────────────────────┬────────────────────────────────────────┤
│  [ C# ]  [ VB6 ]       │                                        │
│                        │   TERMINAL OUTPUT                      │
│  ┌──────────────────┐  │   (dark background, monospace)         │
│  │ Modo de Análise  │  │                                        │
│  │ ◉ Diff/Branch   │  │  [14:32:01] Executando: runner.py...   │
│  │ ○ Staged        │  │  [14:32:02] Analisando (1/3): X.cs     │
│  │ ○ Arquivo único │  │  🟡 L45 [Magic Number] ...             │
│  │ ○ Scan pasta    │  │  ✅ Análise concluída com sucesso.      │
│  └──────────────────┘  │                                        │
│                        │                                        │
│  ┌──────────────────┐  │                                        │
│  │ Opções           │  │                                        │
│  │ Severidade: [▼]  │  │                                        │
│  │ □ Apenas regras  │  │                                        │
│  │ Timeout: [60]    │  │                                        │
│  └──────────────────┘  │                                        │
├────────────────────────┴────────────────────────────────────────┤
│  [Executar]  [Abrir Relatório]  [Limpar Terminal]  [Config ⚙️]  │
├─────────────────────────────────────────────────────────────────┤
│  Repositório: C:/Users/Marcos/Repos/code_review   Pronto        │
└─────────────────────────────────────────────────────────────────┘
```

**Dimensões:** 1100×720px, mínimo 900×600px
**Tema:** Dark mode (customtkinter)

---

## Aba C#

Invoca `runner.py` com os flags apropriados.

### Modos de Análise (RadioButton)

| Modo | Flag gerado | Campos adicionais |
|------|-------------|-------------------|
| **Diff (padrão)** | `--base origin/main` | Texto "Branch base" (default: `origin/main`) |
| **Staged** | `--staged` | Nenhum (mensagem informativa) |
| **Arquivo único** | `--file <caminho>` | Seletor de arquivo `.cs` |
| **Scan de diretório** | `--scan --dir <pasta>` | Seletor de pasta |

### Opções

| Controle | Flag gerado | Padrão |
|----------|-------------|--------|
| Checkbox "Apenas regras (sem IA)" | `--rules-only` | desmarcado |
| Dropdown Severidade mínima | `--severity <valor>` | `info` |
| Dropdown "Falhar em" | `--fail-on <valor>` | `none` |
| Campo Timeout (s) | `--timeout <n>` | `60` |
| Campo Saída (opcional) | `--output <arquivo.html>` | vazio |
| Dropdown Provedor IA | (edita config.json) | Auto |

> O dropdown de Provedor IA fica oculto quando "Apenas regras" está marcado.

---

## Aba VB6

Invoca `vb6_rule_engine.py` com os flags apropriados.

### Modos de Análise (RadioButton)

| Modo | Flag gerado | Campos adicionais |
|------|-------------|-------------------|
| **Arquivo único** | `<caminho>` | Seletor de arquivo `.bas/.cls/.frm/.ctl` |
| **Scan de diretório** | `--scan --dir <pasta>` | Seletor de pasta |
| **Comparação de pastas** | `--compare --base <pasta1> --review <pasta2>` | 2 seletores de pasta |

**Modo Comparação:**
```
┌─────────────────────────────────────┐
│ Comparação de Pastas                │
│ Pasta base (original):              │
│ [C:/projeto/v1/          ] [Escolher]│
│ Pasta revisão (modificada):         │
│ [C:/projeto/v2/          ] [Escolher]│
└─────────────────────────────────────┘
```

### Opções

| Controle | Flag gerado | Padrão |
|----------|-------------|--------|
| Dropdown Severidade mínima | `--severity <valor>` | `info` |
| Dropdown Formato de saída | `--format json/html` ou (padrão) | `text + html` |

> Para saídas com HTML, o nome do arquivo é gerado automaticamente: `.codeguardian/code-review-YYYY-MM-DD-HHMM - VB6.html`

---

## Terminal Output

- Fundo escuro `#1E1E1E`, fonte monospace (Consolas 11pt)
- Auto-scroll para o final a cada nova linha
- Prefixo de timestamp `[HH:MM:SS]` em cinza
- Cores por tipo:

| Tipo | Cor | Exemplos |
|------|-----|---------|
| `success` | Verde `#4EC9B0` | ✅ Análise concluída, Nenhum problema |
| `warning` | Laranja `#CE9178` | 🟡 warnings, saídas com avisos |
| `error` | Vermelho `#F44747` | 🔴 critical/error, 🟠 error |
| `info` | Azul `#9CDCFE` | Mensagens gerais |
| `dim` | Cinza `#858585` | Timestamps, separadores, comandos |

- Não limpa entre execuções — acumula histórico
- Botão "Limpar Terminal" para limpar manualmente

---

## Botões de Ação

| Botão | Estado inicial | Comportamento |
|-------|---------------|---------------|
| **Executar** | Habilitado | Inicia análise. Durante execução: vira "Cancelar" |
| **Abrir Relatório** | Desabilitado | Habilitado após gerar `.html`. Abre no browser padrão |
| **Limpar Terminal** | Habilitado | Limpa o conteúdo do terminal |
| **Configurações ⚙️** | Habilitado | Abre diálogo de configurações |

---

## Diálogo de Configurações

Modal que lê/escreve `code_guardian/config.json`.

### Seções

1. **Provedores de IA** — Dropdown "Primário" e "Fallback" (`gemini/claude/openai/ollama/none`)
2. **Gemini** — Modelo + API Key (campo mascarado, seta env var `GEMINI_API_KEY`)
3. **Claude (Anthropic)** — Modelo + API Key
4. **OpenAI** — Modelo + API Key
5. **Ollama** — URL base + Modelo

> Valores de API key são aplicados como variáveis de ambiente na sessão atual, não gravados no JSON.

---

## Arquitetura Interna

```
code_guardian_ui.py
├── Constantes e importações
├── AppState (dataclass)         — estado mutável (is_running, last_report_path, queue)
├── TerminalOutput               — widget ctk.CTkTextbox com cores e auto-scroll
├── SubprocessRunner             — thread que executa subprocess e alimenta a queue
├── build_csharp_cmd()           — constrói lista de args para runner.py
├── build_vb6_cmd()              — constrói lista de args para vb6_rule_engine.py
├── _find_guardian_dir()         — detecta pasta .codeguardian/ via git rev-parse
├── CsharpPanel                  — painel da aba C#
├── Vb6Panel                     — painel da aba VB6
├── SettingsDialog               — diálogo modal de configurações
├── CodeGuardianApp              — janela principal
└── __main__                     — ponto de entrada
```

### Modelo de threads

- UI thread nunca bloqueia
- `SubprocessRunner` roda em `threading.Thread`
- Output vai para `queue.Queue`
- `root.after(50, _poll_queue)` drena a queue a cada 50ms
- Cancelamento: `proc.terminate()` → `proc.kill()` após 2s

### Variáveis de ambiente para subprocess

```python
env["PYTHONUTF8"] = "1"
env["PYTHONIOENCODING"] = "utf-8:replace"
```
Necessário para evitar bug de Unicode no Windows (documentado em `runner.py`).

---

## Pré-requisitos

```bash
pip install customtkinter
```

Se não instalado, a UI cai automaticamente para tkinter puro com uma mensagem de aviso.

---

## Como executar

```bash
python code_guardian/code_guardian_ui.py
```

---

## Tarefas de Implementação

Ver lista de tarefas em: `docs/code-guardian/22-Tasks-GUI-Implementation.md`
