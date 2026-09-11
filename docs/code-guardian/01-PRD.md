# PRD - Code Guardian: Code Review Automatizado com IA

## Identidade do Projeto

- **Mantenedor atual**: **cygnusforge**
- **Contexto de naming**: este projeto não deve utilizar a marca "Prosoft" em novos artefatos de produto.
- **Atualização**: 2026-03-14

## Visão Geral

**Code Guardian** é um sistema de code review automatizado com IA que analisa Pull Requests em múltiplas dimensões (padrões, lógica, segurança, performance, arquitetura) e publica comentários diretamente nas linhas alteradas da PR no TFS/Azure DevOps.

**Problema**: Code reviews manuais são inconsistentes, demorados e não escalam. Bugs de lógica (NullReference, deadlocks, loops infinitos) frequentemente escapam da revisão humana.

**Solução**: Um sistema multi-agente que combina análise estática, regras customizadas e revisão por IA, executável tanto localmente (pré-commit/pré-push) quanto no pipeline de CI/CD do TFS.

---

## Contexto e Decisões Estratégicas

### Modelo de IA

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| **Modelo principal** | **Google Gemini** | Licença corporativa já existente |
| **Modelo alternativo** | Configurável (OpenAI, Anthropic, Ollama) | Flexibilidade futura |
| **Execução local offline** | Ollama (Llama 3, CodeLlama, DeepSeek Coder) | Sem custo, sem envio de código para nuvem |

### Linguagem do Sistema

| Opção | Prós | Contras | Recomendação |
|-------|------|---------|--------------|
| **Python** | Fácil integração TFS, ecossistema IA maduro, scripts leves | Não é stack principal da equipe | **Recomendado para o Runner/Engine** |
| **C#/.NET** | Stack da equipe, Roslyn nativo | Mais pesado para scripts de pipeline | Bom para analyzers Roslyn customizados |
| **TypeScript/Node** | Leve, bom para CLI | Menos integração com Roslyn | Alternativa viável para CLI local |

**Decisão**: **Python para o core do runner** (melhor integração com TFS pipelines, SDKs de IA, e parsing de diffs) + **Roslyn Analyzers em C#** para análise estática profunda do .NET.

---

## Personas e Stakeholders

| Persona | Necessidade |
|---------|------------|
| **Desenvolvedor** | Feedback rápido antes de criar a PR, sem sair do fluxo |
| **Tech Lead** | Garantia de qualidade e consistência nos padrões |
| **QA** | Menos bugs de lógica chegando para teste |
| **Gestor** | Métricas de qualidade e evolução do time |

---

## Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────┐
│                EXECUÇÃO LOCAL                    │
│                                                  │
│  $ code-guardian review                          │
│  $ code-guardian review --staged                 │
│  $ code-guardian review --file Services/Foo.cs   │
│                                                  │
│  → Resultado no terminal (colorido)              │
│  → Opção: bloquear commit se crítico             │
└──────────────────────┬──────────────────────────┘
                       │ (mesmo engine)
┌──────────────────────▼──────────────────────────┐
│              CODE GUARDIAN ENGINE                 │
│                                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐ │
│  │ Git Diff │  │  Analyzers │  │  AI Reviewer │ │
│  │ Parser   │  │  (Roslyn,  │  │  (Gemini /   │ │
│  │          │  │  Rules)    │  │   Ollama)    │ │
│  └────┬─────┘  └─────┬─────┘  └──────┬───────┘ │
│       └───────────────┼───────────────┘         │
│                       ▼                          │
│              Issue Aggregator                    │
│              (consolida, deduplica, prioriza)    │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              EXECUÇÃO TFS/AZURE DEVOPS           │
│                                                  │
│  PR criada → Pipeline dispara → Engine executa   │
│                                                  │
│  → Comentários inline na PR (por linha)          │
│  → Status: approved / needs work                 │
│  → Score de risco da PR                          │
│  → Build passa ou falha                          │
└─────────────────────────────────────────────────┘
```

---

## Funcionalidades (Épicos)

### EP01 - Engine Core
O motor central que orquestra toda a análise.

### EP02 - Git Diff Parser
Extrai apenas o código alterado da PR/commit, mapeando arquivo + linha.

### EP03 - Rule Engine (Regras Customizadas)
Regras simples baseadas em padrões de texto/regex, configuráveis por projeto.

### EP04 - Roslyn Analyzer Integration
Análise estática profunda do código C# via Roslyn (compilador .NET).

### EP05 - AI Review Engine (Multi-Agente)
Revisão inteligente usando IA com agentes especializados.

### EP06 - Issue Aggregator
Consolida resultados de todas as fontes, remove duplicatas, prioriza.

### EP07 - TFS/Azure DevOps Integration
Integração com API do Azure DevOps para comentários inline em PRs.

### EP08 - CLI Local (Developer Experience)
Ferramenta de linha de comando para execução local.

### EP09 - Métricas e Histórico
Armazena histórico de issues para análise de tendências.

### EP10 - Configuração por Projeto
Permite customizar regras, severidades e comportamento por repositório.

---

## Detalhamento dos Épicos

### EP01 - Engine Core

**Objetivo**: Orquestrar a execução de todos os analyzers e consolidar resultados.

**Componentes**:
- `ReviewOrchestrator` - coordena o fluxo completo
- `AnalyzerPipeline` - executa analyzers em sequência/paralelo
- `ResultCollector` - coleta e normaliza resultados
- `ConfigLoader` - carrega configuração do projeto

**Fluxo**:
```
1. Receber input (arquivos ou diff)
2. Carregar configuração (.code-guardian.yml)
3. Executar Git Diff Parser
4. Para cada arquivo alterado (.cs):
   a. Executar Rule Engine
   b. Executar Roslyn Analyzers
   c. Executar AI Review
5. Consolidar resultados
6. Gerar output (terminal ou API)
```

### EP02 - Git Diff Parser

**Objetivo**: Extrair apenas as linhas alteradas, mapeando arquivo + número da linha.

**Input**: Repositório Git com branch base (main/develop)
**Output**: Lista de `FileChange(filePath, lineNumber, lineContent, changeType)`

**Funcionalidades**:
- Extrair diff entre branches (`git diff origin/main...HEAD`)
- Extrair diff de staged files (`git diff --cached`)
- Parsear hunks do diff unificado
- Mapear número de linha real no arquivo destino
- Filtrar apenas arquivos .cs (configurável)
- Suportar renomeações de arquivo

### EP03 - Rule Engine

**Objetivo**: Regras simples e rápidas baseadas em padrões, sem IA.

**Configuração** (`.code-guardian.yml`):
```yaml
rules:
  - id: NO_CONSOLE_WRITE
    pattern: "Console.WriteLine"
    message: "Evite Console.WriteLine em produção. Use ILogger."
    severity: warning

  - id: NO_THREAD_SLEEP
    pattern: "Thread.Sleep"
    message: "Thread.Sleep bloqueia a thread. Use Task.Delay."
    severity: error

  - id: NO_TASK_RESULT
    pattern: ".Result"
    context: "Task"
    message: "Task.Result pode causar deadlock. Use await."
    severity: error

  - id: NO_EMPTY_CATCH
    pattern_regex: "catch\\s*\\{|catch\\s*\\(\\s*\\)"
    message: "Catch vazio engole exceções. Sempre log ou re-throw."
    severity: error

  - id: NO_TODO_IN_PR
    pattern: "// TODO"
    message: "TODO encontrado. Resolver antes de mergear ou criar issue."
    severity: warning

  - id: NO_MAGIC_NUMBERS
    pattern_regex: "==\\s*\\d{2,}|>\\s*\\d{2,}|<\\s*\\d{2,}"
    message: "Possível magic number. Extrair para constante nomeada."
    severity: info

  - id: NO_SQL_CONCAT
    pattern_regex: "\"SELECT.*\\+|\\$\"SELECT|\"INSERT.*\\+|\"UPDATE.*\\+"
    message: "Possível SQL Injection! Use queries parametrizadas."
    severity: critical
```

**Regras Built-in** (não configuráveis, sempre ativas):
| ID | Padrão | Severidade |
|----|--------|-----------|
| BUILTIN_SQL_INJECTION | Concatenação em strings SQL | Critical |
| BUILTIN_HARDCODED_SECRET | Padrões de API keys/passwords no código | Critical |
| BUILTIN_ASYNC_VOID | `async void` (exceto event handlers) | Error |
| BUILTIN_TASK_RESULT | `.Result` em Task | Error |
| BUILTIN_TASK_WAIT | `.Wait()` em Task | Error |

### EP04 - Roslyn Analyzer Integration

**Objetivo**: Análise estática profunda usando o compilador C#.

**Abordagem**: Executar `dotnet build` com analyzers habilitados e parsear output.

**Analyzers a integrar**:
| Analyzer | O que detecta | Como obter |
|----------|--------------|-----------|
| **Compilador C#** | Null reference, tipos incorretos, async incorreto | Built-in (`dotnet build`) |
| **Microsoft.CodeAnalysis.NetAnalyzers** | CA rules (performance, design, segurança) | NuGet gratuito |
| **Microsoft.CodeAnalysis.BannedApiAnalyzers** | APIs proibidas (Thread.Sleep, etc.) | NuGet gratuito |
| **Roslynator** | 500+ analyzers (naming, simplification, etc.) | NuGet gratuito |
| **SonarAnalyzer.CSharp** | Code smells, bugs, vulnerabilidades | NuGet gratuito (Community) |
| **AsyncFixer** | Problemas com async/await | NuGet gratuito |
| **SecurityCodeScan** | Vulnerabilidades OWASP | NuGet gratuito |

**Execução**:
```bash
dotnet build MySolution.sln -warnaserror /p:TreatWarningsAsErrors=true 2>&1
```

**Parser de output**: Extrair warnings/errors do formato MSBuild:
```
src/Services/UserService.cs(45,12): warning CS8602: Dereference of a possibly null reference.
```

### EP05 - AI Review Engine (Multi-Agente)

**Objetivo**: Detectar problemas de lógica que análise estática não captura.

**Modelo**: Google Gemini (licença corporativa) com fallback para Ollama local.

**Arquitetura Multi-Agente**:

```
                    ┌──────────────────────┐
                    │  Coordinator Agent   │
                    │  (orquestra e        │
                    │   consolida)         │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                     │
   ┌──────▼──────┐   ┌────────▼────────┐   ┌───────▼───────┐
   │ Logic Agent │   │ Security Agent  │   │ Perf Agent    │
   │             │   │                 │   │               │
   │ •NullRef    │   │ •SQL Injection  │   │ •N+1 query    │
   │ •Deadlocks  │   │ •XSS            │   │ •LINQ em loop │
   │ •Loops inf. │   │ •Secrets exp.   │   │ •ToList() cedo│
   │ •Race cond. │   │ •Auth bypass    │   │ •Memory leak  │
   │ •Fluxo      │   │ •IDOR           │   │ •Alloc excess.│
   └─────────────┘   └─────────────────┘   └───────────────┘
```

**Agentes Especializados**:

#### Logic Agent (Problemas de Lógica)
```
Detecta:
- NullReferenceException potencial
- Loops infinitos (while sem break/condição de saída)
- Deadlocks async (Task.Result, .Wait(), async void)
- Race conditions (shared state sem lock)
- Off-by-one errors
- Condições sempre true/false
- Variáveis não inicializadas
- IDisposable não disposto (using/dispose)
- Exception swallowing (catch vazio)
- Fluxo impossível (código morto)
- Dependência circular entre classes
```

#### Security Agent (Segurança)
```
Detecta:
- SQL Injection (concatenação em queries)
- XSS (output não sanitizado)
- Secrets hardcoded (API keys, passwords, connection strings)
- IDOR (acesso sem verificar ownership)
- Mass assignment (bind direto de request para entity)
- Insecure deserialization
- Path traversal
- Weak cryptography (MD5, SHA1 para passwords)
```

#### Performance Agent (Performance)
```
Detecta:
- N+1 queries (loop com query individual)
- LINQ dentro de loop
- ToList() antes de filtrar
- SELECT * (sem projeção)
- Falta de paginação em queries
- Alocações excessivas em hot paths
- String concatenação em loop (usar StringBuilder)
- Falta de caching em dados repetidos
- Async sem CancellationToken
```

**Prompt Template** (exemplo Logic Agent):
```
Você é um revisor de código C# sênior especializado em detectar bugs de lógica.

Analise APENAS o código alterado abaixo (diff de uma Pull Request).

Para cada problema encontrado, retorne um JSON com:
- file: caminho do arquivo
- line: número da linha no arquivo
- severity: "critical" | "error" | "warning" | "info"
- category: categoria do problema
- message: descrição clara do problema em português
- suggestion: sugestão de correção em português

IMPORTANTE:
- Analise APENAS as linhas marcadas com + (adicionadas)
- Considere o contexto das linhas ao redor
- Não reporte problemas em linhas não alteradas
- Seja preciso: não reporte falsos positivos
- Foque em bugs REAIS, não estilo de código

Código alterado:
{diff_content}

Retorne APENAS um JSON array. Se não houver problemas, retorne [].
```

**Formato de resposta da IA (JSON estruturado)**:
```json
[
  {
    "file": "Services/PedidoService.cs",
    "line": 82,
    "severity": "error",
    "category": "NullReference",
    "message": "Possível NullReferenceException: 'cliente' pode ser null mas não há verificação antes de acessar 'cliente.Nome'",
    "suggestion": "Adicionar verificação: if (cliente is null) return Result.Failure(\"Cliente não encontrado\");"
  }
]
```

### EP06 - Issue Aggregator

**Objetivo**: Consolidar, deduplicar e priorizar issues de todas as fontes.

**Funcionalidades**:
- Unificar formato de issues (Rule Engine, Roslyn, IA)
- Deduplicar (mesma linha + mesmo tipo de problema)
- Priorizar por severidade (critical > error > warning > info)
- Calcular **Risk Score** da PR
- Gerar resumo executivo

**Risk Score da PR**:
```
Score = Σ(peso × quantidade)

Pesos:
  critical = 25 pontos
  error    = 10 pontos
  warning  =  3 pontos
  info     =  1 ponto

Classificação:
  0-10:   ✅ Baixo risco (auto-approve possível)
  11-30:  ⚠️ Risco moderado (review humano recomendado)
  31-60:  🔴 Alto risco (review humano obrigatório)
  >60:    🚫 Risco crítico (bloquear merge)
```

### EP07 - TFS/Azure DevOps Integration

**Objetivo**: Publicar resultados como comentários inline na PR.

**API utilizada**:
```
POST /_apis/git/repositories/{repo}/pullRequests/{prId}/threads?api-version=7.0
```

**Funcionalidades**:
- Criar thread de comentário por issue (na linha exata)
- Criar comentário resumo no topo da PR
- Atualizar status da PR (approved / needs work)
- Publicar Risk Score como status check
- Resolver threads automaticamente quando issue é corrigida

**Formato do comentário na PR**:
```markdown
## 🛡️ Code Guardian - Review Automático

**Risk Score**: 🔴 42/100 (Alto Risco)

### Resumo
| Severidade | Quantidade |
|-----------|-----------|
| 🔴 Critical | 1 |
| 🟠 Error | 3 |
| 🟡 Warning | 5 |
| 🔵 Info | 2 |

### Issues Críticas
1. **SQL Injection** em `UserRepository.cs:45` - Concatenação de string em query SQL
2. **NullReference** em `PedidoService.cs:82` - cliente pode ser null

> Gerado por Code Guardian v1.0 | Gemini AI
```

**Comentário inline (na linha)**:
```markdown
⚠️ **Code Guardian** | NullReference | Severity: Error

Possível NullReferenceException: `cliente` pode ser null mas não há verificação antes de acessar `cliente.Nome`.

**Sugestão**:
```csharp
if (cliente is null)
    return Result.Failure("Cliente não encontrado");
```

### EP08 - CLI Local

**Objetivo**: Permitir que desenvolvedores rodem o review antes da PR.

**Comandos**:
```bash
# Revisar alterações staged (pré-commit)
code-guardian review --staged

# Revisar alterações vs main (pré-push)
code-guardian review

# Revisar arquivo específico
code-guardian review --file Services/UserService.cs

# Revisar com modelo local (sem internet)
code-guardian review --model ollama

# Apenas regras (sem IA, mais rápido)
code-guardian review --rules-only

# Gerar relatório
code-guardian review --output report.html

# Configurar
code-guardian init  # cria .code-guardian.yml
code-guardian config set model gemini
code-guardian config set api-key <key>
```

**Output no terminal** (colorido):
```
🛡️ Code Guardian v1.0
━━━━━━━━━━━━━━━━━━━━
Analisando 5 arquivos alterados...

📁 Services/PedidoService.cs
  🔴 L82: NullReference - cliente pode ser null [Logic Agent]
  🟡 L95: Magic number 30 deve ser constante [Rule Engine]

📁 Repositories/UserRepository.cs
  🔴 L45: SQL Injection - query com concatenação [Security Agent]

📁 Controllers/OrderController.cs
  🟠 L23: Controller com 35 linhas de lógica [Rule Engine]
  🟡 L12: Falta CancellationToken no endpoint [Perf Agent]

━━━━━━━━━━━━━━━━━━━━
Risk Score: 🔴 42 (Alto Risco)
🔴 Critical: 1 | 🟠 Error: 1 | 🟡 Warning: 2 | 🔵 Info: 0

💡 Corrija os itens críticos antes de criar a PR.
```

**Integração com Git Hooks**:
```bash
# .git/hooks/pre-push
#!/bin/sh
code-guardian review --staged --fail-on error
```

### EP09 - Métricas e Histórico

**Objetivo**: Rastrear evolução da qualidade do código ao longo do tempo.

**Armazenamento**: SQLite local + opção de exportar para banco centralizado.

**Dados coletados por review**:
```json
{
  "reviewId": "uuid",
  "repository": "MyProject",
  "branch": "feature/pedidos",
  "author": "joao.silva",
  "timestamp": "2026-03-11T10:00:00Z",
  "filesAnalyzed": 5,
  "linesChanged": 120,
  "riskScore": 42,
  "issues": [
    {
      "severity": "critical",
      "category": "SQL Injection",
      "file": "UserRepository.cs",
      "line": 45,
      "agent": "security"
    }
  ],
  "executionTimeMs": 15000
}
```

**Dashboards possíveis**:
- Top 10 tipos de issue mais frequentes
- Evolução do risk score por sprint
- Desenvolvedores com mais regressões
- Áreas do código mais problemáticas (hot spots)
- Tempo médio de execução do review

### EP10 - Configuração por Projeto

**Arquivo**: `.code-guardian.yml` na raiz do repositório.

```yaml
# .code-guardian.yml
version: "1.0"

# Modelo de IA
ai:
  provider: gemini          # gemini | ollama | openai | anthropic
  model: gemini-2.0-flash   # modelo específico
  fallback: ollama           # fallback se provider falhar
  ollama_model: deepseek-coder-v2  # modelo local
  temperature: 0.1           # baixa para consistência
  max_tokens: 4096

# Arquivos a analisar
files:
  include:
    - "**/*.cs"
  exclude:
    - "**/Migrations/**"
    - "**/obj/**"
    - "**/bin/**"
    - "**/*.Designer.cs"
    - "**/Tests/**"

# Analyzers habilitados
analyzers:
  rules: true
  roslyn: true
  ai_logic: true
  ai_security: true
  ai_performance: true

# Severidade mínima para bloquear
blocking:
  fail_on: error             # critical | error | warning
  max_risk_score: 60         # bloquear se score > 60

# Regras customizadas do projeto
rules:
  - id: NO_AUTOMAPPER
    pattern: "AutoMapper"
    message: "AutoMapper é pago. Use mapeamento manual ou Mapster."
    severity: error

# TFS Integration
tfs:
  comment_on_pr: true
  update_pr_status: true
  auto_approve_below: 10     # auto-approve se risk score < 10
```

---

## Abordagens de Execução

### Opção A: CLI Python Puro (Recomendada para MVP)

```
Instalação: pip install code-guardian
Execução local: code-guardian review
Execução TFS: python -m code_guardian.runner
```

**Prós**: Simples, leve, funciona em qualquer agent do TFS
**Contras**: Roslyn requer `dotnet` instalado no agent

### Opção B: Docker Container

```
Imagem: code-guardian:latest
Contém: Python + .NET SDK + Roslyn analyzers
Execução TFS: docker run code-guardian review
```

**Prós**: Ambiente consistente, inclui tudo
**Contras**: Imagem grande (~2GB), requer Docker no agent

### Opção C: Extensão do Azure DevOps (TFS)

```
Marketplace: instalar extensão "Code Guardian"
Pipeline: task CodeGuardian@1
```

**Prós**: Integração nativa, UI no TFS, configuração visual
**Contras**: Mais complexo de desenvolver e publicar

### Opção D: Híbrida (Recomendada para Produção)

```
CLI Python local (dev machine) → mesmo engine
Pipeline YAML no TFS           → mesmo engine via script
Extensão TFS futura            → wrapper do engine
```

**Prós**: Máxima flexibilidade, evolução gradual
**Contras**: Manter dois modos de execução

**Recomendação**: Começar com **Opção A** (MVP), evoluir para **Opção D**.

---

## Roadmap

### Fase 1 - MVP (4-6 semanas)
- [ ] EP02 - Git Diff Parser
- [ ] EP03 - Rule Engine (regras built-in)
- [ ] EP05 - AI Review (apenas Logic Agent com Gemini)
- [ ] EP06 - Issue Aggregator (básico)
- [ ] EP08 - CLI Local (comandos básicos)
- [ ] EP10 - Configuração básica (.code-guardian.yml)

### Fase 2 - TFS Integration (3-4 semanas)
- [ ] EP07 - Integração TFS/Azure DevOps (comentários inline)
- [ ] EP05 - Security Agent e Performance Agent
- [ ] EP06 - Risk Score
- [ ] Pipeline YAML de referência

### Fase 3 - Análise Profunda (3-4 semanas)
- [ ] EP04 - Roslyn Analyzer Integration
- [ ] EP05 - Refinamento dos prompts dos agentes
- [ ] EP08 - Git hooks (pre-push)
- [ ] Suporte a Ollama (execução local offline)

### Fase 4 - Métricas e Evolução (2-3 semanas)
- [ ] EP09 - Histórico e métricas
- [ ] Dashboard de tendências
- [ ] EP01 - Execução paralela de agentes
- [ ] Cache de resultados (não re-analisar arquivos não alterados)

---

## Requisitos Não-Funcionais

| Requisito | Meta |
|-----------|------|
| **Tempo de execução** | < 2 min para PR com até 10 arquivos |
| **Falsos positivos** | < 15% (refinamento contínuo dos prompts) |
| **Disponibilidade** | Pipeline não deve falhar se IA estiver offline (graceful degradation) |
| **Custo** | Zero (Gemini com licença existente, ferramentas gratuitas) |
| **Compatibilidade** | TFS 2019+, Azure DevOps Server, Azure DevOps Services |
| **Segurança** | Código nunca sai da rede interna (Ollama ou Gemini com VPN) |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Falsos positivos da IA | Alta | Médio | Prompt engineering, temperatura baixa, feedback loop |
| IA offline/lenta | Média | Médio | Fallback para Ollama local, timeout com graceful skip |
| Código sensível enviado para nuvem | Média | Alto | Opção Ollama local, Gemini via VPN corporativa |
| Resistência dos devs | Média | Alto | Começar com severity=info (sugestões), não bloquear |
| Custo de tokens Gemini | Baixa | Baixo | Analisar apenas diff (não arquivo inteiro), cache |

---

## Métricas de Sucesso

| Métrica | Baseline | Meta (6 meses) |
|---------|---------|----------------|
| Bugs de lógica em produção | X/mês | -50% |
| Tempo médio de code review | Y min | -40% |
| Cobertura de PRs revisadas por IA | 0% | 100% |
| Falsos positivos reportados | N/A | < 15% |
| Adoção pelo time (uso local) | 0% | > 60% |
