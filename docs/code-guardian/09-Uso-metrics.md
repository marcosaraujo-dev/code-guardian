# metrics.py — Métricas de Qualidade de Código

## O que faz

Analisa um arquivo `.cs` calculando **métricas estruturais** de qualidade.
Não usa IA — execução offline e instantânea.

Detecta: métodos longos, nesting profundo, possíveis God Classes,
classes com excesso de dependências ou métodos públicos.

---

## Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `<arquivo.cs>` | caminho | Sim | Arquivo C# a analisar |
| `--format` | `json` \| `text` | Não (padrão: `json`) | Formato da saída |

---

## Limiares de qualidade

| Métrica | Limite | Severidade ao ultrapassar |
|---------|--------|--------------------------|
| Linhas por método | 30 | `warning` |
| Nesting máximo | 3 níveis | `warning` |
| Dependências no construtor | 5 | `warning` (possível God Class) |
| Métodos públicos por classe | 10 | `warning` (possível God Class) |
| Total de linhas do arquivo | 300 | `info` |

---

## Saída — Formato `text`

```
📊 Métricas: Services/UserService.cs
   Total de linhas: 412

   Classe: UserService
   ├─ Métodos: 14 (públicos: 12)
   ├─ Dependências injetadas: 7
   └─ Nesting máximo: 5

   Métodos longos (2):
   🟡 CreateUserAsync (~48 linhas, L23)
   🟡 ValidateAndProcessOrder (~35 linhas, L89)

   Issues (4):
   🟡 L  1 [God Class] Classe com 7 dependências injetadas (máximo recomendado: 5). Possível God Class — avaliar SRP.
   🟡 L  1 [God Class] Classe com 12 métodos públicos (máximo recomendado: 10). Considerar separar em Use Cases.
   🟡 L  1 [Deep Nesting] Nível máximo de nesting: 5 (máximo recomendado: 3). Usar guard clauses e early return.
   🔵 L  1 [Arquivo Grande] Arquivo com 412 linhas (máximo recomendado: 300). Avaliar separação de responsabilidades.
```

Dentro dos padrões:
```
📊 Métricas: Services/UserService.cs
   Total de linhas: 87

   Classe: UserService
   ├─ Métodos: 4 (públicos: 3)
   ├─ Dependências injetadas: 2
   └─ Nesting máximo: 2

   ✅ Métricas dentro dos padrões recomendados.
```

---

## Saída — Formato `json`

```json
{
  "file": "Services/UserService.cs",
  "total_lines": 412,
  "classes": [
    {
      "name": "UserService",
      "start_line": 1,
      "line_count": 412,
      "methods": [
        {
          "name": "CreateUserAsync",
          "start_line": 23,
          "line_count": 48,
          "is_public": true
        },
        {
          "name": "ValidateAndProcessOrder",
          "start_line": 89,
          "line_count": 35,
          "is_public": false
        }
      ],
      "constructor_deps": 7,
      "public_method_count": 12,
      "max_nesting": 5
    }
  ],
  "issues": [
    {
      "line": 23,
      "severity": "warning",
      "category": "Método Longo",
      "message": "Método 'CreateUserAsync' tem aproximadamente 48 linhas (máximo recomendado: 30). Extrair em métodos menores."
    },
    {
      "line": 1,
      "severity": "warning",
      "category": "God Class",
      "message": "Classe com 7 dependências injetadas (máximo recomendado: 5). Possível God Class — avaliar SRP."
    },
    {
      "line": 1,
      "severity": "warning",
      "category": "God Class",
      "message": "Classe com 12 métodos públicos (máximo recomendado: 10). Considerar separar em Use Cases."
    },
    {
      "line": 1,
      "severity": "warning",
      "category": "Deep Nesting",
      "message": "Nível máximo de nesting: 5 (máximo recomendado: 3). Usar guard clauses e early return."
    },
    {
      "line": 1,
      "severity": "info",
      "category": "Arquivo Grande",
      "message": "Arquivo com 412 linhas (máximo recomendado: 300). Avaliar separação de responsabilidades."
    }
  ]
}
```

### Campos raiz

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `file` | string | Caminho do arquivo analisado |
| `total_lines` | int | Total de linhas do arquivo |
| `classes` | array | Lista de classes detectadas (uma por arquivo) |
| `issues` | array | Lista de issues de qualidade detectadas |

### Campos de `classes[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `name` | string | Nome da classe (derivado do nome do arquivo) |
| `start_line` | int | Linha inicial |
| `line_count` | int | Total de linhas da classe |
| `methods` | array | Lista de métodos detectados |
| `constructor_deps` | int | Número de dependências injetadas (campos `private readonly`) |
| `public_method_count` | int | Número de métodos públicos |
| `max_nesting` | int | Nível máximo de chaves aninhadas |

### Campos de `methods[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `name` | string | Nome do método |
| `start_line` | int | Linha de declaração do método |
| `line_count` | int | Número de linhas (aproximado, até o próximo método) |
| `is_public` | bool | `true` se o método é público |

### Campos de `issues[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `line` | int | Linha de referência (1 para issues de arquivo/classe) |
| `severity` | string | `warning` ou `info` |
| `category` | string | `"Método Longo"`, `"Deep Nesting"`, `"God Class"`, `"Arquivo Grande"` |
| `message` | string | Descrição com os valores medidos e recomendados |

---

## Exit codes

| Código | Condição |
|--------|----------|
| `0` | Nenhuma issue detectada |
| `1` | Pelo menos uma issue detectada (qualquer severidade) |

---

## Exemplos de uso

```bash
# Análise básica (saída JSON)
python code_guardian/metrics.py Services/UserService.cs

# Saída legível no terminal
python code_guardian/metrics.py Services/UserService.cs --format text

# Integrado com jq para filtrar apenas God Classes
python code_guardian/metrics.py Services/UserService.cs \
  | python -c "import json,sys; d=json.load(sys.stdin); [print(i['message']) for i in d['issues'] if i['category']=='God Class']"
```

---

## Uso como módulo Python

```python
from .claude.scripts.code_guardian.metrics import analyze_file

result = analyze_file("Services/UserService.cs")

print(f"Linhas: {result.total_lines}")
for cls in result.classes:
    print(f"Classe: {cls.name}")
    print(f"  Deps: {cls.constructor_deps}, Métodos: {cls.public_method_count}")
    long_methods = [m for m in cls.methods if m.line_count > 30]
    for m in long_methods:
        print(f"  ⚠️  {m.name}: {m.line_count} linhas")
```

---

## Limitações

- Detecção de métodos é **heurística** — baseada em regex de assinatura, não em parsing completo
- `line_count` de métodos é **aproximado** (até a declaração do próximo método, não até o `}` real)
- Uma classe por arquivo — não detecta múltiplas classes no mesmo `.cs`
- Dependências contadas por campos `private readonly` — não conta injeção via propriedade ou método
