# Changelog

Todas as mudanças relevantes do Code Guardian estão documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [1.0.11] - 2026-09-12

### Alterado

#### Python — `rule_engine.py`
- **`NARRATIVE_COMMENT` passa de severidade `warning` para `error`** (bloqueia o Stop hook por padrão, `--fail-on error`), a pedido do usuário do harness — quer que comentário-sem-substância (narra o quê, não o porquê) seja tratado como violação bloqueante, não só um aviso no relatório, assumindo o risco de falso positivo inerente à heurística (regex, não NLP). Escape hatch inalterado: `// guardian: suppress NARRATIVE_COMMENT` na linha anterior à flagrada.
- Corrigido em conjunto: o gate interno de `analyze_file()` que decide se `_detect_narrative_comments()` roda dependendo de `--severity` estava comparando contra o limiar de `"warning"` — ficou desalinhado da severidade real da issue após a mudança acima (com `--severity error`, o comentário deixaria de ser reportado mesmo já sendo `error`). Ajustado para comparar contra `"error"`.

Testes atualizados: `TC-RE-029` (agora espera exit 1) e `TC-RE-030` (agora espera `NARRATIVE_COMMENT` presente com `--severity error`) em `tests/run_tests.py` — suíte completa: 83/83 passando.

---

## [1.0.10] - 2026-09-12

### Adicionado

#### Python — `metrics.py`
- **Detecção de duplicação literal de métodos** (categoria "Duplicação", severidade `error` — bloqueia por padrão, ao contrário das demais métricas que são `warning`/`info`): cada método com 5+ linhas de código ganha um `body_hash` (SHA-256 do corpo normalizado, sem a linha de assinatura nem espaços supérfluos); dois métodos com hash idêntico no mesmo arquivo geram issue citando os dois nomes e linhas. Detecta cópia/cola literal, não duplicação estrutural com variáveis renomeadas (exigiria parser real; ficaria com falso-positivo alto demais para uma checagem determinística). Só compara métodos dentro do mesmo arquivo — duplicação entre arquivos diferentes não é detectada nesta versão.

#### Python — `rule_engine.py`
- **`NARRATIVE_COMMENT` — comentário sem substância** (severidade `warning`, nunca bloqueia por padrão): heurística para comentários `//` (não `///`, que são doc comments legítimos) que só narram O QUE o código faz em vez de justificar O PORQUÊ. Dois sinais, cada um suficiente: (1) abre com frase narrativa clássica ("this function...", "este método..."); (2) alta sobreposição de palavras (≥60%) com a linha de código imediatamente seguinte. Comentários com marcador de "porquê" (`workaround`, `porque`, `nota:`, etc.) ou já cobertos por `TODO_COMMENT`/`FIXME_COMMENT`/`HACK_COMMENT` são ignorados. É heurística, não NLP — falso-positivo/negativo esperado, por isso a severidade nunca bloqueia o Stop hook por padrão (`--fail-on error`).

Fixtures novas: `tests/fixtures/duplicate_methods.cs`, `tests/fixtures/narrative_comments.cs`. 13 casos de teste novos em `tests/run_tests.py` (TC-ME-015..019, TC-RE-026..031) — suíte completa: 83/83 passando.

## [1.0.9] - 2026-05-15

### Corrigido

#### Python — `vb6_rule_engine.py`
- **VB6_MISSING_ERROR_HANDLER — falsos positivos em métodos de ciclo de vida**:
  `Class_Initialize` e `Class_Terminate` não exigem mais `On Error GoTo ErrNomeMetodo`
  — Initialize tipicamente só atribui variáveis privadas; Terminate usa o padrão
  `On Error Resume Next` para liberar objetos com segurança
- **VB6_ON_ERROR_RESUME_NEXT_UNSAFE — falso positivo em Class_Terminate**:
  `On Error Resume Next` dentro de `Class_Terminate` não é mais flagrado como inseguro
  — é o padrão aceito para `Set obj = Nothing` na finalização da classe

---

## [1.0.8] - 2026-05-15

### Corrigido

#### Python — `vb6_rule_engine.py`
- **VB6_INFINITE_LOOP — falso positivo eliminado**: `Do...Loop While condition` e
  `Do...Loop Until condition` não são mais flagrados como loops infinitos. O detector
  agora faz look-ahead até o `Loop` correspondente (até 500 linhas, nesting correto)
  e só reporta quando o `Loop` não tem condição **e** não há `Exit Do` no bloco
- **Diff inacurado — encoding VB6**: `_get_changed_lines` agora detecta encoding em
  ordem de preferência (UTF-8 BOM → UTF-8 → Windows-1252 → Latin-1) e normaliza
  terminadores de linha e espaços finais antes de comparar, eliminando falsos "linhas
  alteradas" causados por diferença de encoding entre arquivo base e revisado
- **`_filter_to_changed` — contexto de método**: issues reportadas no início de um
  método (ex.: `VB6_MISSING_ERROR_HANDLER`) agora são incluídas quando qualquer linha
  desse método foi alterada; issues de nível de arquivo (linha ≤ 1) são sempre incluídas
- **`_filter_to_changed` — score incorreto**: o cálculo anterior acumulava a penalidade
  por cada ocorrência de uma mesma regra; corrigido para usar `_calculate_score`
  (uma penalidade por `rule_id`, consistente com a análise completa)

#### Python — `vb6_compare.py`
- `--diff-only` agora é o comportamento **padrão** no modo de comparação de diretórios
  — apenas issues nas linhas efetivamente alteradas são reportadas
- Adicionado flag `--all-issues` para quem precisar do comportamento anterior (todas
  as issues do arquivo)

#### Executável — `build_exe.py`
- Corrigido `UnicodeEncodeError` ao imprimir `✓` no terminal Windows com codepage 1252

---

## [1.0.7] - 2026-05-04

### Corrigido
- Hook `pre-commit` instalado com caminho `.guardian/` (template desatualizado) corrigido para `.codeguardian/`
- `build-release.ps1` não incluía scripts Python no VSIX gerado manualmente — corrigido

### Adicionado
- Relatório HTML do commit (`last-commit-report.html`) agora é auto-estagiado pelo hook e rastreado pelo git,
  permitindo que revisores acessem o relatório diretamente no repositório
- `HookInstallService`: detecção automática de hook desatualizado via sentinela de versão —
  hooks antigos são re-instalados silenciosamente na próxima abertura do VS
- Flag `--diff-filter=d` no hook `pre-commit` para ignorar arquivos deletados no staged diff

---

## [1.0.6] - 2026-04-26

### Adicionado
- Extensão VS Code: scaffold MVP (TypeScript) com painel WebView, análise de arquivo/solution/incremental,
  DiagnosticCollection, on-save automático, git hooks e 13 configurações via `package.json`

### Alterado
- Diretório de saídas renomeado de `.guardian/` para `.codeguardian/` em todo o projeto
  (runner.py, vb6_rule_engine.py, install_hooks.py, HookInstallService.cs, SarifReportGenerator.cs,
  GuardianToolWindowViewModel.cs, docs, skills, .gitignore)

---

## [1.0.5] - 2026-04-26

### Adicionado

#### Extensão Visual Studio
- `PythonLocator.cs` — centraliza a descoberta do Python (candidates + bundled scripts fallback)
- `SarifReportGenerator.cs` — geração de relatório SARIF 2.1.0 compatível com GitHub Security e Azure DevOps
- `ExportSarifCommand.cs` — comando "Code Guardian: Exportar SARIF" no menu Tools
- Botão **Limpar** no Tool Window para resetar o estado da análise
- Botão **Exportar SARIF** no Tool Window com abertura automática da pasta `.codeguardian/`
- Clique em issue navega diretamente para a linha no editor (`ListBoxIssues_SelectionChanged`)
- Botão **Copiar** por issue (copia issue formatado para clipboard)
- Botão **Suprimir** por issue (insere `// guardian: suppress RULE_ID` acima da linha)
- Fallback para scripts bundlados quando o projeto não contém `code_guardian/`

#### Python — `rule_engine.py`
- Supressão em nível de arquivo: `// guardian: file-suppress RULE_ID` nas primeiras 30 linhas
- Supressão em linha aceita agora `///` (XML doc comments), atributos `[...]` e linhas em branco entre o comentário e a declaração
- Extração de múltiplos IDs por vírgula: `// guardian: suppress RULE1,RULE2`

#### Python — `metrics.py`
- `_is_code_line()` — distingue linhas de código de comentários e linhas vazias
- Contagem de linhas de método usa apenas linhas de código (ignora `///`, `//`, `*`, vazias)
- Detecção de "arquivo grande" baseada em linhas de código, não total de linhas
- Campo `code_lines` no resultado de métricas de classe

#### Documentação
- `README.md` — documentação principal da extensão Visual Studio
- `docs/AVALIACAO-VSCODE-EXTENSION.md` — análise técnica completa para portabilidade ao VS Code (estimativas, comparação de APIs, fases de desenvolvimento)
- `docs/GUIA-DESENVOLVEDOR.md` — guia do desenvolvedor com arquitetura e fluxos internos
- Marketplace description atualizada com novos recursos

### Corrigido
- `DependencyChecker.cs` — delegado para `PythonLocator.ObterCandidatos()` em vez de duplicar lógica
- `DependencyChecker.cs` — scripts do projeto têm prioridade sobre scripts bundlados
- Supressão de issues não reconhecia comentários `///` nem atributos `[...]` entre suppress e declaração

### Removido
- `erro.png` — imagem de debug temporária removida do repositório

---

## [1.0.4] - 2026-04-22

### Adicionado
- Filtro de arquivos deletados na análise staged
- Integração de IA via Options (configuração de provider, API keys, modelo)
- Otimizações de performance no carregamento do Tool Window

### Corrigido
- Análise staged incluía arquivos deletados causando erro no runner
- Botão "Analisar Arquivo" e "Analisar Solution" na tela principal

---

## [1.0.3] - 2026-04-20

### Adicionado
- Melhorias na interface do Tool Window
- Análise de dependências com status visual (Python, runner.py, git)
- Suporte a análise de VB6 via `vb6_rule_engine.py`

---

## [1.0.0] - 2026-04-10

### Adicionado
- Versão inicial da extensão Visual Studio 2022
- Rule Engine com 20+ regras (SQL Injection, deadlocks, secrets, Clean Code)
- Métricas de código (tamanho de métodos, nesting, God Class)
- Risk Score 0–100 com gauge colorido
- Tool Window com filtros por severidade e texto livre
- Integração com Error List do Visual Studio
- Suporte a análise de arquivo, solution e incremental (git diff)
- Git hooks (`pre-commit`, `prepare-commit-msg`)
- Exportação de relatório HTML
- Suporte a múltiplos providers de IA (Gemini, Claude, OpenAI, Ollama)
