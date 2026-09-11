# User Stories - Code Guardian

## Convenções

- **Severidade**: 🔴 Must Have | 🟡 Should Have | 🟢 Nice to Have
- **Estimativa**: Story Points (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Critérios de aceite**: Formato Given/When/Then

---

## EP01 - Engine Core

### US-01.1 🔴 Orquestrar Análise Completa
**Como** desenvolvedor,
**Quero** que o engine execute todas as análises configuradas em sequência,
**Para** receber um resultado consolidado de todos os analyzers.

**Critérios de Aceite**:
- **CA1**: Dado um repositório com `.code-guardian.yml`, quando o engine executa, então ele carrega a configuração e respeita os analyzers habilitados.
- **CA2**: Dado que os analyzers rule-engine e ai-logic estão habilitados, quando o engine executa, então ambos são executados para cada arquivo alterado.
- **CA3**: Dado que um analyzer falha com exceção, quando o engine executa, então os demais analyzers continuam executando e o erro é logado.
- **CA4**: O engine deve retornar um objeto `ReviewResult` com lista unificada de issues, risk score e metadados.

**SP**: 5

---

### US-01.2 🟡 Configuração Padrão sem Arquivo
**Como** desenvolvedor,
**Quero** que o engine funcione sem um `.code-guardian.yml`,
**Para** poder usar imediatamente sem configuração.

**Critérios de Aceite**:
- **CA1**: Dado que o arquivo `.code-guardian.yml` não existe, quando o engine executa, então usa configuração padrão (rules + ai_logic habilitados, fail_on=error).
- **CA2**: A configuração padrão inclui todas as regras built-in ativas.

**SP**: 2

---

## EP02 - Git Diff Parser

### US-02.1 🔴 Extrair Diff entre Branches
**Como** engine,
**Quero** extrair o diff entre a branch atual e a branch base,
**Para** analisar apenas o código que mudou na PR.

**Critérios de Aceite**:
- **CA1**: Dado um repositório git com branch `feature/x` baseada em `main`, quando o parser executa, então retorna apenas os arquivos e linhas alterados.
- **CA2**: O resultado contém: filePath, lineNumber (no arquivo destino), lineContent, changeType (added/modified/deleted).
- **CA3**: Linhas deletadas são retornadas para contexto mas não geram issues.
- **CA4**: Arquivos renomeados são detectados corretamente.

**SP**: 5

---

### US-02.2 🔴 Extrair Diff de Staged Files
**Como** desenvolvedor,
**Quero** analisar apenas os arquivos staged (git add),
**Para** revisar antes do commit.

**Critérios de Aceite**:
- **CA1**: Dado arquivos staged com `git add`, quando `--staged` é passado, então apenas esses arquivos são analisados.
- **CA2**: O diff mostra as mudanças entre HEAD e staging area.

**SP**: 3

---

### US-02.3 🟡 Filtrar por Extensão de Arquivo
**Como** engine,
**Quero** filtrar arquivos pelo padrão configurado,
**Para** não analisar arquivos irrelevantes.

**Critérios de Aceite**:
- **CA1**: Dado `include: ["**/*.cs"]` na config, quando o parser executa, então retorna apenas arquivos .cs.
- **CA2**: Dado `exclude: ["**/Migrations/**"]`, quando o parser executa, então ignora arquivos de migration.
- **CA3**: Padrões glob são suportados (**, *, ?).

**SP**: 2

---

## EP03 - Rule Engine

### US-03.1 🔴 Executar Regras Built-in
**Como** engine,
**Quero** executar regras de detecção por padrão de texto,
**Para** encontrar problemas comuns rapidamente sem IA.

**Critérios de Aceite**:
- **CA1**: Dado um arquivo com `Console.WriteLine`, quando a regra NO_CONSOLE_WRITE está ativa, então gera um warning com a mensagem configurada.
- **CA2**: Dado um arquivo com `Task.Result`, então gera error indicando risco de deadlock.
- **CA3**: A regra reporta o arquivo e número da linha exatos.
- **CA4**: Regras built-in não podem ser desativadas (SQL Injection, secrets hardcoded).
- **CA5**: A análise roda em < 1 segundo para 20 arquivos.

**SP**: 5

---

### US-03.2 🟡 Regras Customizadas por Projeto
**Como** tech lead,
**Quero** definir regras específicas do meu projeto no `.code-guardian.yml`,
**Para** enforçar padrões internos que não são universais.

**Critérios de Aceite**:
- **CA1**: Dado uma regra customizada com `pattern` e `message`, quando o engine executa, então aplica a regra nos arquivos.
- **CA2**: Regras customizadas suportam regex via `pattern_regex`.
- **CA3**: Cada regra tem id único, message e severity configuráveis.
- **CA4**: Regras customizadas podem ser desativadas individualmente.

**SP**: 3

---

### US-03.3 🟢 Regras com Contexto
**Como** rule engine,
**Quero** analisar o contexto ao redor do padrão encontrado,
**Para** reduzir falsos positivos.

**Critérios de Aceite**:
- **CA1**: Dado `.Result` dentro de um comentário, quando a regra NO_TASK_RESULT executa, então NÃO gera issue.
- **CA2**: Dado `.Result` dentro de uma string literal, então NÃO gera issue.
- **CA3**: Dado `.Result` como propriedade de outro tipo (não Task), então NÃO gera issue se configurado.

**SP**: 5

---

## EP04 - Roslyn Analyzer Integration

### US-04.1 🟡 Executar Build com Analyzers
**Como** engine,
**Quero** executar `dotnet build` e capturar warnings/errors dos analyzers,
**Para** ter análise estática profunda do compilador C#.

**Critérios de Aceite**:
- **CA1**: Dado uma solution .NET, quando o engine executa com `roslyn: true`, então roda `dotnet build` com analyzers.
- **CA2**: Warnings e errors do build são parseados e convertidos para o formato padrão de issue.
- **CA3**: Apenas issues em arquivos alterados (do diff) são reportadas.
- **CA4**: Se o build falhar, o engine reporta o erro mas continua com outros analyzers.

**SP**: 5

---

### US-04.2 🟢 Instalar Analyzers Automaticamente
**Como** engine,
**Quero** garantir que analyzers NuGet estejam instalados no projeto,
**Para** não depender de configuração manual.

**Critérios de Aceite**:
- **CA1**: Se o projeto não tem `Microsoft.CodeAnalysis.NetAnalyzers`, o engine sugere instalação.
- **CA2**: Opção `--install-analyzers` adiciona pacotes NuGet necessários.

**SP**: 3

---

## EP05 - AI Review Engine

### US-05.1 🔴 Logic Agent - Detectar Bugs de Lógica
**Como** engine,
**Quero** enviar o diff para IA e detectar bugs de lógica,
**Para** encontrar problemas que análise estática não captura.

**Critérios de Aceite**:
- **CA1**: Dado um diff com acesso a propriedade de objeto possivelmente null, quando o Logic Agent analisa, então detecta NullReferenceException potencial.
- **CA2**: Dado um `while(true)` sem break/return, então detecta loop infinito.
- **CA3**: Dado um `catch {}` vazio, então detecta exception swallowing.
- **CA4**: A IA retorna JSON estruturado com file, line, severity, category, message, suggestion.
- **CA5**: A IA analisa APENAS linhas do diff, não o arquivo inteiro.
- **CA6**: Tempo de resposta < 30 segundos por arquivo.

**SP**: 8

---

### US-05.2 🟡 Security Agent - Detectar Vulnerabilidades
**Como** engine,
**Quero** um agente especializado em segurança,
**Para** detectar vulnerabilidades antes que cheguem a produção.

**Critérios de Aceite**:
- **CA1**: Detecta SQL Injection (string concatenation em queries).
- **CA2**: Detecta secrets hardcoded (padrões de API key, password, connection string).
- **CA3**: Detecta XSS potencial (output sem sanitização).
- **CA4**: Detecta Mass Assignment (bind direto de request para entity).
- **CA5**: Retorna JSON estruturado no mesmo formato do Logic Agent.

**SP**: 5

---

### US-05.3 🟡 Performance Agent - Detectar Problemas de Performance
**Como** engine,
**Quero** um agente especializado em performance,
**Para** detectar código ineficiente.

**Critérios de Aceite**:
- **CA1**: Detecta N+1 queries (query dentro de loop).
- **CA2**: Detecta LINQ dentro de foreach/for.
- **CA3**: Detecta `ToList()` seguido de filtro (materialização prematura).
- **CA4**: Detecta `SELECT *` (falta de projeção).
- **CA5**: Detecta string concatenação em loop (sugerir StringBuilder).

**SP**: 5

---

### US-05.4 🔴 Configurar Provider de IA
**Como** administrador,
**Quero** configurar qual modelo de IA usar,
**Para** usar Gemini (licença corporativa) ou Ollama (local).

**Critérios de Aceite**:
- **CA1**: Dado `provider: gemini` no config, quando o engine executa, então usa API do Gemini.
- **CA2**: Dado `provider: ollama` no config, quando o engine executa, então usa Ollama local.
- **CA3**: Dado `fallback: ollama`, quando Gemini falha, então tenta Ollama automaticamente.
- **CA4**: API key pode ser configurada via variável de ambiente (`CODE_GUARDIAN_API_KEY`) ou config.
- **CA5**: Se nenhum provider está acessível, o engine executa apenas Rule Engine + Roslyn.

**SP**: 5

---

### US-05.5 🟢 Feedback Loop para Melhorar Prompts
**Como** tech lead,
**Quero** marcar issues da IA como falso positivo,
**Para** melhorar a precisão ao longo do tempo.

**Critérios de Aceite**:
- **CA1**: No output do CLI, cada issue tem um ID único.
- **CA2**: `code-guardian feedback <issue-id> false-positive` marca como falso positivo.
- **CA3**: Falsos positivos são armazenados e usados para refinar prompts futuros.

**SP**: 8

---

## EP06 - Issue Aggregator

### US-06.1 🔴 Consolidar Issues de Múltiplas Fontes
**Como** engine,
**Quero** unificar issues do Rule Engine, Roslyn e IA num formato único,
**Para** apresentar resultado consolidado e coerente.

**Critérios de Aceite**:
- **CA1**: Todas as issues têm o mesmo formato: id, file, line, severity, category, message, suggestion, source.
- **CA2**: Issues duplicadas (mesma linha + mesmo tipo) são mescladas.
- **CA3**: Issues são ordenadas por severidade (critical primeiro) e depois por arquivo.

**SP**: 3

---

### US-06.2 🟡 Calcular Risk Score
**Como** tech lead,
**Quero** um score numérico de risco da PR,
**Para** decidir rapidamente se precisa de review humano detalhado.

**Critérios de Aceite**:
- **CA1**: Score calculado com pesos: critical=25, error=10, warning=3, info=1.
- **CA2**: Score é classificado: 0-10 ✅ | 11-30 ⚠️ | 31-60 🔴 | >60 🚫.
- **CA3**: Score é exibido no terminal e no comentário da PR.

**SP**: 2

---

## EP07 - TFS/Azure DevOps Integration

### US-07.1 🔴 Comentar Inline na PR
**Como** pipeline TFS,
**Quero** publicar cada issue como comentário na linha exata do código na PR,
**Para** que o desenvolvedor veja o problema no contexto certo.

**Critérios de Aceite**:
- **CA1**: Dado uma issue na linha 82 de `PedidoService.cs`, quando o integrador publica, então cria thread no Azure DevOps na linha 82 do arquivo na PR.
- **CA2**: O comentário contém severity, category, message e suggestion.
- **CA3**: Issues de severidade different usam ícones visuais distintos.
- **CA4**: Usa API `/_apis/git/repositories/{repo}/pullRequests/{id}/threads` com `threadContext.filePath` e `rightFileStart.line`.

**SP**: 5

---

### US-07.2 🔴 Publicar Resumo na PR
**Como** pipeline TFS,
**Quero** publicar um comentário resumo no topo da PR,
**Para** dar visão geral do review.

**Critérios de Aceite**:
- **CA1**: Comentário resumo contém: Risk Score, contagem por severidade, lista de issues críticas.
- **CA2**: Publicado como primeiro comentário (sem threadContext = comentário geral).
- **CA3**: Inclui link para detalhes e versão do Code Guardian.

**SP**: 3

---

### US-07.3 🟡 Atualizar Status da PR
**Como** pipeline TFS,
**Quero** atualizar o status da PR baseado no resultado,
**Para** bloquear merge automaticamente se houver issues críticas.

**Critérios de Aceite**:
- **CA1**: Dado risk score < threshold configurado, quando o review passa, então status = "succeeded".
- **CA2**: Dado risk score >= threshold, então status = "failed" e build falha.
- **CA3**: Usa API de PR Status do Azure DevOps.

**SP**: 3

---

### US-07.4 🟡 Pipeline YAML de Referência
**Como** tech lead,
**Quero** um template de pipeline YAML pronto para usar,
**Para** integrar o Code Guardian no meu repositório em minutos.

**Critérios de Aceite**:
- **CA1**: Template YAML funciona com Azure DevOps Server (TFS) e Azure DevOps Services.
- **CA2**: Configura Python, instala dependências, executa review, publica resultados.
- **CA3**: Variáveis necessárias documentadas (AZDO_ORG, AZDO_PAT, etc.).
- **CA4**: Suporta Windows e Linux agents.

**SP**: 3

---

## EP08 - CLI Local

### US-08.1 🔴 Comando Review Básico
**Como** desenvolvedor,
**Quero** executar `code-guardian review` no terminal,
**Para** ver problemas antes de criar a PR.

**Critérios de Aceite**:
- **CA1**: Executa análise dos arquivos alterados vs branch base.
- **CA2**: Output colorido no terminal com ícones de severidade.
- **CA3**: Mostra arquivo, linha e descrição de cada issue.
- **CA4**: Exibe risk score e resumo ao final.
- **CA5**: Exit code: 0 = ok, 1 = issues encontradas (conforme `fail_on`).

**SP**: 5

---

### US-08.2 🟡 Git Hook de Pré-Push
**Como** desenvolvedor,
**Quero** que o review rode automaticamente no `git push`,
**Para** não esquecer de revisar.

**Critérios de Aceite**:
- **CA1**: `code-guardian hooks install` cria hook em `.git/hooks/pre-push`.
- **CA2**: `code-guardian hooks uninstall` remove o hook.
- **CA3**: O hook executa `code-guardian review --fail-on error`.
- **CA4**: Push é bloqueado se houver issues com severidade >= `fail_on`.

**SP**: 3

---

### US-08.3 🟢 Modo Watch (Análise Contínua)
**Como** desenvolvedor,
**Quero** que o Code Guardian analise automaticamente quando salvo um arquivo,
**Para** ter feedback em tempo real.

**Critérios de Aceite**:
- **CA1**: `code-guardian watch` monitora alterações em arquivos .cs.
- **CA2**: Ao salvar, executa apenas Rule Engine (sem IA, para ser rápido).
- **CA3**: Mostra issues em tempo real no terminal.

**SP**: 5

---

## EP09 - Métricas e Histórico

### US-09.1 🟢 Armazenar Histórico de Reviews
**Como** tech lead,
**Quero** armazenar o resultado de cada review,
**Para** analisar tendências de qualidade.

**Critérios de Aceite**:
- **CA1**: Cada execução salva resultado em SQLite local (`~/.code-guardian/history.db`).
- **CA2**: Dados incluem: timestamp, repository, branch, author, risk score, issues.
- **CA3**: `code-guardian stats` mostra resumo dos últimos 30 dias.

**SP**: 5

---

### US-09.2 🟢 Exportar Métricas
**Como** gestor,
**Quero** exportar dados de reviews para análise externa,
**Para** criar dashboards e relatórios de qualidade.

**Critérios de Aceite**:
- **CA1**: `code-guardian export --format csv` exporta histórico.
- **CA2**: `code-guardian export --format json` exporta em JSON.
- **CA3**: Filtros por data, repositório e autor.

**SP**: 3

---

## EP10 - Configuração por Projeto

### US-10.1 🔴 Inicializar Configuração
**Como** desenvolvedor,
**Quero** criar um arquivo de configuração facilmente,
**Para** começar a usar o Code Guardian no meu projeto.

**Critérios de Aceite**:
- **CA1**: `code-guardian init` cria `.code-guardian.yml` com configuração padrão.
- **CA2**: O comando é interativo: pergunta provider de IA, branch base, extensões.
- **CA3**: Se `.code-guardian.yml` já existe, pergunta se quer sobrescrever.

**SP**: 3

---

### US-10.2 🟡 Configurar Provider via CLI
**Como** desenvolvedor,
**Quero** configurar a API key sem editar arquivo,
**Para** setup mais rápido e seguro.

**Critérios de Aceite**:
- **CA1**: `code-guardian config set api-key <key>` salva em `~/.code-guardian/config.yml` (não no projeto).
- **CA2**: Variável de ambiente `CODE_GUARDIAN_API_KEY` tem precedência sobre arquivo.
- **CA3**: A API key nunca é logada ou exibida no terminal.

**SP**: 2

---

## Priorização por Fase

### Fase 1 - MVP
| US | Título | SP |
|----|--------|----|
| US-02.1 | Extrair Diff entre Branches | 5 |
| US-02.2 | Extrair Diff de Staged Files | 3 |
| US-03.1 | Executar Regras Built-in | 5 |
| US-05.1 | Logic Agent - Detectar Bugs | 8 |
| US-05.4 | Configurar Provider de IA | 5 |
| US-06.1 | Consolidar Issues | 3 |
| US-08.1 | Comando Review Básico | 5 |
| US-10.1 | Inicializar Configuração | 3 |
| **Total** | | **37** |

### Fase 2 - TFS Integration
| US | Título | SP |
|----|--------|----|
| US-07.1 | Comentar Inline na PR | 5 |
| US-07.2 | Publicar Resumo na PR | 3 |
| US-07.3 | Atualizar Status da PR | 3 |
| US-07.4 | Pipeline YAML de Referência | 3 |
| US-05.2 | Security Agent | 5 |
| US-05.3 | Performance Agent | 5 |
| US-06.2 | Calcular Risk Score | 2 |
| **Total** | | **26** |

### Fase 3 - Análise Profunda
| US | Título | SP |
|----|--------|----|
| US-04.1 | Executar Build com Analyzers | 5 |
| US-03.2 | Regras Customizadas | 3 |
| US-03.3 | Regras com Contexto | 5 |
| US-08.2 | Git Hook de Pré-Push | 3 |
| US-02.3 | Filtrar por Extensão | 2 |
| US-01.2 | Configuração Padrão | 2 |
| US-10.2 | Configurar Provider via CLI | 2 |
| **Total** | | **22** |

### Fase 4 - Métricas e Evolução
| US | Título | SP |
|----|--------|----|
| US-09.1 | Armazenar Histórico | 5 |
| US-09.2 | Exportar Métricas | 3 |
| US-05.5 | Feedback Loop | 8 |
| US-08.3 | Modo Watch | 5 |
| US-04.2 | Instalar Analyzers Auto | 3 |
| **Total** | | **24** |
