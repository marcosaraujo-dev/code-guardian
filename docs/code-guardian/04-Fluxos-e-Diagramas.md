# Fluxos e Diagramas - Code Guardian

## 1. Fluxo Principal - Review Completo

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FLUXO PRINCIPAL DO REVIEW                         │
│                                                                      │
│  START                                                               │
│    │                                                                 │
│    ▼                                                                 │
│  ┌─────────────────┐     ┌──────────────────┐                       │
│  │ Detectar modo   │────▶│ Carregar config   │                       │
│  │ (CLI ou TFS)    │     │ .code-guardian.yml │                       │
│  └─────────────────┘     └────────┬─────────┘                       │
│                                   │                                  │
│                                   ▼                                  │
│                          ┌────────────────┐                          │
│                          │ Git Diff Parse │                          │
│                          │ (extrair mudanças)                        │
│                          └────────┬───────┘                          │
│                                   │                                  │
│                          ┌────────▼───────┐                          │
│                          │ Filtrar arquivos│                          │
│                          │ (.cs, excluir   │                          │
│                          │  Migrations)    │                          │
│                          └────────┬───────┘                          │
│                                   │                                  │
│                    ┌──────────────┼──────────────┐                   │
│                    ▼              ▼               ▼                   │
│            ┌─────────────┐ ┌──────────┐  ┌──────────────┐           │
│            │ Rule Engine │ │ Roslyn   │  │  AI Engine   │           │
│            │ (< 1s)      │ │ (10-30s) │  │  (10-30s)    │           │
│            └──────┬──────┘ └────┬─────┘  └──────┬───────┘           │
│                   │             │               │                    │
│                   └─────────────┼───────────────┘                    │
│                                 ▼                                    │
│                        ┌────────────────┐                            │
│                        │ Aggregator     │                            │
│                        │ •deduplica     │                            │
│                        │ •prioriza      │                            │
│                        │ •risk score    │                            │
│                        └────────┬───────┘                            │
│                                 │                                    │
│                    ┌────────────┼────────────┐                       │
│                    ▼                         ▼                       │
│            ┌──────────────┐         ┌──────────────┐                │
│            │ Console      │         │ TFS Reporter │                │
│            │ Reporter     │         │ (se modo TFS)│                │
│            │ (terminal)   │         │ •PR comments │                │
│            └──────┬───────┘         │ •status      │                │
│                   │                 └──────┬───────┘                │
│                   │                        │                        │
│                   └────────────┬───────────┘                        │
│                                ▼                                    │
│                       ┌────────────────┐                            │
│                       │ History Store  │                            │
│                       │ (SQLite)       │                            │
│                       └────────┬───────┘                            │
│                                │                                    │
│                                ▼                                    │
│                         EXIT CODE                                   │
│                    0 = sem issues bloqueantes                       │
│                    1 = issues >= fail_on                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Fluxo do AI Engine (Multi-Agente)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FLUXO AI ENGINE                                  │
│                                                                      │
│  Input: list[FileChange]                                             │
│    │                                                                 │
│    ▼                                                                 │
│  ┌─────────────────────┐                                             │
│  │ Preparar Prompts    │                                             │
│  │ •Extrair diff       │                                             │
│  │ •Sanitizar secrets  │                                             │
│  │ •Agrupar por batch  │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│  ┌──────────────────────┐                                            │
│  │ Resolver AI Client   │                                            │
│  │                      │                                            │
│  │ Gemini disponível?───┐                                            │
│  │   SIM → GeminiClient │                                            │
│  │   NÃO → Ollama?──────┐                                           │
│  │      SIM → OllamaClient                                          │
│  │      NÃO → Skip AI ──────▶ return [] (graceful)                  │
│  └──────────┬───────────┘                                            │
│             │                                                        │
│             ▼                                                        │
│  ┌──────────────────────────────────────────────────┐                │
│  │         EXECUTAR AGENTES EM PARALELO             │                │
│  │                                                   │                │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────┐│                │
│  │  │Logic Agent │  │Security Agent│  │Perf Agent ││                │
│  │  │            │  │              │  │           ││                │
│  │  │Prompt:     │  │Prompt:       │  │Prompt:    ││                │
│  │  │•NullRef    │  │•SQL Injection│  │•N+1 query ││                │
│  │  │•Deadlock   │  │•XSS          │  │•LINQ loop ││                │
│  │  │•Loop inf.  │  │•Secrets      │  │•ToList()  ││                │
│  │  │•Race cond. │  │•Auth bypass  │  │•Memory    ││                │
│  │  │•Dispose    │  │•IDOR         │  │•String cat││                │
│  │  └─────┬──────┘  └──────┬───────┘  └─────┬─────┘│                │
│  │        │                │                │      │                │
│  └────────┼────────────────┼────────────────┼──────┘                │
│           │                │                │                        │
│           ▼                ▼                ▼                        │
│  ┌──────────────────────────────────────────────┐                    │
│  │ Parse JSON responses                         │                    │
│  │ •Validar schema                              │                    │
│  │ •Filtrar confidence < threshold              │                    │
│  │ •Converter para list[Issue]                  │                    │
│  └──────────────────────┬───────────────────────┘                    │
│                         │                                            │
│                         ▼                                            │
│                 Output: list[Issue]                                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Fluxo TFS - Da PR ao Comentário

```
┌──────────────────────────────────────────────────────────────────────┐
│              FLUXO TFS / AZURE DEVOPS                                │
│                                                                      │
│  Developer                                                           │
│     │                                                                │
│     │ git push + Criar PR                                            │
│     ▼                                                                │
│  ┌─────────────────────┐                                             │
│  │ Azure DevOps        │                                             │
│  │ Branch Policy       │                                             │
│  │ "Build Validation"  │                                             │
│  └──────────┬──────────┘                                             │
│             │ Trigger automático                                     │
│             ▼                                                        │
│  ┌─────────────────────┐                                             │
│  │ Pipeline YAML       │                                             │
│  │                     │                                             │
│  │ 1. checkout (full)  │                                             │
│  │ 2. setup python     │                                             │
│  │ 3. pip install      │                                             │
│  │ 4. code-guardian    │                                             │
│  │    --mode tfs       │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│  ┌─────────────────────┐                                             │
│  │ Code Guardian Engine│  (mesmo engine do CLI)                      │
│  │ ReviewResult        │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│  ┌─────────────────────────────────────────┐                         │
│  │ TFS Reporter                            │                         │
│  │                                         │                         │
│  │ 1. POST /threads (sem context)          │                         │
│  │    → Comentário resumo no topo da PR    │                         │
│  │    ┌────────────────────────────────┐    │                         │
│  │    │ 🛡️ Code Guardian              │    │                         │
│  │    │ Risk Score: 🔴 42             │    │                         │
│  │    │ Critical: 1 | Error: 3        │    │                         │
│  │    │ Warning: 5 | Info: 2          │    │                         │
│  │    └────────────────────────────────┘    │                         │
│  │                                         │                         │
│  │ 2. POST /threads (com threadContext)    │                         │
│  │    → Comentário inline para cada issue  │                         │
│  │    ┌────────────────────────────────┐    │                         │
│  │    │ PedidoService.cs L:82         │    │                         │
│  │    │ ⚠️ NullReference: cliente     │    │                         │
│  │    │    pode ser null              │    │                         │
│  │    └────────────────────────────────┘    │                         │
│  │                                         │                         │
│  │ 3. POST /statuses                       │                         │
│  │    → Status check (succeeded/failed)    │                         │
│  │                                         │                         │
│  └─────────────────────┬───────────────────┘                         │
│                        │                                             │
│                        ▼                                             │
│  ┌─────────────────────────────────────────┐                         │
│  │ PR atualizada no Azure DevOps           │                         │
│  │                                         │                         │
│  │ • Comentários inline visíveis           │                         │
│  │ • Status check verde/vermelho           │                         │
│  │ • Merge bloqueado se failed             │                         │
│  └─────────────────────────────────────────┘                         │
│                        │                                             │
│                        ▼                                             │
│  Developer vê feedback na PR                                         │
│  e corrige antes do merge                                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Fluxo de Decisão - Qual Analyzer Usar

```
                    Arquivo .cs alterado
                           │
                           ▼
                  ┌────────────────┐
                  │ Rule Engine    │───────▶ Issues (se houver)
                  │ (SEMPRE roda)  │        (< 1 segundo)
                  └────────┬───────┘
                           │
                           ▼
               ┌───────────────────────┐
               │ Roslyn habilitado?    │
               │ (config.analyzers.    │
               │  roslyn == true)      │
               └───────┬───────┬───────┘
                  SIM  │       │  NÃO
                       ▼       │
              ┌────────────┐   │
              │ dotnet build│  │
              │ + analyzers │──┤──▶ Issues (se houver)
              └────────────┘   │
                               │
                               ▼
               ┌───────────────────────┐
               │ AI habilitado?        │
               │ (config.analyzers.    │
               │  ai_logic == true)    │
               └───────┬───────┬───────┘
                  SIM  │       │  NÃO
                       ▼       │
              ┌────────────┐   │
              │ AI Client  │   │
              │ disponível?│   │
              └───┬────┬───┘   │
              SIM │    │ NÃO   │
                  ▼    │       │
           ┌──────────┐│       │
           │ Executar  ││       │
           │ Agentes   ││       │
           │ (paralelo)│├───────┤──▶ Issues (se houver)
           └──────────┘│       │
                       │       │
                       ▼       │
              ┌────────────┐   │
              │ Fallback   │   │
              │ disponível?│   │
              └───┬────┬───┘   │
              SIM │    │ NÃO   │
                  ▼    │       │
           ┌──────────┐│       │
           │ Executar  ││       │
           │ com       ││       │
           │ fallback  │├───────┘
           └──────────┘│
                       │
                       ▼
              Log warning:
              "AI indisponível,
               review parcial"
```

---

## 5. Fluxo de Execução Local (Developer Experience)

```
┌──────────────────────────────────────────────────────────────────────┐
│              EXPERIÊNCIA DO DESENVOLVEDOR                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ OPÇÃO 1: Execução Manual                                    │     │
│  │                                                              │     │
│  │  $ code-guardian review                                      │     │
│  │                                                              │     │
│  │  🛡️ Code Guardian v1.0                                      │     │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━                                   │     │
│  │  Analisando 5 arquivos alterados...                          │     │
│  │                                                              │     │
│  │  📁 Services/PedidoService.cs                                │     │
│  │    🔴 L82: NullReference - cliente pode ser null             │     │
│  │    🟡 L95: Magic number 30 → extrair constante               │     │
│  │                                                              │     │
│  │  📁 Repositories/UserRepository.cs                           │     │
│  │    🔴 L45: SQL Injection - concatenação em query             │     │
│  │                                                              │     │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━                                   │     │
│  │  Risk Score: 🔴 42 (Alto Risco)                              │     │
│  │  🔴 Critical: 1 | 🟡 Warning: 1                             │     │
│  │                                                              │     │
│  │  💡 Corrija os itens críticos antes de criar a PR.           │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ OPÇÃO 2: Git Hook Automático                                │     │
│  │                                                              │     │
│  │  $ code-guardian hooks install                               │     │
│  │  ✅ Hook pre-push instalado                                  │     │
│  │                                                              │     │
│  │  Agora, a cada `git push`:                                   │     │
│  │                                                              │     │
│  │  $ git push origin feature/pedidos                           │     │
│  │  🛡️ Code Guardian executando review...                      │     │
│  │  🔴 2 issues críticas encontradas.                           │     │
│  │  Push BLOQUEADO. Corrija as issues antes de fazer push.      │     │
│  │                                                              │     │
│  │  Use --no-verify para bypass (não recomendado)               │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ OPÇÃO 3: Review Rápido (sem IA)                              │     │
│  │                                                              │     │
│  │  $ code-guardian review --rules-only                         │     │
│  │                                                              │     │
│  │  Executa apenas Rule Engine (< 1 segundo)                    │     │
│  │  Ideal para feedback instantâneo durante desenvolvimento     │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ OPÇÃO 4: Review Offline (Ollama)                             │     │
│  │                                                              │     │
│  │  $ code-guardian review --model ollama                       │     │
│  │                                                              │     │
│  │  Usa modelo local, sem internet                              │     │
│  │  Requer: ollama pull deepseek-coder-v2                       │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Fluxo de Fallback e Graceful Degradation

```
             Executar AI Review
                    │
                    ▼
            ┌───────────────┐
            │ Gemini API    │
            │ chamada       │
            └───┬───────┬───┘
           OK   │       │  ERRO
                ▼       │
         Processar      │
         resposta       │
                        ▼
                ┌───────────────┐
                │ Tipo de erro? │
                └─┬─────┬──┬───┘
                  │     │  │
         Rate     │     │  │ Timeout/
         Limit    │     │  │ Connection
                  ▼     │  │
         Retry    │     │  │
         com      │     │  ▼
         backoff  │     │  ┌──────────────┐
         (3x)     │     │  │ Ollama       │
                  │     │  │ disponível?  │
                  │     │  └──┬───────┬───┘
                  │     │  SIM│       │NÃO
                  │     │     ▼       │
                  │     │  Usar       │
                  │     │  Ollama     │
                  │     │             ▼
                  │     │      ┌──────────────┐
                  │     │      │ Skip AI      │
                  │     │      │ Review       │
                  │     │      │              │
                  │     │      │ Log warning: │
                  │     │      │ "AI offline, │
                  │     │      │  review      │
                  │     │      │  parcial"    │
                  │     │      └──────────────┘
                  │     │
                  │     ▼
                  │  JSON Parse
                  │  Error
                  │     │
                  │     ▼
                  │  Retry com
                  │  prompt mais
                  │  restritivo
                  │  (1x)
                  │
                  ▼
              Continuar com
              resultado parcial
```

---

## 7. Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                     CODE GUARDIAN                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ CLI Layer                                              │  │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │  │
│  │ │ review   │ │ init     │ │ config   │ │ hooks     │ │  │
│  │ │ command  │ │ command  │ │ command  │ │ command   │ │  │
│  │ └──────────┘ └──────────┘ └──────────┘ └───────────┘ │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │ Core Layer                                             │  │
│  │                                                        │  │
│  │ ┌──────────────────┐  ┌──────────────────┐            │  │
│  │ │ ReviewOrchestrator│  │ IssueAggregator  │            │  │
│  │ └──────────────────┘  └──────────────────┘            │  │
│  │                                                        │  │
│  │ ┌──────────────────┐  ┌──────────────────┐            │  │
│  │ │ ConfigLoader     │  │ PipelineManager  │            │  │
│  │ └──────────────────┘  └──────────────────┘            │  │
│  │                                                        │  │
│  │ Models: Issue, ReviewResult, RiskScore, FileChange     │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │ Analyzer Layer                                         │  │
│  │                                                        │  │
│  │ ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │  │
│  │ │IAnalyzer │  │IAnalyzer │  │IAnalyzer           │    │  │
│  │ │          │  │          │  │                     │    │  │
│  │ │RuleEngine│  │Roslyn    │  │AIEngine             │    │  │
│  │ │          │  │Analyzer  │  │ ├─LogicAgent        │    │  │
│  │ │          │  │          │  │ ├─SecurityAgent     │    │  │
│  │ │          │  │          │  │ └─PerformanceAgent  │    │  │
│  │ └──────────┘  └──────────┘  └────────────────────┘    │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │ Infrastructure Layer                                   │  │
│  │                                                        │  │
│  │ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────────┐ │  │
│  │ │GitParser │ │IAIClient │ │ITFSClnt │ │HistoryStore│ │  │
│  │ │          │ │          │ │         │ │            │ │  │
│  │ │•diff     │ │•Gemini   │ │•comment │ │•SQLite     │ │  │
│  │ │•staged   │ │•Ollama   │ │•status  │ │•export     │ │  │
│  │ │•filter   │ │•OpenAI   │ │•approve │ │•stats      │ │  │
│  │ └──────────┘ └──────────┘ └─────────┘ └────────────┘ │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Reporter Layer                                         │  │
│  │                                                        │  │
│  │ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │  │
│  │ │IReporter     │ │IReporter     │ │IReporter       │  │  │
│  │ │              │ │              │ │                │  │  │
│  │ │ConsoleReport │ │TFSReporter   │ │HTMLReporter    │  │  │
│  │ └──────────────┘ └──────────────┘ └────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Matriz de Detecção por Fonte

```
┌────────────────────────┬──────────┬────────┬──────────┬──────────┬──────────┐
│ Tipo de Problema       │ Rule     │ Roslyn │ AI Logic │ AI Sec.  │ AI Perf  │
│                        │ Engine   │        │          │          │          │
├────────────────────────┼──────────┼────────┼──────────┼──────────┼──────────┤
│ Console.WriteLine      │ ✅       │        │          │          │          │
│ Thread.Sleep           │ ✅       │        │          │          │          │
│ Task.Result / .Wait()  │ ✅       │ ✅     │ ✅       │          │          │
│ catch vazio            │ ✅       │ ✅     │ ✅       │          │          │
│ TODO no código         │ ✅       │        │          │          │          │
│ Magic numbers          │ ✅       │        │ ✅       │          │          │
├────────────────────────┼──────────┼────────┼──────────┼──────────┼──────────┤
│ NullReferenceException │          │ ✅     │ ✅       │          │          │
│ async void             │ ✅       │ ✅     │ ✅       │          │          │
│ IDisposable não disp.  │          │ ✅     │ ✅       │          │          │
│ Tipos incompatíveis    │          │ ✅     │          │          │          │
│ Unused variables       │          │ ✅     │          │          │          │
│ CS warnings            │          │ ✅     │          │          │          │
├────────────────────────┼──────────┼────────┼──────────┼──────────┼──────────┤
│ Loop infinito          │ ✅(básico)│       │ ✅       │          │          │
│ Deadlock async         │ ✅(básico)│       │ ✅       │          │          │
│ Race condition         │          │        │ ✅       │          │          │
│ Off-by-one             │          │        │ ✅       │          │          │
│ Fluxo impossível       │          │        │ ✅       │          │          │
│ Dependência circular   │          │        │ ✅       │          │          │
│ Condição sempre T/F    │          │        │ ✅       │          │          │
├────────────────────────┼──────────┼────────┼──────────┼──────────┼──────────┤
│ SQL Injection          │ ✅       │        │          │ ✅       │          │
│ XSS                    │          │        │          │ ✅       │          │
│ Secrets hardcoded      │ ✅       │        │          │ ✅       │          │
│ IDOR                   │          │        │          │ ✅       │          │
│ Mass assignment        │          │        │          │ ✅       │          │
│ Path traversal         │          │        │          │ ✅       │          │
├────────────────────────┼──────────┼────────┼──────────┼──────────┼──────────┤
│ N+1 query              │          │        │          │          │ ✅       │
│ LINQ em loop           │          │        │          │          │ ✅       │
│ ToList() prematuro     │          │        │          │          │ ✅       │
│ SELECT *               │          │        │          │          │ ✅       │
│ String concat em loop  │          │        │          │          │ ✅       │
│ Falta paginação        │          │        │          │          │ ✅       │
│ Falta CancellationToken│          │        │          │          │ ✅       │
└────────────────────────┴──────────┴────────┴──────────┴──────────┴──────────┘

Legenda:
✅        = Detecta este tipo de problema
✅(básico) = Detecta padrão simples (regex), pode ter falsos positivos
(vazio)   = Não detecta
```

---

## 9. Sequência de Setup Inicial

```
┌──────────────────────────────────────────────────────────────────────┐
│              SETUP PARA NOVO PROJETO                                 │
│                                                                      │
│  1. INSTALAR                                                         │
│     $ pip install code-guardian                                      │
│                                                                      │
│  2. INICIALIZAR NO PROJETO                                           │
│     $ cd MeuProjeto/                                                 │
│     $ code-guardian init                                             │
│                                                                      │
│     Assistente interativo:                                           │
│     > Qual provider de IA? [gemini/ollama/openai]: gemini            │
│     > Qual branch base? [main]: main                                 │
│     > Extensões para analisar? [.cs]: .cs                            │
│     > Habilitar Roslyn analyzers? [S/n]: S                           │
│     > Severidade mínima para bloquear? [error]: error                │
│                                                                      │
│     ✅ Criado .code-guardian.yml                                     │
│                                                                      │
│  3. CONFIGURAR API KEY                                               │
│     $ code-guardian config set api-key AIza...                       │
│     ✅ API key salva em ~/.code-guardian/config.yml                  │
│                                                                      │
│  4. TESTAR                                                           │
│     $ code-guardian review --rules-only                              │
│     ✅ Review executado (sem IA, validando setup)                    │
│                                                                      │
│     $ code-guardian review                                           │
│     ✅ Review completo com IA                                        │
│                                                                      │
│  5. (OPCIONAL) INSTALAR GIT HOOK                                     │
│     $ code-guardian hooks install                                    │
│     ✅ Hook pre-push instalado                                      │
│                                                                      │
│  6. (OPCIONAL) CONFIGURAR PIPELINE TFS                               │
│     Copiar templates/pipeline-azure-devops.yml para o repo           │
│     Configurar variáveis no pipeline (GEMINI_API_KEY)                │
│     Configurar Branch Policy > Build Validation                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```
