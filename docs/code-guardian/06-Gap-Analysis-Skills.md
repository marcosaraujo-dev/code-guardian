# Gap Analysis - Skills de Code Review

## Skills Existentes vs Necessidades do Code Guardian

### O que já existe (4 skills de review)

| Skill | Foco | Cobre |
|-------|------|-------|
| `clean-code-review` | SRP, métodos curtos, naming, nesting, magic numbers, DRY | Padrões de código |
| `anti-patterns-detector` | God Class, Spaghetti Code, Feature Envy, complexidade ciclomática | Code smells |
| `backend-best-practices` | API design, DI, async/await, segurança, Rich Domain | Arquitetura backend |
| `architecture-patterns` | Camadas, Design Patterns, Use Cases, SOLID | Arquitetura geral |

### O que FALTA (gaps identificados)

```
┌────────────────────────────────────────────────────────────────────┐
│                    GAPS NAS SKILLS ATUAIS                          │
│                                                                     │
│  ❌ BUGS DE LÓGICA (nenhuma skill cobre especificamente)           │
│     • NullReferenceException                                       │
│     • Loops infinitos (análise de fluxo, não regex)                │
│     • Deadlocks async (contexto, não só .Result)                   │
│     • Race conditions                                              │
│     • Off-by-one errors                                            │
│     • Condições sempre true/false                                  │
│     • Fluxo impossível / código morto                              │
│     • IDisposable não disposto                                     │
│     • Uso incorreto de LINQ (side effects, materialização)         │
│                                                                     │
│  ❌ SEGURANÇA APROFUNDADA                                          │
│     • SQL Injection (padrões complexos, EF Core raw queries)       │
│     • XSS em APIs                                                  │
│     • IDOR (Insecure Direct Object Reference)                      │
│     • Mass Assignment                                              │
│     • Insecure Deserialization                                     │
│     • Path Traversal                                               │
│     • Weak Cryptography                                            │
│                                                                     │
│  ❌ PERFORMANCE APROFUNDADA                                        │
│     • N+1 queries (padrões EF Core/Dapper)                         │
│     • Materialização prematura (ToList antes de Where)             │
│     • Alocações excessivas                                         │
│     • String concat em loops                                       │
│     • Falta de CancellationToken                                   │
│     • Boxing/Unboxing desnecessário                                │
│                                                                     │
│  ❌ SKILL ORQUESTRADORA                                            │
│     • Skill que executa TODAS as análises em sequência             │
│     • Consolida resultados num relatório unificado                 │
│     • Calcula Risk Score                                           │
│                                                                     │
│  ❌ SKILL COM SCRIPTS                                              │
│     • Skill que executa scripts Python via Bash tool               │
│     • Rule Engine automatizado (não depende de IA para padrões)    │
│     • Métricas automatizadas (linhas/método, nesting, deps)        │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Proposta: 4 Novas Skills para Code Guardian

### 1. `csharp-logic-bugs` (NOVA - Prioridade Alta)

**Foco**: Detecção de bugs de lógica e runtime em C#.

**Por que é necessária**: As skills existentes focam em padrões/estilo. Esta foca em **bugs que causam crash ou comportamento incorreto em produção**.

**Categorias de detecção**:

```markdown
## NullReferenceException
Detectar:
- Acesso a propriedade/método de variável sem null-check
- Retorno de método que pode ser null usado sem verificação
- Desreferência após cast com `as` sem null-check
- FirstOrDefault()/SingleOrDefault() usado sem null-check
- Acesso a .Value de Nullable<T> sem HasValue
- Parâmetros de método não validados para null
- Navigation properties do EF Core acessadas sem Include

Exemplos:
```csharp
// ❌ BUG: user pode ser null
var user = await _repo.GetByIdAsync(id);
var name = user.Name; // NullReferenceException!

// ✅ CORRETO
var user = await _repo.GetByIdAsync(id);
if (user is null) return Result.Failure("Usuário não encontrado");
var name = user.Name;
```

## Loops Infinitos
Detectar:
- while(true) sem break/return dentro do bloco
- for sem condição de saída alcançável
- Recursão sem caso base
- Loop com condição que nunca muda
- do-while com condição sempre true

## Deadlocks Async
Detectar:
- Task.Result em contexto com SynchronizationContext
- Task.Wait() em async method
- async void (exceto event handlers)
- ConfigureAwait(false) faltando em library code
- Lock dentro de async method (usar SemaphoreSlim)
- Mistura de sync/async no mesmo call stack

## Race Conditions
Detectar:
- Variável compartilhada (static, singleton) sem lock
- Dictionary/List acessado por múltiplas threads
- Check-then-act sem atomicidade
- Lazy<T> com LazyThreadSafetyMode.None
- Event handlers sem null-check thread-safe

## IDisposable
Detectar:
- new de IDisposable sem using
- SqlConnection, HttpClient, StreamReader sem dispose
- IDisposable em campo de classe sem implementar IDisposable
- DbContext usado após dispose

## Fluxo e Lógica
Detectar:
- Condição sempre true/false (código morto)
- Switch sem default case
- Enum com valor não coberto
- Off-by-one: < vs <=, array bounds
- Comparação de float/double com == (usar epsilon)
- String comparison sem StringComparison
```

---

### 2. `csharp-security-review` (NOVA - Prioridade Alta)

**Foco**: Vulnerabilidades de segurança em código C#/.NET.

```markdown
## SQL Injection
Detectar:
- String interpolation/concatenação em queries SQL
- EF Core FromSqlRaw com concatenação
- Dapper com string interpolation
- ADO.NET sem SqlParameter
- Stored procedure chamada com concatenação

Exemplos:
```csharp
// ❌ SQL Injection
var query = $"SELECT * FROM Users WHERE Email = '{email}'";
var users = context.Users.FromSqlRaw($"SELECT * FROM Users WHERE Name = '{name}'");

// ✅ Seguro
var users = context.Users.FromSqlInterpolated($"SELECT * FROM Users WHERE Name = {name}");
var users = connection.Query<User>("SELECT * FROM Users WHERE Email = @Email", new { Email = email });
```

## Secrets Hardcoded
Detectar:
- Strings que parecem API keys (padrões conhecidos)
- Connection strings no código
- Passwords em appsettings.json commitado
- JWT secret keys no código
- Certificados base64 inline

## Mass Assignment
Detectar:
- [FromBody] direto para Entity (sem DTO)
- AutoMapper de Request para Entity sem configuração
- Bind de todos os campos sem [Bind] attribute
- Atualização de campos sensíveis (IsAdmin, Role) via input

## Authentication/Authorization
Detectar:
- Endpoint sem [Authorize]
- Verificação de ownership faltando (IDOR)
- Comparação de senhas em plain text
- Token sem expiração
- CORS com "*" em produção

## Outros
Detectar:
- Path.Combine com input do usuário (Path Traversal)
- Deserialization de tipos arbitrários (BinaryFormatter)
- Regex sem timeout (ReDoS)
- XML parsing sem proteção contra XXE
- Redirect sem validação de URL (Open Redirect)
```

---

### 3. `csharp-performance-review` (NOVA - Prioridade Média)

**Foco**: Problemas de performance em código C#/.NET.

```markdown
## N+1 Queries
Detectar:
- Query dentro de foreach/for
- Acesso a navigation property sem Include/ThenInclude
- Multiple queries que poderiam ser um JOIN
- Count() seguido de ToList() (duas queries)

Exemplos:
```csharp
// ❌ N+1: 1 query para users + N queries para orders
var users = await _context.Users.ToListAsync();
foreach (var user in users)
{
    var orders = await _context.Orders.Where(o => o.UserId == user.Id).ToListAsync();
}

// ✅ Eager loading: 1 query
var users = await _context.Users.Include(u => u.Orders).ToListAsync();
```

## LINQ Performance
Detectar:
- ToList()/ToArray() antes de Where/Select (materialização prematura)
- LINQ dentro de foreach/for
- OrderBy sem índice correspondente
- Contains() em lista grande (usar HashSet)
- Any() vs Count() > 0

## Alocações
Detectar:
- String concatenação em loop (usar StringBuilder)
- new List<T>() em loop (criar fora)
- Boxing de value types (int → object)
- Closures em hot paths capturando variáveis
- params array desnecessário

## Async Performance
Detectar:
- Falta de CancellationToken em métodos async
- await em loop sequencial (usar Task.WhenAll)
- async/await desnecessário (return Task direto)
- ConfigureAwait(false) faltando em library code

## Caching
Detectar:
- Dados estáticos buscados do banco a cada request
- Configurações relidas do arquivo a cada chamada
- Falta de ResponseCache em endpoints de consulta
```

---

### 4. `code-review` (NOVA - Skill Orquestradora)

**Foco**: Orquestra TODAS as análises (scripts + IA) e gera relatório consolidado.

Esta é a skill principal que o desenvolvedor invoca com `/code-review`.

```markdown
## Fluxo da Skill Orquestradora

1. DETECTAR ESCOPO
   - Argumento = arquivo? → analisar só esse
   - --staged? → git diff --cached
   - Sem args? → git diff origin/main...HEAD

2. EXECUTAR SCRIPTS (via Bash tool)
   - python scripts/code_guardian/diff_parser.py
   - python scripts/code_guardian/rule_engine.py <arquivo>
   - python scripts/code_guardian/metrics.py <arquivo>

3. EXECUTAR ANÁLISE IA (o próprio Claude)
   - Ler cada arquivo via Read tool
   - Invocar checklist de csharp-logic-bugs
   - Invocar checklist de csharp-security-review
   - Invocar checklist de csharp-performance-review

4. EXECUTAR SKILLS EXISTENTES (conforme necessidade)
   - Se .cs → clean-code-review, backend-best-practices
   - Se .xaml → wpf-review-code
   - Se .tsx → react-best-practices

5. CONSOLIDAR
   - Unificar issues de todas as fontes
   - Deduplicar (mesmo arquivo + linha)
   - Calcular Risk Score

6. GERAR RELATÓRIO
   - Formato markdown estruturado
   - Tabela resumo
   - Detalhamento por arquivo
   - Sugestões de correção
```

---

## Resumo: Skills Antes e Depois

```
ANTES (4 skills de review):                DEPOIS (8 skills de review):
─────────────────────────                  ──────────────────────────────

✅ clean-code-review                       ✅ clean-code-review
   (padrões, naming, SRP)                     (padrões, naming, SRP)

✅ anti-patterns-detector                  ✅ anti-patterns-detector
   (code smells, God Class)                   (code smells, God Class)

✅ backend-best-practices                  ✅ backend-best-practices
   (API, DI, async, Rich Domain)              (API, DI, async, Rich Domain)

✅ architecture-patterns                   ✅ architecture-patterns
   (camadas, SOLID, patterns)                 (camadas, SOLID, patterns)

❌ (gap) bugs de lógica               →   🆕 csharp-logic-bugs
                                              (NullRef, deadlock, loop, race)

❌ (gap) segurança aprofundada        →   🆕 csharp-security-review
                                              (SQLi, XSS, IDOR, secrets)

❌ (gap) performance aprofundada      →   🆕 csharp-performance-review
                                              (N+1, LINQ, alloc, cache)

❌ (gap) orquestração                 →   🆕 code-review
                                              (scripts + IA, Risk Score)
```

---

## Plano de Criação das Skills

### Fase 1 - Fundação (Scripts + Orquestrador)
1. Criar `scripts/code_guardian/rule_engine.py`
2. Criar `scripts/code_guardian/diff_parser.py`
3. Criar `scripts/code_guardian/metrics.py`
4. Criar skill `code-review` (orquestradora)
5. Testar end-to-end com Claude Code

### Fase 2 - Skills de Análise Profunda
1. Criar skill `csharp-logic-bugs`
2. Criar skill `csharp-security-review`
3. Criar skill `csharp-performance-review`
4. Integrar com skill `code-review` (orquestradora)

### Fase 3 - Refinamento
1. Testar com código real do Prosoft
2. Calibrar falsos positivos
3. Adicionar exemplos específicos do projeto
4. Documentar padrões encontrados

---

## Relação com Agentes Existentes

As novas skills complementam os agentes existentes:

```
Agente                              Skills que pode usar
──────────────────────────          ─────────────────────────────────
senior-code-reviewer          →     clean-code-review
                                    anti-patterns-detector
                                    🆕 code-review (orquestradora)

senior-backend-developer-csharp →   backend-best-practices
                                    architecture-patterns
                                    🆕 csharp-logic-bugs
                                    🆕 csharp-security-review
                                    🆕 csharp-performance-review

wpf-code-reviewer              →   wpf-review-code
                                    wpf-check-antipatterns
                                    🆕 csharp-logic-bugs (para ViewModels)
```

A skill `code-review` é a **entrada principal** que decide quais outras skills usar baseado no tipo de arquivo e contexto.
