# diff_parser.py — Extrator de Arquivos Alterados do Git

## O que faz

Consulta o repositório git e extrai **quais arquivos `.cs` foram alterados** e **quais linhas mudaram**, com contexto ao redor para análise.

Usado principalmente para alimentar o `rule_engine.py` e o `ai_client.py` com apenas os arquivos do PR/commit atual, evitando analisar o repositório inteiro.

Filtra automaticamente arquivos gerados: Migrations, `obj/`, `bin/`, `.Designer.cs`, `.g.cs`.

---

## Entrada

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--staged` | flag | — | Analisa apenas arquivos em staging area (`git add`) |
| `--base <branch>` | string | `origin/main` | Branch base para comparação |
| `--files-only` | flag | — | Retorna apenas lista de arquivos, sem linhas |
| `--for-ai` | flag | — | Formata saída legível para prompt de IA |
| `--format` | `json` \| `text` | `json` | Formato da saída |

> Sem flags: compara `HEAD` com `origin/main` (comportamento padrão para PR review).

---

## Modos de operação

### Modo branch (padrão)
Compara o branch atual com `origin/main`. Ideal para revisar tudo que será mergeado.

```bash
python code_guardian/diff_parser.py
```

### Modo staged
Compara apenas os arquivos que estão no `git stage`. Ideal para review antes do commit.

```bash
python code_guardian/diff_parser.py --staged
```

### Modo com branch base diferente
```bash
python code_guardian/diff_parser.py --base origin/develop
```

---

## Saída — `--files-only --format text`

Lista de caminhos, um por linha:

```
Services/UserService.cs
Controllers/UsersController.cs
Repositories/UserRepository.cs
```

---

## Saída — `--files-only --format json`

Array de strings:

```json
[
  "Services/UserService.cs",
  "Controllers/UsersController.cs",
  "Repositories/UserRepository.cs"
]
```

---

## Saída — `--for-ai`

Formato otimizado para colar em prompts de IA, com indicação de linhas adicionadas (`+`) e contexto (` `):

```
=== Services/UserService.cs (12 linhas adicionadas) ===

+ L  23:     public async Task<User> CreateUserAsync(CreateUserRequest request)
+ L  24:     {
  L  25:         var user = new User { Name = request.Name };
+ L  26:         var result = _context.ExecuteQuery("SELECT * FROM users WHERE id = " + request.Id);
  L  27:         return user;
+ L  28:     }
```

---

## Saída — `--format json` (padrão)

Array de objetos com detalhamento por arquivo:

```json
[
  {
    "file": "Services/UserService.cs",
    "lines_added": 12,
    "changes": [
      {
        "file": "Services/UserService.cs",
        "line": 23,
        "content": "    public async Task<User> CreateUserAsync(CreateUserRequest request)",
        "change_type": "added"
      },
      {
        "file": "Services/UserService.cs",
        "line": 24,
        "content": "    {",
        "change_type": "added"
      },
      {
        "file": "Services/UserService.cs",
        "line": 25,
        "content": "        var user = new User { Name = request.Name };",
        "change_type": "context"
      }
    ]
  }
]
```

### Campos do objeto raiz

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `file` | string | Caminho relativo do arquivo |
| `lines_added` | int | Total de linhas novas neste arquivo |
| `changes` | array | Linhas alteradas + contexto |

### Campos de `changes[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `file` | string | Caminho do arquivo |
| `line` | int | Número da linha no arquivo destino (pós-alteração) |
| `content` | string | Conteúdo da linha (sem o prefixo `+` ou espaço do diff) |
| `change_type` | string | `"added"` (linha nova) ou `"context"` (linha de contexto ao redor) |

---

## Saída — `--format text`

```
📁 Services/UserService.cs (+12 linhas)
   L23:     public async Task<User> CreateUserAsync(CreateUserRequest request)
   L24:     {
   L26:         var result = _context.ExecuteQuery("SELECT * + request.Id);
   ... e mais 8 linhas

📊 Total: 3 arquivo(s) | 28 linha(s) adicionada(s)
```

---

## Exit codes

| Código | Condição |
|--------|----------|
| `0` | Arquivos encontrados (modo `--files-only`) |
| `1` | Nenhum arquivo `.cs` alterado encontrado (modo `--files-only`) |
| `0` | Sempre, nos demais modos |

O exit code `1` no modo `--files-only` é útil para condicionais em shell scripts:

```bash
if python code_guardian/diff_parser.py --files-only --format text; then
    echo "Há arquivos C# para revisar"
else
    echo "Nenhum arquivo C# alterado — pulando review"
fi
```

---

## Exemplos de uso

```bash
# Ver quais arquivos serão analisados no PR atual
python code_guardian/diff_parser.py --files-only --format text

# Ver diff completo com contexto para análise manual
python code_guardian/diff_parser.py --format text

# Gerar entrada formatada para um prompt de IA
python code_guardian/diff_parser.py --for-ai

# Review antes do commit (apenas staged)
python code_guardian/diff_parser.py --staged --files-only --format text

# Comparar com develop em vez de main
python code_guardian/diff_parser.py --base origin/develop --format text
```

### Pipeline típico: diff → rule_engine

```bash
# Obter arquivos alterados e analisar cada um
FILES=$(python code_guardian/diff_parser.py --files-only --format text)

for FILE in $FILES; do
    echo "=== Analisando: $FILE ==="
    python code_guardian/rule_engine.py "$FILE" --format text
done
```

---

## Arquivos excluídos automaticamente

O parser ignora:

| Padrão | Motivo |
|--------|--------|
| `/Migrations/` | Arquivos gerados pelo EF Core |
| `.Designer.cs` | Arquivos gerados por designers WinForms/WPF |
| `/obj/` | Artefatos de build |
| `/bin/` | Binários compilados |
| `/packages/` | Pacotes NuGet |
| `AssemblyInfo.cs` | Metadados de assembly gerados |
| `.g.cs` | Arquivos gerados (Razor, Source Generators) |
| `.g.i.cs` | Arquivos gerados (intellisense) |
| `TemporaryGeneratedFile` | Arquivos temporários gerados |

---

## Uso como módulo Python

```python
from .claude.scripts.code_guardian.diff_parser import get_changed_files, parse_diff, format_diff_for_ai

# Apenas lista de arquivos
files = get_changed_files(mode="branch", base="origin/main")
print(files)  # ["Services/UserService.cs", ...]

# Com detalhamento de linhas
summaries = parse_diff(mode="staged")
for s in summaries:
    print(f"{s.file}: {s.lines_added} linhas adicionadas")
    added_lines = [c for c in s.lines_changed if c.change_type == "added"]

# Formatar para IA
diff_text = format_diff_for_ai(summaries)
# usar diff_text como parte de um prompt
```

---

## Limitações

- Requer que `git` esteja instalado e acessível no PATH
- No modo `branch` (padrão), faz `git fetch origin main` — requer acesso à rede/TFS
- O contexto ao redor de cada mudança é de **3 linhas** (padrão `--unified=3` do git)
- Só processa arquivos `.cs` — outros tipos (`.json`, `.csproj`) são ignorados
