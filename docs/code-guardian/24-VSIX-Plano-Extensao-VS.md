# Code Guardian — Plano de Extensão Visual Studio (VSIX)

## Objetivo

Criar uma extensão `.vsix` para Visual Studio 2019/2022 que integre o Code Guardian diretamente no IDE, eliminando a necessidade de o desenvolvedor rodar manualmente `install_hooks.py` ou qualquer script Python.

## O que o dev ganha com a extensão

| Trigger | Comportamento automático |
|---|---|
| Abrir a solution | Detecta se git hooks estão instalados → InfoBar com "Install now" |
| Salvar qualquer `.cs` | Roda `runner.py` em background → resultados no editor |
| Issues no editor | Squiggly lines coloridos (vermelho = critical/error, verde = warning) |
| Error List | Todos os issues com file/line/descrição/rule_id clicáveis |
| Tool Window | Painel com Risk Score colorido + métricas por arquivo |
| Context menu | "Analyze with Code Guardian" na solution/projeto → scan completo |
| Tools > Options | Configurar Python path, ativar/desativar IA, severidade mínima |

---

## Localização do Projeto

```
C:\source\ideias\code_review\
├── code_guardian/      ← backend Python existente (não muda nada)
├── Prosoft.CadastroFuncionario/        ← projeto de exemplo
└── CodeGuardian.VS/                    ← NOVO: raiz da extensão
    ├── CodeGuardian.VS.sln
    └── src/
        └── CodeGuardian.VS/            ← projeto VSIX
```

---

## Estrutura de Arquivos do Projeto VSIX

```
CodeGuardian.VS/src/CodeGuardian.VS/
├── CodeGuardian.VS.csproj              ← SDK-style, target net472 (obrigatório VS SDK)
├── source.extension.vsixmanifest       ← identidade, suporte VS 2019/2022 [16.0,18.0)
│
├── Package/
│   ├── CodeGuardianPackage.cs          ← AsyncPackage — entry point, registra serviços
│   └── CodeGuardianPackage.vsct        ← XML de menus/comandos/toolbars
│
├── Analysis/
│   ├── GuardianAnalysisService.cs      ← orquestra Python → JSON → distribui resultados
│   ├── IGuardianAnalysisService.cs     ← interface para bridge MEF/AsyncPackage
│   ├── GuardianResult.cs               ← mirror do JSON do runner.py
│   ├── PythonProcessRunner.cs          ← subprocess async (UTF-8, sem janela)
│   └── AnalysisCache.cs                ← cache por arquivo, invalida no save
│
├── Editor/
│   ├── GuardianTaggerProvider.cs       ← MEF: IViewTaggerProvider, ContentType=CSharp
│   └── GuardianTagger.cs               ← ITagger<IErrorTag> — squiggles inline
│
├── ErrorList/
│   ├── GuardianErrorListService.cs     ← ITableDataSource — conecta ao Error List do VS
│   └── GuardianTableEntry.cs           ← ITableEntry: severity, file, line, message, ruleId
│
├── ToolWindow/
│   ├── GuardianToolWindow.cs           ← ToolWindowPane
│   ├── GuardianToolWindowControl.xaml  ← WPF: risk score bar, métricas, resumo de issues
│   └── GuardianToolWindowViewModel.cs  ← INotifyPropertyChanged, subscreve AnalysisCompleted
│
├── Commands/
│   ├── AnalyzeFileCommand.cs           ← "Analyze Current File" no menu Tools
│   ├── AnalyzeSolutionCommand.cs       ← "Analyze with Code Guardian" no context menu
│   └── InstallHooksCommand.cs          ← "Code Guardian: Install Git Hooks"
│
├── Settings/
│   ├── CodeGuardianOptionsPage.cs      ← DialogPage → Tools > Options > Code Guardian
│   └── CodeGuardianSettings.cs        ← POCO com todos os campos de configuração
│
└── GitHooks/
    └── HookInstallService.cs           ← detecta hooks, InfoBar VS, chama install_hooks.py
```

---

## NuGet Packages

```xml
<PackageReference Include="Microsoft.VisualStudio.SDK" Version="17.0.31902.203" />
<PackageReference Include="Microsoft.VSSDK.BuildTools" Version="17.0.3236" />
<PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
```

> Apenas ferramentas gratuitas/open-source. `Newtonsoft.Json` já está presente no VS por padrão.

---

## Detalhamento dos Componentes

### 1. `CodeGuardianPackage.cs` — Entry Point

Herda de `AsyncPackage`. Atributos obrigatórios na classe:

```csharp
[PackageRegistration(UseManagedResourcesOnly = true, AllowsBackgroundLoading = true)]
[ProvideAutoLoad(VSConstants.UICONTEXT.SolutionExists_string, PackageAutoLoadFlags.BackgroundLoad)]
[ProvideMenuResource("Menus.ctmenu", 1)]
[ProvideToolWindow(typeof(GuardianToolWindow))]
[ProvideOptionPage(typeof(CodeGuardianOptionsPage), "Code Guardian", "General", 0, 0, true)]
[ProvideService(typeof(SGuardianAnalysisService), IsAsyncQueryable = true)]
public sealed class CodeGuardianPackage : AsyncPackage { ... }
```

`InitializeAsync` deve:
1. Registrar `GuardianAnalysisService` como async service
2. Assinar `IVsRunningDocumentTable` (evento de save)
3. Chamar `HookInstallService.CheckAndPromptAsync()`
4. Inicializar `GuardianErrorListService`
5. Registrar todos os `OleMenuCommand` da pasta `Commands/`

---

### 2. `GuardianAnalysisService.cs` — Orquestrador Central

Singleton que recebe eventos de save, chama Python, parseia JSON e notifica os consumidores:

```csharp
public interface IGuardianAnalysisService
{
    event EventHandler<AnalysisCompletedEventArgs> AnalysisCompleted;
    Task AnalyzeFileAsync(string filePath, CancellationToken ct);
    Task AnalyzeSolutionAsync(string solutionDir, CancellationToken ct);
    GuardianResult? GetCachedResult(string filePath);
}
```

**Descoberta do `runner.py`:** sobe o diretório a partir da solution até encontrar `code_guardian/runner.py`. Fallback: campo na página de Settings.

**Working directory:** sempre a raiz do git (não a solution dir), pois `runner.py` usa `git rev-parse --show-toplevel` internamente.

**Comandos executados:**
- Por arquivo: `runner.py --file <path> --rules-only --format json`
- Scan completo: `runner.py --scan --dir <path> --rules-only --format json`
- Com IA habilitada: remove o `--rules-only`

---

### 3. `PythonProcessRunner.cs` — Subprocess Assíncrono

```csharp
public async Task<string> RunAsync(
    string pythonExe,       // da configuração, default "python"
    string scriptPath,      // caminho absoluto do runner.py
    string[] args,          // argumentos CLI
    string workingDir,      // raiz do git
    CancellationToken ct)
```

Configuração do `Process`:
- `RedirectStandardOutput = true`
- `RedirectStandardError = true`
- `UseShellExecute = false`
- `CreateNoWindow = true`
- `StandardOutputEncoding = Encoding.UTF8` ← obrigatório

Fallback de Python: tenta `python` → `py` (Python Launcher for Windows) antes de reportar erro.

---

### 4. `GuardianResult.cs` — Mirror do JSON

```csharp
public class GuardianResult
{
    [JsonProperty("risk_score")]    public int RiskScore { get; set; }
    [JsonProperty("risk_label")]    public string RiskLabel { get; set; }
    [JsonProperty("has_blockers")]  public bool HasBlockers { get; set; }
    [JsonProperty("summary")]       public SummaryResult Summary { get; set; }
    [JsonProperty("files")]         public List<FileResult> Files { get; set; }
}

public class IssueResult
{
    [JsonProperty("file")]      public string File { get; set; }
    [JsonProperty("line")]      public int Line { get; set; }
    [JsonProperty("severity")]  public string Severity { get; set; }  // critical|error|warning|info
    [JsonProperty("category")]  public string Category { get; set; }
    [JsonProperty("rule_id")]   public string RuleId { get; set; }
    [JsonProperty("message")]   public string Message { get; set; }
    [JsonProperty("source")]    public string Source { get; set; }
}

public class MetricsResult
{
    [JsonProperty("total_lines")]       public int TotalLines { get; set; }
    [JsonProperty("max_method_lines")]  public int MaxMethodLines { get; set; }
    [JsonProperty("max_nesting")]       public int MaxNesting { get; set; }
    [JsonProperty("constructor_deps")]  public int ConstructorDeps { get; set; }
}
```

---

### 5. Editor Squiggles — MEF `ITagger<IErrorTag>`

```csharp
[Export(typeof(IViewTaggerProvider))]
[ContentType("CSharp")]
[TagType(typeof(IErrorTag))]
public class GuardianTaggerProvider : IViewTaggerProvider
{
    [Import]
    internal SVsServiceProvider ServiceProvider { get; set; }

    public ITagger<T> CreateTagger<T>(ITextView view, ITextBuffer buffer)
    {
        var service = ServiceProvider.GetService(typeof(SGuardianAnalysisService))
                      as IGuardianAnalysisService;
        return buffer.Properties.GetOrCreateSingletonProperty(
            () => new GuardianTagger(buffer, service)) as ITagger<T>;
    }
}
```

**Mapeamento severity → squiggle:**

| Severity | `PredefinedErrorTypeNames` | Visual |
|---|---|---|
| `critical` | `SyntaxError` | Vermelho |
| `error` | `OtherError` | Vermelho |
| `warning` | `Warning` | Verde |
| `info` | `Suggestion` | Pontilhado |

`TagsChanged` deve ser disparado no UI thread via `JoinableTaskFactory.SwitchToMainThreadAsync()`.

---

### 6. Error List — `ITableDataSource`

API moderna do VS (2019/2022) — não usa o legado `IVsTaskList`:

```csharp
// Colunas expostas por cada GuardianTableEntry:
StandardTableKeyNames.ErrorSeverity  → __VSERRORCATEGORY.EC_ERROR / EC_WARNING / EC_MESSAGE
StandardTableKeyNames.Text           → issue.Message
StandardTableKeyNames.DocumentName   → caminho absoluto do arquivo
StandardTableKeyNames.Line           → issue.Line - 1  (0-indexed)
StandardTableKeyNames.Column         → 0
StandardTableKeyNames.ErrorCode      → issue.RuleId  (ex: "SQL_INJECTION_CONCAT")
StandardTableKeyNames.ErrorSource    → "Code Guardian"
StandardTableKeyNames.BuildTool      → "Code Guardian"
```

**Mapeamento severity → ErrorList:**

| Code Guardian | `__VSERRORCATEGORY` |
|---|---|
| `critical` | `EC_ERROR` |
| `error` | `EC_ERROR` |
| `warning` | `EC_WARNING` |
| `info` | `EC_MESSAGE` |

---

### 7. Tool Window — WPF Control

**Três seções:**

**Header — Risk Score:**
```
[ ████████████████████ ]  Score: 35 — 🔴 Alto Risco
```
- 0-10 → verde (`#2ECC71`)
- 11-30 → amarelo (`#F1C40F`)
- 31-60 → laranja (`#E67E22`)
- > 60 → vermelho (`#E74C3C`)

**Resumo de Issues:**
```
🔴 Critical   1
🟠 Error      2
🟡 Warning    3
🔵 Info       1
```

**Métricas (expansível por arquivo):**
```
Services/FuncionarioService.cs
  Total Lines        412   🟡
  Maior Método       45 L  🟠  (limite: 30)
  Nesting Máximo     5     🟡  (limite: 5)
  Dependências       7     🟠  (limite: 5)
```

Thresholds (mesmos do `metrics.py`):
- Método > 30 linhas → warning
- Nesting > 5 → warning
- Deps > 5 → warning
- Classe > 300 linhas → warning

---

### 8. `CodeGuardianOptionsPage.cs` — Tools > Options > Code Guardian

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| Python Executable | string | `python` | Caminho para python.exe ou "python" |
| Analyze on Save | bool | `true` | Analisar automaticamente ao salvar .cs |
| Rules Only | bool | `true` | `--rules-only` (sem IA, mais rápido) |
| Minimum Severity | string | `warning` | `info` / `warning` / `error` / `critical` |
| Analysis Timeout (s) | int | `30` | Timeout do subprocess Python |
| Runner Script Path | string | vazio | Override do caminho do runner.py |

---

### 9. `HookInstallService.cs` — Git Hooks Auto-Install

**Fluxo ao abrir a solution:**

1. Encontra raiz do git subindo diretórios a partir da solution
2. Verifica se `.git/hooks/pre-commit` contém o marker: `"Code Guardian Hook pre-commit"`
3. Se **não instalado** → exibe InfoBar do VS:

```
⚠️ Code Guardian: Git hooks não estão instalados.  [Install now]  [×]
```

4. Ao clicar "Install now" → executa:
   ```
   python code_guardian/install_hooks.py install
   ```
5. Sucesso → status bar: `"Code Guardian: Hooks instalados com sucesso"`

**Verificação de status:**
```csharp
private bool AreHooksInstalled(string gitDir)
{
    var hookPath = Path.Combine(gitDir, "hooks", "pre-commit");
    if (!File.Exists(hookPath)) return false;
    return File.ReadAllText(hookPath).Contains("Code Guardian Hook pre-commit");
}
```

---

### 10. Comandos do Menu

**`.vsct` — Entradas de menu:**

| Comando | Localização | Ação |
|---|---|---|
| `Code Guardian` | Menu Tools | Abre a Tool Window |
| `Analyze with Code Guardian` | Context menu Solution Explorer | `runner.py --scan` |
| `Analyze Current File` | Menu Tools | `runner.py --file <atual>` |
| `Code Guardian: Install Git Hooks` | Menu Tools | `install_hooks.py install` |

---

## Fases de Implementação

### Fase 1 — Foundation (base funcional)
- [ ] Criar `CodeGuardian.VS.csproj` net472
- [ ] Implementar `CodeGuardianPackage.cs` com `InitializeAsync` básico
- [ ] Implementar `PythonProcessRunner.cs`
- [ ] Implementar `GuardianResult.cs` com Newtonsoft.Json
- [ ] Implementar `GuardianAnalysisService.cs` (sem UI ainda)
- [ ] Implementar `AnalysisCache.cs`
- [ ] Implementar `CodeGuardianOptionsPage.cs`
- [ ] Assinar `IVsRunningDocumentTable` (save events)
- **Verificação:** ao salvar `.cs`, JSON é parseado e logado no Output Window do VS

### Fase 2 — Error List
- [ ] Implementar `GuardianTableEntry.cs`
- [ ] Implementar `GuardianErrorListService.cs`
- [ ] Conectar ao `AnalysisCompleted` event
- **Verificação:** issues aparecem no Error List com file/line clicáveis

### Fase 3 — Editor Squiggles
- [ ] Implementar `GuardianTaggerProvider.cs` (MEF export)
- [ ] Implementar `GuardianTagger.cs` com `ITagger<IErrorTag>`
- [ ] Bridge MEF → AsyncPackage via `SVsServiceProvider`
- **Verificação:** squiggles vermelhos/verdes aparecem nas linhas com issues

### Fase 4 — Tool Window
- [ ] Criar `GuardianToolWindow.cs`
- [ ] Criar `GuardianToolWindowControl.xaml` com WPF
- [ ] Implementar `GuardianToolWindowViewModel.cs`
- [ ] Definir comando no `.vsct`
- **Verificação:** Tool Window abre via Tools menu, exibe Risk Score e métricas

### Fase 5 — Comandos e Hooks
- [ ] Implementar `AnalyzeSolutionCommand.cs`
- [ ] Implementar `InstallHooksCommand.cs`
- [ ] Implementar `HookInstallService.cs` com InfoBar
- [ ] Registrar todos os comandos no `.vsct` e no package
- **Verificação:** InfoBar aparece se hooks não instalados, instala ao clicar

### Fase 6 — Polish
- [ ] Ícones (16x16 e 32x32)
- [ ] Status bar progress para scans longos
- [ ] Error handling: Python não encontrado → InfoBar com link para Settings
- [ ] Teste em VS 2019 (16.x)
- [ ] Teste em VS 2022 (17.x)

---

## Desafios Técnicos

### MEF / AsyncPackage Boundary
O `GuardianTagger` é um componente MEF e não pode importar diretamente o `GuardianAnalysisService` (que vive no `AsyncPackage`). A solução é:
1. Definir interface `IGuardianAnalysisService`
2. Definir tipo marker `SGuardianAnalysisService`
3. No MEF component: `[Import] SVsServiceProvider` → `GetService(typeof(SGuardianAnalysisService))`

### Thread Safety
- `TagsChanged` e `PropertyChanged` devem sempre ser disparados no UI thread
- Usar `JoinableTaskFactory.SwitchToMainThreadAsync()` ao atualizar UI
- Análise Python roda em background thread (`TaskScheduler.Default`)

### Working Directory
`runner.py` chama `git rev-parse --show-toplevel` internamente. Se o working directory não for dentro do repositório git, o script falha. Sempre definir `workingDir` como raiz do git, não a solution root.

### Encoding
`runner.py` força `sys.stdout` para UTF-8. O C# deve usar `StandardOutputEncoding = Encoding.UTF8` no `Process`.

### Python Path
No ambiente do VS, o `PATH` pode não incluir Python. Estratégia:
1. Tentar o valor configurado em Settings
2. Tentar `python`
3. Tentar `py` (Python Launcher for Windows)
4. Falhar com InfoBar: "Python não encontrado — configure em Tools > Options > Code Guardian"

---

## `source.extension.vsixmanifest`

```xml
<PackageManifest Version="2.0.0" ...>
  <Metadata>
    <Identity Id="CodeGuardian.VS" Version="1.0.0" Language="pt-BR" Publisher="Prosoft" />
    <DisplayName>Code Guardian</DisplayName>
    <Description>Code review automatizado de C# integrado ao Visual Studio.</Description>
  </Metadata>
  <Installation>
    <!-- [16.0, 18.0) cobre VS 2019 e VS 2022 -->
    <InstallationTarget Id="Microsoft.VisualStudio.Community" Version="[16.0,18.0)" />
    <InstallationTarget Id="Microsoft.VisualStudio.Professional" Version="[16.0,18.0)" />
    <InstallationTarget Id="Microsoft.VisualStudio.Enterprise" Version="[16.0,18.0)" />
  </Installation>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.VsPackage" Path="source.extension.pkgdef" />
    <Asset Type="Microsoft.VisualStudio.MefComponent" Path="CodeGuardian.VS.dll" />
  </Assets>
</PackageManifest>
```

---

## Checklist de Verificação Final

- [ ] Abrir VS → abrir solution → InfoBar aparece se hooks não instalados
- [ ] Salvar `FuncionarioService.cs` → issues aparecem no Error List em < 5s
- [ ] Squiggles aparecem nas linhas corretas do editor
- [ ] Clicar em item do Error List → navega para o arquivo/linha
- [ ] Tool Window exibe Risk Score com cor correta e métricas
- [ ] Click direito na solution → "Analyze with Code Guardian" → scan completo
- [ ] Tools > Options > Code Guardian → todos os campos editáveis e persistentes
- [ ] "Install Hooks" via comando → `.git/hooks/pre-commit` criado com marker
- [ ] Funciona em VS 2019 (v16) e VS 2022 (v17)
- [ ] Python não encontrado → InfoBar com mensagem clara
- [ ] runner.py não encontrado → InfoBar com link para Settings

---

## Referências

- [VS SDK AsyncPackage](https://learn.microsoft.com/en-us/visualstudio/extensibility/how-to-use-asyncpackage-to-load-vspackages-in-the-background)
- [ITableDataSource / Error List](https://learn.microsoft.com/en-us/visualstudio/extensibility/ux-guidelines/notifications-and-progress-for-visual-studio)
- [ITagger / Editor Squiggles](https://learn.microsoft.com/en-us/visualstudio/extensibility/walkthrough-using-a-shell-command-with-an-editor-extension)
- [InfoBar API](https://learn.microsoft.com/en-us/visualstudio/extensibility/ux-guidelines/notifications-and-progress-for-visual-studio#infobar)
- Backend Python: `code_guardian/runner.py`
