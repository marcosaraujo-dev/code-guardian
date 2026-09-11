# runner.py — Orquestrador CLI Completo

## O que faz

Executa **todo o pipeline de review** em um único comando:
1. Detecta arquivos `.cs` (via diff, scan de diretório ou arquivo específico)
2. Executa `rule_engine.py` em cada arquivo
3. Executa `metrics.py` em cada arquivo
4. Executa `ai_client.py` para análise de IA (opcional)
5. Consolida todas as issues com Risk Score
6. Gera relatório em texto ou JSON

---

## Uso básico

```bash
# Analisar o diff completo vs origin/main
python code_guardian/runner.py

# Analisar apenas arquivos staged
python code_guardian/runner.py --staged

# Analisar um arquivo específico
python code_guardian/runner.py --file Services/UserService.cs

# Varrer todo o diretório atual recursivamente (todos os .cs)
python code_guardian/runner.py --scan

# Varrer um diretório específico
python code_guardian/runner.py --scan --dir C:/projetos/MinhaApp

# Apenas análise estática (sem IA, mais rápido)
python code_guardian/runner.py --rules-only

# Saída JSON para CI/CD
python code_guardian/runner.py --format json
```

---

## Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--file <path>` | string | — | Analisar arquivo específico (sem git diff) |
| `--scan` | flag | — | Varrer diretório recursivamente buscando todos os `.cs` |
| `--dir <path>` | string | `.` (atual) | Diretório raiz para `--scan` |
| `--staged` | flag | — | Analisar apenas arquivos em staging area |
| `--base <branch>` | string | `origin/main` | Branch base para comparação |
| `--rules-only` | flag | — | Pular análise de IA (mais rápido) |
| `--severity` | `critical`\|`error`\|`warning`\|`info` | `info` | Nível mínimo a reportar |
| `--format` | `text`\|`json` | `text` | Formato da saída |
| `--fail-on` | `critical`\|`error`\|`warning` | `error` | Exit 1 se houver issues neste nível |

### Prioridade de seleção de arquivos

Quando mais de um modo de seleção poderia se aplicar, o runner segue esta ordem:

1. `--file` — arquivo único especificado
2. `--scan` — varre diretório (`--dir` ou `.`)
3. _(padrão)_ — git diff (`--staged` ou `--base`)

---

## Saída — `--format text` (padrão)

```
# 🛡️ Code Guardian - Review

**Arquivos analisados**: 2
**Risk Score**: 35 — 🔴 Alto Risco

| Severidade | Qtd |
|-----------|-----|
| 🔴 Critical | 1  |
| 🟠 Error    | 2  |
| 🟡 Warning  | 3  |
| 🔵 Info     | 1  |

---

## 📁 `Services/UserService.cs`

### Issues Detectadas

- 🔴 **L42** [SQL_INJECTION_CONCAT] *[rule_engine]* Possível SQL Injection: query por concatenação.
- 🟠 **L87** [TASK_RESULT_DEADLOCK] *[rule_engine]* Task.Result pode causar deadlock. Use await.
- 🟡 **L1** [Metrics] *[metrics]* Classe com 7 dependências injetadas — possível God Class.

### Métricas

| Métrica        | Valor | Status |
|----------------|-------|--------|
| Linhas totais  | 412   | 🟡     |
| Maior método   | 45 L  | 🟠     |
| Nesting máximo | 5     | 🟠     |
| Dependências   | 7     | 🟡     |

### Análise de IA

[guardian] Usando Gemini (gemini-1.5-pro) para análise de IA...
[guardian] Análise concluída em 8.1s

## Bugs de Lógica
...

---
```

---

## Saída — `--format json` (para CI/CD)

```json
{
  "risk_score": 35,
  "risk_label": "🔴 Alto Risco",
  "has_blockers": true,
  "files_analyzed": ["Services/UserService.cs"],
  "summary": {
    "critical": 1,
    "error": 2,
    "warning": 3,
    "info": 1
  },
  "files": [
    {
      "file": "Services/UserService.cs",
      "issues": [
        {
          "file": "Services/UserService.cs",
          "line": 42,
          "severity": "critical",
          "category": "SQL_INJECTION_CONCAT",
          "rule_id": "SQL_INJECTION_CONCAT",
          "message": "Possível SQL Injection: query construída por concatenação.",
          "source": "rule_engine"
        }
      ],
      "metrics": {
        "file": "Services/UserService.cs",
        "total_lines": 412,
        "method_count": 14,
        "max_method_lines": 45,
        "max_nesting": 5,
        "constructor_deps": 7
      }
    }
  ]
}
```

---

## Relatórios HTML

O runner gera automaticamente um relatório HTML a cada execução (exceto `--format json`):

| Contexto | Arquivo gerado |
|----------|---------------|
| `python runner.py` (qualquer modo) | `.codeguardian/last-runner-report.html` |
| `--output relatorio.html` | caminho especificado |
| hook pre-commit | `.codeguardian/last-commit-report.html` |
| hook pre-push | `.codeguardian/last-push-report.html` |
| `python tests/run_tests.py` | `.codeguardian/last-test-report.html` |

O arquivo é sobrescrito a cada execução — representa sempre o estado mais recente.

```bash
# Gerar e abrir HTML explicitamente em caminho customizado
python runner.py --scan --output meu-relatorio.html

# HTML automático (sem --output) — salvo em .codeguardian/last-runner-report.html
python runner.py --staged --rules-only

# Sem HTML (CI/CD)
python runner.py --format json
```

> A pasta `.codeguardian/` está no `.gitignore`.

---

## Risk Score

| Pontuação | Classificação |
|-----------|---------------|
| 0–10 | ✅ Baixo Risco |
| 11–30 | ⚠️ Risco Moderado |
| 31–60 | 🔴 Alto Risco |
| > 60 | 🚫 Risco Crítico |

Pesos: `critical = 25 pts`, `error = 10 pts`, `warning = 3 pts`, `info = 1 pt`

---

## Exit codes

| Código | Condição |
|--------|----------|
| `0` | Nenhum bloqueador encontrado (conforme `--fail-on`) |
| `1` | Pelo menos um issue no nível `--fail-on` ou acima |
| `0` | Sem arquivos .cs para analisar |

```bash
# CI: bloquear se houver critical ou error
python code_guardian/runner.py --format json || echo "BLOQUEADO"

# Bloquear apenas em critical
python code_guardian/runner.py --fail-on critical || echo "CRÍTICO"
```

---

## Exemplos práticos

```bash
# Review rápido antes de commitar (staged, sem IA)
python code_guardian/runner.py --staged --rules-only

# Review completo do PR com IA
python code_guardian/runner.py --base origin/main

# Review de arquivo com saída mínima (só critical/error)
python code_guardian/runner.py --file Services/PedidoService.cs --severity error

# Review em JSON para pipeline CI/CD
python code_guardian/runner.py --format json --rules-only

# Review comparando com branch develop em vez de main
python code_guardian/runner.py --base origin/develop

# Análise completa de um projeto inteiro (sem git)
python code_guardian/runner.py --scan --rules-only

# Análise de projeto em outro diretório
python code_guardian/runner.py --scan --dir C:/projetos/MinhaApp --severity error

# Análise de projeto inteiro com IA e saída JSON
python code_guardian/runner.py --scan --dir ./src --format json
```

---

## Como é diferente dos scripts individuais

| Script individual | runner.py |
|-------------------|-----------|
| Analisa um arquivo por vez | Analisa todos os arquivos do diff |
| Retorna resultados de uma fonte | Consolida rule_engine + metrics + IA |
| Sem Risk Score | Calcula Risk Score total |
| Sem relatório formatado | Relatório em texto ou JSON |
| Exit code por script | Exit code unificado para CI |

O `runner.py` é o **ponto de entrada para CI/CD** e para uso manual quando você quer o review completo com um único comando.

---

## Documentação relacionada

| Documento | Conteúdo |
|-----------|----------|
| [08-Uso-rule-engine.md](08-Uso-rule-engine.md) | Regras disponíveis, severidades |
| [09-Uso-metrics.md](09-Uso-metrics.md) | Métricas calculadas |
| [10-Uso-diff-parser.md](10-Uso-diff-parser.md) | Como o diff é extraído |
| [11-Uso-ai-client.md](11-Uso-ai-client.md) | Provedores de IA, configuração |
| [14-TFS-Pipeline.md](14-TFS-Pipeline.md) | Como integrar no pipeline TFS |
