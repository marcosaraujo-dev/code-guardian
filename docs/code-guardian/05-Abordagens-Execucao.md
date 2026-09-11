# Abordagens de Execução - Code Guardian

## Resumo das 5 Abordagens

```
┌────────────────────────────────────────────────────────────────────────┐
│                    CANAIS DE EXECUÇÃO                                  │
│                                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ 1. CLI       │  │ 2. TFS       │  │ 3. Claude    │                │
│  │    Python    │  │    Pipeline  │  │    Code Skill│                │
│  │              │  │              │  │              │                │
│  │ Terminal     │  │ Branch Policy│  │ /code-review │                │
│  │ local        │  │ auto na PR   │  │ dentro IDE   │                │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │
│         │                 │                 │                         │
│         └─────────────────┼─────────────────┘                        │
│                           ▼                                           │
│                  ┌────────────────┐                                   │
│                  │ CODE GUARDIAN  │                                   │
│                  │ ENGINE (core)  │                                   │
│                  └────────────────┘                                   │
│                           │                                           │
│         ┌─────────────────┼─────────────────┐                        │
│         ▼                 ▼                 ▼                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ 4. Git Hook  │  │ 5. Docker    │  │ 6. Extensão  │                │
│  │    pre-push  │  │    Container │  │    TFS       │                │
│  │              │  │              │  │    (futuro)  │                │
│  │ Automático   │  │ Consistente  │  │ Marketplace  │                │
│  │ no push      │  │ qualquer env │  │ visual       │                │
│  └──────────────┘  └──────────────┘  └──────────────┘                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Abordagem 1: CLI Python (Local)

**Uso**: Desenvolvedor executa manualmente no terminal.

```bash
# Instalar
pip install code-guardian

# Executar
code-guardian review
code-guardian review --staged
code-guardian review --rules-only
code-guardian review --model ollama
```

**Prós**: Simples, rápido, funciona offline (com Ollama)
**Contras**: Depende do dev lembrar de executar

**Quando usar**: Durante desenvolvimento, antes de criar a PR.

---

## Abordagem 2: Pipeline TFS/Azure DevOps

**Uso**: Automático, dispara quando PR é criada.

```yaml
# azure-pipelines-code-guardian.yml
trigger: none
pr:
  branches:
    include: [main, develop]

steps:
  - checkout: self
    fetchDepth: 0
  - task: UsePythonVersion@0
    inputs: { versionSpec: '3.11' }
  - script: pip install code-guardian
  - script: python -m code_guardian.runner --mode tfs
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
      CODE_GUARDIAN_API_KEY: $(GEMINI_API_KEY)
```

**Prós**: Automático, sem esforço do dev, comentários inline na PR
**Contras**: Requer config no TFS, depende de network para IA

**Quando usar**: Garantia em toda PR, gate obrigatório.

---

## Abordagem 3: Skill do Claude Code (/code-review)

**Uso**: Desenvolvedor executa `/code-review` dentro do Claude Code (IDE).

Esta é uma abordagem muito poderosa porque o Claude Code já tem acesso ao código, pode ler arquivos, executar scripts e gerar output formatado diretamente na conversa.

### Como Funciona

```
Desenvolvedor no Claude Code:
  │
  │ /code-review
  │ /code-review Services/PedidoService.cs
  │ /code-review --staged
  │
  ▼
┌────────────────────────────────────────────────┐
│ SKILL: code-review                              │
│                                                  │
│ 1. Detectar modo (staged, arquivo, diff)         │
│ 2. Executar scripts Python via Bash tool         │
│    $ python scripts/rule_engine.py <arquivo>     │
│    $ python scripts/diff_parser.py               │
│ 3. O próprio Claude analisa com IA (sem API ext) │
│ 4. Consolida e formata resultado                 │
│                                                  │
│ VANTAGEM: O Claude Code É o AI reviewer!         │
│ Não precisa chamar Gemini/Ollama externo.         │
│ O modelo já está rodando na conversa.            │
└────────────────────────────────────────────────┘
```

### SKILL.md Proposta

```markdown
---
name: code-review
description: Executa Code Review automatizado com análise de lógica, padrões,
  segurança e performance. Combina scripts de Rule Engine com análise de IA
  do próprio Claude. Use quando quiser revisar código, detectar bugs de lógica,
  verificar padrões ou quando o usuário pedir code review, análise de PR ou
  revisão de código.
---

# Code Review Automatizado

## Fluxo de Execução

### Passo 1: Determinar Escopo
- Se argumento é um arquivo: analisar apenas esse arquivo
- Se `--staged`: executar `git diff --cached --name-only` e filtrar .cs
- Se sem argumentos: executar `git diff origin/main...HEAD --name-only` e filtrar .cs
- Excluir: Migrations, Designer.cs, obj/, bin/, Tests/

### Passo 2: Executar Rule Engine (Script Python)
Executar via Bash tool:
```bash
python scripts/code_guardian/rule_engine.py <arquivo> --format json
```

O script retorna JSON com issues de padrões:
```json
[
  {"file": "Service.cs", "line": 45, "severity": "error",
   "category": "TASK_RESULT", "message": "Task.Result pode causar deadlock"}
]
```

### Passo 3: Análise de IA (o próprio Claude)
Para cada arquivo alterado, ler o conteúdo via Read tool e analisar:

**Checklist de Análise de Lógica**:
- [ ] NullReferenceException potencial (acesso sem null-check)
- [ ] Loops infinitos (while sem condição de saída)
- [ ] Deadlocks async (Task.Result, .Wait(), async void)
- [ ] Race conditions (shared state sem lock/semaphore)
- [ ] IDisposable não disposto (falta using/Dispose)
- [ ] Exception swallowing (catch vazio ou genérico)
- [ ] Off-by-one errors (< vs <=, índices de array)
- [ ] Condições sempre true/false (código morto)
- [ ] Dependência circular entre classes

**Checklist de Segurança**:
- [ ] SQL Injection (concatenação em queries)
- [ ] Secrets hardcoded (API keys, passwords, connection strings)
- [ ] Mass Assignment (bind direto request → entity)
- [ ] XSS (output não sanitizado)

**Checklist de Performance**:
- [ ] N+1 queries (query dentro de loop)
- [ ] LINQ dentro de foreach/for
- [ ] ToList() antes de filtrar
- [ ] String concatenação em loop (usar StringBuilder)
- [ ] Falta de CancellationToken em async
- [ ] SELECT * (falta de projeção)

**Checklist de Padrões** (conforme rules do projeto):
- [ ] Result Pattern usado nos Services
- [ ] NotificationContext acumula TODOS os erros
- [ ] Logging presente (LogInfo, LogError)
- [ ] Métodos <= 30 linhas
- [ ] Nesting <= 3 níveis
- [ ] Nomenclatura correta (PascalCase classes, camelCase vars)
- [ ] Sem Magic Numbers
- [ ] Sem dependências pagas

### Passo 4: Calcular Risk Score
```
critical = 25pts, error = 10pts, warning = 3pts, info = 1pt
0-10: ✅ Baixo | 11-30: ⚠️ Moderado | 31-60: 🔴 Alto | >60: 🚫 Crítico
```

### Passo 5: Gerar Relatório

Formato de saída:
```markdown
# 🛡️ Code Guardian - Review

**Escopo**: [arquivos analisados]
**Risk Score**: [score com ícone]

## Resumo
| Severidade | Qtd |
|-----------|-----|
| 🔴 Critical | X |
| 🟠 Error | X |
| 🟡 Warning | X |
| 🔵 Info | X |

## Issues Encontradas

### 🔴 [Categoria] - [Arquivo:Linha]
**Problema**: [descrição]
**Código atual**:
```csharp
// código problemático
```
**Sugestão de correção**:
```csharp
// código corrigido
```

## Métricas
| Arquivo | Linhas/Método (max) | Nesting (max) | Deps |
|---------|-------|---------|------|
| file.cs | 45 🔴 | 5 🔴 | 3 ✅ |
```
```

### Scripts Python para a Skill

A skill utiliza scripts Python leves que rodam via `Bash tool` do Claude Code:

#### `scripts/code_guardian/rule_engine.py`
```python
#!/usr/bin/env python3
"""Rule Engine - Detecta padrões problemáticos em arquivos C#."""
import sys
import json
import re

RULES = [
    {
        "id": "NO_CONSOLE_WRITE",
        "pattern": "Console.WriteLine",
        "message": "Evite Console.WriteLine em produção. Use ILogger.",
        "severity": "warning"
    },
    {
        "id": "NO_THREAD_SLEEP",
        "pattern": "Thread.Sleep",
        "message": "Thread.Sleep bloqueia a thread. Use Task.Delay.",
        "severity": "error"
    },
    {
        "id": "NO_TASK_RESULT",
        "pattern": ".Result",
        "pattern_context": "Task|await",
        "message": "Task.Result pode causar deadlock. Use await.",
        "severity": "error"
    },
    {
        "id": "NO_TASK_WAIT",
        "pattern": ".Wait()",
        "message": "Task.Wait() pode causar deadlock. Use await.",
        "severity": "error"
    },
    {
        "id": "NO_ASYNC_VOID",
        "pattern_regex": r"async\s+void\s+(?!.*EventHandler)",
        "message": "async void perde exceções. Use async Task.",
        "severity": "error"
    },
    {
        "id": "NO_EMPTY_CATCH",
        "pattern_regex": r"catch\s*(\(\s*\))?\s*\{[\s\n]*\}",
        "message": "Catch vazio engole exceções. Sempre log ou re-throw.",
        "severity": "error"
    },
    {
        "id": "SQL_INJECTION",
        "pattern_regex": r'"\s*SELECT\s.*\+|"\s*INSERT\s.*\+|"\s*UPDATE\s.*\+|"\s*DELETE\s.*\+|\$".*SELECT.*\{',
        "message": "Possível SQL Injection! Use queries parametrizadas.",
        "severity": "critical"
    },
    {
        "id": "NO_HARDCODED_SECRET",
        "pattern_regex": r'(password|pwd|secret|apikey|api_key|connectionstring)\s*=\s*"[^"]{8,}"',
        "message": "Possível secret hardcoded. Use variáveis de ambiente ou Secret Manager.",
        "severity": "critical"
    },
    {
        "id": "NO_TODO",
        "pattern": "// TODO",
        "message": "TODO encontrado. Resolver antes de mergear ou criar issue.",
        "severity": "info"
    },
    {
        "id": "NO_MAGIC_NUMBER",
        "pattern_regex": r"[=<>!]+\s*\d{3,}(?!\s*(px|em|rem|ms|MB|GB|KB))",
        "message": "Possível magic number. Extrair para constante nomeada.",
        "severity": "warning"
    }
]

def analyze_file(file_path: str) -> list[dict]:
    """Analisa um arquivo C# e retorna issues encontradas."""
    issues = []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return [{"file": file_path, "line": 0, "severity": "error",
                 "category": "FILE_NOT_FOUND", "message": f"Arquivo não encontrado: {file_path}"}]

    content = "".join(lines)

    for rule in RULES:
        if "pattern_regex" in rule:
            for match in re.finditer(rule["pattern_regex"], content, re.IGNORECASE):
                line_num = content[:match.start()].count("\n") + 1
                # Verificar se está dentro de comentário ou string
                line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                if line_content.startswith("//") or line_content.startswith("*"):
                    continue
                issues.append({
                    "file": file_path,
                    "line": line_num,
                    "severity": rule["severity"],
                    "category": rule["id"],
                    "message": rule["message"],
                    "source": "rule_engine"
                })
        elif "pattern" in rule:
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                if rule["pattern"] in line:
                    issues.append({
                        "file": file_path,
                        "line": i,
                        "severity": rule["severity"],
                        "category": rule["id"],
                        "message": rule["message"],
                        "source": "rule_engine"
                    })

    return issues

def main():
    if len(sys.argv) < 2:
        print("Uso: python rule_engine.py <arquivo.cs> [--format json|text]", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    output_format = "json"

    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        if idx + 1 < len(sys.argv):
            output_format = sys.argv[idx + 1]

    issues = analyze_file(file_path)

    if output_format == "json":
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            icon = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}.get(issue["severity"], "⚪")
            print(f"{icon} {issue['file']}:{issue['line']} [{issue['category']}] {issue['message']}")

    sys.exit(1 if any(i["severity"] in ("critical", "error") for i in issues) else 0)

if __name__ == "__main__":
    main()
```

#### `scripts/code_guardian/diff_parser.py`
```python
#!/usr/bin/env python3
"""Diff Parser - Extrai arquivos e linhas alterados do git diff."""
import subprocess
import sys
import json
import re

def get_changed_files(mode: str = "branch", base: str = "origin/main") -> list[str]:
    """Retorna lista de arquivos .cs alterados."""
    if mode == "staged":
        cmd = ["git", "diff", "--cached", "--name-only"]
    else:
        subprocess.run(["git", "fetch", "origin", "main"], check=False, capture_output=True)
        cmd = ["git", "diff", f"{base}...HEAD", "--name-only"]

    result = subprocess.check_output(cmd).decode().splitlines()
    return [f for f in result if f.endswith(".cs")
            and "/Migrations/" not in f
            and ".Designer.cs" not in f
            and "/obj/" not in f
            and "/bin/" not in f]

def parse_diff(mode: str = "branch", base: str = "origin/main") -> list[dict]:
    """Parseia o diff e retorna mudanças por arquivo com número de linha."""
    if mode == "staged":
        cmd = ["git", "diff", "--cached"]
    else:
        cmd = ["git", "diff", f"{base}...HEAD"]

    diff = subprocess.check_output(cmd).decode()
    changes = []
    current_file = None
    line_number = 0

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.replace("+++ b/", "")

        match = re.match(r"@@ .* \+(\d+)", line)
        if match:
            line_number = int(match.group(1))

        elif line.startswith("+") and not line.startswith("+++"):
            if current_file and current_file.endswith(".cs"):
                changes.append({
                    "file": current_file,
                    "line": line_number,
                    "content": line[1:],
                    "type": "added"
                })
            line_number += 1

        elif not line.startswith("-"):
            line_number += 1

    return changes

def main():
    mode = "branch"
    base = "origin/main"

    if "--staged" in sys.argv:
        mode = "staged"
    if "--base" in sys.argv:
        idx = sys.argv.index("--base")
        if idx + 1 < len(sys.argv):
            base = sys.argv[idx + 1]

    if "--files-only" in sys.argv:
        files = get_changed_files(mode, base)
        print(json.dumps(files, ensure_ascii=False, indent=2))
    else:
        changes = parse_diff(mode, base)
        print(json.dumps(changes, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

#### `scripts/code_guardian/metrics.py`
```python
#!/usr/bin/env python3
"""Metrics - Calcula métricas de código C#."""
import sys
import json
import re

def analyze_metrics(file_path: str) -> dict:
    """Calcula métricas de um arquivo C#."""
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    content = "".join(lines)

    # Contar métodos e suas linhas
    method_pattern = re.compile(
        r'(public|private|protected|internal)\s+(static\s+)?(async\s+)?'
        r'(Task<[^>]+>|Task|void|[A-Z]\w+<?[^>]*>?)\s+(\w+)\s*\('
    )

    methods = []
    max_nesting = 0
    current_nesting = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Contar nesting
        current_nesting += stripped.count("{") - stripped.count("}")
        max_nesting = max(max_nesting, current_nesting)

        # Detectar métodos
        match = method_pattern.search(stripped)
        if match:
            methods.append({"name": match.group(5), "start_line": i})

    # Contar linhas por método (aproximado)
    for j, method in enumerate(methods):
        end = methods[j + 1]["start_line"] if j + 1 < len(methods) else len(lines)
        method_lines = end - method["start_line"]
        method["lines"] = method_lines

    # Contar dependências (injeção via construtor)
    constructor_deps = len(re.findall(
        r'private\s+readonly\s+I\w+\s+_\w+', content
    ))

    return {
        "file": file_path,
        "total_lines": len(lines),
        "method_count": len(methods),
        "max_method_lines": max(m["lines"] for m in methods) if methods else 0,
        "max_nesting": max_nesting,
        "constructor_deps": constructor_deps,
        "methods": [{"name": m["name"], "lines": m["lines"]} for m in methods],
        "issues": [
            *[{"severity": "error", "message": f"Método '{m['name']}' tem {m['lines']} linhas (max: 30)",
               "line": m["start_line"]}
              for m in methods if m["lines"] > 30],
            *([{"severity": "error", "message": f"Nesting máximo de {max_nesting} (max: 3)",
                "line": 1}] if max_nesting > 3 else []),
            *([{"severity": "warning", "message": f"Classe com {constructor_deps} dependências (max: 5) - possível God Class",
                "line": 1}] if constructor_deps > 5 else []),
        ]
    }

def main():
    if len(sys.argv) < 2:
        print("Uso: python metrics.py <arquivo.cs>", file=sys.stderr)
        sys.exit(1)

    result = analyze_metrics(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

### Vantagens da Abordagem Claude Code Skill

```
┌────────────────────────────────────────────────────────────────────┐
│           POR QUE A SKILL DO CLAUDE CODE É PODEROSA                │
│                                                                     │
│  1. O CLAUDE É O AI REVIEWER                                       │
│     → Não precisa chamar API externa (Gemini/Ollama)                │
│     → O modelo já está rodando na conversa                          │
│     → Análise de lógica mais profunda (contexto da conversa)        │
│     → Pode fazer perguntas ao dev se algo for ambíguo               │
│                                                                     │
│  2. ACESSO DIRETO AO CÓDIGO                                        │
│     → Read tool lê qualquer arquivo                                 │
│     → Grep tool busca padrões                                       │
│     → Glob tool encontra arquivos                                   │
│     → Bash tool executa scripts Python                              │
│                                                                     │
│  3. SCRIPTS PYTHON = SPEED                                          │
│     → Rule Engine roda em < 1 segundo                               │
│     → Métricas calculadas instantaneamente                          │
│     → Diff parser extrai mudanças sem IA                            │
│     → IA (Claude) analisa apenas o que os scripts não cobrem        │
│                                                                     │
│  4. INTERATIVO                                                      │
│     → Dev pode pedir para explicar uma issue                        │
│     → Dev pode pedir para corrigir o código                         │
│     → Dev pode pedir para ignorar uma issue (com justificativa)     │
│     → Feedback em tempo real na conversa                            │
│                                                                     │
│  5. JÁ CONHECE AS RULES DO PROJETO                                 │
│     → As 5 rules (.claude/rules/) são carregadas no contexto        │
│     → O Claude já sabe sobre Result Pattern, Logging, etc.          │
│     → Não precisa configurar prompts separados                      │
│                                                                     │
│  6. COMBINA COM OS AGENTES EXISTENTES                               │
│     → Pode delegar para senior-code-reviewer                        │
│     → Pode usar design-system-reviewer para XAML                    │
│     → Pode usar wpf-code-reviewer para WPF                         │
│     → Orquestração automática por tipo de arquivo                   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Fluxo Híbrido: Scripts + Claude IA

```
/code-review executado
        │
        ▼
┌───────────────────┐
│ Detectar escopo   │ (args, --staged, diff)
│ via Bash + Git    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Para cada .cs:    │
│                   │
│ 1. Bash: python   │ ← Executa rule_engine.py (< 1s)
│    rule_engine.py │    Retorna issues de padrões em JSON
│                   │
│ 2. Bash: python   │ ← Executa metrics.py (< 1s)
│    metrics.py     │    Retorna métricas (linhas/método, nesting)
│                   │
│ 3. Read tool:     │ ← Claude lê o código fonte
│    arquivo.cs     │
│                   │
│ 4. CLAUDE ANALISA │ ← O próprio Claude faz review de lógica:
│    (sem API ext)  │    • NullRef, deadlocks, loops, race cond.
│                   │    • Segurança, performance
│                   │    • Padrões do projeto (rules já no contexto)
│                   │
│ 5. Consolidar     │ ← Junta issues dos scripts + análise Claude
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Gerar relatório   │ → Output formatado na conversa
│ Risk Score        │ → Dev pode interagir ("corrija o item 3")
└───────────────────┘
```

---

## Abordagem 4: Git Hook (pre-push)

**Uso**: Automático antes de cada push.

```bash
# Instalar
code-guardian hooks install

# O que o hook faz:
#!/bin/sh
code-guardian review --fail-on error
if [ $? -ne 0 ]; then
    echo "❌ Code Guardian encontrou issues. Push bloqueado."
    exit 1
fi
```

**Prós**: Automático, sem esquecer
**Contras**: Pode ser lento (se usar IA), dev pode bypassar com `--no-verify`

---

## Abordagem 5: Docker Container

**Uso**: Ambiente consistente para TFS ou execução local.

```dockerfile
FROM python:3.11-slim

# Instalar .NET SDK (para Roslyn analyzers)
RUN apt-get update && apt-get install -y dotnet-sdk-8.0

# Instalar Code Guardian
RUN pip install code-guardian

ENTRYPOINT ["python", "-m", "code_guardian.runner"]
```

```bash
# Local
docker run -v $(pwd):/code code-guardian review

# TFS Pipeline
- script: docker run -v $(Build.SourcesDirectory):/code code-guardian --mode tfs
```

**Prós**: Ambiente idêntico local e TFS, inclui .NET SDK
**Contras**: Imagem grande (~2GB), requer Docker

---

## Comparativo das Abordagens

| Aspecto | CLI Python | TFS Pipeline | Claude Code Skill | Git Hook | Docker |
|---------|-----------|-------------|-------------------|----------|--------|
| **Setup** | `pip install` | YAML + config | Já pronto (skill) | `hooks install` | `docker pull` |
| **Automático** | ❌ Manual | ✅ Na PR | ❌ Manual (ou hook) | ✅ No push | Depende |
| **Velocidade** | Rápido | Médio | Rápido | Médio | Médio |
| **IA inclusa** | Via API | Via API | ✅ Claude nativo | Via API | Via API |
| **Offline** | Com Ollama | ❌ | ✅ (Claude local) | Com Ollama | Com Ollama |
| **Interativo** | ❌ | ❌ | ✅ Conversa | ❌ | ❌ |
| **Custo IA** | Gemini API | Gemini API | ✅ Zero (já pago) | Gemini API | Gemini API |
| **Comenta PR** | ❌ | ✅ Inline | ❌ | ❌ | ✅ se TFS |
| **Bloqueia merge** | ❌ | ✅ | ❌ | Bloqueia push | ✅ se TFS |

---

## Recomendação de Implementação por Fase

### Fase 1 (MVP) - Claude Code Skill + Scripts
```
1. Criar scripts Python (rule_engine.py, diff_parser.py, metrics.py)
2. Criar SKILL.md /code-review
3. Testar localmente com Claude Code
4. Já tem valor imediato sem infra adicional
```

**Justificativa**: Menor esforço, maior valor imediato. O Claude já é o AI reviewer, os scripts adicionam velocidade para detecções simples.

### Fase 2 - CLI Python + TFS Pipeline
```
1. Empacotar scripts como CLI (pip install)
2. Integrar com Gemini API
3. Criar pipeline YAML de referência
4. Configurar Branch Policy no TFS
```

### Fase 3 - Git Hooks + Refinamento
```
1. Implementar git hook pre-push
2. Adicionar Roslyn analyzer integration
3. Feedback loop (marcar falsos positivos)
4. Ollama como fallback
```

### Fase 4 - Métricas e Docker
```
1. Histórico em SQLite
2. Dashboard de tendências
3. Docker container para TFS
4. Extensão TFS (marketplace)
```
