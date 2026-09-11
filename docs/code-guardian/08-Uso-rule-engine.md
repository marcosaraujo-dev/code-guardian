# rule_engine.py — Detecção de Padrões Problemáticos

## O que faz

Analisa um arquivo `.cs` aplicando **20+ regras** baseadas em regex e busca textual.
Não usa IA — execução instantânea e offline.

Detecta: SQL Injection, secrets hardcoded, deadlocks async, exception swallowing,
magic numbers, loops infinitos, `HttpClient` mal usado, ausência do Result Pattern.

---

## Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `<arquivo.cs>` | caminho | Sim | Arquivo C# a analisar |
| `--format` | `json` \| `text` | Não (padrão: `json`) | Formato da saída |
| `--severity` | `critical` \| `error` \| `warning` \| `info` | Não (padrão: `info`) | Nível mínimo a reportar |

---

## Saída — Formato `text`

```
📁 Services/UserService.cs

  🔴 L  42 [SQL Injection] Possível SQL Injection: query construída por concatenação/interpolação. Use queries parametrizadas.
  🟠 L  87 [Deadlock Async] Task.Result pode causar deadlock em contextos com SynchronizationContext. Use await.
  🟡 L 134 [Logging] Console.WriteLine em produção polui stdout. Use ILogger com nível apropriado.
  🔵 L 201 [Padrões do Projeto] Método async retornando Task<T> sem Result<T>. Considere usar Result Pattern.

Rule Engine: 4 issue(s) encontrada(s) — 🔴 1 critical  🟠 1 error  🟡 1 warning  🔵 1 info
```

Sem problemas:
```
✅ Services/UserService.cs: Nenhum problema encontrado pelo Rule Engine.
```

---

## Saída — Formato `json`

Array de objetos `Issue`. Array vazio `[]` se nenhum problema encontrado.

```json
[
  {
    "file": "Services/UserService.cs",
    "line": 42,
    "severity": "critical",
    "category": "SQL Injection",
    "rule_id": "SQL_INJECTION_CONCAT",
    "message": "Possível SQL Injection: query construída por concatenação/interpolação. Use queries parametrizadas.",
    "source": "rule_engine"
  },
  {
    "file": "Services/UserService.cs",
    "line": 87,
    "severity": "error",
    "category": "Deadlock Async",
    "rule_id": "TASK_RESULT_DEADLOCK",
    "message": "Task.Result pode causar deadlock em contextos com SynchronizationContext (ASP.NET, WPF). Use await.",
    "source": "rule_engine"
  }
]
```

### Campos do objeto Issue

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `file` | string | Caminho do arquivo analisado |
| `line` | int | Número da linha onde o problema foi detectado |
| `severity` | string | `critical`, `error`, `warning` ou `info` |
| `category` | string | Categoria do problema (ex: "SQL Injection") |
| `rule_id` | string | Identificador único da regra disparada |
| `message` | string | Descrição do problema com sugestão de correção |
| `source` | string | Sempre `"rule_engine"` (para diferenciação de outras fontes) |

---

## Exit codes

| Código | Condição |
|--------|----------|
| `0` | Nenhum problema encontrado, ou apenas `warning` e `info` |
| `1` | Pelo menos um `critical` ou `error` detectado |

Útil em scripts de CI para bloquear merge automaticamente.

---

## Exemplos de uso

```bash
# Análise básica (saída JSON, todos os níveis)
python code_guardian/rule_engine.py Services/UserService.cs

# Saída legível no terminal
python code_guardian/rule_engine.py Services/UserService.cs --format text

# Apenas erros graves (critical + error)
python code_guardian/rule_engine.py Services/UserService.cs --severity error

# Em CI/CD — bloquear se houver critical ou error
python code_guardian/rule_engine.py Services/UserService.cs
echo "Exit code: $?"   # 0 = ok, 1 = bloqueado
```

---

## Regras disponíveis

### CRITICAL — Bloqueiam merge

| ID | Categoria | O que detecta |
|----|-----------|---------------|
| `SQL_INJECTION_CONCAT` | SQL Injection | Query SQL construída com `+` ou `$"...{var}..."` |
| `SQL_INJECTION_FROMSQLRAW` | SQL Injection | `FromSqlRaw($"...")` no EF Core |
| `HARDCODED_PASSWORD` | Secrets Hardcoded | `password = "..."` com string longa |
| `HARDCODED_API_KEY` | Secrets Hardcoded | `apiKey = "..."`, `token = "..."` com valor longo |
| `HARDCODED_CONNECTION_STRING` | Secrets Hardcoded | `ConnectionString = "..."` com valor longo |

### ERROR — Devem ser corrigidos

| ID | Categoria | O que detecta |
|----|-----------|---------------|
| `TASK_RESULT_DEADLOCK` | Deadlock Async | Uso de `.Result` em Task |
| `TASK_WAIT_DEADLOCK` | Deadlock Async | Uso de `.Wait()` em Task |
| `ASYNC_VOID` | Async Incorreto | Métodos `async void` (exceto event handlers) |
| `EMPTY_CATCH` | Exception Handling | Bloco `catch {}` vazio |
| `INFINITE_WHILE` | Loop Infinito | `while(true)` sem break visível |
| `THREAD_SLEEP` | Performance | `Thread.Sleep(...)` em código async |

### WARNING — Devem ser revisados

| ID | Categoria | O que detecta |
|----|-----------|---------------|
| `CONSOLE_WRITELINE` | Logging | `Console.WriteLine` em código de produção |
| `CONSOLE_WRITE` | Logging | `Console.Write(` em código de produção |
| `MAGIC_NUMBER_COMPARISON` | Magic Numbers | Comparações com números >= 3 dígitos |
| `GETAWAITER_GETRESULT` | Deadlock Async | `.GetAwaiter().GetResult()` |
| `OBJECT_DISPOSABLE_NOUSE` | IDisposable | Conexão de banco criada sem `using` |
| `HTTPCLIENT_NEW` | IDisposable | `new HttpClient()` direto (socket exhaustion) |

### INFO — Oportunidades de melhoria

| ID | Categoria | O que detecta |
|----|-----------|---------------|
| `TODO_COMMENT` | Code Quality | `// TODO` no código |
| `FIXME_COMMENT` | Code Quality | `// FIXME` no código |
| `HACK_COMMENT` | Code Quality | `// HACK` no código |
| `NO_RESULT_PATTERN` | Padrões do Projeto | `Task<T>` público sem `Result<T>` |

---

## Uso como módulo Python

```python
from .claude.scripts.code_guardian.rule_engine import analyze_file

issues = analyze_file("Services/UserService.cs", min_severity="error")

for issue in issues:
    print(f"L{issue.line} [{issue.severity}] {issue.message}")

has_blockers = any(i.severity in ("critical", "error") for i in issues)
```

---

## Limitações

- Análise baseada em **padrões de texto** — não faz parsing semântico do código C#
- Pode gerar falsos positivos em comentários (mitigado por verificação de contexto)
- Não detecta bugs de lógica complexos — para isso, usar `ai_client.py`
- Uma regra regex pode não capturar todas as variações de um padrão
