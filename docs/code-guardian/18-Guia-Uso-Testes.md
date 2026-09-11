# Guia de Uso — Testes e Scripts do Code Guardian

## Início Rápido

A partir da raiz do projeto (`C:\source\ideias\code_review\`), no **Prompt de Comando do Windows**:

```bat
:: Rodar todos os testes
test-guardian

:: Rodar code review em um arquivo
review --file MeuService.cs
```

---

## Scripts `.bat` disponíveis

Ficam na raiz do projeto. Funcionam de qualquer subdiretório, pois usam caminhos relativos ao próprio `.bat`.

### `test-guardian.bat` — Suite de Testes

Executa os testes automatizados do Code Guardian.

```bat
:: Todos os testes (72 casos)
test-guardian

:: Apenas um script específico
test-guardian re     :: rule_engine.py  — regras de detecção
test-guardian me     :: metrics.py      — métricas de qualidade
test-guardian dp     :: diff_parser.py  — extração de diffs git
test-guardian ai     :: ai_client.py    — cliente de IA
test-guardian ru     :: runner.py       — orquestrador
```

**Saída esperada (todos os testes):**
```
Code Guardian — Suite de Testes Automatizados
Base: C:\...\code_guardian
Fixtures: C:\...\code_guardian\tests\fixtures

── TC-RE  rule_engine.py ──────────────────────
  ✅ TC-RE-001: SQL Injection por concatenacao (+)
  ✅ TC-RE-002: Exit code 1 quando ha critical
  ...

=================================================================
  RESULTADO FINAL: 72/72 PASSOU  |  0 FALHOU
=================================================================
```

**Exit codes:**
- `0` — todos os testes passaram
- `1` — um ou mais testes falharam (detalhes listados no final)

---

### `review.bat` — Code Review

Executa o Code Guardian em arquivos C#. Todos os argumentos são repassados diretamente ao `runner.py`.

```bat
:: Arquivo específico (busca automática pelo nome)
review --file FuncionarioService.cs

:: Arquivo específico com caminho parcial
review --file Services/FuncionarioService.cs

:: Sem IA (apenas regras e métricas — mais rápido)
review --file FuncionarioService.cs --rules-only

:: Apenas arquivos staged no git
review --staged

:: Diff em relação a uma branch
review --base origin/develop

:: Controlar qual severidade bloqueia (padrão: error)
review --file MeuService.cs --fail-on critical

:: Filtrar issues exibidas (padrão: info — exibe tudo)
review --file MeuService.cs --severity warning

:: Saída JSON (para CI/CD ou integração)
review --file MeuService.cs --format json
```

---

## Scripts Python diretamente

Se preferir chamar os scripts sem os `.bat`, execute a partir de qualquer diretório passando o caminho completo:

```bat
python .claude\scripts\code_guardian\tests\run_tests.py
python .claude\scripts\code_guardian\runner.py --file MeuService.cs
```

Ou entre no diretório dos scripts:

```bat
cd .claude\scripts\code_guardian
python tests\run_tests.py
python runner.py --file MeuService.cs
```

---

## Estrutura dos Testes

```
code_guardian/
├── tests/
│   ├── run_tests.py              ← Suite principal (72 casos)
│   ├── test_should_include.py    ← Teste unitário do diff_parser
│   └── fixtures/                 ← Arquivos .cs de entrada para os testes
│       ├── clean.cs              ← Sem problemas (linha de base)
│       ├── sql_injection.cs      ← SQL por concatenação e interpolação
│       ├── deadlock.cs           ← .Result e .Wait() em async
│       ├── async_void.cs         ← async void fora de event handler
│       ├── secrets.cs            ← Senha e API key hardcoded
│       ├── empty_catch.cs        ← catch vazio
│       ├── god_class.cs          ← 7 deps + 12 métodos públicos
│       ├── deep_nesting.cs       ← Nesting de 6 níveis
│       ├── long_methods.cs       ← Método com > 30 linhas
│       ├── console_warning.cs    ← Console.WriteLine / Console.Write
│       ├── todo_comment.cs       ← TODO, FIXME, HACK
│       ├── httpclient_new.cs     ← new HttpClient() sem factory
│       ├── event_handler.cs      ← async void em event handler (não deve disparar)
│       └── comment_false_positive.cs ← Padrões em comentários (não deve disparar)
```

### IDs dos Casos de Teste

| Prefixo | Script testado       | Quantidade |
|---------|----------------------|------------|
| TC-RE   | rule_engine.py       | 25         |
| TC-ME   | metrics.py           | 14         |
| TC-DP   | diff_parser.py       | 11         |
| TC-AI   | ai_client.py         | 8          |
| TC-RU   | runner.py            | 18         |
| **Total** |                    | **72**     |

---

## O que cada script testa

### `rule_engine.py` (TC-RE)
Verifica se as 25 regras de detecção funcionam corretamente:
- SQL Injection por concatenação e interpolação
- Deadlocks async (`.Result`, `.Wait()`)
- `async void` em método comum (mas não em event handlers)
- Secrets hardcoded (senha, API key)
- Empty catch
- Console.Write / Console.WriteLine
- TODO / FIXME / HACK em comentários
- `new HttpClient()` sem factory
- Filtro de severidade (`--severity`)
- Ausência de falsos positivos em comentários
- Arquivo inexistente retorna `FILE_NOT_FOUND`

### `metrics.py` (TC-ME)
Verifica o cálculo de métricas de qualidade:
- Método longo (> 30 linhas) com nome correto na mensagem
- Deep nesting (> 3 níveis) com valor reportado
- God Class por dependências injetadas (> 5)
- God Class por métodos públicos (> 10)
- Arquivo limpo não gera issues
- Estrutura JSON completa (`file`, `total_lines`, `classes`, `issues`)

### `diff_parser.py` (TC-DP)
Verifica a extração de arquivos alterados do git:
- Filtro de arquivos excluídos (`/Migrations/`, `.Designer.cs`, `/obj/`, `/bin/`, `AssemblyInfo.cs`)
- Apenas arquivos `.cs` são incluídos
- `--staged` sem staged retorna lista vazia
- `--files-only --staged` sem staged retorna exit 1
- Formatos de saída (`json`, `text`, `--for-ai`)

### `ai_client.py` (TC-AI)
Verifica o cliente de IA (todos funcionam sem API key):
- `--list-providers` lista os provedores disponíveis
- Arquivo inexistente retorna exit 1
- JSON contém `ai_available`, `provider`, `model`, `analysis`
- Exit code sempre 0 mesmo sem IA configurada

### `runner.py` (TC-RU)
Verifica o orquestrador completo:
- `--file` com nome simples (busca automática por `rglob`)
- `--file` com caminho completo
- `--fail-on critical/error/warning` controla o exit code
- `--severity` filtra as issues exibidas
- `--rules-only` exclui análise de IA
- Métricas não aparecem zeradas na saída JSON
- `risk_score` e `risk_label` calculados corretamente
- `has_blockers` correto para cada cenário

---

## Adicionando novos testes

1. **Criar a fixture** em `tests/fixtures/NomeDoArquivo.cs` com o código C# mínimo que representa o cenário.

2. **Adicionar o caso** na função correspondente em `tests/run_tests.py`:

```python
def test_rule_engine():
    # ...
    # TC-RE-026 — Novo caso
    code, out, _ = run([PY, RULE_ENGINE, f("minha_fixture.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-026", "Descricao do que estou testando",
          ok and contains_rule(data, "MINHA_REGRA"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
```

3. **Rodar apenas o script afetado** para validar rapidamente:

```bat
test-guardian re
```

---

## Interpretando falhas

Quando um caso falha, o relatório final lista o motivo:

```
=================================================================
  RESULTADO FINAL: 71/72 PASSOU  |  1 FALHOU
=================================================================

Casos que falharam:
  ❌ TC-RE-013: Detecta TODO_COMMENT
     rules=['NO_RESULT_PATTERN']
```

O campo após `>>>` mostra o que foi recebido. Use para diagnosticar:
- **`exit=`** — exit code obtido vs esperado
- **`rules=`** — quais rule_ids foram encontrados
- **`data=`** — conteúdo JSON retornado
- **`saida=`** — primeiros 200-300 caracteres da saída texto
