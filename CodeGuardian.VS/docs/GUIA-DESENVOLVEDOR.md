# Code Guardian — Guia do Desenvolvedor

Referência completa para desenvolvedores que utilizam o Code Guardian no dia a dia.
Este documento cobre todas as funcionalidades, configurações, integrações e fluxos de uso.

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Instalação e Configuração](#instalação-e-configuração)
4. [Funcionalidades](#funcionalidades)
   - [Análise de Arquivo](#análise-de-arquivo)
   - [Análise de Solution](#análise-de-solution)
   - [Análise Incremental](#análise-incremental)
   - [AI Toggle](#ai-toggle)
   - [Filtros de Issues](#filtros-de-issues)
   - [Risk Score e Tendência](#risk-score-e-tendência)
   - [Navegação por Clique](#navegação-por-clique)
   - [Copiar Issue](#copiar-issue)
   - [Suprimir Issue](#suprimir-issue)
   - [Relatório HTML](#relatório-html)
   - [Exportação SARIF](#exportação-sarif)
   - [Git Hooks](#git-hooks)
   - [Métricas de Código](#métricas-de-código)
5. [Regras de Análise](#regras-de-análise)
6. [Scripts Python](#scripts-python)
7. [Monitoramento e Histórico](#monitoramento-e-histórico)
8. [Integração CI/CD](#integração-cicd)
9. [Configurações Avançadas](#configurações-avançadas)
10. [Supressão de Issues](#supressão-de-issues)
11. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O Code Guardian é uma extensão para Visual Studio 2019/2022 que integra análise estática de código C# diretamente no IDE. A análise é executada localmente via scripts Python, sem dependências de serviços externos. O motor de IA usa a cadeia de fallback `Gemini → Claude → OpenAI → Ollama`.

**Componentes principais:**

| Componente | Responsabilidade |
|------------|-----------------|
| Extensão VSIX (.NET 4.7.2) | Interface, integração VS, orquestração |
| `runner.py` | Orquestrador Python — chama rule engine, métricas e IA |
| `rule_engine.py` | 20+ regras regex estáticas |
| `metrics.py` | Tamanho de métodos, nesting, acoplamento |
| `ai_client.py` | Análise de IA com fallback automático entre providers |
| `diff_parser.py` | Extrai arquivos alterados do git diff |

---

## Arquitetura

```
Visual Studio (VSIX)
│
├── Commands/                    # Comandos do menu Tools / context menu
│   ├── AnalyzeFileCommand       # Analisar arquivo ativo
│   ├── AnalyzeSolutionCommand   # Analisar solution completa
│   ├── InstallHooksCommand      # Instalar Git Hooks
│   └── ExportSarifCommand       # Exportar SARIF
│
├── Analysis/
│   ├── GuardianAnalysisService  # Serviço singleton de análise
│   ├── PythonProcessRunner      # Executa runner.py como processo filho
│   ├── SarifReportGenerator     # Gera SARIF 2.1.0 e guardian-metrics.json
│   └── AnalysisCache            # Cache de resultados por arquivo
│
├── ToolWindow/
│   ├── GuardianToolWindowViewModel  # MVVM — toda lógica de apresentação
│   ├── GuardianToolWindowControl    # Code-behind (handlers VS/DTE)
│   └── GuardianToolWindow           # ToolWindowPane (host)
│
├── GitHooks/
│   └── HookInstallService       # Instala/remove hooks pre-commit e prepare-commit-msg
│
└── Settings/
    └── CodeGuardianSettings     # Configurações persistidas (Tools → Options)
```

---

## Instalação e Configuração

### 1. Instalar a extensão

Instale o arquivo `.vsix` via **Extensions → Manage Extensions** ou clicando duas vezes no arquivo.

### 2. Adicionar os scripts Python ao repositório

Clone ou copie a pasta `code_guardian/` para a raiz do repositório:

```
seu-repositorio/
├── code_guardian/
│   ├── runner.py
│   ├── rule_engine.py
│   ├── metrics.py
│   ├── diff_parser.py
│   ├── ai_client.py
│   ├── spelling_checker.py
│   └── config.json
├── src/
└── .sln
```

### 3. Configurar Python

Acesse **Tools → Options → Code Guardian**:

**Categoria Python**

| Campo | Descrição | Padrão |
|---|---|---|
| Python Executable | Caminho para `python.exe` ou simplesmente `python` / `py` | `python` |

**Categoria Análise**

| Campo | Descrição | Padrão |
|---|---|---|
| Analisar ao Salvar | Executa análise automaticamente ao salvar `.cs` | `true` |
| Apenas Regras (sem IA) | `true` = somente rule engine + métricas, sem chamar IA | `true` |
| Severidade Mínima | Oculta issues abaixo desta severidade: `info`, `warning`, `error`, `critical` | `warning` |
| Timeout (segundos) | Tempo máximo de espera por análise | `30` |

**Categoria Avançado**

| Campo | Descrição | Padrão |
|---|---|---|
| Caminho do runner.py | Deixar vazio para auto-detect; preencher apenas se a estrutura for não-padrão | — |

**Categoria IA** (ver passo 4 para detalhes)

| Campo | Descrição | Padrão |
|---|---|---|
| Provider Primário | `gemini`, `claude`, `openai` ou `ollama` | `ollama` |
| Provider Fallback | Provider de backup quando o primário falha | `none` |
| Gemini / Claude / OpenAI API Key | Chaves de API — armazenadas no registro do VS, injetadas como env vars na análise | — |
| Ollama URL / Modelo | Endereço e modelo do Ollama local | `http://localhost:11434` / `qwen2.5-coder:32b` |

O auto-detect sobe a árvore de diretórios a partir do arquivo atual procurando `code_guardian/runner.py`.

### 4. Configurar IA (opcional)

A forma recomendada é via **Tools → Options → Code Guardian → IA**:

| Campo | Descrição | Padrão |
|---|---|---|
| **Provider Primário** | Provider principal: `gemini`, `claude`, `openai`, `ollama` | `ollama` |
| **Provider Fallback** | Provider usado se o primário falhar: mesmos valores + `none` | `none` |
| **Gemini API Key** | Chave do Google Gemini (aistudio.google.com) | — |
| **Claude API Key** | Chave da Anthropic (console.anthropic.com) | — |
| **OpenAI API Key** | Chave da OpenAI (platform.openai.com) | — |
| **Ollama URL** | URL do servidor Ollama local | `http://localhost:11434` |
| **Ollama Modelo** | Modelo Ollama a usar | `qwen2.5-coder:32b` |

As chaves são armazenadas nas configurações do Visual Studio (registro do usuário) e injetadas automaticamente como variáveis de ambiente (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) ao rodar qualquer análise — sem precisar editar arquivos.

**Cadeia de fallback:** Provider Primário → Provider Fallback → análise sem IA (apenas rules + métricas).

#### Alternativa: config.json

Para configurações avançadas de modelo ou uso sem o Visual Studio (CI/CD, linha de comando), edite `code_guardian/config.json`:

```json
{
  "ai": {
    "primary": "gemini",
    "fallback": "ollama",
    "gemini":  { "model": "gemini-1.5-pro",        "api_key_env": "GEMINI_API_KEY" },
    "claude":  { "model": "claude-sonnet-4-6",      "api_key_env": "ANTHROPIC_API_KEY", "max_tokens": 4096 },
    "openai":  { "model": "gpt-4o",                 "api_key_env": "OPENAI_API_KEY",    "max_tokens": 4096 },
    "ollama":  { "base_url": "http://localhost:11434", "model": "qwen2.5-coder:32b",    "timeout_seconds": 120 }
  }
}
```

> Quando as configurações do Visual Studio e o `config.json` coexistem, as **variáveis de ambiente injetadas pelo VS** têm precedência sobre as chaves lidas pelo `config.json`, pois o processo Python herda o ambiente configurado pelo VS ao ser iniciado.

---

## Funcionalidades

### Análise de Arquivo

**Como usar:** **Tools → Analyze Current File (Code Guardian)** ou botão **Analisar Arquivo** no Tool Window.

Analisa o arquivo `.cs` ativo no editor. O cache é invalidado antes de cada nova análise para garantir resultados frescos.

**Saída:** Risk Score, lista de issues, métricas — exibidos no Tool Window e no Error List.

---

### Análise de Solution

**Como usar:** Botão **Analisar Solution** no Tool Window ou menu de contexto do Solution Explorer → **Analyze with Code Guardian**.

Varre todos os arquivos `.cs` da pasta da solution, ignorando `obj/`, `bin/` e arquivos `*.Designer.cs`. Uma progress bar exibe o arquivo sendo processado e o total.

---

### Análise Incremental

**Como usar:** Botão **Incremental** no Tool Window.

Analisa apenas os arquivos `.cs` modificados desde o último commit, obtidos via:

```bash
git diff HEAD --name-only
```

Filtros aplicados: apenas `.cs`, sem `obj/`, sem `bin/`, sem `*.Designer.cs`.

**Ideal para:** Desenvolvimento ativo — feedback rápido sobre o que foi alterado na sessão atual sem re-analisar arquivos não modificados.

Se não houver arquivos modificados, exibe "Nenhum arquivo modificado" sem executar análise.

> O modo **IA: ON / IA: OFF** é respeitado na análise incremental — com IA ativa, cada arquivo modificado passa também pela análise de IA.

---

### AI Toggle

**Como usar:** Botão **IA: OFF / IA: ON** no Tool Window.

Alterna o modo de análise para a sessão atual:
- **IA: ON** (verde) — `runner.py` executa rule engine + métricas + análise de IA
- **IA: OFF** (cinza) — `runner.py` executa apenas rule engine + métricas (`--rules-only`)

O estado do toggle é temporário (dura enquanto a sessão do VS estiver aberta). Para configurar permanentemente, use **Tools → Options → Code Guardian**:

| Configuração | Efeito |
|---|---|
| **Análise → Apenas Regras (sem IA) = True** | IA desligada por padrão em todas as sessões |
| **IA → Provider Primário** | Define qual provider de IA usar (gemini, claude, openai, ollama) |
| **IA → API Keys** | Chaves injetadas automaticamente como variáveis de ambiente ao rodar a análise |

> Para a IA funcionar, é necessário ter pelo menos um provider configurado com chave válida em **Tools → Options → Code Guardian → IA**, ou Ollama rodando localmente. Veja a seção [Configurar IA](#4-configurar-ia-opcional) para detalhes.

---

### Filtros de Issues

**Como usar:** Linha de filtros no topo da lista de issues no Tool Window.

| Controle | Função |
|----------|--------|
| ComboBox de severidade | Filtra por Todos / CRITICAL / ERROR / WARNING / INFO |
| Campo de texto | Filtra por texto livre — busca em RuleId, arquivo e mensagem |

Os filtros são aplicados em tempo real e combinados (AND). O campo de texto é case-insensitive.

---

### Risk Score e Tendência

**Risk Score:** Número de 0 a 100 calculado pelo `runner.py` baseado em contagem e severidade dos issues encontrados.

| Score | Rótulo | Cor |
|-------|--------|-----|
| 0–10 | Low Risk | Verde |
| 11–30 | Moderate | Amarelo |
| 31–60 | High Risk | Laranja |
| 61–100 | Critical | Vermelho |

**Tendência:** Compara o score atual com a última análise armazenada em `guardian-metrics.json`:

| Indicador | Significado |
|-----------|-------------|
| `↑ +N pts (piorou)` | Score aumentou em relação à análise anterior |
| `↓ -N pts (melhorou)` | Score diminuiu |
| `= estável` | Sem variação |

A tendência é exibida abaixo do Risk Score no Tool Window.

**Caption da aba:** Quando há issues Critical ou Error, o título da aba muda para `Code Guardian (N)` onde N é a soma de críticos + erros. Útil para monitorar mesmo com a janela minimizada.

---

### Navegação por Clique

**Como usar:** Clique em qualquer issue na lista do Tool Window.

Abre o arquivo no editor e posiciona o cursor na linha exata do issue usando `DTE.ItemOperations.OpenFile` + `TextSelection.GotoLine`. Após a navegação, o item é deselecionado para permitir clicar no mesmo issue novamente.

---

### Copiar Issue

**Como usar:** Botão **⎘** ao lado de cada issue na lista.

Copia o texto formatado para a área de transferência:

```
[CRITICAL] GRD001 — MeuServico.cs:42 — Possível SQL Injection detectado
```

Útil para colar em tickets, PRs ou documentação de revisão.

---

### Suprimir Issue

**Como usar:** Botão **✕** ao lado de cada issue na lista.

Abre o arquivo, navega para a linha do issue e insere automaticamente o comentário de supressão **acima** da linha:

```csharp
// guardian: suppress GRD001
public void MetodoProblematico()
```

O `rule_engine.py` ignora linhas precedidas por esse comentário em análises futuras. Use apenas quando o issue for um falso positivo documentado.

---

### Relatório HTML

**Como usar:** Botão **Abrir Relatório HTML** no Tool Window.

Abre um arquivo HTML auto-contido no browser padrão com:
- Card de resumo (Risk Score, contagens por severidade)
- Tabela de métricas por arquivo com células coloridas por threshold
- Tabela completa de issues com badges de severidade, arquivo e linha

O arquivo é gerado em memória e salvo temporariamente ao abrir.

---

### Exportação SARIF

**Como usar:** Botão **Exportar SARIF** no Tool Window ou **Tools → Export SARIF (Code Guardian)**.

Gera um arquivo **SARIF 2.1.0** em `.codeguardian/guardian-report.sarif` na raiz do repositório.

**Conteúdo do SARIF:**
- Todas as rules com descrição e nível de severidade
- Todos os issues com URI relativo do arquivo, linha, mensagem e nível
- Metadados da execução: branch git, commit hash (8 chars), URL remota, timestamp, Risk Score
- `run.properties` com todos os campos de monitoramento

**Exemplo de estrutura SARIF:**
```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "Code Guardian",
        "version": "1.0.3",
        "rules": [ ... ]
      }
    },
    "results": [ ... ],
    "properties": {
      "riskScore": 45,
      "riskLabel": "High Risk",
      "gitBranch": "feature/minha-feature",
      "gitCommit": "a1b2c3d4",
      "runId": "abc12345",
      "timestamp": "2025-04-22T10:30:00Z"
    }
  }]
}
```

---

### Git Hooks

**Como usar:** Menu **Tools → Code Guardian: Install Git Hooks** ou aceitar o InfoBar automático ao abrir uma solution sem hooks.

Instala dois hooks no `.git/hooks/` do repositório:

| Hook | Comportamento |
|------|---------------|
| `pre-commit` | Executa `runner.py --staged --rules-only`. Bloqueia o commit se houver issues CRITICAL. |
| `prepare-commit-msg` | Adiciona resumo da análise (Risk Score, contagem) na mensagem do commit. |

**Conflito com hooks de terceiros:** Se já existir um hook que não foi instalado pelo Code Guardian (sem o marcador interno), a instalação **não sobrescreve** o arquivo. Uma caixa de diálogo explica o conflito e o caminho do arquivo para integração manual.

**Remover:** Clique em **Remover Hooks** no Tool Window (disponível quando hooks estão instalados).

---

### Métricas de Código

Para cada arquivo analisado, o `metrics.py` calcula:

| Métrica | Descrição | Threshold padrão |
|---------|-----------|-----------------|
| **Total de linhas** | Linhas brutas do arquivo (incluindo comentários) | — |
| **Maior método** | Linhas de **código** do maior método (exclui `///`, `//`, `*`, `/*` e linhas vazias) | Warning: >30 |
| **Nesting máximo** | Maior profundidade de blocos aninhados | Warning: >5 |
| **Dependências** | Campos `private readonly` injetados via construtor | Warning: >5 |

> **Contagem de linhas:** o tamanho dos métodos e o threshold de "Arquivo Grande" são calculados com base em **linhas de código** — doc comments XML (`///`), comentários de linha (`//`), comentários de bloco (`/* */`) e linhas em branco são excluídos da contagem. O "Total de linhas" exibido no UI mostra o valor bruto para referência.

As métricas aparecem na seção expandível de métricas do Tool Window e no relatório HTML.

---

## Regras de Análise

O `rule_engine.py` contém 20+ regras divididas por categoria:

### Segurança

| Rule ID | Nome | Severidade |
|---------|------|-----------|
| `GRD-SEC-001` | SQL Injection | Critical |
| `GRD-SEC-002` | Hardcoded Password | Critical |
| `GRD-SEC-003` | Hardcoded Secret/Token | Critical |
| `GRD-SEC-004` | Path Traversal | Error |
| `GRD-SEC-005` | Dangerous Deserialization | Error |
| `GRD-SEC-006` | Weak Cryptography (MD5/SHA1) | Warning |

### Confiabilidade

| Rule ID | Nome | Severidade |
|---------|------|-----------|
| `GRD-REL-001` | Swallowed Exception (catch vazio) | Error |
| `GRD-REL-002` | Catch genérico sem re-throw | Warning |
| `GRD-REL-003` | Thread.Sleep em código de produção | Warning |
| `GRD-REL-004` | Loop sem condição de saída clara | Warning |

### Performance

| Rule ID | Nome | Severidade |
|---------|------|-----------|
| `GRD-PERF-001` | N+1 Query pattern | Error |
| `GRD-PERF-002` | String concatenation em loop | Warning |
| `GRD-PERF-003` | CancellationToken ausente em async | Warning |
| `GRD-PERF-004` | Select * em queries | Info |

### Async/Await

| Rule ID | Nome | Severidade |
|---------|------|-----------|
| `GRD-ASYNC-001` | `.Result` ou `.Wait()` (deadlock) | Critical |
| `GRD-ASYNC-002` | async void (exceto event handlers) | Error |
| `GRD-ASYNC-003` | Fire-and-forget sem tratamento | Warning |

### Clean Code

| Rule ID | Nome | Severidade |
|---------|------|-----------|
| `GRD-CC-001` | God Class (>500 linhas) | Warning |
| `GRD-CC-002` | Método longo (>30 linhas) | Warning |
| `GRD-CC-003` | Nesting profundo (>5 níveis) | Warning |
| `GRD-CC-004` | Magic Number | Info |

---

## Scripts Python

Uso direto pela linha de comando (para debugging ou uso fora do VS):

```bash
# Análise completa de um arquivo (rules + métricas + IA)
python code_guardian/runner.py --file Services/MeuServico.cs --format json

# Análise da solution completa
python code_guardian/runner.py --scan --dir ./src --format json

# Apenas staged (pré-commit)
python code_guardian/runner.py --staged --rules-only

# Apenas rule engine (sem IA, mais rápido)
python code_guardian/rule_engine.py Services/MeuServico.cs --format text

# Apenas métricas
python code_guardian/metrics.py Services/MeuServico.cs --format text

# Diff — arquivos e linhas alteradas
python code_guardian/diff_parser.py --staged --for-ai

# Análise de IA isolada
python code_guardian/ai_client.py Services/MeuServico.cs --format json

# VB6 Rule Engine
python code_guardian/vb6_rule_engine.py Views/frmCadastro.frm --format text
```

**Exit codes do `rule_engine.py`:**
- `0` — Nenhum issue Critical ou Error
- `1` — Há pelo menos um issue Critical ou Error (útil para scripts de CI)

---

## Monitoramento e Histórico

### guardian-metrics.json

Cada análise bem-sucedida acumula uma entrada em `.codeguardian/guardian-metrics.json`:

```json
{
  "runs": [
    {
      "runId": "abc12345",
      "timestamp": "2025-04-22T10:30:00Z",
      "riskScore": 42,
      "riskLabel": "High Risk",
      "hasBlockers": false,
      "countCritical": 0,
      "countError": 3,
      "countWarning": 8,
      "countInfo": 2,
      "gitBranch": "feature/nova-feature",
      "gitCommit": "a1b2c3d4"
    }
  ]
}
```

**Retenção:** Máximo de 100 entradas (FIFO — a mais antiga é removida).
**Localização:** `.codeguardian/` na raiz do repositório (recomenda-se adicionar ao `.gitignore` ou commitar para rastreio de histórico).

### Interpretação da Tendência

A tendência é calculada comparando o `riskScore` atual com o da última entrada antes da análise atual:

```
Score atual 55, score anterior 48 → ↑ +7 pts (piorou)
Score atual 30, score anterior 45 → ↓ -15 pts (melhorou)
Score atual 30, score anterior 30 → = estável
```

---

## Integração CI/CD

### GitHub Actions

```yaml
name: Code Guardian Analysis

on: [push, pull_request]

jobs:
  code-guardian:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r code_guardian/requirements.txt

      - name: Run Code Guardian
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python code_guardian/runner.py --scan --dir ./src --format json \
            > .codeguardian/guardian-report.json

      - name: Export SARIF
        run: |
          python code_guardian/runner.py --scan --dir ./src --format sarif \
            > .codeguardian/guardian-report.sarif

      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: .codeguardian/guardian-report.sarif
```

### Azure DevOps

```yaml
trigger:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: pip install -r code_guardian/requirements.txt
    displayName: 'Install dependencies'

  - script: |
      python code_guardian/runner.py --scan --dir ./src --rules-only \
        > .codeguardian/guardian-report.sarif
    displayName: 'Run Code Guardian'

  - task: PublishBuildArtifacts@1
    inputs:
      pathToPublish: '.codeguardian'
      artifactName: 'code-guardian-results'
```

### Pre-commit hook (instalação manual)

Se o Code Guardian detectou um conflito com um hook existente, integre manualmente adicionando ao seu hook `pre-commit`:

```bash
#!/bin/bash
# ... seu hook existente ...

# Code Guardian
GUARDIAN_MARKER="# code-guardian-hook"
if [ -f "code_guardian/runner.py" ]; then
    python code_guardian/runner.py --staged --rules-only
    if [ $? -ne 0 ]; then
        echo "Code Guardian: issues críticos encontrados. Commit bloqueado."
        exit 1
    fi
fi
```

---

## Configurações Avançadas

### Ajustar timeout por projeto

Para projetos grandes onde a análise demora mais que 60 segundos:

**Tools → Options → Code Guardian → Analysis Timeout → 120**

### Forçar caminho do runner.py

Se a auto-detecção não encontrar o `runner.py` (repositório com estrutura não-padrão):

**Tools → Options → Code Guardian → Runner Script Path → `C:\caminho\absoluto\para\runner.py`**

### Rules Only permanente

Para desabilitar IA permanentemente (sem token de API, ambiente offline):

**Tools → Options → Code Guardian → Rules Only → True**

O botão de toggle no Tool Window pode ser usado para sobrescrever temporariamente por sessão.

---

## Supressão de Issues

O `rule_engine.py` suporta dois mecanismos de supressão, úteis quando uma regra dispara falso positivo em situações legítimas (ex.: modelos de domínio com setters públicos, classes Btrieve, DTOs gerados).

### 1. Supressão por linha (inline)

Adicione o comentário **imediatamente acima** da linha problemática, usando o Rule ID exato:

```csharp
// guardian: suppress PUBLIC_SETTER_ENTITY
public string NomeCampo { get; set; }
```

Múltiplas regras separadas por vírgula:

```csharp
// guardian: suppress PUBLIC_SETTER_ENTITY,NO_RESULT_PATTERN
public Task<string> BuscarDados() { ... }
```

O botão **✕** no Tool Window insere esse comentário automaticamente na linha correta.

> **IDs das regras:** use exatamente o `rule_id` retornado na análise — ex.: `PUBLIC_SETTER_ENTITY`, `SQL_INJECTION_CONCAT`, `TASK_RESULT_DEADLOCK`. O ID aparece em negrito na lista de issues do Tool Window.

---

### 2. Supressão por arquivo inteiro (file-suppress)

Para suprimir uma ou mais regras em **todo o arquivo**, adicione nas primeiras 30 linhas do `.cs`:

```csharp
// guardian: file-suppress PUBLIC_SETTER_ENTITY
```

Múltiplas regras em uma só linha:

```csharp
// guardian: file-suppress PUBLIC_SETTER_ENTITY,NO_RESULT_PATTERN
```

**Caso de uso típico — classe modelo Btrieve / NuGet de integração:**

```csharp
// guardian: file-suppress PUBLIC_SETTER_ENTITY
// Modelo de integração Btrieve — setters públicos são obrigatórios
// para leitura e escrita de campos no arquivo posicional.
namespace MinhaEmpresa.Integracao.Btrieve
{
    public class RegistroFuncionario
    {
        /// <summary>Posição 0 (1738/1) — Código do funcionário</summary>
        public int CodFuncionario { get; set; }

        /// <summary>Posição 1 (1739/1) — Nome</summary>
        public string Nome { get; set; }

        // ... demais campos
    }
}
```

Com isso, nenhuma das 500+ propriedades do modelo dispara `PUBLIC_SETTER_ENTITY`, e o Risk Score não é inflado por falsos positivos.

---

### Boas práticas de supressão

| Situação | Recomendação |
|----------|-------------|
| Falso positivo documentado e justificado | `// guardian: file-suppress` no topo do arquivo |
| Exceção pontual em um único método/linha | `// guardian: suppress` acima da linha |
| Regra incorreta ou muito agressiva | Abrir issue no repositório para ajuste da regra |
| Dúvida se é falso positivo | Corrigir o código — não suprimir |

- Documente **por que** o falso positivo existe (comentário ou PR description)
- Prefira corrigir o código a suprimir
- Revise supressões periodicamente — se a classe foi refatorada, a supressão pode não ser mais necessária

---

## Troubleshooting

### "runner.py não encontrado"

1. Verifique se a pasta `code_guardian/` existe na raiz do repositório
2. Confirme que `runner.py` está dentro da pasta
3. Se necessário, configure o caminho manualmente em **Tools → Options → Code Guardian → Runner Script Path**

### "Python não encontrado"

1. Verifique se Python está no PATH: abra um terminal e execute `python --version`
2. Se usar ambiente virtual, configure o caminho completo: **Tools → Options → Code Guardian → Python Executable → `C:\caminho\para\venv\Scripts\python.exe`**

### Análise demora muito / timeout

1. Aumente o timeout em **Tools → Options → Code Guardian → Analysis Timeout**
2. Ative **Rules Only** para pular a análise de IA (muito mais rápido)
3. Use **Análise Incremental** em vez de Análise de Solution durante o desenvolvimento

### InfoBar de Git Hooks aparece repetidamente

Isso ocorre quando existe um hook de terceiro no `.git/hooks/`. O Code Guardian não sobrescreve hooks que não instalou. Solução: integre o script do hook manualmente (veja [Pre-commit hook — instalação manual](#pre-commit-hook-instalação-manual)) ou remova o hook existente antes de instalar.

### Issues não aparecem no Error List

O Error List é atualizado após a análise. Se estiver vazio:
1. Verifique se a análise foi executada (o Tool Window deve mostrar resultados)
2. Confirme que o filtro do Error List não está ocultando as mensagens (verifique o filtro de projeto/arquivo)

### SARIF exportado não é aceito pelo GitHub

Verifique se o arquivo está no caminho correto (`.codeguardian/guardian-report.sarif`) e se o workflow do GitHub Actions tem permissão de `security-events: write`.

---

*Code Guardian é desenvolvido por [CygnusForge](https://cygnusforge.com.br).*
*Para suporte, abra uma issue no repositório do projeto.*
