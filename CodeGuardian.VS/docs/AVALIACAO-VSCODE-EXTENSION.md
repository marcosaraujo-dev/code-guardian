# Code Guardian — Avaliação: Extensão VS Code

Documento de análise técnica para decisão sobre desenvolvimento da extensão VS Code.
Elaborado com base na leitura completa do código da extensão Visual Studio atual.

---

## Sumário

1. [Contexto e Motivação](#1-contexto-e-motivação)
2. [O que é Reutilizável](#2-o-que-é-reutilizável)
3. [Suporte a Versões do Visual Studio](#3-suporte-a-versões-do-visual-studio)
4. [Inventário de Componentes](#4-inventário-de-componentes)
5. [Comparação de APIs](#5-comparação-de-apis)
6. [Estimativa de Esforço](#6-estimativa-de-esforço)
7. [Fases de Desenvolvimento](#7-fases-de-desenvolvimento)
8. [Riscos e Pontos de Atenção](#8-riscos-e-pontos-de-atenção)
9. [Recomendação](#9-recomendação)

---

## 1. Contexto e Motivação

A extensão atual do Code Guardian roda exclusivamente no **Visual Studio 2022** (versão interna 17.x), construída em C#/WPF usando o VS SDK. A demanda é avaliar:

- Suporte a versões futuras do Visual Studio (2025/2026)
- Uma versão para **VS Code**, que tem base de usuários maior e é multiplataforma

A camada Python (`runner.py`, `rule_engine.py`, `metrics.py`, etc.) é **completamente independente** do IDE — todo o trabalho de portabilidade está na camada de apresentação e integração.

---

## 2. O que é Reutilizável

### Reutilização total (zero mudanças)

| Componente | Localização |
|---|---|
| `runner.py` | `code_guardian/runner.py` |
| `rule_engine.py` | `code_guardian/rule_engine.py` |
| `metrics.py` | `code_guardian/metrics.py` |
| `ai_client.py` | `code_guardian/ai_client.py` |
| `diff_parser.py` | `code_guardian/diff_parser.py` |
| `spelling_checker.py` | `code_guardian/spelling_checker.py` |
| Git hooks `.sh` gerados | Mesmos scripts Bash |
| Formato SARIF 2.1.0 | Mesmo schema |
| Relatório HTML | Mesmo HTML gerado pelo `runner.py` |

> **Conclusão:** toda a inteligência do produto (análise, regras, métricas, IA) já está nos scripts Python e não precisa ser portada.

---

## 3. Suporte a Versões do Visual Studio

### Situação anterior
O manifesto declarava `[17.0, 18.0)` — instalava apenas no VS 2022.

### Situação atual (já corrigida)
O manifesto foi atualizado para `[17.0,)` — instala em qualquer versão a partir do VS 2022, incluindo versões futuras (2025, 2026).

```xml
<!-- source.extension.vsixmanifest — após a correção -->
<InstallationTarget Id="Microsoft.VisualStudio.Community"    Version="[17.0,)" />
<InstallationTarget Id="Microsoft.VisualStudio.Professional" Version="[17.0,)" />
<InstallationTarget Id="Microsoft.VisualStudio.Enterprise"   Version="[17.0,)" />
```

### Risco residual
O `Microsoft.VisualStudio.SDK` no `.csproj` está na versão `17.0.31902.203`. Se uma versão futura do VS remover ou renomear alguma API usada pela extensão, haverá um ajuste pontual necessário. As APIs utilizadas (ToolWindow, DTE, OutputWindow, RunningDocTable) são estáveis e retrocompatíveis há muitas versões.

**Ação necessária se VS 2025/2026 quebrar algo:** bumpar `Microsoft.VisualStudio.SDK` para a versão correspondente no `.csproj` e ajustar pontualmente.

---

## 4. Inventário de Componentes

### 4.1 UI do Painel — `GuardianToolWindowControl.xaml`

**O que faz hoje (WPF/XAML):**
- Banner de aviso para dependências ausentes (Python, runner.py)
- Logo + 4 botões em grade 2×2: Arquivo, Solution, Incremental, IA toggle
- Seção Git Hooks com indicador de status (ponto colorido) e botão toggle
- Card de Risk Score (0–100) com barra de progresso colorida
- Resumo de issues por severidade com contadores (Critical / Error / Warning / Info)
- Filtro por severidade (dropdown) + busca por texto livre (tempo real)
- Lista de issues com navegação por clique, botão copiar e botão suprimir
- Seção expansível de métricas por arquivo
- Botões de exportação (HTML + SARIF)

**Equivalente no VS Code:**
- `vscode.window.createWebviewPanel()` — painel HTML/CSS no lugar do XAML
- A UI HTML pode reaproveitar o CSS do relatório HTML que o `runner.py` já gera
- `vscode.window.createStatusBarItem()` — Risk Score na barra inferior

**Complexidade:** Média | **Esforço estimado:** 12–16h

---

### 4.2 Lógica de Apresentação — `GuardianToolWindowViewModel.cs`

**O que faz hoje (C# MVVM):**
- ~30 propriedades observáveis com `INotifyPropertyChanged`
- Filtros combinados (severidade AND texto)
- Cálculo de cor do Risk Score por faixa (verde ≤10, amarelo ≤30, laranja ≤60, vermelho >60)
- Tendência histórica lendo `guardian-metrics.json` (↑ piorou / ↓ melhorou / = estável)
- `IssueViewModel` — representa issue individual com cor de severidade
- `FileMetricsViewModel` — calcula cor das métricas vs thresholds
- Geração do relatório HTML (chama o browser)
- Exportação SARIF (coleta contexto git: branch, commit, remote URL)
- Sincronização com `HookInstallService`

**Equivalente no VS Code:**
- Classe TypeScript de "store" com `EventEmitter` para notificações
- Sem framework pesado necessário — estado simples com Map e arrays
- JSON nativo para serialização/leitura do `guardian-metrics.json`

**Complexidade:** Alta | **Esforço estimado:** 16–20h

---

### 4.3 Integração com o Editor — `GuardianToolWindowControl.xaml.cs`

**O que faz hoje (DTE / EnvDTE):**
- Obtém arquivo ativo via `dte.ActiveDocument.FullName`
- Obtém diretório da solution via `dte.Solution.FullName`
- Navega para linha do issue via `dte.ItemOperations.OpenFile()` + `TextSelection.GotoLine()`
- Insere `// guardian: suppress RULE_ID` acima da linha via `EditPoint`
- Copia issue formatado para clipboard via `Clipboard.SetText()`
- Verifica dependências ao abrir o painel

**Equivalente no VS Code:**
```typescript
// Arquivo ativo
vscode.window.activeTextEditor?.document.uri.fsPath

// Diretório do workspace
vscode.workspace.workspaceFolders?.[0].uri.fsPath

// Navegar para linha
vscode.window.showTextDocument(uri, { selection: new vscode.Range(line, 0, line, 0) })

// Inserir comentário acima da linha
const edit = new vscode.WorkspaceEdit()
edit.insert(uri, new vscode.Position(line - 1, 0), `// guardian: suppress ${ruleId}\n`)
await vscode.workspace.applyEdit(edit)

// Clipboard
vscode.env.clipboard.writeText(texto)
```

**Complexidade:** Média | **Esforço estimado:** 8–12h

---

### 4.4 Orquestração da Análise — `GuardianAnalysisService.cs`

**O que faz hoje (C#):**
- 3 modos: arquivo único, solution completa, incremental (git diff)
- `SemaphoreSlim` — evita análises concorrentes
- Descobre `runner.py` subindo a árvore de diretórios ou em `%LOCALAPPDATA%\CodeGuardian\scripts`
- Descobre raiz do repositório git (busca `.git`)
- Timeout configurável com `CancellationTokenSource`
- Monta argumentos: `--file`, `--scan`, `--dir`, `--format json`, `--rules-only`
- Injeta env vars de IA: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Parseia JSON (com fallback: busca `{` no output caso haja logs antes do JSON)
- Cache de resultados por arquivo (`AnalysisCache`)
- Merge de resultados incrementais (soma contagens, pega maior Risk Score)
- Dispara eventos: `AnalysisCompleted`, `AnalysisFailed`, `ScanProgress`
- Loga erros no Output Window do VS

**Equivalente no VS Code:**
```typescript
class GuardianAnalysisService {
  private running = false
  private cache = new Map<string, GuardianResult>()

  async analyzeFile(filePath: string): Promise<void> { ... }
  async analyzeSolution(workspaceDir: string): Promise<void> { ... }
  async analyzeIncremental(workspaceDir: string): Promise<void> { ... }

  // Eventos
  onCompleted = new vscode.EventEmitter<AnalysisResult>()
  onFailed    = new vscode.EventEmitter<string>()
  onProgress  = new vscode.EventEmitter<ScanProgress>()
}
```

**Complexidade:** Alta | **Esforço estimado:** 14–18h

---

### 4.5 Executor do Python — `PythonProcessRunner.cs`

**O que faz hoje (C#):**
- Tenta candidatos em ordem: executável configurado → `python` → `py`
- `ProcessStartInfo` com `UseShellExecute=false`, sem janela, encoding UTF-8
- Captura stdout/stderr assíncrono linha a linha
- Cancela e mata processo se `CancellationToken` disparar
- Injeta variáveis de ambiente extras (API keys de IA)
- Exceções tipadas: `PythonNotFoundException`, `GuardianScriptException`

**Equivalente no VS Code (Node.js):**
```typescript
import { spawn } from 'child_process'

function runPython(
  pythonExe: string,
  scriptPath: string,
  args: string[],
  env: Record<string, string>,
  signal: AbortSignal
): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn(pythonExe, [scriptPath, ...args], {
      env: { ...process.env, ...env },
      signal,
    })
    let stdout = ''
    let stderr = ''
    proc.stdout.on('data', d => stdout += d)
    proc.stderr.on('data', d => stderr += d)
    proc.on('close', code => {
      if (code !== 0 && !stdout) reject(new Error(stderr))
      else resolve(stdout)
    })
  })
}
```

**Complexidade:** Média | **Esforço estimado:** 6–8h

---

### 4.6 Git Hooks — `HookInstallService.cs`

**O que faz hoje (C#):**
- Verifica se hooks já estão instalados (busca marcador interno no arquivo)
- Instala dois hooks no `.git/hooks/`:
  - `pre-commit` — roda `runner.py --staged --rules-only --fail-on error`; bloqueia commit se Critical
  - `prepare-commit-msg` — injeta trailer `Guardian-Review: ✅ Score: N` na mensagem
- Não sobrescreve hooks de terceiros (detecta conflito, exibe InfoBar)
- Copia scripts bundlados do VSIX → `%LOCALAPPDATA%\CodeGuardian\scripts`
- Converte paths Windows para Bash (`C:\foo` → `/c/foo`)

**Equivalente no VS Code:**
- Mesma lógica de geração de scripts `.sh`
- Substituir InfoBar por `vscode.window.showWarningMessage()` com botão "Como resolver"
- Scripts bundlados ficam na pasta da extensão (acessível via `context.extensionPath`)
- Sem necessidade de copiar para `%LOCALAPPDATA%` — caminhos resolvidos diretamente

**Complexidade:** Média-Alta | **Esforço estimado:** 10–12h

---

### 4.7 Exportação SARIF — `SarifReportGenerator.cs`

**O que faz hoje (C#):**
- Gera SARIF 2.1.0 completo com `tool.driver.rules[]` e `results[]`
- Mapeia severidades: critical/error → `"error"`, warning → `"warning"`, info → `"note"`
- URIs relativas quando o arquivo está dentro do repositório
- Salva em `.codeguardian/guardian-report.sarif`
- Acumula histórico em `.codeguardian/guardian-metrics.json` (máximo 100 entradas FIFO)
- Extrai contexto git: branch, commit (8 chars), remote URL

**Equivalente no VS Code:**
- Serialização JSON nativa (TypeScript)
- Mesma lógica de mapeamento — ~80 linhas de código
- `vscode.workspace.fs` para escrita de arquivos

**Complexidade:** Baixa | **Esforço estimado:** 4–6h

---

### 4.8 Ponto de Entrada — `CodeGuardianPackage.cs`

**O que faz hoje (C#):**
- `[ProvideAutoLoad]` — carrega em background quando a solution abre
- Registra `ICodeGuardianSettingsProvider` como serviço VS
- Registra `GuardianAnalysisService` como serviço async
- Assina `IVsRunningDocTableEvents` para detectar saves de documentos
- Inicializa `GuardianErrorListService` para integração com Error List
- Verifica e instala git hooks ao abrir
- Registra 5 comandos de menu: OpenToolWindow, AnalyzeFile, AnalyzeSolution, ExportSarif, InstallHooks
- `OnAfterSave()` — dispara análise automática se `AnalyzeOnSave == true`

**Equivalente no VS Code:**
```typescript
// extension.ts
export function activate(context: vscode.ExtensionContext) {
  const service = new GuardianAnalysisService(context)

  context.subscriptions.push(
    vscode.commands.registerCommand('codeguardian.analyzeFile', () => service.analyzeFile(...)),
    vscode.commands.registerCommand('codeguardian.analyzeSolution', () => service.analyzeSolution(...)),
    vscode.commands.registerCommand('codeguardian.analyzeIncremental', () => service.analyzeIncremental(...)),
    vscode.commands.registerCommand('codeguardian.installHooks', () => hookService.install(...)),
    vscode.commands.registerCommand('codeguardian.exportSarif', () => sarifService.export(...)),
    vscode.workspace.onDidSaveTextDocument(doc => {
      if (doc.languageId === 'csharp' && config.analyzeOnSave)
        service.analyzeFile(doc.uri.fsPath)
    })
  )

  // Verificar hooks ao abrir workspace
  hookService.checkAndPrompt()
}

export function deactivate() { /* cleanup */ }
```

**Complexidade:** Média | **Esforço estimado:** 8–10h

---

### 4.9 Configurações — `CodeGuardianOptionsPage.cs`

**O que faz hoje (VS Options Page):**

Interface gráfica automática gerada pelo VS em Tools → Options → Code Guardian com os campos:

| Categoria | Campo | Padrão |
|---|---|---|
| Python | Python Executable | `python` |
| Análise | Analisar ao Salvar | `true` |
| Análise | Apenas Regras (sem IA) | `true` |
| Análise | Severidade Mínima | `warning` |
| Análise | Timeout (segundos) | `30` |
| Avançado | Caminho do runner.py | — |
| IA | Provider Primário | `ollama` |
| IA | Provider Fallback | `none` |
| IA | Gemini API Key | — |
| IA | Claude API Key | — |
| IA | OpenAI API Key | — |
| IA | Ollama URL | `http://localhost:11434` |
| IA | Ollama Modelo | `qwen2.5-coder:32b` |

**Equivalente no VS Code (`package.json`):**
```json
"contributes": {
  "configuration": {
    "title": "Code Guardian",
    "properties": {
      "codeguardian.pythonExecutable":   { "type": "string",  "default": "python" },
      "codeguardian.analyzeOnSave":      { "type": "boolean", "default": true },
      "codeguardian.rulesOnly":          { "type": "boolean", "default": true },
      "codeguardian.minimumSeverity":    { "type": "string",  "enum": ["info","warning","error","critical"], "default": "warning" },
      "codeguardian.timeoutSeconds":     { "type": "number",  "default": 30 },
      "codeguardian.runnerScriptPath":   { "type": "string",  "default": "" },
      "codeguardian.ia.providerPrimary": { "type": "string",  "enum": ["gemini","claude","openai","ollama"], "default": "ollama" },
      "codeguardian.ia.providerFallback":{ "type": "string",  "default": "none" },
      "codeguardian.ia.geminiApiKey":    { "type": "string",  "default": "" },
      "codeguardian.ia.claudeApiKey":    { "type": "string",  "default": "" },
      "codeguardian.ia.openaiApiKey":    { "type": "string",  "default": "" },
      "codeguardian.ia.ollamaUrl":       { "type": "string",  "default": "http://localhost:11434" },
      "codeguardian.ia.ollamaModel":     { "type": "string",  "default": "qwen2.5-coder:32b" }
    }
  }
}
```

Diferença: no VS Code não há GUI gerada automaticamente — as configurações aparecem na UI de Settings do próprio VS Code (arquivo `settings.json`), que renderiza os campos automaticamente com base no schema JSON.

> **Atenção para API keys:** o VS Code não tem um campo `password` nativo nas configurações. Para armazenar chaves com segurança, usar `vscode.SecretStorage` em vez de `workspace.getConfiguration()`.

**Complexidade:** Baixa | **Esforço estimado:** 3–4h

---

## 5. Comparação de APIs

| Funcionalidade | Visual Studio (atual) | VS Code |
|---|---|---|
| Painel lateral | `ToolWindowPane` + XAML/WPF | `WebviewPanel` ou `TreeView` |
| Issues inline no editor | `IVsTaskList` / Error List | `DiagnosticCollection` |
| Arquivo ativo | `DTE.ActiveDocument` | `window.activeTextEditor` |
| Diretório do projeto | `DTE.Solution.FullName` | `workspace.workspaceFolders` |
| Navegar para linha | `TextSelection.GotoLine()` | `window.showTextDocument()` com Range |
| Editar arquivo | `EditPoint.Insert()` | `WorkspaceEdit.insert()` |
| Clipboard | `Clipboard.SetText()` | `env.clipboard.writeText()` |
| On-save | `IVsRunningDocTableEvents` | `workspace.onDidSaveTextDocument` |
| Configurações | `DialogPage` + registro | `contributes.configuration` no `package.json` |
| Secrets (API keys) | Registro do Windows (via VS) | `SecretStorage` API |
| Notificação (InfoBar) | `IVsInfoBarUIFactory` | `window.showWarningMessage()` |
| Output Window | `IVsOutputWindow` | `window.createOutputChannel()` |
| Progresso | `IVsStatusbar` | `window.withProgress()` |
| Processo filho | `System.Diagnostics.Process` | `child_process.spawn()` |
| Publicação | VS Marketplace | VS Code Marketplace |

---

## 6. Estimativa de Esforço

### Por componente

| Componente | Complexidade | Esforço mínimo | Esforço máximo |
|---|---|---|---|
| UI do painel (WebView HTML/CSS) | Média | 12h | 16h |
| Lógica de estado (TypeScript) | Alta | 16h | 20h |
| Integração com editor (Commands/Events) | Média | 8h | 12h |
| Serviço de análise (orquestração) | Alta | 14h | 18h |
| Executor Python (`child_process`) | Média | 6h | 8h |
| Git Hooks | Média-Alta | 10h | 12h |
| SARIF + histórico | Baixa | 4h | 6h |
| Ponto de entrada (`extension.ts`) | Média | 8h | 10h |
| Configurações (`package.json`) | Baixa | 3h | 4h |
| **Total** | | **81h** | **106h** |

### Por fase de desenvolvimento

| Fase | Escopo | Estimativa |
|---|---|---|
| **MVP** | Painel básico, análise arquivo/solution/incremental, toggle IA, settings | 3–4 semanas |
| **Paridade completa** | MVP + Git hooks, SARIF, histórico, diagnósticos inline, suppression via botão | 6–8 semanas |
| **Publicação no Marketplace** | Paridade + ícones, README, changelog, testes, CI/CD de publicação | 8–10 semanas |

> Estimativas baseadas em **1 desenvolvedor em tempo integral** familiarizado com TypeScript e a API do VS Code.

---

## 7. Fases de Desenvolvimento

### Fase 1 — MVP (3–4 semanas)

Objetivo: extensão funcional para uso interno.

- [ ] Setup do projeto TypeScript (`yo code` scaffolding)
- [ ] Descoberta do Python e do `runner.py`
- [ ] Executor de processo Python com timeout e env vars
- [ ] Serviço de análise (arquivo, solution, incremental)
- [ ] Painel WebView com Risk Score, lista de issues e filtros
- [ ] On-save automático configurável
- [ ] Configurações via `package.json` (todas as 13 opções)
- [ ] Armazenamento seguro de API keys via `SecretStorage`
- [ ] Output Channel para logs

### Fase 2 — Paridade (mais 3–4 semanas)

- [ ] Git hooks (instalar / remover / detectar conflito)
- [ ] Exportação SARIF + histórico `guardian-metrics.json`
- [ ] `DiagnosticCollection` — issues sublinhados diretamente no editor
- [ ] Botão suprimir issue (insere `// guardian: suppress`)
- [ ] Botão copiar issue
- [ ] Tendência histórica no painel
- [ ] Métricas por arquivo (expansível)
- [ ] Relatório HTML (abre no browser externo)

### Fase 3 — Publicação (mais 2 semanas)

- [ ] Ícone da extensão, badges, screenshots para Marketplace
- [ ] `README.md` do repositório da extensão
- [ ] `CHANGELOG.md`
- [ ] Testes automatizados (mínimo: processo Python, parser JSON, git hooks)
- [ ] Pipeline de publicação automática (`vsce publish` via GitHub Actions)
- [ ] Página no VS Code Marketplace

---

## 8. Riscos e Pontos de Atenção

### Segurança das API Keys
O VS Code não tem um campo `password` nativo nas configurações. Se as chaves forem salvas em `settings.json`, ficam em texto claro no disco. Solução: usar `context.secrets` (`SecretStorage`) que usa o keychain do sistema operacional. Isso muda levemente a UX — o usuário configura as chaves via comando (`>Code Guardian: Set API Key`) em vez de um campo no Settings UI.

### WebView vs DTE
A navegação no editor (abrir arquivo e ir para linha) é mais simples no VS Code do que no VS — `showTextDocument` aceita opções de seleção diretamente. Sem equivalente ao `EditPoint` — usar `WorkspaceEdit` que é mais moderno e seguro.

### Git Bash no Windows
A extensão VS atual gera scripts Bash e converte paths Windows (`C:\foo` → `/c/foo`). No VS Code, o mesmo comportamento é necessário para Windows. Alternativa: criar o hook como script Python (`.py`) em vez de `.sh`, eliminando a dependência do Git Bash.

### Multiplataforma
VS Code roda em Windows, Mac e Linux. O `PythonProcessRunner` atual só testa `python` e `py` (Python Launcher, Windows-only). A versão TypeScript precisa testar também `python3` para Mac/Linux.

### Tamanho da extensão
Os scripts Python bundlados (~400KB) aumentam o tamanho do `.vsix`. Alternativa: não bundar — exigir que o usuário tenha o `code_guardian/` na raiz do repositório (mesma abordagem atual, só sem bundling).

---

## 9. Recomendação

### Curto prazo (agora)
✅ **VS 2022 e versões futuras** — já resolvido com a atualização do manifesto para `[17.0,)`. Nenhuma ação adicional necessária até que uma versão futura do VS quebre alguma API.

### Médio prazo (próximos 2–3 meses)
**Iniciar pelo MVP do VS Code** com foco nas funcionalidades mais usadas:
1. Análise de arquivo, solution e incremental
2. Toggle IA e configurações (incluindo API keys via SecretStorage)
3. Painel WebView simples com Risk Score e lista de issues

O MVP reutiliza 100% dos scripts Python e valida a demanda antes de investir na paridade completa.

### Por que VS Code vale o esforço
- Base de usuários ~40× maior que o Visual Studio
- Multiplataforma — funciona em Mac e Linux, abre a ferramenta para times mistos
- API mais simples e moderna que o VS SDK
- Publicação no Marketplace amplifica o alcance do produto

---

*Documento elaborado em 2026-04-24. Baseado na análise do código do Code Guardian v1.0.4.*
*Para dúvidas técnicas, consulte o [Guia do Desenvolvedor](GUIA-DESENVOLVEDOR.md).*
