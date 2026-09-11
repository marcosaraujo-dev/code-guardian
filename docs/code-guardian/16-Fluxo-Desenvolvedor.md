# Guia do Desenvolvedor — Como Usar o Code Guardian no Dia a Dia

Este guia explica **quando e como** usar cada ferramenta do Code Guardian durante o desenvolvimento.

---

## Setup inicial (uma vez por repositório)

```bash
# 1. Verificar se Python 3.11+ está disponível
python --version

# 2. Instalar os git hooks (roda automaticamente antes de commit e push)
python code_guardian/install_hooks.py install

# 3. Confirmar instalação
python code_guardian/install_hooks.py status
```

Saída esperada:

```text
Hooks instalados:
  pre-commit   OK (Code Guardian)
  pre-push     OK (Code Guardian)
```

A partir daqui, a análise estática roda **automaticamente** a cada commit e push.

---

## Fluxo diário — com hooks instalados

```text
Você escreve o código
        ↓
git add Services/PedidoService.cs   ← adiciona ao stage
        ↓
git commit -m "feat: novo pagamento"
        ↓
  [Code Guardian verifica automaticamente]
  - Sem issues → commit salvo
  - Issues críticas → commit bloqueado, mensagem exibida
        ↓
git push origin feature/pagamentos
        ↓
  [Code Guardian verifica novamente — barreira final]
  - Sem issues → push enviado
  - Issues críticas → push bloqueado
```

---

## Analisar antes de fazer `git add` (opcional, proativo)

Se quiser ver problemas **antes mesmo de entrar no stage**:

```bash
# Analisar um arquivo específico
python code_guardian/runner.py --file Services/PedidoService.cs

# Ver só critical e error (mais rápido de ler)
python code_guardian/runner.py --file Services/PedidoService.cs --severity error

# Só análise estática, sem IA
python code_guardian/runner.py --file Services/PedidoService.cs --rules-only
```

---

## Analisar tudo que está no stage agora

```bash
# Ver quais arquivos estão no stage
git diff --cached --name-only

# Analisar todos os arquivos staged
python code_guardian/runner.py --staged

# Versão rápida (só análise estática)
python code_guardian/runner.py --staged --rules-only
```

---

## Analisar o diff completo do branch (simula o que a PR vai mostrar)

```bash
# Comparar com origin/main
python code_guardian/runner.py

# Comparar com outra branch base
python code_guardian/runner.py --base origin/develop
```

---

## Varrer um diretório completo — C#

Útil para auditar uma pasta inteira, analisar um módulo antes de mexer nele ou checar a base de código de um projeto legado.

```bash
# Varrer o diretório atual (todos os .cs encontrados recursivamente)
python code_guardian/runner.py --scan

# Varrer uma pasta específica
python code_guardian/runner.py --scan --dir src/
python code_guardian/runner.py --scan --dir Services/
python code_guardian/runner.py --scan --dir C:/projetos/MinhaApp/src

# Só análise estática, sem IA (mais rápido)
python code_guardian/runner.py --scan --dir src/ --rules-only

# Ver só erros críticos
python code_guardian/runner.py --scan --dir src/ --severity error

# Salvar resultado em arquivo
python code_guardian/runner.py --scan --dir src/ --rules-only > relatorio.txt
```

O scan percorre subpastas automaticamente e gera um **Risk Score consolidado** ao final.

---

## Comparar revisão com código atual — VB6 (`--compare`)

Para source control que coloca o código da branch de revisão em uma pasta temporária, use `--compare`. Ele compara as duas pastas arquivo por arquivo e analisa **apenas o que mudou** — arquivos idênticos são ignorados.

```bash
# Comparar pasta atual com a pasta da revisão
python code_guardian/vb6_rule_engine.py \
    --compare \
    --base  C:/projetos/SistemaFolha \
    --review C:/temp/revisao_branch

# Gerar relatório HTML com badges MODIFICADO / NOVO
python code_guardian/vb6_rule_engine.py \
    --compare \
    --base  C:/projetos/SistemaFolha \
    --review C:/temp/revisao_branch \
    --output .codeguardian/vb6-diff.html

# Ver só erros críticos no terminal
python code_guardian/vb6_rule_engine.py \
    --compare \
    --base  C:/projetos/SistemaFolha \
    --review C:/temp/revisao_branch \
    --format text --severity error
```

O que o `--compare` faz:
- **Arquivo idêntico** (mesmo conteúdo) → ignorado, sem análise
- **Arquivo modificado** (existe nos dois, conteúdo diferente) → analisado, marcado `✏️ MODIFICADO`
- **Arquivo novo** (só existe na revisão) → analisado, marcado `🆕 NOVO`

No relatório HTML, a tabela de arquivos exibe uma coluna extra com o badge de mudança.

---

## Varrer um diretório completo — VB6

```bash
# Varrer o diretório atual (todos os .bas/.cls/.frm/.ctl encontrados recursivamente)
python code_guardian/vb6_rule_engine.py --scan

# Varrer uma pasta específica
python code_guardian/vb6_rule_engine.py --scan --dir Views/
python code_guardian/vb6_rule_engine.py --scan --dir C:/projetos/SistemaVB6

# Gerar relatório HTML salvo em arquivo
python code_guardian/vb6_rule_engine.py --scan --dir Views/ --output .codeguardian/vb6-scan.html

# Ver só erros críticos (leitura rápida)
python code_guardian/vb6_rule_engine.py --scan --dir Views/ --format text --severity error

# Saída JSON (integração com outras ferramentas)
python code_guardian/vb6_rule_engine.py --scan --dir src/ --format json > scan.json
```

Ao final do scan, é exibido um resumo consolidado:

```text
────────────────────────────────────────────────────────────
VB6 Rule Engine — 47 arquivo(s) analisado(s)
Total: 312 issue(s) — 🔴 8 critical  🟠 41 error  🟡 215 warning  🔵 48 info
Score médio: 52 / 100 — High technical debt
```

---

## Usar o Code Review completo com IA no Claude Code

Dentro do Claude Code (IDE), execute:

```text
/code-review
```

Isso roda **análise estática + análise de IA** (o próprio Claude) e gera um relatório detalhado com:
- Issues por severidade
- Sugestões de correção com código
- Risk Score do PR
- Métricas de qualidade (tamanho de métodos, nesting, dependências)

Variações:

```text
/code-review --staged            → analisa só o que está no stage
/code-review --rules-only        → sem IA, mais rápido
/code-review --file Services/X.cs → arquivo específico
```

---

## O que cada ferramenta verifica

### Análise estática (`rule_engine.py`) — sempre roda, < 1 segundo

| Categoria | Exemplos |
| --------- | -------- |
| SQL Injection | `"SELECT * WHERE id = " + id` |
| Secrets hardcoded | `password = "MinhaSenh@123"` |
| Deadlock async | `.Result`, `.Wait()`, `async void` |
| Exception swallowing | `catch {}` vazio |
| Logging inadequado | `Console.WriteLine` em produção |
| Loop infinito | `while(true)` sem break |
| IDisposable sem using | `new HttpClient()` direto |

### Métricas (`metrics.py`) — sempre roda, < 1 segundo

| Métrica | Limite | O que sinaliza |
| ------- | ------ | -------------- |
| Linhas por método | > 30 | Método muito longo |
| Nesting | > 3 | Deep nesting |
| Dependências injetadas | > 5 | Possível God Class |
| Linhas totais no arquivo | > 300 | Arquivo grande |

### Análise de IA (`ai_client.py` ou Claude nativo) — opcional

- Bugs de lógica complexos (NullRef, race conditions, off-by-one)
- Segurança avançada (IDOR, Mass Assignment, Path Traversal)
- Performance (N+1 queries, LINQ em loops, materialização prematura)
- Conformidade com padrões do projeto (Result Pattern, logging obrigatório)

---

## Quando pular o hook (use com cautela)

```bash
# Hotfix urgente que precisa ir imediatamente
git commit --no-verify -m "hotfix: corrigir crash em produção"
git push --no-verify origin main
```

> O `--no-verify` pula **todos** os hooks do git, não só o Code Guardian.
> Documente o motivo no commit message quando usar.

---

## Interpretando os resultados

| Ícone | Nível | O que fazer |
| ----- | ----- | ----------- |
| 🔴 Critical | SQL Injection, secrets, corrupção de dados | **Corrigir antes de commitar** |
| 🟠 Error | Deadlock, null ref, exception swallowing | **Corrigir antes de commitar** |
| 🟡 Warning | Console.Write, magic numbers, método longo | Revisar — não bloqueia commit |
| 🔵 Info | TODOs, oportunidades de melhoria | Opcional |

**Risk Score do PR** (calculado pelo `/code-review`):

| Score | Classificação | O que fazer |
| ----- | ------------- | ----------- |
| 0–10 | ✅ Baixo Risco | PR pode ser aprovado |
| 11–30 | ⚠️ Risco Moderado | Review humano recomendado |
| 31–60 | 🔴 Alto Risco | Review humano obrigatório |
| > 60 | 🚫 Risco Crítico | Corrigir antes de abrir PR |

---

## Referência rápida de comandos

### C#

```bash
# Setup (uma vez)
python code_guardian/install_hooks.py install

# Arquivo específico
python code_guardian/runner.py --file Services/PedidoService.cs

# Staged files
python code_guardian/runner.py --staged --rules-only

# Scan de pasta
python code_guardian/runner.py --scan --dir src/
python code_guardian/runner.py --scan --dir C:/projetos/MinhaApp

# Review completo com IA no Claude Code
# /code-review

# Emergência — commitar sem verificação
git commit --no-verify -m "hotfix: ..."

# Desinstalar hooks
python code_guardian/install_hooks.py uninstall
```

### VB6

```bash
# Arquivo específico — relatório HTML (padrão)
python code_guardian/vb6_rule_engine.py frmCadastro.frm

# Arquivo específico — salvar HTML
python code_guardian/vb6_rule_engine.py frmCadastro.frm --output .codeguardian/review.html

# Scan de pasta — HTML salvo em arquivo
python code_guardian/vb6_rule_engine.py --scan --dir Views/ --output .codeguardian/vb6-scan.html

# Scan de pasta — texto rápido no terminal
python code_guardian/vb6_rule_engine.py --scan --dir Views/ --format text

# Só erros críticos
python code_guardian/vb6_rule_engine.py frmCadastro.frm --format text --severity error

# Comparação de revisão (source control com pasta temp)
python code_guardian/vb6_rule_engine.py \
    --compare --base C:/projetos/Sistema --review C:/temp/revisao \
    --output .codeguardian/vb6-diff.html

# Review completo com IA no Claude Code
# /vb6-code-review frmCadastro.frm
```

---

## Documentação relacionada

| Documento | Conteúdo |
| --------- | -------- |
| [15-Git-Hooks.md](15-Git-Hooks.md) | Detalhe dos hooks pre-commit e pre-push |
| [13-Runner-CLI.md](13-Runner-CLI.md) | Todos os parâmetros do runner.py |
| [14-TFS-Pipeline.md](14-TFS-Pipeline.md) | Análise automática em PRs no TFS |
| [00-Inicio-Rapido.md](00-Inicio-Rapido.md) | Visão geral do projeto |
